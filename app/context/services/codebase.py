import glob
import aiofiles
import aiofiles.os
from pathlib import Path
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from app.context.schemas import FileReadResult, FileStatus, FileTreeNode

SCAN_ALL_PATTERN = ["."]


class _IgnoreMatcher:
    """Internal helper for gitignore pattern matching."""
    DEFAULT_PATTERNS = [
        ".git", ".idea/", ".vscode/", ".venv/", "node_modules/", "__pycache__/", ".env",
        "*.pyc", "*.log", ".DS_Store", "Thumbs.db", "*.svg", "*.pdf", "*.png", "*.jpg"
    ]

    @staticmethod
    def matches(spec: PathSpec, path: str, is_dir: bool = False) -> bool:
        check_path = f"{path}/" if is_dir else path
        return spec.match_file(check_path)

    async def get_spec(self, project_root: str) -> PathSpec:
        root = Path(project_root)
        gitignore_path = root / ".gitignore"
        lines = self.DEFAULT_PATTERNS[:]

        if await aiofiles.os.path.exists(gitignore_path):
            async with aiofiles.open(gitignore_path, "r") as f:
                content = await f.read()
                lines.extend(content.splitlines())

        return PathSpec.from_lines(GitWildMatchPattern, lines)


class CodebaseService:
    """
    Service for interacting with the physical codebase (file system).
    Acts as a facade for file scanning, reading, and tree building.
    """

    def __init__(self):
        self.matcher = _IgnoreMatcher()

    @staticmethod
    def _is_subpath(root: Path, path: Path) -> bool:
        """Checks if path is a subpath of root."""
        return path.resolve().is_relative_to(root.resolve())

    async def validate_file_path(self, project_root: str, file_path: str, must_exist: bool = True) -> Path:
        """
        Validates that a file is safe to access (inside root) and not ignored.
        STRICT MODE: Raises ValueError if invalid.
        Returns the absolute Path object.
        """
        root = Path(project_root).resolve()
        path = Path(file_path)

        # 1. Security: Resolve and ensure inside root
        abs_path = path.resolve() if path.is_absolute() else (root / path).resolve()

        if not self._is_subpath(root, abs_path):
            raise ValueError(f"Access denied: '{file_path}' is outside project root.")

        # Calculate canonical relative path for correct gitignore matching
        rel_path = abs_path.relative_to(root)

        # 2. Existence Check
        if must_exist and (not abs_path.exists() or not abs_path.is_file()):
            raise ValueError(f"File not found or invalid: '{file_path}'")

        # 3. Ignore Check
        if await self.is_file_ignored(project_root, str(rel_path)):
            raise ValueError(f"Access denied: '{file_path}' is ignored by project configuration.")

        return abs_path

    async def is_file_ignored(self, project_root: str, file_path: str) -> bool:
        """Checks if a file matches gitignore rules."""
        root = Path(project_root).resolve()
        spec = await self.matcher.get_spec(project_root)
        
        path = Path(file_path)
        if path.is_absolute():
            try:
                path = path.resolve().relative_to(root)
            except ValueError:
                return False
                
        return self.matcher.matches(spec, str(path), is_dir=False)

    async def _collect_files(self, project_root: Path, path: Path, spec: PathSpec) -> set[str]:
        """
        Collects valid files from a path (file or directory), respecting ignores.
        """
        files = set()

        async def _scan_dir(current_dir: Path):
            try:
                entries = await aiofiles.os.listdir(current_dir)
            except OSError:
                return

            for entry in entries:
                full_path = current_dir / entry
                try:
                    rel_path = full_path.relative_to(project_root)
                    is_dir = await aiofiles.os.path.isdir(full_path)
                    
                    if self.matcher.matches(spec, str(rel_path), is_dir=is_dir):
                        continue

                    if is_dir:
                        if not await aiofiles.os.path.islink(full_path):
                            await _scan_dir(full_path)
                    else:
                        files.add(str(rel_path))
                except ValueError:
                    continue

        if path.is_file():
            file_rel_path = path.relative_to(project_root)
            if not self.matcher.matches(spec, str(file_rel_path), is_dir=False):
                files.add(str(file_rel_path))
        elif path.is_dir():
            await _scan_dir(path)
            
        return files

    async def list_dir(self, project_root: str, dir_path: str = ".") -> list[str]:
        """
        Lists contents of a directory, respecting ignores.
        Returns list of names (appended with / for dirs).
        """
        root = Path(project_root).resolve()
        spec = await self.matcher.get_spec(project_root)

        target_path = (root / dir_path).resolve()
        
        if not self._is_subpath(root, target_path):
             raise ValueError(f"Access denied: '{dir_path}' is outside project root.")
             
        if not target_path.exists() or not target_path.is_dir():
            raise ValueError(f"Directory not found: '{dir_path}'")

        try:
            entries = sorted(await aiofiles.os.listdir(target_path))
        except OSError as e:
            raise ValueError(f"Error reading directory: {e}")

        results = []
        for entry in entries:
            full_path = target_path / entry
            rel_path = full_path.relative_to(root)
            is_dir = await aiofiles.os.path.isdir(full_path)
            
            if not self.matcher.matches(spec, str(rel_path), is_dir=is_dir):
                suffix = "/" if is_dir else ""
                results.append(f"{entry}{suffix}")

        return results

    async def read_file(self, project_root: str, file_path: str, must_exist: bool = True) -> FileReadResult:
        """
        Reads content of a single file returning structured result.
        """
        try:
            abs_path = await self.validate_file_path(project_root, file_path, must_exist=must_exist)

            if not abs_path.exists():
                # If we are here, must_exist=False (otherwise validate would have raised)
                # In case file doesn't exist, we just return empty as success in order for it to be created
                return FileReadResult(file_path=file_path, content="", status=FileStatus.SUCCESS)

            async with aiofiles.open(abs_path, "r", encoding="utf-8") as f:
                content = await f.read()
                return FileReadResult(file_path=file_path, content=content, status=FileStatus.SUCCESS)
        except UnicodeDecodeError:
            return FileReadResult(file_path=file_path, status=FileStatus.BINARY)
        except ValueError as e:
            # Validation failed (ignored or outside root)
            return FileReadResult(file_path=file_path, status=FileStatus.ERROR, error_message=str(e))
        except Exception as e:
            return FileReadResult(file_path=file_path, status=FileStatus.ERROR, error_message=str(e))

    async def read_files(self, project_root: str, file_paths: list[str]) -> list[FileReadResult]:
        """
        Reads content of multiple files returning structured results.
        """
        results = []
        for fp in file_paths:
            results.append(await self.read_file(project_root, fp))
        return results

    async def resolve_file_patterns(self, project_root: str, patterns: list[str] | None = None) -> list[str]:
        """Resolves globs to relative file paths."""
        root = Path(project_root).resolve()
        spec = await self.matcher.get_spec(project_root)
        results = set()

        if not patterns:
            patterns = SCAN_ALL_PATTERN

        for pattern in patterns:
            full_pattern = str(root / pattern)

            if not self._is_subpath(root, Path(full_pattern)):
                raise ValueError(f"Access denied: Pattern '{pattern}' targets outside project root.")

            matched_paths = glob.glob(full_pattern, recursive=True)
            
            for p in matched_paths:
                path_obj = Path(p)
                
                files = await self._collect_files(root, path_obj, spec)
                results.update(files)

        return sorted(list(results))

    async def build_file_tree(self, project_root: str) -> list[FileTreeNode]:
        """
        Builds a pure domain representation of the file tree.
        No UI logic (selected state) here.
        """
        root = Path(project_root).resolve()
        spec = await self.matcher.get_spec(project_root)

        async def _recurse(current_path: Path) -> list[FileTreeNode]:
            try:
                entries = sorted(await aiofiles.os.listdir(current_path))
            except PermissionError:
                return []

            nodes = []
            for entry in entries:
                full_path = current_path / entry
                rel_path = full_path.relative_to(root)
                rel_path_str = str(rel_path.as_posix())

                is_dir = await aiofiles.os.path.isdir(full_path)
                if self.matcher.matches(spec, rel_path_str, is_dir=is_dir):
                    continue

                node = FileTreeNode(
                    name=entry,
                    path=rel_path_str,
                    is_dir=is_dir
                )

                if is_dir and not await aiofiles.os.path.islink(full_path):
                    children = await _recurse(full_path)
                    # Only add directories if they are not empty (optional preference)
                    if children:
                        node.children = children
                        nodes.append(node)
                else:
                    nodes.append(node)

            # Sort folders first, then files
            return sorted(nodes, key=lambda x: (not x.is_dir, x.name.lower()))

        return await _recurse(root)

    async def filter_and_resolve_paths(self, project_root: str, file_paths: list[str]) -> set[str]:
        """
        Filters a list of relative paths, removing ignored or unsafe files.
        LENIENT MODE: Skips invalid files instead of raising errors.
        Returns a set of absolute resolved paths.
        """
        valid_abs_paths = set()

        for fp in file_paths:
            try:
                # Reuse the strict validator, but catch the error to skip
                abs_path = await self.validate_file_path(project_root, fp, must_exist=True)
                valid_abs_paths.add(str(abs_path))
            except ValueError:
                # Explicitly skip invalid, unsafe, or ignored files
                continue
                
        return valid_abs_paths

    async def write_file(self, project_root: str, file_path: str, content: str) -> None:
        """
        Writes content to a file, ensuring the path is valid and safe.
        """
        abs_path = await self.validate_file_path(project_root, file_path, must_exist=False)
        await aiofiles.os.makedirs(abs_path.parent, exist_ok=True)
        async with aiofiles.open(abs_path, "w", encoding="utf-8") as f:
            await f.write(content)