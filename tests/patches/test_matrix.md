# Patches test matrix (skeleton phase)

## dependencies
- get_diff_patch_service delegates to build_diff_patch_service and returns instance
- get_diff_patch_service propagates factory errors

## factories
- build_diff_patch_service returns DiffPatchService
- build_diff_patch_service wires db + repo factory + subfactories

## models
- DiffPatch can be persisted
- DiffPatch FK cascade delete via ChatSession

## repositories
- list_pending_by_turn filters by session_id/turn_id/status=PENDING and orders asc
- list_by_turn filters by session_id/turn_id and orders asc

## schemas
- PatchRepresentation.from_text routes based on PatchProcessorType
- UDiffRepresentationExtractor: split multi-file diffs and compute operations
- ParsedDiffPatch: rename/add/remove/path normalization

## services
- DiffPatchService.extract_diffs_from_blocks extracts only ```diff fenced blocks
- DiffPatchService.extract_diffs_from_blocks ignores non-text blocks
- DiffPatchService.process_diff marks APPLIED on success, FAILED on processor error
- DiffPatchService._build_processor chooses UDiffProcessor, errors for CODEX_APPLY

## processors
- UDiffProcessor._strip_markdown extracts fenced code content