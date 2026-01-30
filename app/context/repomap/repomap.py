import fnmatch
import logging
import os
from collections import Counter, defaultdict
from pathlib import Path

import aiofiles
import networkx as nx
from grep_ast import TreeContext, filename_to_lang
from grep_ast.tsl import get_language, get_parser
from tree_sitter import QueryCursor

from app.context.exceptions import RepoMapExtractionException
from app.context.schemas import Tag
from app.core.config import settings

logger = logging.getLogger(__name__)


class RepoMap:
    """
    Generates a context-aware map of the repository using Tree-sitter.

    It builds a dependency graph of definitions and references across all files,
    ranks them using PageRank, and generates a compact text representation
    to aid the LLM in understanding the codebase structure.
    """

    def __init__(
        self,
        all_files: list[str],
        active_context_files: list[str],
        mentioned_filenames: set[str] | None = None,
        mentioned_idents: set[str] | None = None,
        ignore_patterns: list[str] | None = None,
        token_limit: int = 4096,
        include_definitions: bool = True,
        root: str | None = None,
    ):
        self.root = root
        self.ignore_patterns = ignore_patterns or []
        self.all_files = self._filter_ignored_files(sorted(all_files))
        self.active_context_files = set(active_context_files)
        self.mentioned_filenames = mentioned_filenames or set()
        self.mentioned_idents = mentioned_idents or set()
        self.token_limit = token_limit
        self.include_definitions = include_definitions
        self.queries_dir = Path(settings.queries_dir)

    def _filter_ignored_files(self, files: list[str]) -> list[str]:
        if not self.ignore_patterns:
            return files

        filtered = []
        for f in files:
            rel_path = self._get_rel_path(f)
            if not any(
                fnmatch.fnmatch(rel_path, pattern) for pattern in self.ignore_patterns
            ):
                filtered.append(f)
        return filtered

    async def generate(self, include_active_content: bool = True) -> str:
        """
        Generates the repository map string.
        """
        output_parts = []
        current_tokens = 0

        header = "### Repository Map\n"
        output_parts.append(header)
        current_tokens += self._estimate_token_count(header)

        current_tokens = self._add_file_structure(output_parts, current_tokens)

        if include_active_content:
            current_tokens = await self._add_active_files_content(
                output_parts, current_tokens
            )

        if self.include_definitions:
            await self._add_ranked_definitions(output_parts, current_tokens)

        return "".join(output_parts)

    @staticmethod
    def _estimate_token_count(text: str) -> int:
        """Approximation of token count."""
        # todo it is a mock
        return len(text) // 4

    def _add_file_structure(self, output_parts: list[str], current_tokens: int) -> int:
        """
        Adds a flat list of files to ensure structure is visible even if ranking fails.
        """
        header = "#### File Structure\n"
        temp_parts = [header]
        temp_tokens = self._estimate_token_count(header)

        for file_path in self.all_files:
            rel_path = self._get_rel_path(file_path)
            line = f"{rel_path}\n"
            line_tokens = self._estimate_token_count(line)

            temp_parts.append(line)
            temp_tokens += line_tokens

        # Ensures the text is actually added to the output
        output_parts.extend(temp_parts)
        output_parts.append("\n")
        return current_tokens + temp_tokens + 1

    def _get_rel_path(self, file_path: str) -> str:
        """
        Returns path relative to root.
        """
        try:
            return os.path.relpath(file_path, self.root)
        except ValueError:
            return file_path

    def get_top_level_structure(self) -> list[str]:
        rel_files = [self._get_rel_path(f) for f in self.all_files]
        top_level = set()
        for f in rel_files:
            parts = f.split(os.sep)
            if len(parts) > 1:
                top_level.add(parts[0] + "/")
            else:
                top_level.add(parts[0])
        return sorted(top_level)

    def format_top_level_structure(self) -> str:
        header = "### Repository Map\n#### File Structure\n"
        return header + "\n".join(self.get_top_level_structure()) + "\n"

    async def extract_tags(self, file_path: str) -> list[Tag]:
        """
        Extracts definitions and references from a file using Tree-sitter.
        Raises RepoMapExtractionException on failure.
        """
        lang = filename_to_lang(file_path)
        if not lang:
            return []

        scm_path = self.queries_dir / f"{lang}-tags.scm"
        if not scm_path.exists():
            # logger.warning(f"RepoMap: Tag query file not found for {lang} at {scm_path}")
            return []

        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                code = await f.read()

            if not code:
                return []

            language = get_language(lang)
            parser = get_parser(lang)
            tree = parser.parse(bytes(code, "utf8"))

            query_scm = scm_path.read_text()
            query = language.query(query_scm)
            captures = QueryCursor(query).captures(tree.root_node)

            all_nodes = []
            for tag, nodes in captures.items():
                all_nodes.extend([(node, tag) for node in nodes])

            tags = []
            for node, tag_name in all_nodes:
                kind = None
                if tag_name.startswith("name.definition"):
                    kind = "def"
                elif tag_name.startswith("name.reference"):
                    kind = "ref"

                if kind:
                    tags.append(
                        Tag(
                            name=node.text.decode("utf8"),
                            kind=kind,
                            line=node.start_point[0],
                        )
                    )

            return tags

        except Exception as e:
            raise RepoMapExtractionException(
                f"Failed to extract tags from {file_path}: {str(e)}"
            ) from e

    async def _rank_files(
        self,
    ) -> tuple[dict[str, float], dict[tuple[str, str], list[Tag]]]:
        """
        Builds a dependency graph and runs PageRank to identify important files and definitions.
        """
        defines = defaultdict(set)
        references = defaultdict(list)
        definitions = defaultdict(list)

        # collect Tags
        for file_path in self.all_files:
            rel_path = self._get_rel_path(file_path)
            try:
                tags = await self.extract_tags(file_path)
            except RepoMapExtractionException as e:
                logger.warning(str(e))
                continue
            for tag in tags:
                if tag.kind == "def":
                    defines[tag.name].add(rel_path)
                    definitions[(rel_path, tag.name)].append(tag)
                elif tag.kind == "ref":
                    references[tag.name].append(rel_path)

        # build Graph
        graph = nx.MultiDiGraph()

        # Add self-edges for definitions (ensures they have some weight even without refs)
        for name, definers in defines.items():
            for definer in definers:
                graph.add_edge(definer, definer, weight=0.1, ident=name)

        # Add edges from referencer's to definers
        idents = set(defines.keys()).intersection(set(references.keys()))

        active_rel_paths = {self._get_rel_path(f) for f in self.active_context_files}
        mentioned_rel_paths = {self._get_rel_path(f) for f in self.mentioned_filenames}

        for ident in idents:
            definers = defines[ident]

            # Weight boosting heuristics
            mul = 1.0
            if ident.startswith("_"):
                mul *= 0.1  # Downweight private members

            if ident in self.mentioned_idents:
                mul *= 10.0

            # Distribute references
            for referencer, num_refs in Counter(references[ident]).items():
                for definer in definers:
                    # Boost if referenced by active context
                    weight = mul * num_refs
                    if referencer in active_rel_paths:
                        weight *= 10.0
                    if referencer in mentioned_rel_paths:
                        weight *= 10.0

                    graph.add_edge(referencer, definer, weight=weight, ident=ident)

        if not graph.nodes:
            return {}, definitions

        try:
            ranked = nx.pagerank(graph, weight="weight")
        except Exception as e:
            logger.error(f"RepoMap: PageRank calculation failed: {e}")
            return {}, definitions

        return ranked, definitions

    async def _add_active_files_content(
        self, output_parts: list[str], current_tokens: int
    ) -> int:
        """
        Adds full content of active files.
        """
        if not self.active_context_files:
            return current_tokens

        header = "#### Active Context\n"
        if current_tokens + self._estimate_token_count(header) >= self.token_limit:
            return current_tokens

        output_parts.append(header)
        current_tokens += self._estimate_token_count(header)

        for file_path in sorted(self.active_context_files):
            rel_path = self._get_rel_path(file_path)
            try:
                async with aiofiles.open(file_path, encoding="utf-8") as f:
                    content = await f.read()

                header = f"{rel_path}:\n"
                ext = Path(rel_path).suffix.lstrip(".")
                block = f"```{ext}\n{content}\n```\n"

                tokens = self._estimate_token_count(header + block)
                if current_tokens + tokens > self.token_limit:
                    continue

                output_parts.append(header + block)
                current_tokens += tokens
            except Exception as e:
                logger.warning(f"RepoMap: Could not read active file {file_path}: {e}")
                continue

        return current_tokens

    async def _add_ranked_definitions(
        self, output_parts: list[str], current_tokens: int
    ) -> None:
        """
        Adds ranked snippets from the repository.
        """
        ranked_files, definitions = await self._rank_files()
        if not ranked_files:
            return

        header = "#### Ranked Definitions\n"
        if current_tokens + self._estimate_token_count(header) > self.token_limit:
            return
        output_parts.append(header)
        current_tokens += self._estimate_token_count(header)

        # Sort files by rank
        sorted_files = sorted(ranked_files.items(), key=lambda x: x[1], reverse=True)

        # Active files are already added in full, so we skip them here
        active_rel_paths = {self._get_rel_path(f) for f in self.active_context_files}

        for rel_path, _rank in sorted_files:
            if rel_path in active_rel_paths:
                continue

            # Get all tags for this file
            file_tags = []
            for (f, _name), tags in definitions.items():
                if f == rel_path:
                    file_tags.extend(tags)

            if not file_tags:
                continue

            # Identify lines of interest (definitions)
            lois = sorted({tag.line for tag in file_tags})

            try:
                abs_path = os.path.join(self.root, rel_path)
                async with aiofiles.open(abs_path, encoding="utf-8") as f:
                    code = await f.read()

                tc = TreeContext(rel_path, code)
                tc.add_lines_of_interest(lois)
                tc.add_context()
                snippet = tc.format()

                entry = f"{rel_path}:\n{snippet}\n"
                entry_tokens = self._estimate_token_count(entry)

                if current_tokens + entry_tokens > self.token_limit:
                    output_parts.append(
                        "\n... (remaining definitions truncated due to token limit)\n"
                    )
                    return

                output_parts.append(entry)
                current_tokens += entry_tokens
            except Exception as e:
                logger.error(f"RepoMap: Error generating snippet for {rel_path}: {e}")
