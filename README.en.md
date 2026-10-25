# climate-data-access

A directory of 44 climate-data products, distribution routes and tools, plus a Python client for regional ERA5 hourly retrieval through Google Earth Engine. Requests use UTC hours and 0.25-degree grid centers; outputs contain compressed NetCDF batches and a provenance/checksum manifest.

This is an early public-source release candidate. The packaged client is tested with synthetic offline responses; it has not been live-retested. No meteorological data, credentials, or private research database are included. See [validation status](docs/status.md).

[中文使用说明](README.md) · [Methods](docs/methods.md) · [44-source directory](catalog/sources.json)

See the [Chinese public-access guide](docs/public-access.md) for per-source steps, account requirements, bounded access checks, and restrictions. Directory listings are separate from executable adapters.

## Install and plan offline

Use Python 3.11 or later in a virtual environment:

```sh
python -m venv .venv
# Activate .venv using the command appropriate to your shell.
python -m pip install -e .
climate-access plan examples/two_hours.json
```

Planning validates the request and reports dimensions, batches, and estimated numerical output size. It does not authenticate or make cloud requests. Importing `climate_access` also makes no cloud requests.

## Explicit cloud retrieval

Install the Earth Engine extra, then configure your own account and eligible Cloud project using Google's [authentication guide](https://developers.google.com/earth-engine/guides/auth). If you need to authenticate, run `earthengine authenticate` yourself. The package uses `ee.Initialize(project=...)` with your existing SDK credentials and does not launch authentication.

```sh
python -m pip install -e ".[gee]"
climate-access fetch examples/two_hours.json --project YOUR_PROJECT_ID --output data/two-hours
climate-access verify data/two-hours
climate-access bundle data/two-hours --output exports/two-hours.zip
```

`fetch` makes external requests and consumes the permissions and quotas of the project you supply. Check current service eligibility and dataset terms before using it. A successful offline plan does not confirm cloud access, data availability, or a successful download.

Keep the same configuration and output directory to resume: recorded batches are validated before reuse. Changed configurations and corrupt existing outputs are rejected. Use a new directory for a different request. Bundling verifies the output and refuses to overwrite an existing archive.

An abrupt termination may leave `.run.lock`. Confirm that no other process is writing before inspecting/removing that lock. If a `.nc` file was published but its manifest entry was not committed, resume deliberately refuses to overwrite it. Preserve the directory for inspection and use a new output directory; do not delete verified results to force a retry. Budget settings are part of request identity, so changing them also requires a new directory.

## Request format

```json
{
  "start": "2004-01-01T00:00:00Z",
  "end": "2004-01-01T02:00:00Z",
  "area": [30, 75, 29.5, 75.5],
  "variables": ["t2m", "d2m", "sp"],
  "batch_hours": 6,
  "max_output_mib": 128
}
```

- `start` is inclusive and `end` exclusive. Both must be whole UTC hours ending in `Z`. A request contains at most 744 consecutive hours.
- Requested timestamps must fit the NetCDF nanosecond encoding range (through `2262-04-11T23:00:00Z`); this encoding bound is not a claim of future ERA5 availability.
- `area` is an array of inclusive pixel-center bounds on the 0.25-degree grid, ordered `[north, west, south, east]`. Longitude crossing the antimeridian is unsupported.
- Variables: `u10`, `v10`, `d2m`, `t2m`, `sp`, `tp`, `ssrdc`, `ssrd`, `tcc`.
- `batch_hours` is at most 24; each batch is limited to 32 MiB estimated uncompressed float64 band values.
- `max_output_mib` is a runtime budget for actual output artifacts plus the manifest. It is not a process-memory, global cache, or service-quota limit.

See [methods and units](docs/methods.md) before interpreting precipitation or radiation. Values retain source semantics; no unit conversion, clipping, gap filling, or local-time aggregation is applied.

## Scope and provenance

The implemented route is [`ECMWF/ERA5/HOURLY`](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_HOURLY) through the official Earth Engine SDK. The directory lists 44 public products, distribution channels, and tools. Each entry has a separate status; listing a service does not create a connector. CDS API and ARCO adapters are not implemented, and the package never switches channels automatically.

The predecessor regional method was used for 2003–2010: 96 months, 70,128 UTC hours, nine variables, and a 37 × 61 grid. Those raw files were subsequently deleted and are absent from this repository. This is historical methodological context, not a reproducibility claim for the new client. Cross-channel values are not guaranteed equal.

## Development

```sh
python -m pip install -e ".[gee,query]"
python -m unittest discover -s tests
```

Tests use synthetic, non-meteorological arrays and temporary directories; no live credentials are required. The optional query example uses a separate local Parquet file and DuckDB. It does not integrate with an existing research database.

```sh
python examples/query_point.py data/two-hours --output exports/north-west-point.parquet
```

This example selects the north-west grid point; it does not calculate an area mean.

Contributions should include focused offline tests and explain any change to source, units, timestamp semantics, or output format. Do not commit downloaded data or credential files.

## License and attribution

Project code is [MIT licensed](LICENSE). ERA5 and other upstream data retain their own terms and attribution requirements; the code license grants no additional data rights. See [third-party notices](THIRD_PARTY.md) and [security guidance](SECURITY.md).
