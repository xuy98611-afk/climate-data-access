"""Benchmark tools must reject existing files before creating any scratch data."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


BENCHMARKS = Path(__file__).resolve().parents[1]/'benchmarks'


class BenchmarkSafetyTests(unittest.TestCase):
    def test_table_worker_refuses_existing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory)/'sample.csv'
            marker.write_bytes(b'existing data must remain unchanged\n')
            result = subprocess.run([sys.executable,str(BENCHMARKS/'benchmark_tables.py'),
                                     '--worker','csv','--directory',directory],
                                    capture_output=True,timeout=30)
            self.assertEqual(marker.read_bytes(),b'existing data must remain unchanged\n')
            self.assertNotEqual(result.returncode,0)

    def test_benchmarks_refuse_existing_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ['benchmark_arrays.py','benchmark_tables.py']:
                with self.subTest(name=name):
                    marker = Path(directory)/(name+'.json')
                    marker.write_bytes(b'existing report\n')
                    result = subprocess.run([sys.executable,str(BENCHMARKS/name),'--output',str(marker)],
                                            capture_output=True,timeout=15)
                    self.assertNotEqual(result.returncode,0)
                    self.assertEqual(marker.read_bytes(),b'existing report\n')
