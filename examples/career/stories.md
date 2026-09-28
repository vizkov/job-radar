<!-- FICTIONAL SAMPLE. STAR stories for interviews and cover letters. One "## [Sxx] title" per story. -->

## [S01] Auth bypass found in code review before launch
Situation: a payments API was two weeks from launch and SAST was clean.
Task: manual review of the authorisation layer.
Action: traced every route to its permission check; found a fallback path that skipped tenant checks.
Result: fixed before launch; the pattern became a Semgrep rule used across all services.

## [S02] Threat modeling that changed an architecture
Situation: a team planned to store card tokens in a shared cache.
Task: run a threat-modeling session before build.
Action: walked the data flows with STRIDE; showed cross-tenant read risk.
Result: design moved to a per-tenant vault; no rework after launch.
