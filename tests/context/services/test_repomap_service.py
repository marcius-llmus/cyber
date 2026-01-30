import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.context.exceptions import RepoMapExtractionException
from app.context.repomap.repomap import RepoMap
from app.context.services.repomap import RepoMapService
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.models import Project


@pytest.fixture
def service(
    workspace_service_mock,
    codebase_service_mock,
    project_service_mock,
):
    return RepoMapService(
        workspace_service_mock, codebase_service_mock, project_service_mock
    )


async def test_generate_repo_map_no_project(
    service, project_service_mock, settings_snapshot
):
    project_service_mock.get_active_project = AsyncMock(return_value=None)
    with pytest.raises(ActiveProjectRequiredException):
        await service.generate_repo_map(
            session_id=1,
            token_limit=settings_snapshot.ast_token_limit,
        )


async def test_generate_repo_map_success(
    service,
    workspace_service_mock,
    codebase_service_mock,
    project_service_mock,
    mocker,
    settings_snapshot,
):
    # 1. Setup Mocks
    project = Project(id=1, name="p", path="/tmp/proj")
    project_service_mock.get_active_project = AsyncMock(return_value=project)

    # Codebase returns relative paths
    codebase_service_mock.resolve_file_patterns = AsyncMock(
        return_value=["src/main.py", "README.md"]
    )

    # Context returns absolute paths
    workspace_service_mock.get_active_file_paths_abs = AsyncMock(
        return_value=["/tmp/proj/src/main.py"]
    )

    # Mentioned files resolution
    codebase_service_mock.filter_and_resolve_paths = AsyncMock(
        return_value={"/tmp/proj/other.py"}
    )

    settings_snapshot.ast_token_limit = 2000

    # Patch RepoMap
    repomap_cls = mocker.patch("app.context.services.repomap.RepoMap")
    repomap_instance = repomap_cls.return_value
    repomap_instance.generate = AsyncMock(return_value="Repo Map Content")

    # 2. Execute
    result = await service.generate_repo_map(
        session_id=1,
        mentioned_filenames={"other.py"},
        mentioned_idents={"Foo", "Bar"},
        include_active_content=False,
        mode=settings_snapshot.repomap_mode,
        token_limit=settings_snapshot.ast_token_limit,
        ignore_patterns_str="*.log\nnode_modules/\n",
    )

    # 3. Assert
    assert result == "Repo Map Content"

    # Check constructor call
    repomap_cls.assert_called_once()
    _, kwargs = repomap_cls.call_args
    assert kwargs["root"] == "/tmp/proj"
    assert "/tmp/proj/src/main.py" in kwargs["all_files"]
    assert "/tmp/proj/README.md" in kwargs["all_files"]
    assert kwargs["active_context_files"] == ["/tmp/proj/src/main.py"]
    assert kwargs["mentioned_filenames"] == {"/tmp/proj/other.py"}
    assert kwargs["mentioned_idents"] == {"Foo", "Bar"}
    assert kwargs["token_limit"] == 2000
    assert kwargs["ignore_patterns"] == ["*.log", "node_modules/"]

    repomap_instance.generate.assert_awaited_once_with(include_active_content=False)

    project_service_mock.get_active_project.assert_awaited_once_with()
    codebase_service_mock.resolve_file_patterns.assert_awaited_once_with("/tmp/proj")
    workspace_service_mock.get_active_file_paths_abs.assert_awaited_once_with(
        1, "/tmp/proj"
    )
    codebase_service_mock.filter_and_resolve_paths.assert_awaited_once_with(
        "/tmp/proj", ["other.py"]
    )


async def test_repomap_extract_tags_unknown_extension_returns_empty(
    repomap_instance, repomap_tmp_project
):
    tags = await repomap_instance.extract_tags(repomap_tmp_project["unknown"])
    assert tags == []


async def test_repomap_extract_tags_empty_file_returns_empty(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    empty_py = root / "empty.py"
    empty_py.write_text("", encoding="utf-8")
    rm = RepoMap(all_files=[str(empty_py)], active_context_files=[], root=str(root))

    tags = await rm.extract_tags(str(empty_py))
    assert tags == []


async def test_repomap_extract_tags_python_finds_definitions_and_references(
    repomap_instance, repomap_tmp_project
):
    defs_tags = await repomap_instance.extract_tags(repomap_tmp_project["defs"])
    names_kinds = {(t.name, t.kind) for t in defs_tags}

    assert ("core", "def") in names_kinds
    assert ("MyClass", "def") in names_kinds

    use1_tags = await repomap_instance.extract_tags(repomap_tmp_project["use1"])
    use1_names_kinds = {(t.name, t.kind) for t in use1_tags}

    assert ("core", "ref") in use1_names_kinds
    assert ("MyClass", "ref") in use1_names_kinds


async def test_repomap_extract_tags_non_existent_file_raises_exception(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    missing = root / "missing.py"
    rm = RepoMap(all_files=[str(missing)], active_context_files=[], root=str(root))

    with pytest.raises(RepoMapExtractionException, match="Failed to extract tags"):
        await rm.extract_tags(str(missing))


async def test_repomap_rank_files_empty_repo_returns_empty_rankings(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    f = root / "a.py"
    f.write_text("x = 1\n", encoding="utf-8")
    rm = RepoMap(all_files=[str(f)], active_context_files=[], root=str(root))

    ranked, defs = await rm._rank_files()
    assert ranked == {}
    assert defs == {}


async def test_repomap_rank_files_ranks_defining_file_higher_when_referenced(
    repomap_instance, repomap_tmp_project
):
    ranked, _definitions = await repomap_instance._rank_files()
    defs_rel = os.path.relpath(repomap_tmp_project["defs"], repomap_tmp_project["root"])

    assert defs_rel in ranked
    assert ranked[defs_rel] == max(ranked.values())


async def test_repomap_rank_files_private_ident_downweighted(repomap_tmp_project):
    rm = RepoMap(
        all_files=[
            repomap_tmp_project["public_defs"],
            repomap_tmp_project["hidden_defs"],
            repomap_tmp_project["refs_equal"],
        ],
        active_context_files=[],
        mentioned_idents=set(),
        mentioned_filenames=set(),
        root=repomap_tmp_project["root"],
        token_limit=10_000,
    )

    ranked, _definitions = await rm._rank_files()

    public_rel = os.path.relpath(
        repomap_tmp_project["public_defs"], repomap_tmp_project["root"]
    )
    hidden_rel = os.path.relpath(
        repomap_tmp_project["hidden_defs"], repomap_tmp_project["root"]
    )

    assert ranked[public_rel] > ranked[hidden_rel]


async def test_repomap_rank_files_mentioned_idents_boost_overrides_private_downweight(
    repomap_tmp_project,
):
    rm = RepoMap(
        all_files=[
            repomap_tmp_project["public_defs"],
            repomap_tmp_project["hidden_defs"],
            repomap_tmp_project["refs_equal"],
        ],
        active_context_files=[],
        mentioned_idents={"_hidden2"},
        mentioned_filenames=set(),
        root=repomap_tmp_project["root"],
        token_limit=10_000,
    )

    ranked, _definitions = await rm._rank_files()

    public_rel = os.path.relpath(
        repomap_tmp_project["public_defs"], repomap_tmp_project["root"]
    )
    hidden_rel = os.path.relpath(
        repomap_tmp_project["hidden_defs"], repomap_tmp_project["root"]
    )

    assert ranked[hidden_rel] >= ranked[public_rel]


async def test_repomap_generate_includes_structure_active_context_and_ranked_definitions(
    repomap_tmp_project,
):
    rm = RepoMap(
        all_files=[
            repomap_tmp_project["defs"],
            repomap_tmp_project["use1"],
            repomap_tmp_project["use2"],
        ],
        active_context_files=[repomap_tmp_project["use1"]],
        mentioned_filenames=set(),
        mentioned_idents=set(),
        token_limit=10_000,
        root=repomap_tmp_project["root"],
    )

    out = await rm.generate(include_active_content=True)

    assert "### Repository Map" in out
    assert "#### File Structure" in out
    assert "#### Active Context" in out
    assert "#### Ranked Definitions" in out
    assert "```py" in out
    assert "core" in out


async def test_repomap_generate_include_active_content_false_omits_active_context(
    repomap_tmp_project,
):
    rm = RepoMap(
        all_files=[
            repomap_tmp_project["defs"],
            repomap_tmp_project["use1"],
        ],
        active_context_files=[repomap_tmp_project["use1"]],
        root=repomap_tmp_project["root"],
        token_limit=10_000,
    )

    out = await rm.generate(include_active_content=False)
    assert "#### Active Context" not in out


async def test_repomap_generate_does_not_truncate_file_structure_by_token_limit(
    repomap_tmp_project,
):
    root = repomap_tmp_project["root"]
    many_files = []
    for i in range(200):
        p = Path(root) / f"f{i}.py"
        p.write_text("x = 1\n", encoding="utf-8")
        many_files.append(str(p))

    rm = RepoMap(
        all_files=many_files,
        active_context_files=[],
        root=root,
        token_limit=25,
    )
    out = await rm.generate(include_active_content=False)
    assert "... (file list truncated" not in out


async def test_repomap_format_top_level_structure_includes_repo_map_and_file_structure_headers(
    repomap_tmp_project,
):
    rm = RepoMap(
        all_files=[
            repomap_tmp_project["defs"],
            repomap_tmp_project["use1"],
        ],
        active_context_files=[],
        root=repomap_tmp_project["root"],
    )

    out = rm.format_top_level_structure()

    assert out.startswith("### Repository Map\n#### File Structure\n")
    assert "src/" in out


async def test_repomap_generate_ranked_definitions_truncates_with_notice(
    repomap_tmp_project,
):
    # Small limit to force truncation during ranked definitions.
    rm = RepoMap(
        all_files=[
            repomap_tmp_project["defs"],
            repomap_tmp_project["use1"],
            repomap_tmp_project["use2"],
            repomap_tmp_project["public_defs"],
            repomap_tmp_project["hidden_defs"],
            repomap_tmp_project["refs_equal"],
        ],
        active_context_files=[],
        root=repomap_tmp_project["root"],
        token_limit=60,
    )
    out = await rm.generate(include_active_content=False)
    assert "#### Ranked Definitions" in out
    assert "... (remaining definitions truncated due to token limit)" in out


async def test_repomap_generate_omits_ranked_definitions_when_no_defs_or_refs(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    f = root / "a.py"
    f.write_text("x = 1\n", encoding="utf-8")

    rm = RepoMap(
        all_files=[str(f)], active_context_files=[], root=str(root), token_limit=10_000
    )
    out = await rm.generate(include_active_content=False)

    assert "### Repository Map" in out
    assert "#### File Structure" in out
    assert "#### Ranked Definitions" not in out


async def test_repomap_generate_ranked_definitions_skips_active_files(
    repomap_tmp_project,
):
    rm = RepoMap(
        all_files=[
            repomap_tmp_project["defs"],
            repomap_tmp_project["use1"],
            repomap_tmp_project["use2"],
        ],
        active_context_files=[repomap_tmp_project["defs"]],
        mentioned_filenames=set(),
        mentioned_idents=set(),
        token_limit=10_000,
        root=repomap_tmp_project["root"],
    )

    out = await rm.generate(include_active_content=True)
    defs_rel = os.path.relpath(repomap_tmp_project["defs"], repomap_tmp_project["root"])

    assert "#### Active Context" in out
    assert f"{defs_rel}:\n```py" in out

    ranked_section = out.split("#### Ranked Definitions\n", 1)[1]
    assert f"{defs_rel}:\n" not in ranked_section


async def test_repomap_generate_active_context_omitted_when_header_exceeds_token_limit(
    repomap_tmp_project,
):
    rm = RepoMap(
        all_files=[
            repomap_tmp_project["defs"],
            repomap_tmp_project["use1"],
        ],
        active_context_files=[repomap_tmp_project["use1"]],
        mentioned_filenames=set(),
        mentioned_idents=set(),
        root=repomap_tmp_project["root"],
        token_limit=18,
    )

    out = await rm.generate(include_active_content=True)
    assert "#### Active Context" not in out


async def test_repomap_generate_active_file_skipped_when_block_exceeds_token_limit(
    tmp_path,
):
    root = tmp_path / "project"
    root.mkdir()

    active = root / "active.py"
    active.write_text("x = '" + ("y" * 500) + "'\n", encoding="utf-8")
    other = root / "other.py"
    other.write_text("def foo():\n    return 1\n\nfoo()\n", encoding="utf-8")

    rm = RepoMap(
        all_files=[str(active), str(other)],
        active_context_files=[str(active)],
        mentioned_filenames=set(),
        mentioned_idents=set(),
        root=str(root),
        token_limit=90,
    )

    out = await rm.generate(include_active_content=True)

    assert "#### Active Context" in out
    assert "active.py:\n" not in out


async def test_repomap_extract_tags_returns_empty_when_query_file_missing(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    f = root / "a.py"
    f.write_text("def core():\n    return 1\n", encoding="utf-8")

    rm = RepoMap(
        all_files=[str(f)], active_context_files=[], root=str(root), token_limit=10_000
    )
    empty_queries = tmp_path / "empty_queries"
    empty_queries.mkdir()
    rm.queries_dir = empty_queries

    tags = await rm.extract_tags(str(f))
    assert tags == []


async def test_repomap_rank_files_active_context_referencer_boost_changes_rank(
    repomap_tmp_project,
):
    all_files = [
        repomap_tmp_project["defs"],
        repomap_tmp_project["use1"],
        repomap_tmp_project["use2"],
    ]

    rm_base = RepoMap(
        all_files=all_files,
        active_context_files=[],
        mentioned_filenames=set(),
        mentioned_idents=set(),
        root=repomap_tmp_project["root"],
        token_limit=10_000,
    )
    ranked_base, _ = await rm_base._rank_files()

    rm_boosted = RepoMap(
        all_files=all_files,
        active_context_files=[repomap_tmp_project["use2"]],
        mentioned_filenames=set(),
        mentioned_idents=set(),
        root=repomap_tmp_project["root"],
        token_limit=10_000,
    )
    ranked_boosted, _ = await rm_boosted._rank_files()

    defs_rel = os.path.relpath(repomap_tmp_project["defs"], repomap_tmp_project["root"])
    assert ranked_boosted[defs_rel] > ranked_base[defs_rel]


async def test_repomap_rank_files_mentioned_filenames_referencer_boost_changes_rank(
    repomap_tmp_project,
):
    all_files = [
        repomap_tmp_project["defs"],
        repomap_tmp_project["use1"],
        repomap_tmp_project["use2"],
    ]

    rm_base = RepoMap(
        all_files=all_files,
        active_context_files=[],
        mentioned_filenames=set(),
        mentioned_idents=set(),
        root=repomap_tmp_project["root"],
        token_limit=10_000,
    )
    ranked_base, _ = await rm_base._rank_files()

    rm_boosted = RepoMap(
        all_files=all_files,
        active_context_files=[],
        mentioned_filenames={repomap_tmp_project["use2"]},
        mentioned_idents=set(),
        root=repomap_tmp_project["root"],
        token_limit=10_000,
    )
    ranked_boosted, _ = await rm_boosted._rank_files()

    defs_rel = os.path.relpath(repomap_tmp_project["defs"], repomap_tmp_project["root"])
    assert ranked_boosted[defs_rel] > ranked_base[defs_rel]


async def test_repomap_add_active_files_content_continues_on_missing_file(
    repomap_tmp_project, tmp_path
):
    missing = str(tmp_path / "missing.py")
    rm = RepoMap(
        all_files=[repomap_tmp_project["defs"], repomap_tmp_project["use1"]],
        active_context_files=[missing, repomap_tmp_project["use1"]],
        root=repomap_tmp_project["root"],
        token_limit=10_000,
    )

    out = await rm.generate(include_active_content=True)
    use1_rel = os.path.relpath(repomap_tmp_project["use1"], repomap_tmp_project["root"])
    assert "#### Active Context" in out
    assert f"{use1_rel}:\n```py" in out


async def test_repomap_ranked_definitions_excludes_files_without_definitions(
    repomap_tmp_project, tmp_path
):
    # A file that calls functions but defines nothing (e.g. a script)
    # It should be in the graph (as a referencer) but excluded from Ranked Definitions snippets.
    root = Path(repomap_tmp_project["root"])
    script_file = root / "script.py"
    script_file.write_text("from src.defs import core\ncore()\n", encoding="utf-8")

    rm = RepoMap(
        all_files=[repomap_tmp_project["defs"], str(script_file)],
        active_context_files=[],
        root=repomap_tmp_project["root"],
        token_limit=10_000,
        mentioned_filenames=set(),
    )

    out = await rm.generate(include_active_content=False)

    assert "#### Ranked Definitions" in out

    # The definition file SHOULD be there
    defs_rel = os.path.relpath(repomap_tmp_project["defs"], repomap_tmp_project["root"])
    assert f"{defs_rel}:\n" in out

    # The script file SHOULD NOT be there (it has no definitions)
    script_rel = os.path.relpath(str(script_file), repomap_tmp_project["root"])
    # It is listed in File Structure
    assert f"{script_rel}\n" in out

    # But not in Ranked Definitions
    ranked_section = out.split("#### Ranked Definitions\n", 1)[1]
    assert f"{script_rel}:\n" not in ranked_section
