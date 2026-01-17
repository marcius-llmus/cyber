import pytest
import os
from pathlib import Path
from unittest.mock import AsyncMock

from app.context.repomap.repomap import RepoMap
from app.context.services.repomap import RepoMapService
from app.context.exceptions import RepoMapExtractionException
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.models import Project
from app.settings.models import Settings

@pytest.fixture
def service(workspace_service_mock, codebase_service_mock, settings_service_mock, project_service_mock):
    return RepoMapService(workspace_service_mock, codebase_service_mock, settings_service_mock, project_service_mock)

async def test_generate_repo_map_no_project(service, project_service_mock):
    project_service_mock.get_active_project = AsyncMock(return_value=None)
    with pytest.raises(ActiveProjectRequiredException):
        await service.generate_repo_map(session_id=1)

    project_service_mock.get_active_project.assert_awaited_once_with()

async def test_generate_repo_map_success(
    service, 
    workspace_service_mock, 
    codebase_service_mock, 
    settings_service_mock, 
    project_service_mock,
    mocker
):
    # 1. Setup Mocks
    project = Project(id=1, name="p", path="/tmp/proj")
    project_service_mock.get_active_project = AsyncMock(return_value=project)
    
    # Codebase returns relative paths
    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["src/main.py", "README.md"])
    
    # Context returns absolute paths
    workspace_service_mock.get_active_file_paths_abs = AsyncMock(return_value=["/tmp/proj/src/main.py"])
    
    # Mentioned files resolution
    codebase_service_mock.filter_and_resolve_paths = AsyncMock(return_value={"/tmp/proj/other.py"})
    
    # Settings
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(ast_token_limit=2000, max_history_length=0, grep_token_limit=0, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))
    
    # Patch RepoMap
    repomap_cls = mocker.patch("app.context.services.repomap.RepoMap")
    repomap_instance = repomap_cls.return_value
    repomap_instance.generate = AsyncMock(return_value="Repo Map Content")

    # 2. Execute
    result = await service.generate_repo_map(
        session_id=1,
        mentioned_filenames={"other.py"}, 
        mentioned_idents={"Foo", "Bar"},
        include_active_content=False
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
    
    repomap_instance.generate.assert_awaited_once_with(include_active_content=False)

    project_service_mock.get_active_project.assert_awaited_once_with()
    codebase_service_mock.resolve_file_patterns.assert_awaited_once_with("/tmp/proj")
    workspace_service_mock.get_active_file_paths_abs.assert_awaited_once_with(1, "/tmp/proj")
    codebase_service_mock.filter_and_resolve_paths.assert_awaited_once_with("/tmp/proj", ["other.py"])
    settings_service_mock.get_settings.assert_awaited_once_with()


async def test_repomap_extract_tags_unknown_extension_returns_empty(repomap_instance, repomap_tmp_project):
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


async def test_repomap_extract_tags_python_finds_definitions_and_references(repomap_instance, repomap_tmp_project):
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


async def test_repomap_rank_files_ranks_defining_file_higher_when_referenced(repomap_instance, repomap_tmp_project):
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

    public_rel = os.path.relpath(repomap_tmp_project["public_defs"], repomap_tmp_project["root"])
    hidden_rel = os.path.relpath(repomap_tmp_project["hidden_defs"], repomap_tmp_project["root"])

    assert ranked[public_rel] > ranked[hidden_rel]


async def test_repomap_rank_files_mentioned_idents_boost_overrides_private_downweight(repomap_tmp_project):
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

    public_rel = os.path.relpath(repomap_tmp_project["public_defs"], repomap_tmp_project["root"])
    hidden_rel = os.path.relpath(repomap_tmp_project["hidden_defs"], repomap_tmp_project["root"])

    assert ranked[hidden_rel] > ranked[public_rel]


async def test_repomap_generate_includes_structure_active_context_and_ranked_definitions(repomap_tmp_project):
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


async def test_repomap_generate_include_active_content_false_omits_active_context(repomap_tmp_project):
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


async def test_repomap_generate_respects_token_limit_file_structure_truncates(repomap_tmp_project):
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
    assert "... (file list truncated)" in out


async def test_repomap_generate_ranked_definitions_truncates_with_notice(repomap_tmp_project):
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
        token_limit=250,
    )
    out = await rm.generate(include_active_content=False)
    assert "#### Ranked Definitions" in out
    assert "... (remaining definitions truncated due to token limit)" in out