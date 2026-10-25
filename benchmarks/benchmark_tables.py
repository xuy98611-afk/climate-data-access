"""Controlled synthetic table benchmark. Never opens a user's database or input file."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

ROWS = 1048576
BATCH = 65536
CASES = ['csv', 'parquet_none', 'parquet_zstd1', 'parquet_zstd9']


def rss():
    if sys.platform != 'win32':
        import resource
        return {'peak_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)}
    class Counters(ctypes.Structure):
        _fields_ = [('cb',ctypes.c_ulong), ('faults',ctypes.c_ulong)] + [
            (name,ctypes.c_size_t) for name in ['peak','current','quota_peak_paged','quota_paged',
                                             'quota_peak_nonpaged','quota_nonpaged','pagefile','peak_pagefile','private']]
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL('psapi',use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong]
    data = Counters(); data.cb=ctypes.sizeof(data)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(data),data.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'peak_bytes':data.peak,'current_bytes':data.current,'private_bytes':data.private}


def worker(case, output):
    root=Path(output).absolute()
    if (any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in (root,*root.parents))
        or not root.is_dir() or any(root.iterdir())):
        raise ValueError('Worker scratch must be a fresh empty directory without symlinks or junctions')
    import numpy as np
    import pyarrow as pa
    import pyarrow.csv as csv
    import pyarrow.parquet as pq
    import duckdb
    schema=pa.schema([('time_index',pa.int64()),('lat_id',pa.int16()),('lon_id',pa.int16()),
                      ('temperature',pa.float32()),('humidity',pa.float32())])
    baseline=rss()
    path=root/('sample.csv' if case=='csv' else 'sample.parquet')
    hashes={name:hashlib.sha256() for name in schema.names}
    def batch(offset):
        index=np.arange(offset,offset+BATCH,dtype=np.int64)
        lat=((index//128)%64).astype(np.int16)
        lon=(index%128).astype(np.int16)
        rng=np.random.default_rng(917+offset)
        temperature=(273+lat.astype(np.float32)*.05+lon.astype(np.float32)*.02+
                     np.sin(index.astype(np.float32)/8192)*2+rng.normal(0,.02,BATCH).astype(np.float32)).astype(np.float32)
        humidity=(60+lat.astype(np.float32)*.1+rng.normal(0,.1,BATCH).astype(np.float32)).astype(np.float32)
        arrays=[index,lat,lon,temperature,humidity]
        for name,array in zip(schema.names,arrays): hashes[name].update(array.tobytes())
        return pa.RecordBatch.from_arrays([pa.array(array) for array in arrays],schema=schema)
    started=time.perf_counter()
    if case=='csv':
        writer=csv.CSVWriter(path,schema)
    else:
        options={} if case=='parquet_none' else {'compression_level':int(case.removeprefix('parquet_zstd'))}
        writer=pq.ParquetWriter(path,schema,compression='NONE' if case=='parquet_none' else 'zstd',
                                use_dictionary=['lat_id','lon_id'],write_statistics=True,**options)
    try:
        for offset in range(0,ROWS,BATCH):
            record=batch(offset)
            if case=='csv': writer.write_batch(record)
            else: writer.write_batch(record,row_group_size=BATCH)
    finally:
        writer.close()
    write_seconds=time.perf_counter()-started
    expected={name:hasher.hexdigest() for name,hasher in hashes.items()}
    actual={name:hashlib.sha256() for name in schema.names}
    tick=time.perf_counter()
    if case=='csv':
        reader=csv.open_csv(path,convert_options=csv.ConvertOptions(column_types=schema))
    else:
        reader=pq.ParquetFile(path).iter_batches(batch_size=BATCH)
    count=0
    for record in reader:
        count+=record.num_rows
        for name,column in zip(schema.names,record.columns): actual[name].update(column.to_numpy().tobytes())
    if hasattr(reader,'close'): reader.close()
    assert count==ROWS
    assert expected=={name:hasher.hexdigest() for name,hasher in actual.items()}
    verify_seconds=time.perf_counter()-tick
    con=duckdb.connect()
    con.execute("SET memory_limit='64MB'")
    con.execute('SET threads=1')
    temporary=Path(output)/'spill'
    con.execute('SET temp_directory=?',[str(temporary)])
    if case=='csv':
        source="read_csv(?, header=true, columns={'time_index':'BIGINT','lat_id':'SMALLINT','lon_id':'SMALLINT','temperature':'FLOAT','humidity':'FLOAT'})"
    else:
        source='read_parquet(?)'
    samples=[]
    for _ in range(3):
        tick=time.perf_counter()
        result=con.execute('SELECT count(*),sum(temperature) FROM '+source+' WHERE time_index>=? AND time_index<?',
                           [str(path),ROWS//2,ROWS//2+1024]).fetchone()
        samples.append(time.perf_counter()-tick)
        assert result[0]==1024
    tick=time.perf_counter()
    con.execute('CREATE TABLE imported AS SELECT * FROM '+source,[str(path)])
    imported_seconds=time.perf_counter()-tick
    assert con.execute('SELECT count(*) FROM imported').fetchall()[0][0]==ROWS
    tick=time.perf_counter()
    imported_hashes={name:hashlib.sha256() for name in schema.names}
    relation=con.sql('SELECT * FROM imported ORDER BY time_index')
    reader_method=getattr(relation,'to_arrow_reader',None) or relation.fetch_record_batch
    imported_reader=reader_method(BATCH)
    imported_types=str(imported_reader.schema)
    for record in imported_reader:
        for name,column in zip(schema.names,record.columns):
            imported_hashes[name].update(column.to_numpy().tobytes())
    imported_reader.close()
    assert expected=={name:hasher.hexdigest() for name,hasher in imported_hashes.items()}
    import_verification_seconds=time.perf_counter()-tick
    con.close()
    result={'case':case,'rows':ROWS,'batch_rows':BATCH,'numeric_payload_bytes':ROWS*20,
            'file_bytes':path.stat().st_size,'write_and_generate_seconds':write_seconds,'verify_seconds':verify_seconds,
            'filter_query_median_seconds':statistics.median(samples),'duckdb_import_seconds':imported_seconds,
            'duckdb_import_verification_seconds':import_verification_seconds,
            'duckdb_import_types':imported_types,'duckdb_import_values_exact':True,
            'duckdb_buffer_limit':'64MB (not a process RSS cap)','baseline_memory':baseline,'final_memory':rss(),
            'column_sha256':expected,'values_and_types_exact':True,'artifact_retained':False,
            'versions':{'numpy':np.__version__,'pyarrow':pa.__version__,'duckdb':duckdb.__version__}}
    # The parent removes this worker's new temporary directory after process exit.
    # Windows readers may retain a file handle until interpreter teardown.
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',choices=CASES)
    parser.add_argument('--directory')
    parser.add_argument('--output',default='table-results.json')
    args=parser.parse_args()
    if args.worker:
        if not args.directory:
            parser.error('Worker requires --directory')
        print(json.dumps(worker(args.worker,args.directory),ensure_ascii=False))
        return
    destination=Path(args.output).absolute()
    if destination.exists() or destination.is_symlink(): raise FileExistsError(destination)
    if any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in destination.parents):
        raise ValueError('Report path must not contain symlinks or junctions')
    destination.parent.mkdir(parents=True,exist_ok=True)
    report={'schema_version':1,'status':'running','passed':False,
            'kind':'controlled_synthetic_not_climate_observations','rows':ROWS,'cases':[],
            'limitations':['Single local run; warm filesystem caches; not a production 100GB test',
                           'Repeated identifiers and smooth synthetic floats influence compression ratio',
                           'Generation, hashing and encoding are included in write timing',
                           'Peak RSS includes Python, Arrow, DuckDB and I/O caches; buffer limit is not RSS limit',
                           'Peak RSS includes the full post-import ordered readback verification',
                           'Host background load and OneDrive synchronization were not isolated',
                           'User databases and files are never read or modified']}
    for case in CASES:
        with tempfile.TemporaryDirectory(prefix='synthetic-table-',dir=destination.parent) as directory:
            completed=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',case,'--directory',directory],
                                     capture_output=True,text=True,encoding='utf-8',timeout=300)
            if completed.returncode:
                raise RuntimeError(completed.stderr)
            result=json.loads(completed.stdout)
        report['cases'].append(result)
        destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({key:result[key] for key in ['case','file_bytes','duckdb_import_seconds','filter_query_median_seconds']}),flush=True)
    assert all(case['column_sha256']==report['cases'][0]['column_sha256'] for case in report['cases'])
    report.update(status='complete',passed=True,case_count=len(report['cases']))
    destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
