# Codebase Review — 260901

Full-codebase review of slurm-usage-history: 131 source files across `src/`, `backend/app`, `scripts/`, and `frontend/src` (~21k LOC), reviewed by 11 module-group reviewers; every high/medium finding was then adversarially verified. Raw findings: 144; confirmed: 80; refuted: 1; unverified low-confidence notes: 62; verification failed for 1 finding (session limit).

## Baseline gates

The project's own gates at review time (main @ f2aa6da, before the baseline-fix MR 50):

| Gate | Result |
|---|---|
| ruff check + format | pass (80 files) |
| vulture (min-confidence 80) | pass |
| pytest | 205 passed |
| tsc | pass |
| eslint | 1 warning (react-hooks/exhaustive-deps, AdminUsers.tsx) — fixed in MR 50 |
| vitest | 19 passed |
| 1000-LOC file limit | 1 violation (distribution_generators.py, 1038) — fixed in MR 50 |
| mypy | not a configured gate; ad-hoc run with --ignore-missing-imports found 36 errors in 12 files |

## Summary

Confirmed findings: 9 high, 39 medium, 32 low.

Recurring themes:

1. **Dead code** (18 findings): entire unimported components (ReportGenerator.tsx 537 LOC, ReportOverview.tsx), unused library functions (six of nine in tools.py), unused models, dead sys.path hacks, unreferenced types/colors/formatters. The vulture gate covers only Python at confidence 80 and nothing covers TypeScript exports.
2. **Forked/duplicated logic** (11): number/hour formatting forked across three frontend modules with diverging output; two parallel X-API-Key verifiers; SLURM duration parsing duplicated with divergent behavior; time-column mapping triplicated; report period validation duplicated.
3. **Architecture boundary violations** (6): the library reaches into the backend app via sys.path manipulation and singletons; backend imports scripts/ files via sys.path mutation. No import-scanning gate exists yet.
4. **Hardcoded environment assumptions** (6): CWD-relative data paths probed at import time, hardcoded localhost URLs, hardcoded @tudelft.nl domain, settings bypassed with os.getenv.
5. **Report correctness** (4): previous-period comparison windows ignore report type; per-day cards divide by bin count; captions say "daily" regardless of period.
6. **Caption/docstring accuracy** (5): several captions and docstrings describe different quantities than the code computes.

## High severity (9 confirmed)

### `src/slurm_usage_history/app/duckdb_datastore.py:100` — Missing-duckdb fallback is defeated by eagerly evaluated return annotation

*Category: correctness · verifier confidence: high*

The module guards `import duckdb` with try/except and sets `duckdb = None`, but `def _get_connection(self) -> duckdb.DuckDBPyConnection:` evaluates the annotation at class-definition time on the supported Pythons (requires-python is >=3.10,<3.13; no `from __future__ import annotations` in this file). Verified on the project's Python 3.10: with `duckdb = None` the class body raises `AttributeError: 'NoneType' object has no attribute 'DuckDBPyConnection'` at import. So when duckdb is absent, importing the module crashes with AttributeError instead of reaching the graceful `raise ImportError` in `__init__`, and backend/app/datastore_singleton.py (which catches only ImportError to fall back to PandasDataStore) crashes the backend instead of falling back. The entire DUCKDB_AVAILABLE machinery is unreachable in the scenario it exists for.

**Fix:** Add `from __future__ import annotations` at the top of the file (or quote the annotation as "duckdb.DuckDBPyConnection").

### `src/slurm_usage_history/app/duckdb_datastore.py:509` — Filter values interpolated into SQL without escaping (injection/breakage)

*Category: correctness · verifier confidence: high*

`filter()` and `get_filter_values_for_period()` build WHERE clauses by f-string interpolation of caller-supplied values, e.g. `account_list = "', '".join(accounts); where_clauses.append(f"Account IN ('{account_list}')")`, and similarly for users, qos, states, partitions (`list_contains(string_split(Partition, ','), '{partition}')`) and dates. Any value containing a single quote (an account named `o'brien`, or a crafted API filter parameter) breaks the query or injects arbitrary SQL into the DuckDB connection. These values arrive from HTTP query parameters via the backend API, so this is externally reachable.

**Fix:** Use DuckDB parameterized queries (`conn.execute(query, params)` with `?` placeholders or `IN (SELECT unnest(?))`), or at minimum escape single quotes in every interpolated value including dates.

### `src/slurm_usage_history/app/duckdb_datastore.py:328` — Library reaches into the backend application via sys.path manipulation

*Category: design · verifier confidence: high*

`_auto_discover_nodes` does `sys.path.insert(0, str(backend_path))` and `from app.services.node_discovery import get_node_discovery_service`, importing the consumer application from inside the library. This inverts the dependency direction and violates the project rule 'depend on injected interfaces, never on discovered implementations'. It also only works in a source checkout with a sibling `backend/` directory; in an installed wheel the failure is silently downgraded to a debug log, so node auto-discovery works or not depending on how the package happens to be laid out on disk.

**Fix:** Define a node-discovery callback/interface parameter on DuckDBDataStore (injected by the backend when it constructs the store) and remove the sys.path probing.

### `scripts/consolidate_data.py:85` — Timestamped files that failed consolidation are still deleted

*Category: correctness · verifier confidence: high*

The removal loop `for f in timestamped_files: ... f.unlink()` deletes every globbed file, including files that hit the `except Exception` during `pd.read_parquet(f)` and files lacking a `Submit` column (both are silently excluded from `year_data` and never written into a yearly file). Their job records are permanently lost. Also, if `combined_df.to_parquet(year_file)` raises for one year, the loop above it has already partially written and the unlink loop still removes all inputs.

**Fix:** Track which files were successfully merged and saved, and unlink only those; leave failed/skipped files in place and log them.

### `src/slurm_usage_history/scripts/waiting_times.py:35` — Monitor crashes when squeue reports zero pending jobs

*Category: correctness · verifier confidence: high*

When `squeue --states=PD` prints nothing, `result.stdout.strip().split("\n")` yields `[""]`, and `job_id_full, submit_time, username = line.split(maxsplit=2)` raises ValueError (not enough values to unpack). The surrounding try only catches `subprocess.CalledProcessError`, so the long-running monitor (installed as the `slurm-dashboard-wait-times` entry point) dies the first time the queue is empty.

**Fix:** Skip empty lines: `for line in result.stdout.strip().split("\n"):` guard with `if not line.strip(): continue`.

### `backend/app/core/config.py:88` — get_admin_email_roles hardcodes data/clusters.json, ignoring settings.data_path and ClusterDB

*Category: correctness · verifier confidence: high*

`db_path = Path("data/clusters.json")` is a cwd-relative hardcoded path, while `Settings.__init__` deliberately absolutizes `self.data_path` and ClusterDB has its own (also hardcoded, cwd-relative) `db_path: str = "data/clusters.json"`. If DATA_PATH is configured to another location or the process cwd differs, admin/superadmin role lookups silently read the wrong (or a missing) file and fall through to env vars via `except Exception: pass` — an admin can silently lose or gain privileges depending on cwd. This also duplicates storage-layout knowledge in three places (core/config.py:88, db/clusters.py:28, api/admin.py:484/599) instead of going through one injected interface, violating the project rule against discovered implementations.

**Fix:** Derive the path once (e.g. Path(self.data_path) / "clusters.json" or expose it from ClusterDB) and have config.py, ClusterDB, and admin.py all use that single source. Log the fallback instead of bare `except Exception: pass`.

### `backend/app/db/clusters.py:43` — Corrupted DB file is silently treated as empty, then destroyed on next write

*Category: correctness · verifier confidence: high*

`_read_db` catches `json.JSONDecodeError` and returns `{"clusters": {}, "stats": {}}`. Every mutator (and even `verify_api_key`, which writes on the read path during plaintext-key migration) does read-modify-write, so a transiently corrupted or truncated clusters.json is read as empty and the next `_write_db` permanently erases all clusters, API key hashes, and admin_users entries. A JSONDecodeError on an existing file should be surfaced, not converted into an empty database.

**Fix:** Only treat FileNotFoundError as empty; re-raise or fail loudly on JSONDecodeError of an existing file, and write via a temp file + os.replace for atomicity.

### `backend/app/models/data_models.py:32` — Client-supplied hostname in DataIngestionRequest bypasses the authenticated cluster identity

*Category: design · verifier confidence: high*

`hostname: str = Field(..., description="Cluster hostname")` duplicates information the server already derives from the API key. In backend/app/api/data.py the verified cluster name is bound as `_cluster_name` and ignored, while `request.hostname` decides the write directory (`Path(settings.data_path) / request.hostname / "data"`). Any holder of one valid cluster key can therefore ingest data into any other cluster's dataset (or an arbitrary new directory) by choosing `hostname`.

**Fix:** Drop hostname from the ingestion payload (or validate it equals the cluster name returned by verify_api_key) and key the storage path on the authenticated cluster name.

### `frontend/src/components/reports/ReportSummaryCards.tsx:214` — Per-day cards divide by timeline bin count, wrong for quarterly/annual reports

*Category: correctness · verifier confidence: high*

Backend report_generator.py aggregates the timeline by week for quarterly reports and by month for annual reports (lines 129-161), so timeline.length is the number of weeks/months, not days. The cards 'Avg Jobs/Day' ({total_jobs / timeline.length}, caption 'Over {timeline.length} days', lines 214-224), 'Peak Jobs/Day' (line 234), 'Avg CPU-Hours/Day' (line 254, 'max ... h/day'), and 'Avg GPU-Hours/Day' (line 274) therefore report per-week/per-month values labeled as per-day for quarterly and annual reports - e.g. an annual report shows monthly averages labeled 'Avg Jobs/Day'.

**Fix:** Derive the bin unit from reportType (day/week/month) as ReportTimelines does with getTimeUnit(), and label/compute accordingly (e.g. 'Avg Jobs/Week', 'Over N weeks'), or divide by actual days in the period.

## Medium severity (39 confirmed)

### `src/slurm_usage_history/app/duckdb_datastore.py:134` — get_hostnames discovers clusters.json by probing hardcoded CWD-relative paths

*Category: design · verifier confidence: high*

`get_hostnames()` tries `data/clusters.json`, `backend/data/clusters.json`, `/app/data/clusters.json`, `/app/backend/data/clusters.json` to decide which hosts are 'active'. The result depends on the process working directory and container layout rather than on anything the caller controls — a hidden dependency the project rules explicitly forbid ('a component that reaches out to find its collaborator... has a hidden dependency'). It is also re-read on every call (load_data calls get_hostnames three times), and the function re-imports `json` and `Path` locally, shadowing the module-level Path import.

**Fix:** Inject the active-cluster source (path or lookup callable) via the constructor; hoist the local imports.

### `src/slurm_usage_history/app/duckdb_datastore.py:197` — weekly-data fallback exists only in metadata loading, not in query paths

*Category: correctness · verifier confidence: high*

`_load_host_metadata` falls back to `<host>/weekly-data` when `<host>/data` is missing, but `filter()` (line 506), `get_filter_values_for_period()` (line 406) and `_check_host_updates()` (line 715) hardcode `<host>/data`. A host whose files live in weekly-data loads metadata and appears healthy, then every filter query targets a non-existent glob and raises a DuckDB IO error, and file changes are never detected. Relatedly, `filter()` performs no hostname/data existence check at all, whereas PandasDataStore.filter returns an empty DataFrame — the two stores fail differently for the same bad input.

**Fix:** Resolve the host data directory once (in _load_host_metadata), store it in self.hosts[hostname], and use it in all query and update-check paths; return an empty DataFrame for unknown hosts as the pandas store does.

### `src/slurm_usage_history/app/duckdb_datastore.py:473` — filter() silently ignores complete_periods_only, period_type and account_segments

*Category: consistency · verifier confidence: high*

The parameters are accepted 'for interface compatibility' with PandasDataStore but do nothing (noqa: ARG002). PandasDataStore honors all three, so the same call yields different data depending on the active store, with no warning to the caller. The docstring for `account_segments` ('Number of segments for account formatting') does not say it is unused, unlike the other two.

**Fix:** Implement the period filtering in SQL and account_segments via the formatter, or raise/log when a caller passes a value the store will ignore, and fix the account_segments docstring.

### `src/slurm_usage_history/__init__.py:49` — Non-editable installs report __version__ = 0.0.0-dev (wrong distribution name)

*Category: correctness · verifier confidence: high*

Both fallback paths call `version(__name__)`, i.e. look up a distribution named 'slurm_usage_history', but the distribution is named 'slurm-dashboard' (pyproject line 2). Verified in the project venv: `version('slurm_usage_history')` and `version('slurm-usage-history')` raise PackageNotFoundError while `version('slurm-dashboard')` returns 0.6.1.dev...; so any non-editable (wheel) install takes the `except Exception` branch and reports '0.0.0-dev'. The editable path only works because setuptools_scm is queried instead. `_is_editable()` already knows the correct name pair.

**Fix:** Use `version("slurm-dashboard")` with a fallback to `version("slurm-usage-history")`, mirroring _is_editable().

### `src/slurm_usage_history/tools.py` — Six of nine functions in tools.py are unused anywhere in the repo

*Category: dead-code · verifier confidence: high*

Repo-wide grep (src, backend, tests, scripts, cluster-agent; excluding build dirs) finds no callers for `natural_sort_key`, `get_time_column`, `week_to_date`, `month_to_date`, `print_column_info_in_markdown`, `categorize_time`, or `categorize_time_series`. Only `unpack_nodelist_string` (backend node_generators + tests) and `timeit` (datastore.py decorators) are used. The backend has its own private `_get_time_column` in distribution_generators.py, so the library variant is a stranded near-duplicate. Project rule: remove dead code rather than keep it.

**Fix:** Delete the seven unused functions (and the pandas import if it becomes unused); if period-column selection is meant to be shared, move the backend's _get_time_column into the library instead.

### `src/slurm_usage_history/app/__init__.py` — Entry point slurm-dashboard-legacy targets non-existent slurm_usage_history.app.main

*Category: correctness · verifier confidence: high*

pyproject.toml declares `slurm-dashboard-legacy = "slurm_usage_history.app.main:main"`, but the app package contains only __init__.py, account_formatter.py, datastore.py and duckdb_datastore.py — there is no main.py, so the installed console script fails with ModuleNotFoundError when invoked.

**Fix:** Remove the slurm-dashboard-legacy script entry (it is marked deprecated) or point it at an existing module.

### `src/slurm_usage_history/scripts/exporter.py:220` — parse_alloc_tres substring matching crashes on gres/gpumem and similar TRES keys

*Category: correctness · verifier confidence: high*

`elif "gpu" in key: result["gpu"] = int(val)` matches any TRES key containing 'gpu'. On clusters that report `gres/gpumem=80G` or `gres/gpuutil=...` in AllocTRES, `int("80G")` raises ValueError inside `df["AllocTRES"].apply(...)`, which is uncaught and aborts the whole chunk extraction. The same substring approach means `gres/gpu:a100=2` silently overwrites the plain `gres/gpu` count depending on ordering.

**Fix:** Match keys exactly (`key == "cpu"`, `key in ("gres/gpu",)` or `key.split(":")[0] == "gres/gpu"`, `key == "mem"`) and wrap int() in try/except.

### `src/slurm_usage_history/scripts/exporter.py:276` — count_nodes miscounts SLURM compressed nodelist notation

*Category: correctness · verifier confidence: high*

`count_nodes` splits NodeList on commas. `node[01-04]` counts as 1 (the comment admits ranges are unsupported), and `node[01,03]` splits into the bogus tokens `node[01` and `03]`, counting 2 nodes that do not match real node names. AllocNodes feeds `parse_reqmem_to_mb(row["ReqMem"], AllocCPUS, AllocNodes)`, so per-node ReqMem conversion is wrong for multi-node jobs, and the project's multi-node equal-split semantics inherit a wrong node count.

**Fix:** Expand bracket notation (e.g. reuse or port a hostlist expansion helper into the library) or use sacct's AllocNodes field directly instead of parsing NodeList.

### `src/slurm_usage_history/scripts/cluster_agent.py:122` — sync_config lets requests exceptions escape the documented RuntimeError contract

*Category: correctness · verifier confidence: high*

The docstring says `Raises: RuntimeError: If scontrol fails or the server rejects the upload`, but `requests.post(...)` can raise ConnectionError/Timeout, which neither `sync_config_command` nor `run_command` catches (both catch only RuntimeError). In `run_command --sync-config` a network blip therefore produces a full traceback and aborts the run instead of the intended 'WARNING: configuration sync failed, continuing with job collection'. `setup_command` by contrast catches `requests.exceptions.RequestException` — inconsistent error handling between siblings.

**Fix:** Wrap the POST in try/except requests.exceptions.RequestException and re-raise as RuntimeError, matching the docstring.

### `src/slurm_usage_history/scripts/cluster_agent.py:10` — slurm-dashboard entry point imports requests, which is not a core dependency

*Category: design · verifier confidence: high*

cluster_agent.py imports `requests` at module level, and pyproject exposes it as the unconditional console script `slurm-dashboard = "slurm_usage_history.scripts.cluster_agent:main"`. Core dependencies are only python-dotenv and pyyaml; requests lives in the [agent] extra. A base `pip install slurm-dashboard` produces a console script that fails with ImportError even for `--help`. Violates the project rule that every directly imported package is declared (for the code path that ships it).

**Fix:** Either add requests to core dependencies or mark the script with the extra (`slurm-dashboard = "...:main" [agent]`) / import requests lazily inside the commands that need it.

### `src/slurm_usage_history/scripts/exporter.py:228` — Duplicated SLURM duration parsing with divergent behavior

*Category: consistency · verifier confidence: high*

Module-level `parse_duration_hours` (line 23, used for TotalCPU, tested in tests/test_efficiency.py) and the nested `elapsed_to_hours` inside `format_jobs` (line 228, used for Elapsed) implement the same [D-]HH:MM:SS parsing but diverge: one returns None for unparseable input, the other returns 0.0 and swallows all exceptions with a broad `except Exception`. Same-format values are parsed by two forks in one file.

**Fix:** Use parse_duration_hours for Elapsed too (mapping None to 0.0 at the call site if needed), and consider moving it next to parse_memory_to_mb in slurm_usage_history (library-level shared parsing).

### `scripts/generate_test_cluster_data.py` — Backend imports this scripts/ file via sys.path hack; generator belongs in the library

*Category: design · verifier confidence: high*

backend/app/api/config_admin.py:161-162 does `sys.path.insert(0, .../scripts)` then `from generate_test_cluster_data import SyntheticClusterDataGenerator` to power the demo-cluster API. A runtime feature depends on a loose script discovered by path, violating the project rules 'shared functionality in the library' and 'depend on injected interfaces, never on discovered implementations', and it silently breaks in any deployment that ships only the installed package without the repo's scripts/ directory.

**Fix:** Move SyntheticClusterDataGenerator into src/slurm_usage_history (e.g. slurm_usage_history/testing/synthetic_data.py) and keep scripts/generate_test_cluster_data.py as a thin CLI wrapper importing it.

### `backend/app/core/auth.py:12` — Two parallel X-API-Key verifiers with divergent behavior (auth.verify_api_key vs agent_auth.verify_agent_api_key)

*Category: consistency · verifier confidence: high*

core/auth.py verify_api_key (APIKeyHeader, auto_error=False, legacy .env-key fallback returning cluster name "unknown", special 500 when no keys configured) and core/agent_auth.py verify_agent_api_key (Header(...), cluster DB only) both verify the same X-API-Key header against get_cluster_db().verify_api_key. The duplication means /data/ingest accepts legacy env keys but the agent endpoints do not, missing-key handling differs (401 "Missing API Key" vs FastAPI 422), and the sentinel "unknown" cluster name flows downstream (e.g. into update_submission_stats, where it silently no-ops). One shared dependency should implement key verification, with the legacy fallback either retired or applied uniformly.

**Fix:** Collapse into a single dependency in one module; if the legacy .env fallback is still needed, make it explicit and shared, otherwise delete it together with Settings.api_keys/get_api_keys.

### `backend/app/db/clusters.py` — Unsynchronized read-modify-write JSON store loses concurrent updates

*Category: design · verifier confidence: high*

Every ClusterDB method does `_read_db()` -> mutate -> `_write_db()` with no file lock or in-process lock, and `verify_api_key` even writes during request handling (plaintext-key migration). Two concurrent requests (multiple uvicorn workers, or an ingest racing an admin edit) can interleave and silently drop one write — e.g. a rotated key hash overwritten by a stale stats update, locking the agent out. `_write_db` is also non-atomic (in-place open("w")), so a crash mid-dump truncates the file, which combined with the JSONDecodeError-to-empty fallback destroys the database.

**Fix:** Serialize access with a lock (in-process plus file lock if multiple workers) and write atomically via temp file + os.replace.

### `backend/app/datastore_singleton.py:23` — ImportError fallback crashes module on annotation evaluation

*Category: correctness · verifier confidence: high*

When the try-import fails, both DuckDBDataStore and PandasDataStore are rebound to None. The module-level annotated assignment `_datastore: DuckDBDataStore | None = None` then evaluates `None | None`, which raises `TypeError: unsupported operand type(s) for |: 'NoneType' and 'NoneType'` on the project's supported interpreters (requires-python >=3.10,<3.13; verified on the repo venv Python 3.10.16). The entire fallback path the try/except pretends to provide can never execute - the module import itself dies. The PandasDataStore fallback branch in get_datastore() is therefore unreachable code.

**Fix:** Quote the annotation (`_datastore: "DuckDBDataStore | None" = None`) or annotate as `Any | None`. Better: drop the optional-import dance entirely and import unconditionally, since the sibling dead-import findings show the fallback is fiction.

### `backend/app/api/dashboard.py:197` — reload-data all-clusters path uses PandasDataStore-only internals; broken with default DuckDB store

*Category: correctness · verifier confidence: high*

`if datastore.hosts[host]["data"] is None:` and `datastore._load_host_data(host)` - DuckDBDataStore._initialize_hosts creates host entries with keys max_date/min_date/partitions/accounts/users/qos/states/parquet_files and no "data" key (verified in src/slurm_usage_history/app/duckdb_datastore.py:119-133), so this raises KeyError for every host; and `_load_host_data` is defined only on PandasDataStore (src/slurm_usage_history/app/datastore.py:281). Since get_datastore() prefers DuckDBDataStore, POST /api/dashboard/reload-data without a hostname always returns 500 once any cluster directory exists. No test covers this endpoint (grep of tests/ found none). It also violates the injected-interface rule by reaching into private members.

**Fix:** Replace the private-member poking with a public datastore method (e.g. datastore.load_data() or a rescan API on the datastore interface) and add a test that exercises reload-data against DuckDBDataStore.

### `backend/app/api/admin.py:484` — admin-emails endpoints bypass ClusterDB and hardcode a CWD-relative database path

*Category: design · verifier confidence: high*

get_admin_emails and update_admin_emails open `Path("data/clusters.json")` directly (lines 484 and 599), duplicating the default path literal from ClusterDB.__init__ (backend/app/db/clusters.py:28) instead of going through get_cluster_db(). If the server runs with a different working directory or a ClusterDB configured with another path, these endpoints silently read nothing / raise 500 ("Database file not found") while the rest of the admin API works. Direct file writes also race with ClusterDB's own read-modify-write cycles.

**Fix:** Add read/write admin-email methods to ClusterDB and call them from both endpoints so there is exactly one owner of the file path and file format.

### `backend/app/api/saml.py:359` — print()-based [DEBUG] logging of user emails and admin status in /saml/me

*Category: consistency · verifier confidence: high*

Lines 359, 363, 372 and 383 use `print(f"[DEBUG] ...")` including the full result dict with user attributes and the configured admin email roles, on every request to /saml/me. Every sibling module uses `logger = logging.getLogger(__name__)`; saml.py itself uses a logger inside saml_acs. This is leftover debug output that bypasses log configuration and prints personal data to stdout in production.

**Fix:** Replace the prints with logger.debug calls (without dumping full attribute sets and admin lists) or remove them.

### `backend/app/api/admin.py:188` — Hardcoded "@tudelft.nl" domain duplicated in two admin checks

*Category: design · verifier confidence: high*

`full_email = f"{username}@tudelft.nl"` appears in admin.py:188 (/admin/saml-token) and saml.py:370 (/saml/me). The institution domain is deployment configuration, not code, and the duplication means the two admin checks can drift. Consumer-app configuration belongs in settings per the project architecture rules.

**Fix:** Add a settings field (e.g. saml_email_domain) and use it in both places, or extract one shared helper resolve_admin_email(user_data, settings).

### `backend/app/api/reports.py:146` — Period validation block duplicated verbatim between /generate and /preview

*Category: consistency · verifier confidence: high*

The ~50 lines validating month/quarter bounds and rejecting incomplete/future periods (generate_report lines 44-93 and preview_report lines 146-192) are copy-pasted, including the datetime import and error strings. Only the filename_suffix differs. Any fix (e.g. timezone handling, quarter logic) must land twice. Additionally, `format` and `type` shadow builtins, and get_datastore is imported indirectly via `.dashboard` instead of `..datastore_singleton` like every other module.

**Fix:** Extract a helper returning (start_date, end_date, report_type, filename_suffix) shared by both endpoints; import get_datastore from ..datastore_singleton; rename the query params' Python names (report_format, report_type) while keeping the public alias.

### `backend/app/api/config_admin.py:161` — generate_demo_cluster imports from scripts/ via sys.path mutation

*Category: design · verifier confidence: high*

`sys.path.insert(0, .../"scripts")` followed by `from generate_test_cluster_data import SyntheticClusterDataGenerator` makes a production endpoint depend on an undeclared, discovered module outside the package - the kind of hidden dependency the project's architecture rules forbid, and it breaks in any deployment that ships the backend without the repo's scripts directory. The module also re-imports Path inside the function (line 229) though it is already imported at line 158 and module top, and the atomic tempfile+os.replace YAML write block is copy-pasted four times in this file (lines 190, 291, 401, 469).

**Fix:** Move the generator into the library (src/slurm_usage_history) or the backend services package and import it normally; extract one _write_yaml_atomic(config_path, data) helper used by all four endpoints.

### `backend/app/api/config_admin.py:428` — cleanup_demo_cluster deletes any cluster, not just the demo one

*Category: naming · verifier confidence: high*

DELETE /config/{cluster_name}/cleanup is named cleanup_demo_cluster and documented as "Delete a demo cluster's data and configuration", but nothing restricts cluster_name: it shutil.rmtree's the data directory, removes the YAML entry and the DB record of whatever cluster name is passed. The name and docstring understate a destructive operation.

**Fix:** Either restrict it to the DemoCluster name (matching the docstring) or rename it to delete_cluster_completely and document that it destroys production data.

### `backend/app/services/reports/report_generator.py:31` — Empty-period report dict omits generated_at, crashing CSV and PDF export

*Category: correctness · verifier confidence: high*

The empty-DataFrame branch of generate_report_data returns a dict without the "generated_at" key (the non-empty path adds it at line 182). format_report_as_csv accesses report_data['generated_at'] (report_formatters.py:55) and format_report_as_pdf calls datetime.fromisoformat(report_data['generated_at']) (report_formatters.py:161). backend/app/api/reports.py:96-113 passes the generator output straight to these formatters, so requesting a CSV or PDF report for a period with no jobs raises KeyError, surfaced as a 500 'Error generating report'. No test covers this path (no test file references format_report_as_csv/pdf or generate_report_data).

**Fix:** Add "generated_at": datetime.now().isoformat() to the empty-branch return dict, or restructure so both paths share one return-dict construction; add a test exporting CSV/PDF for an empty period.

### `backend/app/services/reports/comparison_metrics.py:83` — Previous-period timeline aggregates by Start columns while current timeline uses Submit columns

*Category: correctness · verifier confidence: high*

calculate_comparison_metrics picks time_column = "StartYearMonth" / "StartYearWeek" for Annual/Quarterly reports, but generate_report_data builds the current timeline from "SubmitYearMonth" / "SubmitYearWeek" with the explicit comment 'Use Submit time to match datastore filtering and prevent date leakage' (report_generator.py:133-142). The PDF comparison overlay (create_comparison_timeline) therefore compares Submit-time bins against Start-time bins, and the Start-based previous timeline can leak jobs whose Start falls outside the queried Submit window. Monthly reports (SubmitDay) are consistent; only Annual/Quarterly diverge.

**Fix:** Use SubmitYearMonth/SubmitYearWeek in calculate_comparison_metrics to mirror report_generator, and update the string-conversion check at line 103 accordingly.

### `backend/app/services/reports/comparison_metrics.py:11` — 'Previous period' ignores report type, so monthly/quarterly comparisons use misaligned calendar windows

*Category: correctness · verifier confidence: high*

calculate_previous_period_dates takes _report_type but never uses it (its docstring still claims 'based on report type', and the caller passes the literal "" at line 42 even though report_type is in scope). It always goes back by the same number of days, so a March monthly report (31 days) is compared against Jan 29 - Feb 28 rather than February, and a Q3 report against a 92-day window straddling Q1/Q2. The unused underscored parameter plus the hardcoded "" argument indicate intended-but-unimplemented behavior.

**Fix:** Either implement calendar-aware previous periods (previous month/quarter/year) using the report type, or drop the parameter and fix the docstring to state the day-count-based semantics honestly.

### `backend/app/services/node_discovery.py:246` — Library reaches into backend app via get_node_discovery_service singleton

*Category: design · verifier confidence: high*

get_node_discovery_service exists solely to be resolved at runtime by the library: src/slurm_usage_history/app/duckdb_datastore.py:349-352 does 'from app.services.node_discovery import get_node_discovery_service' inside the library. This inverts the library/app dependency direction and violates the project rule 'depend on injected interfaces, never on discovered implementations' (a component resolving a global from another layer). It also means node discovery silently does nothing when the backend package is not importable.

**Fix:** Define the discovery interface in the library and inject the NodeDiscoveryService from the backend composition root; remove the module-level singleton.

### `backend/app/services/charts/distribution_generators.py:377` — memory_hours_by_account is always empty when a grouping dimension is selected

*Category: correctness · verifier confidence: high*

In generate_by_dimension, the grouped (pie) branch only supports `metric in ["CPUHours", "GPUHours"]`; any other metric hits `else: return {"type": "pie", "labels": [], "values": []}`. The API (backend/app/api/charts.py:282) calls `generate_by_dimension(df, color_by, metric="MemGBHours", ...)` for the memory_hours_by_account chart, so whenever the user selects a color_by dimension (Account, Partition, ...), the memory chart silently returns an empty pie while the CPU and GPU siblings return data. The ungrouped histogram branch at line 317 already supports MemGBHours, confirming the metric is intended to work.

**Fix:** Add "MemGBHours" to the allowed metrics in the grouped branch: `elif metric in ["CPUHours", "GPUHours", "MemGBHours"]:`, and add a test that generate_by_dimension(df, "Account", metric="MemGBHours") returns non-empty labels/values.

### `backend/app/services/charts/distribution_generators.py:406` — generate_jobs_by_account, generate_cpu_hours_by_account and generate_gpu_hours_by_account are not used by the application

*Category: dead-code · verifier confidence: high*

Grep across backend/, src/ and tests/ shows these three functions are referenced only by tests/test_chart_generation.py and the package __init__. The API endpoint builds the jobs_by_account / cpu_hours_by_account / gpu_hours_by_account payload keys via generate_by_dimension instead (backend/app/api/charts.py:254, 278-279). generate_jobs_by_partition and generate_jobs_by_state, by contrast, are still called (marked "Keep for now"). These are library functions kept alive solely by their own tests — production-dead code under the project's dead-code rule. Also applies to lines 830 (generate_cpu_hours_by_account) and 842 (generate_gpu_hours_by_account).

**Fix:** Remove the three functions, their tests, and their __init__/__all__ entries, or wire them back into the API if the generate_by_dimension replacement was not intended to supersede them.

### `backend/app/services/charts/distribution_generators.py:13` — Time-column mapping and year-fallback logic duplicated three times across the package

*Category: consistency · verifier confidence: high*

distribution_generators.TIME_COLUMN_MAP (line 13) and timeline_generators.TIME_COLUMN_MAP_START (line 11) are identical dicts; the StartYearMonth->StartYear fallback is implemented once in _get_time_column (distribution_generators line 102) and again inline in _generate_timeline (timeline_generators lines 66-75); and generate_user_activity_frequency (line 887) re-declares a local `submit_time_column_map` identical to timeline_generators.TIME_COLUMN_MAP_SUBMIT. On top of that, efficiency_generators and memory_generators import the private helpers `_get_time_column` and `_generate_timeline` from sibling modules, so the de-facto shared helpers live behind private names in the wrong module while chart_helpers.py exists for exactly this purpose. Any change to period handling must currently land in three places.

**Fix:** Move the time-column maps and a single time-column-resolution helper into chart_helpers.py (public names) and have all four generator modules use it.

### `frontend/src/components/charts/GaugeChart.tsx:15` — Dark mode inferred by string-comparing textColor instead of an isDark prop

*Category: consistency · verifier confidence: high*

`const isDark = textColor === '#ffffff' || textColor === '#fff';` re-derives the theme from a magic value that happens to match darkColors.textColor in hooks/useDarkMode.ts. The sibling StackedPercentageChart receives an explicit `isDark: boolean` prop. If the dark palette's textColor is ever tuned (e.g. to '#e5e5e5'), the gauge silently renders the light-mode track on dark background with no type error. This is a discovered implementation detail, not an injected interface.

**Fix:** Add an `isDark?: boolean` prop (as StackedPercentageChart already does) and pass it from ResourceSection; drop the string comparison.

### `frontend/src/pages/AdminUsers.tsx:112` — Logout is a no-op for SAML-authenticated admins

*Category: correctness · verifier confidence: high*

handleLogout only calls adminClient.logout() (clears localStorage) and navigate('/admin/login'). AdminLogin's checkSamlAuth effect then finds the still-live SAML session, silently re-issues an admin token via /api/admin/saml-token, and redirects straight back to /admin/clusters. The same pattern exists in ClusterPage.tsx line 107 (onClick={() => { adminClient.logout(); navigate('/admin/login'); }}). Only AdminClusters.tsx redirects to the SAML logout endpoint. So a SAML admin clicking Logout on AdminUsers or ClusterPage bounces back in, logged in.

**Fix:** Extract one shared logout helper (redirect to the SAML logout endpoint, as AdminClusters does) and use it from all three admin pages.

### `frontend/src/pages/AdminClusters.tsx:40` — SAML logout uses a relative URL instead of the API base

*Category: correctness · verifier confidence: high*

handleLogout does window.location.href = '/saml/logout?redirect_to=/admin/login'. Every other SAML redirect (components/Header.tsx lines 22 and 93) prefixes `${import.meta.env.VITE_API_URL || 'http://localhost:8100'}`. When the frontend is served from a different origin than the backend (the dev setup this fallback implies), '/saml/logout' hits the SPA origin, where the router's '*' catch-all swallows it and the SAML session is never terminated.

**Fix:** Build the URL from the same VITE_API_URL base used in Header.tsx (ideally via the shared logout helper from the logout finding).

### `frontend/src/components/ReportGenerator.tsx` — ReportGenerator.tsx (537 LOC) is never imported anywhere

*Category: dead-code · verifier confidence: high*

grep across src/ finds no import of ReportGenerator; Dashboard.tsx uses ReportControls + ReportPreview instead, which duplicate this file's controls UI, print CSS, and report layout. The file also carries its own copy of the ReportData interface (identical to the one exported from ReportPreview.tsx) and its own useQuery. Notably it contains the only implementation of incomplete-period disabling (isCompletePeriod marks current month/quarter/year options as '(incomplete)' and disabled) - the live path via ReportControls lost that behavior, so users can currently select incomplete periods with no warning.

**Fix:** Delete ReportGenerator.tsx. If the incomplete-period disabling is wanted, port isCompletePeriod into ReportControls first, then remove the file.

### `frontend/src/components/Footer.tsx:37` — API Documentation link hardcodes http://localhost:8100/docs

*Category: correctness · verifier confidence: high*

The footer link `href="http://localhost:8100/docs"` points at the developer's machine, so in any deployed environment it is broken for users. The same file already uses a relative '/api/dashboard/version' for the version fetch, and Header.tsx uses `import.meta.env.VITE_API_URL || 'http://localhost:8100'` for its backend URLs - the footer follows neither pattern.

**Fix:** Use `${import.meta.env.VITE_API_URL || ''}/docs` (or a relative path proxied like the version endpoint) so the link works in production.

### `frontend/src/components/reports/ReportTimelines.tsx:61` — Users/Jobs chart captions hardcode 'each day'/'daily' regardless of report type

*Category: correctness · verifier confidence: high*

The component computes timeUnit from reportType (Daily/Weekly/Monthly) and uses it for the CPU and GPU chart titles/captions, but the Active Users caption (line 61: 'unique active users each day') and Submitted Jobs caption (line 130: 'jobs submitted daily') hardcode daily wording. For quarterly reports the points are weekly aggregates and for annual reports monthly aggregates, so the captions misstate what the data shows.

**Fix:** Use timeUnit in these two captions the same way the CPU/GPU charts do.

### `frontend/src/components/reports/reportHelpers.ts:27` — Formatting helpers duplicate src/utils/format.ts with colliding names and divergent behavior

*Category: consistency · verifier confidence: high*

reportHelpers exports formatNumber (byte-identical to utils/format.formatNumber), formatCompact (near-duplicate with different <1000 behavior: rounds vs. not), and formatHours whose behavior is entirely different from utils/format.formatHours (plain 2-decimal number vs. converting to 'min'/'hours'/'days' units). StatsCards imports from utils/format while all report components import from reportHelpers, so the same function name produces different output depending on which sibling module a component happens to import - a forked-utility hazard the project rules explicitly prohibit.

**Fix:** Delete the duplicates from reportHelpers.ts and import formatNumber/formatCompact from ../utils/format; rename the report-specific hours formatter (e.g. formatHoursValue) or fold its behavior into the shared module.

### `frontend/src/components/reports/ReportTimelines.tsx:83` — Hardcoded metric colors bypass the theme palette

*Category: consistency · verifier confidence: high*

The current-period Users line uses '#10b981' (line 83) and the Jobs line '#8b5cf6' (line 152) instead of COLORS.users / COLORS.total_jobs from theme/colors.ts, which the file already imports and uses for CPU/GPU. Combined with StatsCards using yet another hardcoded set (users '#64748B' slate, jobs '#6f42c1'), the same metric is rendered in three different colors across the dashboard and report views despite colors.ts declaring the COLORS map 'consistent across all views'.

**Fix:** Use COLORS.users and COLORS.total_jobs here, and reconcile the theme palette with the intended SECTION_COLORS scheme (users slate, jobs violet) in one place that both StatsCards and the report components consume.

### `frontend/src/utils/format.ts` — Number/hour formatting is forked across three modules with diverging behavior

*Category: consistency · verifier confidence: high*

`formatNumber` and `formatCompact` exist both in utils/format.ts and components/reports/reportHelpers.ts, and the copies disagree: for values < 1000 the utils formatCompact uses a thousands-separated Intl format while the reportHelpers copy uses Math.round().toString(). `formatHours` exists three times with three different meanings: utils/format.ts returns '30.0 min'/'1.2 hours'/'2.0 days', reportHelpers.ts returns a bare number with 2 decimals (callers append 'h' themselves), and hooks/useTimingStats.ts returns '30m'/'1.2h'/'2.0d'. The same quantity is therefore formatted differently depending on which screen renders it, and fixes must land in three places. The project rule forbids forked shared functionality.

**Fix:** Consolidate into utils/format.ts as the single formatting module (rename the reportHelpers formatHours to formatDecimalHours or similar since it does something different), and have reportHelpers, useTimingStats/TimingSection and StatsCards import from it.

### `frontend/src/hooks/useTimingStats.ts:35` — waitMedian/waitP95 are means of per-period medians/p95s but are labeled 'Median'/'P95'

*Category: naming · verifier confidence: high*

`waitMedian: calcAverage(waitStats?.median)` computes the unweighted arithmetic mean of the per-period median values from the trend series (same for waitP95, durationMedian, durationP95), and TimingSection.tsx renders these under the labels 'Median' and 'P95'. The mean of per-period medians is not the median of the filtered jobs: quiet periods with a handful of jobs weigh exactly as much as busy ones, so the displayed number can differ substantially from the true median/p95 of the selected window. The field names and UI labels overstate what is computed.

**Fix:** Either have the backend return overall median/p95 for the filtered window (it already computes the per-period stats) and display those, or rename the fields (e.g. meanOfPeriodMedians) and label the tiles honestly (e.g. 'Avg period median').

## Low severity (32 confirmed)

### `src/slurm_usage_history/app/duckdb_datastore.py:621` — Opposite canonical column names to PandasDataStore for CPU/GPU allocation

*Category: consistency · verifier confidence: high*

DuckDBDataStore.filter normalizes `AllocCPUS`->`CPUs` and `AllocGPUS`->`GPUs` (lines 621-624), while PandasDataStore._transform_data normalizes the exact opposite direction, `CPUs`->`AllocCPUS` and `GPUs`->`AllocGPUS` (datastore.py lines 356-363). backend/app/datastore_singleton.py documents PandasDataStore as the drop-in fallback for the same chart consumers, so the columns delivered to chart code differ depending on which store is active — code written against one store silently loses the allocation columns under the other.

**Fix:** Pick one canonical set of column names, implement the normalization once in shared library code (e.g. alongside add_memory_columns), and use it from both stores.

### `src/slurm_usage_history/app/datastore.py:651` — account_segments override leaks mutated state on error and across threads

*Category: correctness · verifier confidence: high*

In `filter()`, the account_segments path mutates the shared singleton formatter (`self.account_formatter.max_segments = account_segments`), applies formatting, then restores. If `df_filtered["Account"].apply(...)` raises, control jumps to the `except` at line 664 and the restore at line 660 never runs, leaving the global formatter permanently reconfigured for all subsequent requests. The temporary mutation is also visible to concurrent requests (the backend serves FastAPI threads), so parallel filters can format with the wrong segment count.

**Fix:** Wrap the mutation in try/finally, or better, make format_account accept max_segments as an argument instead of mutating shared state.

### `src/slurm_usage_history/app/account_formatter.py:19` — lru_cache is cleared on every call, so nothing is ever cached

*Category: correctness · verifier confidence: high*

`format_account` executes `self._format_account_cached.cache_clear()` unconditionally before every lookup (comment says 'Clear cache if needed', but there is no condition). The `@lru_cache(maxsize=1000)` on `_format_account_cached` therefore never retains an entry across calls; the cache and its noqa justification are dead weight and the code misrepresents itself as cached.

**Fix:** Clear the cache only when configuration changes (e.g. in a max_segments/separator setter) and remove the per-call clear, or drop the lru_cache entirely.

### `src/slurm_usage_history/scripts/waiting_times.py:94` — Doubled braces in f-string print the literal placeholder

*Category: correctness · verifier confidence: high*

`print(f"JobID {job_id} | ... | Waiting: {{waiting_time_seconds}} seconds")` — the doubled braces escape interpolation, so the log line shows the literal text `{waiting_time_seconds}` instead of the value.

**Fix:** Use single braces: `{waiting_time_seconds}`.

### `src/slurm_usage_history/scripts/waiting_times.py:111` — add_mock_job and the mock_jobs machinery are dead code

*Category: dead-code · verifier confidence: high*

`add_mock_job` is never called anywhere in the source tree or tests (grepped the whole repo; only definitions and self-references inside this file). The `self.mock_jobs` dict and `new_pending_jobs.update(self.mock_jobs)` in fetch_pending_jobs exist solely to serve it — test scaffolding shipped in a production entry point. Also lines 59-60 assign `completed_jobs = []` / `new_jobs = []` and immediately overwrite both.

**Fix:** Delete add_mock_job, mock_jobs, the update() call, and the two dead initial assignments.

### `backend/app/core/saml_auth.py:12` — saml_auth bypasses Settings (os.getenv) and its module-level settings instance is unused

*Category: consistency · verifier confidence: high*

`settings = get_settings()` at line 12 is never referenced in the file (verified by reading the whole module) — dead code. Instead the module reads SECRET_KEY, ENABLE_SAML, and SAML_SETTINGS_PATH via os.getenv, diverging from every sibling (admin_auth uses settings.admin_secret_key). This only works because config.py calls load_dotenv() at import time, a hidden coupling; and it leaves `Settings.secret_key` (core/config.py:23) defined but never read anywhere in the repo (verified by grep). The function-local `import jwt` / `from datetime import ...` at lines 106 and 141-143 also diverge from the top-level import style of the sibling auth modules.

**Fix:** Route SECRET_KEY through settings.secret_key, add enable_saml and saml_settings_path fields to Settings, delete the unused module-level settings assignment, and move the jwt/datetime imports to the top of the file.

### `backend/app/core/admin_auth.py:32` — get_password_hash is never called; create_admin.py forks the hashing logic with passlib

*Category: dead-code · verifier confidence: high*

Repo-wide grep finds no caller of `get_password_hash` — the only place passwords are hashed is backend/create_admin.py, which independently uses `passlib.CryptContext(schemes=["bcrypt"])` while this module verifies with `bcrypt.checkpw` directly. That is dead code plus a fork of the same functionality in two libraries; if the passlib format or ident ever diverges from what bcrypt.checkpw accepts, logins break with no test catching it.

**Fix:** Have create_admin.py import and use get_password_hash (single bcrypt implementation), or delete get_password_hash and standardize on one library in both places.

### `backend/app/models/admin_models.py:97` — AdminUser model is never used anywhere

*Category: dead-code · verifier confidence: high*

Repo-wide grep (backend, src, tests) finds only the definition of `class AdminUser(BaseModel)`. It is also the sole use of `EmailStr`, which drags in the email-validator dependency for nothing. Per the project rule, code written but never reached must be wired in or deleted.

**Fix:** Delete AdminUser and the EmailStr import.

### `backend/app/main.py:132` — GET /api endpoint is unreachable when the frontend is served

*Category: correctness · verifier confidence: high*

The SPA catch-all `@app.get("/{full_path:path}")` (line 104) is registered before `@app.get("/api")` (line 132). Starlette matches routes in registration order, so GET /api is captured by serve_frontend, whose `full_path.startswith(("api", ...))` check raises 404. The api_info endpoint only works in the no-frontend fallback mode. The same bare-prefix check also 404s any legitimate SPA route beginning with "api", "docs" or "saml" (e.g. /docs-help).

**Fix:** Register the /api route before the catch-all (or mount the SPA handler last via a sub-application), and match reserved prefixes as path segments ("api/", exact "api") rather than raw string prefixes.

### `backend/app/api/charts.py:338` — _empty_charts_response omits seven keys the populated response contains

*Category: consistency · verifier confidence: high*

The empty response lacks active_users_distribution, jobs_distribution, job_duration_stacked, waiting_times_stacked, waiting_times_trends, job_duration_trends and user_activity_frequency, all of which are present in charts_data on the populated path; node_cpu_usage/node_gpu_usage/node_memory_usage also lack the total_hours field the populated path adds. A filter that matches no jobs returns a differently-shaped payload, so any frontend code reading these keys sees undefined only in the empty case.

**Fix:** Make _empty_charts_response enumerate exactly the keys the populated branch produces (ideally derive both from one schema) and include total_hours: null on the node usage entries.

### `backend/app/api/dashboard.py:17` — sys.path hack and PandasDataStore/DuckDBDataStore imports are dead

*Category: dead-code · verifier confidence: high*

Lines 13-21 insert src/ into sys.path and import PandasDataStore/DuckDBDataStore with an ImportError fallback, but grep confirms neither name is used anywhere else in the module - all datastore access goes through get_datastore() from datastore_singleton (which does its own sys.path insertion). The comment 'after optional-import fallback' on line 27 justifies an ordering that no longer has a reason to exist.

**Fix:** Delete lines 13-21 and move the datastore_singleton import to the top import block.

### `backend/app/api/charts.py:61` — Runtime import of DuckDBDataStore/PandasDataStore is unused

*Category: dead-code · verifier confidence: high*

The TYPE_CHECKING import (line 58) covers the only typing use; the runtime try/except import at lines 60-65 binds names never referenced elsewhere in the module (grep confirms only the import lines match). The sys.path.insert at line 55 exists solely to serve this dead import.

**Fix:** Delete the sys.path.insert and the runtime try/except import, keeping only the TYPE_CHECKING import.

### `backend/app/config.py:293` — ClusterConfig.get_hardware_defaults has no callers

*Category: dead-code · verifier confidence: high*

Grep across backend/, src/, frontend/src/ and tests/ finds only the definition (`def get_hardware_defaults`) - nothing calls it. It also hardcodes invented capacity defaults (48/4, 24/0), which the project's domain rules say must not be used as capacity.

**Fix:** Delete the method.

### `backend/app/services/reports/pdf_charts.py:17` — Four chart functions are never called anywhere

*Category: dead-code · verifier confidence: high*

create_timeline_chart (line 17), create_pie_chart (line 117), create_cumulative_chart (line 263), and create_stacked_bar_chart (line 322) have no references anywhere in backend, src, scripts, or tests (grep over the whole tree finds only their definitions). Only create_bar_chart and create_comparison_timeline are imported by report_formatters.py. This is roughly 250 of the file's 382 lines. Project rule: remove code that is written but never reached.

**Fix:** Delete the four unused functions (and the then-unused base_colors/pie logic).

### `backend/app/services/charts/memory_generators.py:27` — generate_memory_per_job docstring claims '20 most common sizes' but code returns the 20 smallest sizes

*Category: docstring · verifier confidence: high*

The docstring says "Distribution of requested memory per job in whole GB (20 most common sizes)" but the implementation is `counts = gb.value_counts().sort_index().head(20)`: value_counts is re-sorted by memory size (the index) before head(20), so the result is the 20 smallest distinct sizes, not the most common. A cluster where large requests dominate would show none of them. The sibling generators (generate_cpus_per_job etc.) use the same sort_index().head(20) pattern, so the code is likely intentional and the docstring is wrong.

**Fix:** Either fix the docstring to "(20 smallest distinct sizes)" or, if most-common is the intended behavior, use `.value_counts().head(20).sort_index()` and update the sibling generators consistently.

### `backend/app/services/charts/distribution_generators.py:864` — generate_user_activity_frequency docstring says only color_by='User' triggers pie mode, but Account/Partition/QOS do too

*Category: docstring · verifier confidence: high*

Docstring: 'When color_by is None or not "User": Shows histogram ... When color_by="User": Shows pie chart'. The code at line 919 defines `pie_chart_dimensions = ["User", "Account", "Partition", "QOS"]` and produces a pie of summed user-periods for the non-User dimensions as well. The documented contract and the implemented behavior disagree.

**Fix:** Update the docstring to describe the Account/Partition/QOS pie mode (sum of active periods across users per group), or restrict pie mode to "User" if that was the intent.

### `backend/app/services/charts/distribution_generators.py:527` — _aggregate_period_distribution has two never-used parameters and an unreachable color_by branch

*Category: dead-code · verifier confidence: high*

`metric_name` and `allowed_pie_dimensions` are suppressed with `# noqa: ARG001 (part of the aggregation interface)` and never read. Both callers (generate_active_users_distribution line 651 and generate_jobs_distribution line 715 — verified by grep, there are no others) hard-code `color_by=None`, so the entire `if color_by and color_by in df.columns:` branch (lines 539-550) can never execute. This violates the project rule against code written but never reached; the noqa comments name an aspirational interface that nothing uses.

**Fix:** Delete metric_name, allowed_pie_dimensions, and the color_by parameter/branch; the function then takes (df, period_type, agg_func) and both call sites simplify.

### `backend/app/services/charts/distribution_generators.py` — File exceeds the 1000-LOC limit (1038 lines) — known; natural split exists

*Category: design · verifier confidence: medium*

distribution_generators.py is 1038 lines against the project's 1000-line rule. It currently mixes four concerns: bin/color constants, generic aggregation helpers (_get_time_column, _generate_stacked_distribution, _generate_trends, _aggregate_value_histogram, _aggregate_period_distribution), the per-dimension distribution charts, and the unrelated wait/duration scatter (generate_wait_duration_scatter plus DISPLAY_FLOOR_HOURS, appended at the bottom and imported separately in __init__.py line 78).

**Fix:** Move generate_wait_duration_scatter into its own module (it shares nothing with the histogram machinery) and move the bin constants plus the generic private helpers into chart_helpers.py; removing the dead functions flagged above also recovers ~60 lines.

### `frontend/src/components/charts/index.ts` — Barrel file is never imported anywhere

*Category: dead-code · verifier confidence: high*

Grepped the whole frontend source tree (excluding node_modules/dist): no file imports from 'components/charts' or 'charts/index'. Every consumer imports component files directly (e.g. `import StackedAreaChart from '../StackedAreaChart'`, `import { createGlobalColorMap } from './charts/chartHelpers'`). The barrel's comment also misdescribes itself ('Export all chart components') while omitting ScatterChart, ChartCaption, StackedPercentageChart, Plot, and resourceConfigs. Per the project rule 'code that is written but never reached is dead code', this file is dead.

**Fix:** Delete frontend/src/components/charts/index.ts, or make it the single import surface and convert all consumers to use it. Deleting matches the existing direct-import convention.

### `frontend/src/components/charts/chartHelpers.ts:140` — hardware_config customdata/hovertemplate block duplicated three times in generateChartTraces

*Category: consistency · verifier confidence: high*

The identical block that maps `chartData.x` to `Configured: ${hw.cpu_cores} cores, ${hw.gpu_count} GPUs` customdata strings and switches the hovertemplate appears verbatim at ~lines 137-151 (aggregated bar), 185-200 (stacked bar), and 249-264 (single-series bar). Any change to the hover wording or to NodeHardwareConfig fields (e.g. surfacing memory_gb, which the type already carries) must land in three places.

**Fix:** Extract a helper, e.g. `buildHardwareHover(chartData): { customdata?: string[]; hovertemplate: string }`, and call it from the three bar branches.

### `frontend/src/components/charts/sections/UsersJobsSection.tsx:158` — Jobs Distribution histogram caption describes the wrong quantity

*Category: correctness · verifier confidence: high*

The fallback caption is `<ChartCaption text={dim ? `Share of all jobs per ${dim}.` : 'Distribution of jobs per user.'} />`. The fallback branch fires exactly when color_by is unset, and in that mode the backend (generate_jobs_distribution in backend/app/services/charts/distribution_generators.py, docstring: 'When color_by is None: Shows histogram of jobs per period distribution') returns a histogram of jobs per period, which is why the chart's own axis titles are xTitle="Jobs per Period" / yTitle="Count" (lines 147-148). The caption tells the user the chart shows jobs per user, which it never does.

**Fix:** Change the fallback caption to describe jobs per period, e.g. 'Distribution of jobs submitted per period.'

### `frontend/src/components/charts/sections/UsersJobsSection.tsx:92` — User Activity Frequency caption misstates the axes and is reused for pie mode

*Category: docstring · verifier confidence: high*

The caption 'How many periods each user was active in: users on the x-axis grouped by number of active periods.' is wrong on the axes: the histogram puts the number-of-active-periods bins on the x-axis (xTitle=`Active ${period_label}`, line 81) and the count of users on the y-axis (yTitle="Number of Users", line 82). Additionally the same caption is rendered unconditionally for the pie variant (colorBy User/Account/Partition/QOS), where there is no x-axis and the content is top users or user-periods per group. Every sibling card in this file and in TimingSection/ResourceSection switches its caption between pie and histogram mode (e.g. line 158 here, TimingSection lines 172/212, ResourceSection byDimCaption); this card is the only one that does not.

**Fix:** Fix the axis wording (e.g. 'Number of users per count of active periods.') and branch the caption on data.user_activity_frequency.type === 'pie' like the sibling cards do.

### `frontend/src/components/charts/sections/TimingSection.tsx:67` — Waiting-time color hardcoded instead of SECTION_COLORS.waiting, leaving the palette token dead

*Category: consistency · verifier confidence: high*

TimingSection passes defaultColor="#dc3545" as a raw literal in two places (line 67 for Waiting Time Trends, line 163 for the waiting-times histogram), while the duration charts in the same file correctly use SECTION_COLORS.duration (lines 103, 203, 232). SECTION_COLORS.waiting is defined as '#DC3545' in chartHelpers.ts exactly for this purpose, and a grep across frontend/src shows it is referenced nowhere — the intentional palette token is dead code while its value is duplicated as a differently-cased literal. If the palette is ever adjusted, the waiting charts silently diverge.

**Fix:** Use defaultColor={SECTION_COLORS.waiting} at lines 67 and 163.

### `frontend/src/pages/AdminUsers.tsx:19` — Auth-header logic and admin API calls duplicated in page components

*Category: consistency · verifier confidence: high*

AdminUsers.tsx defines getAuthHeaders() as a verbatim copy of AdminClient's private getAuthHeaders, and calls /api/admin/admin-emails with raw fetch. AdminClusters.tsx lines 65-78 does the same for /api/admin/generate-demo-cluster (re-declaring API_BASE_URL locally), and AdminLogin.tsx lines 23-28 raw-fetches /api/admin/saml-token. adminClient even exposes authHeaders() specifically 'for admin API calls made outside this client' and clusterAdminApi uses it. Every other admin endpoint lives in the api/ layer; these three are forked into pages, so error handling and auth behavior can drift.

**Fix:** Move getAdminEmails/updateAdminEmails, generateDemoCluster, and the saml-token exchange into adminClient (or clusterAdminApi's request helper) and delete the page-local fetch plumbing.

### `frontend/src/pages/AdminUsers.css` — Large unused style blocks left over from a removed Admin Config page

*Category: dead-code · verifier confidence: high*

The file header still says 'Admin Config Page Styles' and roughly half the file styles UI that AdminUsers.tsx never renders. Grep across all .tsx/.ts finds zero uses of: .admin-control-panel, .admin-controls, .admin-cluster-selector, .admin-button-group, .admin-stats-grid, .admin-stat-card (+ stat-primary/purple/blue/green/orange/indigo), .admin-stat-value/.admin-stat-label, .admin-tabs/.admin-tab, .admin-search-filters/.admin-search-grid/.admin-search-input/.admin-filter-select/.admin-filter-result, .admin-badge (+ color variants), .admin-synonym-pills/.admin-synonym-pill, .admin-hardware-cards/.admin-hardware-card (+ hw-cpu/hw-ram/hw-gpu), .admin-empty/.admin-empty-icon/.admin-empty-message, and .admin-header-title .emoji. The /admin/config route itself is now just a Navigate redirect in App.tsx.

**Fix:** Delete the unused rule blocks and retitle the file to match the AdminUsers page.

### `frontend/src/pages/AdminUsers.tsx:144` — Nav link 'Configuration' points to a removed page

*Category: dead-code · verifier confidence: high*

<a href="/admin/config">Configuration</a> targets a route that App.tsx line 29 immediately redirects to /admin/clusters (the config page was removed). The link is misleading; no other admin page links to /admin/config.

**Fix:** Remove the Configuration nav link (and consider removing the /admin/config redirect route once nothing references it).

### `frontend/src/components/reports/ReportOverview.tsx` — ReportOverview.tsx (148 LOC) is never imported anywhere

*Category: dead-code · verifier confidence: high*

grep across src/ finds no importer. ReportSummaryCards.tsx duplicates its entire content (renderComparisonIndicator and the four summary cards are copy-pasted verbatim) and is the component actually rendered by ReportPreview/Dashboard.

**Fix:** Delete frontend/src/components/reports/ReportOverview.tsx.

### `frontend/src/api/client.ts:67` — dashboardApi.filterData, getHealth and getClusterStats are never called

*Category: dead-code · verifier confidence: high*

Grep across frontend/src (and no e2e/tests dirs exist) finds no caller of `filterData`, `getHealth`, or `getClusterStats` outside their definitions in api/client.ts (lines 68, 78, 88). Only `getMetadata` and `getAggregatedCharts` are used by Dashboard.tsx, and `previewReport`/`downloadReport` from reportsApi are used. The project rule is explicit: code written but never reached is dead code.

**Fix:** Delete filterData, getHealth and getClusterStats from dashboardApi (or wire them into the UI if the endpoints are meant to be reachable).

### `frontend/src/types/index.ts:1` — JobRecord, FilterResponse, HealthResponse, ClusterStats and two FilterRequest fields are unreferenced

*Category: dead-code · verifier confidence: high*

`JobRecord`, `FilterResponse`, `HealthResponse` and `ClusterStats` are only imported by the dead dashboardApi methods (filterData/getHealth/getClusterStats). `FilterRequest.complete_periods_only` and `FilterRequest.normalize_node_usage` are never set by any caller: useOverviewFilters builds the only FilterRequest in the codebase (lines 126-141) and omits both; node-usage normalization is handled client-side in utils/nodeChart.ts. The inline comment on line 36 even documents that hide_unused_nodes/sort_by_usage were removed for the same reason but leaves normalize_node_usage behind.

**Fix:** Remove the four unused interfaces together with the dead client methods, and drop complete_periods_only and normalize_node_usage from FilterRequest (or send normalize_node_usage if the backend still honors it).

### `frontend/src/theme/colors.ts:28` — STATE_COLORS and SECTION_COLORS in theme/colors.ts are never imported

*Category: dead-code · verifier confidence: high*

Grep shows every import of '../theme/colors' pulls only `COLORS` or `PARTITION_COLORS` (ReportSummaryCards, ReportOverview, ReportDistributions, ReportBreakdowns, ReportTimelines). `STATE_COLORS` (line 28) and `SECTION_COLORS` (line 38) have zero importers. Worse, the live palette actually used by the dashboard is a different `SECTION_COLORS` defined in components/charts/chartHelpers.ts (users slate, jobs violet, cpu #04A5D5, gpu #EC7300, memory green, waiting red, duration teal) with entirely different keys ({summary, duration, waiting, resources} here vs {users, jobs, cpu, gpu, memory, waiting, duration} there). Two exports with the same name and different contents invite importing the wrong one.

**Fix:** Delete STATE_COLORS and SECTION_COLORS from theme/colors.ts; if a section palette belongs in the theme module, move the chartHelpers SECTION_COLORS here instead so there is exactly one definition.

### `frontend/src/utils/format.ts:12` — formatDate, formatDateTime and formatHours in utils/format.ts are never imported

*Category: dead-code · verifier confidence: high*

The only import of utils/format in the tree is `import { formatNumber, formatCompact } from '../utils/format'` in components/StatsCards.tsx. `formatDate` (line 12), `formatDateTime` (line 21) and `formatHours` (line 32) have no importers; `formatDecimal` is exported but only used internally by this file. Meanwhile pages/AdminClusters.tsx:128, pages/cluster/OverviewTab.tsx:23 and pages/cluster/CredentialsPanel.tsx:17 each define their own local formatDate instead of using this one.

**Fix:** Either make the pages import the shared formatDate/formatDateTime and keep them, or delete the unused exports. Un-export formatDecimal if it stays internal-only.

### `frontend/src/api/adminClient.ts:103` — Error paths call response.json() unguarded and most methods discard the backend detail

*Category: correctness · verifier confidence: high*

In login (line 103), createCluster (line 172) and reloadData (line 238), the failure branch does `const error = await response.json()` with no catch: a non-JSON error body (proxy 502/504 HTML, empty body) makes the thrown error a SyntaxError ('Unexpected token ...') instead of the intended message. The sibling module clusterAdminApi.ts already solves this with `response.json().catch(() => ({}))`. The remaining methods (getClusters, getCluster, updateCluster, deleteCluster, rotateAPIKey, generateDeployKey) do not read the body at all and throw fixed strings, silently dropping the backend's `detail` that the other methods surface — inconsistent error handling within one class.

**Fix:** Extract one request helper (or reuse the clusterAdminApi pattern) that parses detail with a .catch fallback and use it for every AdminClient method.

## Refuted

- frontend/src/pages/Dashboard.tsx:147 No-data guard uses filtered metadata and hides the filter sidebar — the verifier reproduced the scenario and found the behavior correct.

## Appendix: unverified notes

63 lower-confidence findings that did not go through adversarial verification. Treat as leads, not confirmed defects.

- `backend/app/api/admin.py:269` [dead-code] create_cluster re-imports logging and shadows the module logger: Inside create_cluster: `import logging` / `logger = logging.getLogger(__name__)` (lines 269-271) recreates the logger already defined at module level (line 31), shadowing it for no reason. Similar deferred re-imports of json/Path/datetime appear in get_admin_emails, update_admin_emails and get_deplo

- `backend/app/api/admin.py:565` [correctness] deploy-key expiry check uses deprecated naive datetime.utcnow(): `is_expired = datetime.utcnow() > expires_dt` works only because generate_deploy_key also stores naive `datetime.utcnow().isoformat()` (backend/app/db/clusters.py:259-263); datetime.utcnow() is deprecated on Python 3.12 (in the supported range), and the implicit naive-UTC pairing between two modules

- `backend/app/api/agent.py:160` [docstring] health_check docstring documents a parameter that does not exist: The Args section documents `api_key: Verified API key from header`, but the parameter is `_api_key` and verify_agent_api_key actually returns the cluster name, not the key. Google-style docstrings must match the signature.

- `backend/app/api/dashboard.py:95` [consistency] Leftover per-request [METADATA] info logging with inline logging import: get_metadata imports logging and builds a logger inside the request handler, then logs four INFO lines tagged [METADATA] on every metadata request (initial hostnames, query param, filtered list, returned list). Siblings define `logger = logging.getLogger(__name__)` at module level; this is debug sca

- `backend/app/api/dashboard.py:72` [correctness] /version depends on repo-root _version.py being on sys.path: `from _version import __version__` imports a top-level module that hatch writes to the repository root (pyproject.toml: version-file = "_version.py"). It resolves only when the server's CWD/sys.path includes the repo root; in a packaged deployment or when started from backend/, the ImportError branc

- `backend/app/api/data.py:143` [typing] get_current_admin dependency annotated as dict but returns str: `admin: dict = Depends(get_current_admin)` - get_current_admin is annotated `-> str` (backend/app/core/admin_auth.py:89) and every other endpoint annotates the injected value as `_admin: str`. The dict annotation is wrong and the f-string log then prints the username as if it were a dict.

- `backend/app/config.py:40` [consistency] config module reports warnings/errors via print instead of logging: ClusterConfig uses print() for the missing-config warning (lines 40-41), load success (line 52) and load errors (line 54), while every other backend module logs through logging.getLogger(__name__). Config-load failures therefore bypass log handlers entirely. Note also that `Error loading config` swa

- `backend/app/core/admin_auth.py:61` [typing] verify_token annotates payload.get("sub") result as str though it can be None: `username: str = payload.get("sub")` — the very next line checks `if username is None`, so the annotation is dishonest. Should be `str | None = payload.get("sub")` (or drop the annotation).

- `backend/app/core/auth.py` [docstring] Missing module docstrings in core/auth.py, core/config.py, models/data_models.py: Sibling modules (admin_auth.py, agent_auth.py, saml_auth.py, db/clusters.py, admin_models.py) all open with a module docstring; core/auth.py, core/config.py, and models/data_models.py do not, diverging from the file-header convention.

- `backend/app/core/config.py:144` [dead-code] get_email_role and is_development are never called: Repo-wide grep finds no caller of `get_email_role` (line 144) or `is_development` (line 151); only `is_admin_email` and `is_production` are used (api/saml.py, api/admin.py). get_email_role's return annotation `str | None` is also inaccurate — it returns AdminRole values. Note the role distinction it

- `backend/app/db/clusters.py` [correctness] datetime.utcnow() is deprecated on supported Python 3.12 and yields naive timestamps: requires-python is ">=3.10,<3.13", so Python 3.12 is in range, where `datetime.utcnow()` emits DeprecationWarning. It is used throughout db/clusters.py (12 call sites), core/admin_auth.py (lines 42, 44), and core/saml_auth.py (lines 152-153). The naive datetimes are also compared against `datetime.f

- `backend/app/models/data_models.py:61` [dead-code] Comment documenting removed fields left in FilterRequest: `# Note: hide_unused_nodes and sort_by_usage removed - now handled client-side` documents code that no longer exists — the pattern the project rules say to delete rather than memorialize.

- `backend/app/services/charts/__init__.py:78` [consistency] Second import block placed after __all__, and section comments in __all__ no longer match the entries: Lines 78-87 import generate_wait_duration_scatter, the efficiency generators and the memory generators after the `__all__` list, diverging from the single top-of-file import block the module starts with (E402-style layout). Inside the alphabetized `__all__`, the grouping comments are stranded: "# Ti

- `backend/app/services/charts/distribution_generators.py:41` [consistency] DURATION_BINS and WAITING_TIME_BINS are identical copies of TIME_HISTOGRAM_BIN_EDGES: The 11 (label, min, max) tuples in DURATION_BINS (line 41) and WAITING_TIME_BINS (line 69) are element-for-element identical, and their edges restate TIME_HISTOGRAM_BIN_EDGES (line 25) — the constant the project rules designate as the shared source of truth for time bins. The max element of each tup

- `backend/app/services/charts/distribution_generators.py:306` [dead-code] generate_by_dimension: identity column_map and unreachable .get default: `column_map` maps each dimension name to itself ({"Account": "Account", ...}), so it adds nothing over a set of allowed names, and `group_column = column_map.get(group_by, "Account")` (line 370) can never use the "Account" default because line 315 already returned when `group_by not in column_map`.

- `backend/app/services/charts/distribution_generators.py:362` [consistency] generate_by_dimension histogram return shapes are inconsistent between metrics: The hours-metric histogram branch returns `"type": "histogram"` (line 342) but no bin_labels; the job-count histogram branch (line 362) returns `bin_labels` but omits the `type` key entirely, and its empty-guard returns (lines 347, 352) also lack it. A frontend switching on `type` sees an untyped pa

- `backend/app/services/charts/timeline_generators.py:63` [dead-code] No-op string replace when resolving the fallback time column: `time_column = time_column_map.get(period_type, fallback_month_col.replace("YearMonth", "YearMonth"))` — replacing "YearMonth" with "YearMonth" returns the string unchanged. The .replace call is a confusing leftover that suggests a transformation that never happens.

- `backend/app/services/charts/timeline_generators.py:83` [dead-code] `df_copy is df` guards are always False after the unconditional copy: Line 79 executes `df_copy = df_copy[needed].copy()`, so from that point `df_copy is df` can never be True. The three conditionals that depend on it — line 83 `df_copy.copy() if df_copy is df else df_copy`, line 89-91 (filter_nulls) and line 96 (filter_positive) — always take the else branch; the def

- `backend/app/services/cluster_config_store.py` [consistency] ClusterConfigStore and NodeDiscoveryService write clusters.yaml with divergent dump settings: Both classes independently implement load/dump of the same clusters.yaml file. ClusterConfigStore.update_cluster dumps with allow_unicode=True (line 38); NodeDiscoveryService._write_config and discover_and_update_nodes dump without it (node_discovery.py:101, 199). A cluster description containing no

- `backend/app/services/node_discovery.py:54` [consistency] discover_and_update_nodes duplicates config I/O instead of using _load_config/_write_config: sync_cluster loads and writes clusters.yaml through the class helpers _load_config/_write_config, while discover_and_update_nodes inlines its own open/yaml.safe_load (lines 54-59) and open/yaml.dump (lines 99-108), each wrapped in a broad 'except Exception' that logs and returns 0, silently swallowi

- `backend/app/services/reports/pdf_charts.py` [typing] Return annotations say Image but every function can return None: All six chart functions are annotated '-> Image' yet return None when their input data is empty (e.g. 'if not timeline_data: return None'). Callers in report_formatters.py already guard with 'if users_chart:', confirming the real contract is Image | None.

- `backend/app/services/reports/report_formatters.py:147` [dead-code] Bare expression styles["Normal"] has no effect: Line 147 is the standalone statement 'styles["Normal"]' - it subscripts the stylesheet and discards the result. Leftover from a removed variable assignment.

- `backend/app/services/reports/report_formatters.py:100` [docstring] format_hours_readable docstring examples are unproducible: The docstring gives examples "'1,234.5 hours' or '51.4 days'", but the hours branch only fires below 24 (max '23.9 hours') and the days branch only below 168 hours (max '6.9 days'); 1,234.5 hours would render as '7.3 weeks'. Both examples can never be output.

- `backend/app/services/reports/report_generator.py:51` [consistency] Empty-period branch returns {} for stats while non-empty path returns keyed stats dicts: The empty branch returns "job_duration_stats": {} and "waiting_time_stats": {}, but calculate_duration_stats/calculate_waiting_time_stats on an empty DataFrame already return the full zeroed shape via _empty_stats() (report_helpers.py:65-75). The two paths therefore produce different response shapes

- `backend/app/services/reports/report_generator.py:177` [dead-code] Sorting the always-empty by_user list is dead logic: by_user is hardcoded to [] (line 104, intentionally, for privacy), yet the return statement sorts it with 'sorted(by_user, key=lambda x: x["cpu_hours"], reverse=True)' - a sort key that can never execute. The lambda suggests per-user aggregation that no longer exists.

- `frontend/src/api/client.ts:27` [consistency] Debug console.log statements left in the 401 redirect interceptors: Both interceptors log to the console before redirecting ('401 Unauthorized from apiClient - Redirecting to SAML login', line 27; the axios-global twin at line 42). These are leftover debug statements in production code; no other module in api/ or hooks/ logs on its happy or error paths.

- `frontend/src/components/ReportPreview.tsx:168` [correctness] Report cards mix hardcoded white/black with theme variables, breaking dark mode: The report page container hardcodes `background: 'white'` (line 168) while the header block inside it uses `background: 'var(--card-bg)'` with `color: '#000000'` text (lines 175-189). In dark mode --card-bg resolves to a dark color, producing black text on a dark card sitting on a white page. The sa

- `frontend/src/components/charts/HistogramChart.tsx:109` [correctness] `data.average || data.mean` treats a legitimate 0 average as missing: `createMedianMeanAnnotation(data.median, data.average || data.mean, ...)` uses `||`, so an `average` of exactly 0 falls through to `mean`, and if `mean` is also absent the annotation is suppressed even though a 0 average is valid data. types/index.ts documents both `mean` and `average` as alternativ

- `frontend/src/components/charts/ScatterChart.tsx:35` [consistency] Hover hardcodes an 'h' unit while axis titles already carry '(hours)': `hovertemplate: `${xTitle}: %{x:.2f}h<br>...`` bakes an hours suffix into an otherwise generic component (props claim arbitrary xTitle/yTitle), and at the single call site the titles are 'Job Duration (hours)' / 'Waiting Time (hours)', so the tooltip reads 'Job Duration (hours): 0.52h' — the unit is

- `frontend/src/components/charts/StackedPercentageChart.tsx:80` [consistency] Bypasses getCommonConfig, so modebar behavior diverges from every other chart: `config={{ responsive: true }}` omits `displayModeBar: 'hover'`, `displaylogo: false`, `modeBarButtonsToRemove`, and the PNG export options that getCommonConfig() applies to TimelineChart, HistogramChart, StackedAreaChart, ScatterChart, and PieChart. This chart alone shows the plotly logo and a perm

- `frontend/src/components/charts/chartHelpers.ts:138` [dead-code] hovertemplate initializers are unconditionally overwritten: In all three duplicated blocks the initial assignment (e.g. `let hovertemplate = '%{x}<br>Value: %{y:,.1f}';` at line 138, and the equivalents at lines 187 and 250) is dead: both the `if (chartData.hardware_config)` branch and the `else` branch reassign the variable before use. The initial value (wh

- `frontend/src/components/charts/chartHelpers.ts:299` [correctness] adjustColorForDarkMode silently produces '#NaNNaNNaN' for non-hex input: The function assumes a hex string: `parseInt(hex.substring(0,2), 16)` on an `rgb(...)`/`hsl(...)` value yields NaN and the function returns `#NaNNaNNaN` (invisible trace). The same module's generateColorFromIndex emits `hsl(...)` strings, so a plausible future caller feeds it a format it cannot pars

- `frontend/src/components/charts/sections/ResourceSection.tsx:97` [consistency] Inline hardcoded '#666' annotations do not adapt to dark mode: All three section components hardcode `color: '#666'` in inline styles for heading annotations and the unknown-capacity note (ResourceSection lines 97, 146, 161, 192; UsersJobsSection lines 60, 128, 165; TimingSection lines 144, 184, 222), while the sibling StackedPercentageChart uses `color: 'var(-

- `frontend/src/components/charts/sections/TimingSection.tsx:11` [consistency] Duplicate import statements from '../chartHelpers': Lines 11-12 import COLORS and SECTION_COLORS from '../chartHelpers' in two separate statements: `import { COLORS } from '../chartHelpers';` followed by `import { SECTION_COLORS } from '../chartHelpers';`. Sibling files (UsersJobsSection.tsx line 8) merge these into one import.

- `frontend/src/components/reports/ReportBreakdowns.tsx:63` [consistency] Top-10 CPU chart relies on backend ordering while the GPU chart sorts locally: The CPU chart uses `byAccount.slice(0, 10)` (lines 63-64), silently depending on the backend's sorted(by_account, key=cpu_hours, reverse=True); the GPU chart explicitly re-sorts with `[...byAccount].sort((a, b) => b.gpu_hours - a.gpu_hours)` (lines 110-111, computed twice for x and y). The two adjac

- `frontend/src/components/reports/ReportDistributions.tsx:90` [consistency] Area fill colors are leftover Plotly defaults that mismatch the line colors: The cumulative CPU chart line uses COLORS.cpu_hours (#04A5D5) but fills with 'rgba(99, 110, 250, 0.2)' (Plotly default blue #636EFA, line 90); the GPU chart line uses COLORS.gpu_hours (#EC7300) but fills with 'rgba(239, 85, 59, 0.2)' (Plotly default red #EF553B, line 157). Each area chart shows a fi

- `frontend/src/components/reports/ReportTimelines.tsx:67` [consistency] Previous-period traces take x from aligned data but y from the raw array: All four charts build the overlay as `x: alignPreviousPeriodDates(timeline, previousTimeline).map(d => d.date)` with `y: previousTimeline.map(d => d.users)` (lines 67-68, 136-137, 205-206, 274-275). alignPreviousPeriodDates slices previousTimeline to timeline.length, so when the previous period has

- `frontend/src/hooks/useTimingStats.ts:45` [consistency] Presentation helper formatHours lives in a hooks module: `formatHours` is a pure display formatter, not a hook, yet it is exported from hooks/useTimingStats.ts and imported by TimingSection.tsx from there. Sibling formatters live in utils/format.ts and components/reports/reportHelpers.ts, so the module boundary between hooks and formatting utilities is in

- `frontend/src/pages/AdminClusters.css` [dead-code] Unused selectors: clusters-api-key, clusters-copy-btn, action-warning, action-secondary: Grep across all .tsx finds no use of .clusters-api-key, .clusters-api-key code, .clusters-copy-btn, .clusters-action-btn.action-warning, or .clusters-action-btn.action-secondary; the API-key column and those action variants were removed from AdminClusters.tsx (keys now live in the ClusterPage Creden

- `frontend/src/pages/AdminClusters.tsx:123` [correctness] copyToClipboard reports success without awaiting the clipboard promise: navigator.clipboard.writeText(text) is fire-and-forget and alert('Copied to clipboard!') fires even when the write rejects (e.g. document not focused, permission denied), so the user can be told the one-time API key was copied when it was not. CredentialsPanel.tsx's copy() awaits the same call - div

- `frontend/src/pages/AdminClusters.tsx:223` [consistency] Creating a cluster skips the dashboard data reload that delete/toggle perform: handleDelete and handleToggleActive both call handleReloadData after the change 'so the cluster appears/disappears from the dropdown', but the CreateClusterForm onSuccess handler only calls loadClusters(), so a newly created cluster does not reach the dashboard dropdown until a manual reload. The de

- `frontend/src/pages/AdminLogin.tsx:43` [dead-code] Debug console.log left in the SAML auth check: console.log('SAML auth check failed, showing login form') in the catch block is leftover debug output; no other page logs to the console.

- `frontend/src/pages/AdminLogin.tsx:74` [dead-code] Empty login-icon divs and unused .login-error-icon rule: Both renders emit an empty <div className="login-icon"></div> (lines 74-75 and 94-95) that displays a blank styled circle, and AdminLogin.css defines .login-error-icon (line 66) which no TSX references - both leftovers of removed icon content.

- `frontend/src/pages/AdminUsers.tsx:169` [consistency] Emoji and symbol glyphs in UI strings: Line 169 renders an information emoji in the 'About Admin Access' card and line 345 renders a glyph-prefixed save label ('⎗ Save Changes'). The project rule forbids emojis in code; no other admin page uses them.

- `frontend/src/pages/AdminUsers.tsx:196` [consistency] Deprecated onKeyPress used for Enter handling: The two email inputs (lines 196 and 275) use onKeyPress, which React documents as deprecated; the sibling EditableCell component handles Enter/Escape with onKeyDown.

- `frontend/src/pages/Dashboard.tsx:139` [correctness] Loading screen hardcodes 'API: http://localhost:8100': <p className="loading-detail">API: http://localhost:8100</p> ignores VITE_API_URL, so the loading screen reports the wrong API address in any non-local deployment.

- `frontend/src/pages/cluster/EditableCell.tsx:49` [design] Select mode cannot represent or restore an empty value: When options are provided (NodesTab type column) and the current value is '' or not in NODE_TYPES, the controlled <select value={draft}> matches no option, so the control opens showing a blank selection, and there is no empty option to clear a type back to unset. The select branch also lacks the Ent

- `frontend/src/theme/colors.ts:3` [docstring] Header comment references backend/app/theme_colors.py, which does not exist: The file docstring says 'Keep in sync with backend/app/theme_colors.py'. No such file exists anywhere in the repository; the backend hardcodes its colors inline in backend/app/services/reports/pdf_charts.py and report_formatters.py. The sync instruction points maintainers at a phantom file.

- `frontend/src/utils/nodeChart.ts:36` [correctness] Normalized stacked series are capped at 100% per series, so stacked totals can exceed 100%: `scale` applies `Math.min(100, ...)` to each value independently. For a single-series chart this keeps the bar at or under 100%, but for stacked series each segment is capped separately, so a node's stacked total can reach N*100%. The test at nodeChart.test.ts:49 encodes this: two series scale to 75

- `scripts/cleanup_old_data.py:30` [consistency] Cleanup and consolidation scripts assume different directory layouts: cleanup_old_data.py scans `hostname_dir / "data"` only, while consolidate_data.py operates on `data_dir / "weekly-data"` only (and hardcodes the unrelated root /data/slurm-usage-history vs cleanup's /opt/slurm-usage-history/data). The datastore supports both layouts; each maintenance script silently

- `scripts/generate_test_cluster_data.py:605` [consistency] Help text and output directory disagree; CLI writes to the legacy directory layout: The --output-dir help says 'default: ./data/{cluster}/data' but line 629 writes to `data/{cluster}/weekly-data`. duckdb_datastore.py:197-200 treats `data` as the new structure and `weekly-data` as the legacy fallback, and the backend demo generation (config_admin.py) writes to `.../data`. The CLI de

- `scripts/generate_test_cluster_data.py:663` [correctness] Final instructions reference a nonexistent CLUSTER_*_DATA_PATH configuration mechanism: `print(f"  CLUSTER_{args.cluster.upper()}_DATA_PATH={output_dir}")` tells the user to set a per-cluster env var; grepping backend/ finds no code reading any `CLUSTER_*_DATA_PATH` variable (clusters are configured via the YAML config / DATA_PATH). The guidance is aspirational and misleads users.

- `scripts/generate_test_cluster_data.py:450` [correctness] MaxRSS string column contradicts MaxRSSMB in generated records: For COMPLETED jobs `max_rss = f"{random.randint(1000, 50000)}K"` (about 1-50 MB) while line 466 computes `max_rss_mb = round(req_mem_mb * used_fraction, 1)` (typically GB-scale) from an independent random draw. The two columns describing the same quantity disagree by orders of magnitude in every syn

- `src/slurm_usage_history/__init__.py:2` [docstring] Module docstring grammar error and dubious UserWarning catch: Docstring reads 'Dashboard for to display the usage history of a Slurm scheduler.' ('for to display'). Additionally, line 47 catches `UserWarning` in the except tuple; setuptools_scm only raises it as an exception under warning-as-error filters, so its presence documents a CI workaround that deserve

- `src/slurm_usage_history/app/datastore.py:11` [dead-code] Unreachable ImportError guard and duplicated formatter import: Module level: `try: from .account_formatter import formatter except ImportError: formatter = None` — account_formatter.py is a sibling module importing only functools, so the ImportError branch can never fire; the same guarded import is then repeated inside `__init__` (lines 73-79) and again in duck

- `src/slurm_usage_history/app/datastore.py:368` [consistency] Root logger used instead of module logger in _transform_data: Lines 368, 388 and 393 call `logging.info(...)` on the root logger while the rest of the file (and both stores) use the module-level `logger`. duckdb_datastore.py line 23 similarly calls `logging.error` at import time. Log records from these calls carry the wrong logger name and bypass any per-modul

- `src/slurm_usage_history/app/duckdb_datastore.py:32` [consistency] Singleton metaclass duplicated across datastore.py and duckdb_datastore.py: An identical `Singleton` metaclass (ClassVar _instances + lock + __call__) is defined in both datastore.py (lines 20-42) and duckdb_datastore.py (lines 32-42). Duplicated shared functionality that the project rules say belongs in one place; the copies can drift.

- `src/slurm_usage_history/app/duckdb_datastore.py:178` [dead-code] Redundant local imports shadow module-level imports: `import time` appears inside `load_data` (line 178) and `filter` (line 552) although `time` is imported at module level (line 11); `from pathlib import Path` is re-imported inside `get_hostnames` (line 139) and `_auto_discover_nodes` (line 343) although Path is imported at line 13; `import json`/`im

- `src/slurm_usage_history/backend/cli.py:33` [consistency] --workers flag is parsed but never applied; inconsistent ValueError handling: The `--workers` branch parses the value only to print a gunicorn advice message — `config` is never updated, so `slurm-backend --workers 4` still starts a single uvicorn worker, which a caller can easily miss among the startup prints. Its `except ValueError: pass` (line 44) also silently swallows a

- `src/slurm_usage_history/memory.py:12` [typing] Untyped `value` parameter on public parse functions: `parse_memory_to_mb(value) -> float | None` and `parse_reqmem_to_mb(value, cpus: int, nodes: int)` leave `value` unannotated even though every other parameter and return in this otherwise fully typed module is annotated. The accepted domain is `str | float | None`.

- `src/slurm_usage_history/scripts/cluster_agent.py:165` [design] run_command shells out to exporter.py by file path instead of importing it: run_command builds `cmd = [sys.executable, str(script_path)]` for `Path(__file__).parent / "exporter.py"` and re-serializes its own parsed arguments back into argv. exporter.py is an importable module in the same package (tests import SlurmDataExtractor directly); discovering it by filesystem path a

- `src/slurm_usage_history/scripts/waiting_times.py` [docstring] No module, class, or method docstrings; inconsistent csv_file defaults: This installed entry point (`slurm-dashboard-wait-times`) is the only file in the package's scripts directory with no docstrings at all — no module docstring, none on SlurmJobMonitor or its methods — violating the Google-style docstring rule its siblings follow. Additionally the class default `csv_f

- `src/slurm_usage_history/tools.py:174` [consistency] categorize_time and categorize_time_series define conflicting bin sets: `categorize_time` uses categories `<5min` (5/60) and `<30min`, while `categorize_time_series` uses `<15min` (bin edge 15/60) for the same conceptual binning; the two 'predefined categories' disagree. Both are currently dead (see dead-code finding), and the project mandates shared time bins (TIME_HIS
