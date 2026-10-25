"""Controlled synthetic HDF5 benchmark; never reads research data or a database.

Run with Python plus numpy and h5py. Each measured case uses a fresh subprocess.
Output is refused if the report already exists. Scratch data is generated in fresh
directories and deleted only after byte-exact decoded-value verification.
"""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

import h5py
import numpy as np

SHAPE = (512, 256, 256)
SLAB = 8
SEED = 20261025
DTYPE = np.dtype('<f4')
DECODED_BYTES = int(np.prod(SHAPE)) * DTYPE.itemsize
PROFILES = ('smooth_noise', 'high_entropy')
CASES = {
    'eager_gzip4_shuffle': dict(chunks=(8, 256, 256), compression='gzip', compression_opts=4, shuffle=True),
    'stream_raw': dict(chunks=(8, 256, 256)),
    'stream_gzip1_shuffle': dict(chunks=(8, 256, 256), compression='gzip', compression_opts=1, shuffle=True),
    'stream_gzip4_no_shuffle': dict(chunks=(8, 256, 256), compression='gzip', compression_opts=4, shuffle=False),
    'stream_gzip4_shuffle': dict(chunks=(8, 256, 256), compression='gzip', compression_opts=4, shuffle=True),
    'stream_gzip4_shuffle_tiled': dict(chunks=(64, 32, 32), compression='gzip', compression_opts=4, shuffle=True),
}


def rss():
    """Actual process current/peak working set, not a Python allocator estimate."""
    if os.name == 'nt':
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
                    'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                    'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return dict(current_bytes=int(counters.WorkingSetSize), peak_bytes=int(counters.PeakWorkingSetSize),
                    method='Windows GetProcessMemoryInfo WorkingSetSize/PeakWorkingSetSize')
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_bytes = int(peak if sys.platform == 'darwin' else peak * 1024)
    current = None
    if sys.platform.startswith('linux'):
        current = int(Path('/proc/self/statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
    return dict(current_bytes=current, peak_bytes=peak_bytes, method='resource.ru_maxrss; /proc current RSS where available')


def generate(profile, start):
    """Exactly one <=2 MiB float32 output slab; RNG seeded separately per slab."""
    rng = np.random.default_rng(SEED + start)
    slab = rng.random((SLAB, SHAPE[1], SHAPE[2]), dtype=np.float32)
    if profile == 'high_entropy':
        slab *= np.float32(2)
        slab -= np.float32(1)
    else:
        slab -= np.float32(.5)
        slab *= np.float32(.0002)
        latitude = np.sin(np.linspace(-1.5, 1.5, SHAPE[1], dtype=np.float32))[:, None]
        longitude = np.cos(np.linspace(-3, 3, SHAPE[2], dtype=np.float32))[None, :]
        spatial = (latitude * np.float32(12) + longitude * np.float32(3)).astype(DTYPE)
        slab += spatial[None, :, :]
        slab += (np.arange(start, start + SLAB, dtype=np.float32) * np.float32(.01))[:, None, None]
    assert slab.dtype == DTYPE and slab.nbytes == 2 * 1024**2
    return slab


def update_hash(digest, array):
    assert array.flags.c_contiguous
    digest.update(memoryview(array).cast('B'))


def query_median(dataset, selection):
    # Prime both OS and HDF5 caches, then time three identical selections. Each
    # selection materializes only its result; no cold-cache claim is made.
    warm = dataset[selection]
    del warm
    timings = []
    for _ in range(3):
        start = time.perf_counter()
        result = dataset[selection]
        timings.append(time.perf_counter() - start)
        assert np.isfinite(result).all()
        del result
    return dict(median_seconds=statistics.median(timings), seconds=timings,
                measured_reads=3, cache='Warm OS cache; same open HDF5 handle with default raw chunk cache')


def worker(profile, case, scratch):
    root = Path(scratch)
    if root.is_symlink() or not root.is_dir() or any(root.iterdir()):
        raise ValueError('Worker scratch must be a fresh empty non-symlink directory')
    file = root / 'synthetic-array.h5'
    baseline = rss()
    digest = hashlib.sha256()
    eager = case.startswith('eager_')
    original = None
    write_start = time.perf_counter()
    if eager:
        original = np.empty(SHAPE, dtype=DTYPE)
        for start in range(0, SHAPE[0], SLAB):
            block = generate(profile, start)
            update_hash(digest, block)
            original[start:start + SLAB] = block
            del block
    with h5py.File(file, 'x') as handle:
        dataset = handle.create_dataset('values', shape=SHAPE, dtype=DTYPE, **CASES[case])
        if eager:
            dataset[:] = original
        else:
            for start in range(0, SHAPE[0], SLAB):
                block = generate(profile, start)
                update_hash(digest, block)
                dataset[start:start + SLAB] = block
                del block
        handle.flush()
    write_seconds = time.perf_counter() - write_start
    encoded_bytes = file.stat().st_size
    if encoded_bytes >= 512 * 1024**2:
        raise ValueError('Scratch file exceeded the 512 MiB safety bound')
    expected_sha = digest.hexdigest()
    verified = hashlib.sha256()
    verify_start = time.perf_counter()
    with h5py.File(file, 'r') as handle:
        dataset = handle['values']
        assert dataset.shape == SHAPE and dataset.dtype == DTYPE
        if eager:
            decoded = dataset[:]
            update_hash(verified, decoded)
            # Keep original and full decoded arrays alive through memory reading.
        else:
            for start in range(0, SHAPE[0], SLAB):
                block = dataset[start:start + SLAB]
                assert block.dtype == DTYPE and block.nbytes <= 2 * 1024**2
                update_hash(verified, block)
                del block
    verify_seconds = time.perf_counter() - verify_start
    if expected_sha != verified.hexdigest():
        raise ValueError('Decoded float32 bytes changed; failed artifact retained for inspection')
    with h5py.File(file, 'r') as handle:
        point_query = query_median(handle['values'], (slice(None), 128, 128))
        map_query = query_median(handle['values'], (256, slice(None), slice(None)))
    memory = rss()
    # The only deletion target is our constant filename inside this fresh worker
    # directory. Failed verification above never reaches deletion.
    if file.is_symlink() or file.resolve().parent != root.resolve() or file.name != 'synthetic-array.h5':
        raise ValueError('Unsafe scratch deletion target')
    file.unlink()
    return dict(profile=profile, case=case, passed=True, shape=list(SHAPE), dtype=DTYPE.str,
                seed=SEED, seed_rule='default_rng(seed + first time index) per 8-time slab',
                generation_slab_bytes=2 * 1024**2, chunks=list(CASES[case]['chunks']),
                compression=CASES[case].get('compression'), compression_level=CASES[case].get('compression_opts'),
                shuffle=CASES[case].get('shuffle', False), decoded_bytes=DECODED_BYTES,
                artifact_bytes=encoded_bytes, encoded_to_decoded_ratio=encoded_bytes / DECODED_BYTES,
                decoded_to_encoded_factor=DECODED_BYTES / encoded_bytes,
                write_including_generation_and_source_hash_seconds=write_seconds,
                full_verification_seconds=verify_seconds, full_value_sha256=expected_sha,
                decoded_value_sha256=verified.hexdigest(), baseline_rss_bytes=baseline['current_bytes'],
                baseline_peak_rss_bytes=baseline['peak_bytes'], peak_rss_bytes=memory['peak_bytes'],
                peak_minus_baseline_rss_bytes=(memory['peak_bytes'] - baseline['current_bytes']) if baseline['current_bytes'] is not None else None,
                rss_method=memory['method'], single_point_512_times=point_query, single_map_time_256=map_query,
                artifact_retained=False, scratch_file_removed=not file.exists(),
                libraries=dict(python=platform.python_version(), numpy=np.__version__, h5py=h5py.__version__, hdf5=h5py.version.hdf5_version))


def run(report_path):
    target = Path(report_path).absolute()
    if target.exists() or target.is_symlink():
        raise FileExistsError('Refusing to overwrite an existing benchmark report')
    if not target.parent.is_dir():
        raise ValueError('Report parent directory must already exist')
    report = dict(schema_version=1, status='running', created_utc=datetime.now(timezone.utc).isoformat(),
                  benchmark='Controlled synthetic HDF5 array storage; not complete NetCDF',
                  hardware=dict(system=platform.system(), release=platform.release(), machine=platform.machine()),
                  shape=list(SHAPE), decoded_bytes=DECODED_BYTES, slab_bytes=2 * 1024**2,
                  limitations=[
                      'Synthetic values are not ERA5 or representative empirical climate distributions.',
                      '128 MiB per decoded array; no 100 GB, remote ingestion or database benchmark claim.',
                      'Write time includes generation, source hashing, HDF5 flush and close, not an fsync durability guarantee.',
                      'One fresh subprocess per case; same imports; cases run sequentially once; no statistical write-time replication.',
                      'Host background load and OneDrive synchronization were not isolated; timings are one local run.',
                      'Query timings prime caches, then median of 3 reads on one open HDF5 handle; OS and HDF5 cache effects remain.',
                      'Streaming bounds decoded generation/verification slabs to 2 MiB; HDF5 caches, compression buffers and interpreter use additional RAM.',
                      'Eager case retains the original full array and one full decoded copy through verification and query measurement.',
                      'Lossless float32 bit preservation is checked with full SHA-256; no quantization or imputation.'],
                  results=[])
    # Establish exclusive ownership before starting workers; only this newly
    # created report is replaced as each completed result is flushed.
    with target.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    def publish():
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent, suffix='.array-report.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        try:
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    scratch_root = Path(tempfile.mkdtemp(prefix='array-benchmark-', dir=target.parent))
    try:
        for profile in PROFILES:
            for case in CASES:
                child = Path(tempfile.mkdtemp(prefix='case-', dir=scratch_root))
                completed = subprocess.run([sys.executable, str(Path(__file__).absolute()), '--worker',
                                            '--profile', profile, '--case', case, '--scratch', str(child)],
                                           capture_output=True, text=True, check=False, timeout=300)
                if completed.returncode:
                    raise RuntimeError('Worker failed; own scratch retained for inspection: ' + completed.stderr[-2000:])
                result = json.loads(completed.stdout)
                if not result['passed'] or not result['scratch_file_removed']:
                    raise ValueError('Worker did not prove successful verification and scratch cleanup')
                hashes = [item['full_value_sha256'] for item in report['results'] if item['profile'] == profile]
                if hashes and any(value != result['full_value_sha256'] for value in hashes):
                    raise ValueError('Source values changed between benchmark cases')
                if any(child.iterdir()):
                    raise ValueError('Unexpected scratch files; refusing to remove directory')
                child.rmdir()
                report['results'].append(result)
                publish()
                print(f"{len(report['results'])}/12 {profile} {case}: {result['artifact_bytes']/1024**2:.2f} MiB, "
                      f"write {result['write_including_generation_and_source_hash_seconds']:.3f}s, "
                      f"peak RSS {result['peak_rss_bytes']/1024**2:.2f} MiB", flush=True)
        report.update(status='complete', passed=True, finished_utc=datetime.now(timezone.utc).isoformat(),
                      case_count=len(report['results']), scratch_artifacts_retained=False)
        publish()
    except Exception as error:
        report.update(status='failed', passed=False, error=str(error))
        publish()
        raise
    finally:
        if scratch_root.is_dir() and not any(scratch_root.iterdir()):
            scratch_root.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(Path(__file__).with_name('array-results.json')))
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--profile', choices=PROFILES)
    parser.add_argument('--case', choices=tuple(CASES))
    parser.add_argument('--scratch')
    args = parser.parse_args()
    if args.worker:
        if not args.profile or not args.case or not args.scratch:
            parser.error('Worker requires profile, case and scratch')
        print(json.dumps(worker(args.profile, args.case, args.scratch), allow_nan=False))
    else:
        run(args.output)


if __name__ == '__main__':
    main()
