"""Exercise isolated interpreter startup used by the embedded Windows runtime."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path

class WorkerStartupTests(unittest.TestCase):
    def test_diagnostics_from_isolated_python_and_unrelated_directory(self):
        worker=Path(__file__).resolve().parents[1]/'backend'/'worker.py'
        with tempfile.TemporaryDirectory(prefix='cutlab isolated ') as folder:
            # A working-directory module must never shadow our backend.
            (Path(folder)/'engine.py').write_text('raise RuntimeError("untrusted cwd imported")')
            result=subprocess.run([sys.executable,'-I',str(worker)],
                input=json.dumps({'op':'diagnostics','cache':folder})+'\n',
                cwd=folder,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads(result.stdout)['result']
            self.assertIn('python',data)
            self.assertIn('ffmpeg',data)
            self.assertIn('setupAvailable',data)
