# Climate Data Workbench · climate-data-access

A local personal research workbench with a Chinese interface, a searchable **44-entry source directory**, reusable JSON requests, explicit retrieval and verifiable outputs. Version **0.2** implements **three retrieval routes**, not 44 connectors.

[中文主文档](README.md) · [Access guide](docs/public-access.md) · [Validation status](docs/status.md) · [Architecture](docs/architecture.md) · [Extending](docs/extending.md) · [Ecosystem](docs/ecosystem.md)

## Start the workbench

Python 3.11+ is required. Windows users may run 启动工作台.cmd, which installs the project on first use. Alternatively, create and activate a virtual environment from the repository directory.

Windows PowerShell:

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
climate-access serve --open
~~~

macOS / Linux:

~~~sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
climate-access serve --open
~~~

The page opens at http://127.0.0.1:8765. Its three tabs cover retrieval, the source directory and run history. Choose a source, inspect an offline plan, explicitly start retrieval, then inspect and verify the result. Save/import JSON requests or reuse a historical request. ERA5 is the default priority route; choose NASA POWER to try a route without an account.

Results default to data/workbench. Stop with Ctrl+C. Set a location and port with:

~~~sh
climate-access serve --open --output data/workbench --port 8765
~~~

The server binds only to loopback. It does not write to a research database, schedule tasks or upload private research files. The page offers point CSV/raw JSON/manifest downloads; ERA5 NetCDF files are available in the local run directory, with the manifest downloadable in the page.

## Implemented routes

| Source | Scope | Authentication and output |
| --- | --- | --- |
| era5-gee | Hourly regional ERA5; native 0.25° pixel centers, nine supported variables, at most 744 hours | Your eligible GEE project and local SDK authentication; compressed NetCDF and manifest |
| nasa-power | Daily/hourly point; at most 31 days and eight variables per request | Public API, no account; CSV, raw JSON and manifest |
| open-meteo | Hourly point, explicitly fixed to ERA5; at most 31 days and eight variables | Public noncommercial API, no account; CSV, raw JSON and manifest |

Sources are explicit. Failed retrievals do not fall back to another source. Point data and regional ERA5 retain their own variable, unit and processing conventions. POWER is a source-derived gridded product, not a station observation.

## CLI workflow

~~~sh
climate-access catalog --search NASA
climate-access catalog --search NASA --tier no_account
climate-access request-plan examples/power_daily.json
climate-access request-fetch examples/power_daily.json --output data/power-example
climate-access request-verify data/power-example
~~~

Catalog search and planning are offline. Unified retrieval requires a new output directory and never overwrites an existing one. All intervals are [start, end): the daily example covers January 1–2, 2001. Daily dates use YYYY-MM-DD; hourly timestamps use whole-hour UTC YYYY-MM-DDTHH:00:00Z. Point requests cannot include future times. See [POWER](examples/power_daily.json), [Open-Meteo](examples/open_meteo_hourly.json), and [ERA5](examples/era5_unified.json) examples.

For GEE, follow the [official authentication guide](https://developers.google.com/earth-engine/guides/auth), using your own account, eligible project and local credentials:

~~~sh
python -m pip install -e ".[gee]"
earthengine authenticate
climate-access request-plan examples/era5_unified.json
climate-access request-fetch examples/era5_unified.json --project YOUR_PROJECT_ID --output data/era5-example
climate-access request-verify data/era5-example
~~~

Credentials are not stored by this project, and the project ID is not written to result manifests. Legacy ERA5 plan / fetch / verify / bundle commands remain available. Legacy fetch can resume an identical request in the same directory after checking existing batches; unified request-fetch always requires a new directory. See [ERA5 methods](docs/methods.md).

## Interpretation and limits

- Keep source units, UTC and numeric values. There is no automatic unit conversion, gap filling or cross-source merging. ERA5 retains its strict finite-value checks and rejects missing responses.
- Point APIs request full upstream days. Raw JSON preserves that response; CSV contains only the selected interval. null and POWER -999 become empty CSV fields with per-variable missing counts.
- Open-Meteo fixes models=era5, nearest-cell selection, elevation=nan, UTC and wind speed in m/s. POWER retains source provenance and response coordinates; raw JSON retains the full header and variable definitions. Actual per-variable native grid centers remain unknown.
- Point HTTP uses fixed HTTPS endpoints, a 60-second timeout and a 64 MiB maximum response size, also bounded by the configured total output budget. It has no automatic retries or fallback. Failed jobs are not complete. ERA5 retains its existing batching and limited retry rules.
- Verification checks hashes, sequence, variables, units and provenance. Point verification reparses raw JSON and compares the exact CSV. These are consistency checks, not independent meteorological accuracy validation.

## Validation and development

~~~sh
python -m unittest discover -s tests
~~~

Offline tests use synthetic responses. Small live POWER daily/hourly and Open-Meteo ERA5 requests were checked; the new GEE client remains offline-tested in this batch. See [status](docs/status.md) and [v0.2 validation evidence](docs/workbench-validation.json). Historical 2003–2010 ERA5 files were deleted and are not included or claimed as reproduced by this version.

EODAG, earthaccess, earthkit-data and intake-esm are future reuse candidates, not installed integrations. See [extension contracts](docs/extending.md) and [ecosystem notes](docs/ecosystem.md). Code is [MIT licensed](LICENSE); upstream data/API terms, eligibility, quotas and attribution apply separately. See [third-party notices](THIRD_PARTY.md) and [security](SECURITY.md).
