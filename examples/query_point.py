"""Query the north-west grid point of a verified SMALL run; creates only requested output."""
import argparse
from pathlib import Path
import json
import pandas as pd
import xarray as xr
import duckdb
from climate_access.artifacts import verify_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run'); parser.add_argument('--output', required=True)
    args = parser.parse_args(); root = Path(args.run); target = Path(args.output)
    verify_run(root)
    if target.exists(): raise FileExistsError(target.name)
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    frames = []
    for item in manifest['files']:
        with xr.open_dataset(root/item['name'], engine='h5netcdf') as ds:
            frames.append(ds.isel(latitude=0, longitude=0).to_dataframe().reset_index())
    table = pd.concat(frames, ignore_index=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream: table.to_parquet(stream, index=False)
    with duckdb.connect(':memory:') as con:
        print(con.execute('SELECT * FROM read_parquet(?) ORDER BY time LIMIT 5', [str(target)]).fetchdf().to_string(index=False))


if __name__ == '__main__': main()
