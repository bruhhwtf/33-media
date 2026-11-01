"""Setup command/guard tests. These do not install or validate real SAM."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from setup_ai import pip_steps,install
from engine import Engine
class SetupTests(unittest.TestCase):
    def test_pinned_commands_target_private_staging(self):
        with tempfile.TemporaryDirectory(prefix='runtime path ') as td:
            runtime=Path(td);(runtime/'model-wheel').mkdir();(runtime/'model-wheel'/'SAM_2.whl').touch()
            stage=runtime/'ai.partial';steps=pip_steps(runtime,stage)
            self.assertEqual(len(steps),3)
            for args in steps:
                self.assertEqual(args[args.index('--target')+1],str(stage));self.assertNotIn('shell',args)
            self.assertIn('--no-deps',steps[0]);self.assertIn('torch==2.5.1',steps[0]);self.assertIn('https://download.pytorch.org/whl/cu124',steps[0])
            self.assertIn('--no-deps',steps[2]);self.assertTrue(steps[2][-1].endswith('.whl'))
    def test_missing_wheel_is_actionable(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError,'Reinstall'):pip_steps(Path(td),Path(td)/'ai.partial')
    @unittest.skipIf(sys.platform=='win32','Non-Windows guard only')
    def test_non_windows_guard(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError,'Windows installer'):install(Engine(td))
