"""Offline regression tests for app callbacks using real file-backed storage.

Run: python -m unittest discover -s tests -p test_app_restore.py -v
Gradio rendering and model/API calls are deliberately outside these tests.
"""
import ast
import os
from pathlib import Path
import tempfile
import types
import unittest

from storage import LocalStorage


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.storage = LocalStorage(self.root)
        # Execute the actual callbacks without importing model/UI dependencies.
        source = Path(__file__).resolve().parents[1] / 'app.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        callbacks = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)], type_ignores=[])
        self.ns = {'storage': self.storage, 'gr': types.SimpleNamespace(
            Dropdown=lambda **kw: kw, Error=RuntimeError)}
        exec(compile(callbacks, str(source), 'exec'), self.ns)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def test_restart_restores_history_latest_preview_and_download_without_writes(self):
        n = self.storage.create_notebook('Saved')
        history = [{'role': 'user', 'content': '问题'}, {'role': 'assistant', 'content': '答案'}]
        self.storage.save_history(n.id, history)
        old = self.storage.save_artifact(n.id, 'report.md', '# Old')
        latest = self.storage.save_artifact(n.id, 'quiz.md', '# 最新 Quiz\n答案')
        os.utime(old, (100, 100))
        os.utime(latest, (200, 200))
        self.storage.add_source(n.id, {'name': 'sample.txt', 'type': 'txt', 'chunks': 2})
        before = self.snapshot()
        self.ns['storage'] = LocalStorage(self.root)
        result = self.ns['refresh']()
        self.assertEqual(result[0]['value'], n.id)
        self.assertEqual(result[1], history)
        self.assertIn('sample.txt', result[2])
        self.assertEqual(result[3], '# 最新 Quiz\n答案')
        self.assertEqual(Path(result[4]).read_text(), result[3])
        self.assertEqual(before, self.snapshot())

    def test_switch_to_empty_notebook_clears_old_view(self):
        a = self.storage.create_notebook('A')
        self.storage.save_artifact(a.id, 'report.md', 'A only')
        b = self.storage.create_notebook('B')
        self.ns['load_notebook'](a.id)
        view = self.ns['load_notebook'](b.id)
        self.assertEqual(view[:4], ([], 'No sources yet.', '', None))
        self.assertEqual(view[5:], ('', '', ''))

    def test_empty_startup_and_missing_selection(self):
        self.assertIsNone(self.ns['refresh']()[0]['value'])
        n = self.storage.create_notebook('Fallback')
        self.assertEqual(self.ns['refresh']('deleted-id')[0]['value'], n.id)

    def test_refresh_keeps_current_selection(self):
        a = self.storage.create_notebook('A')
        self.storage.create_notebook('B')
        self.assertEqual(self.ns['refresh'](a.id)[0]['value'], a.id)

    def test_create_and_delete_restore_correct_view(self):
        a = self.storage.create_notebook('A')
        self.storage.save_artifact(a.id, 'report.md', 'A content')
        created = self.ns['create_notebook']('B')
        b_id = created[0]['value']
        self.assertEqual(created[4:6], ('', None))
        deleted = self.ns['delete_notebook'](b_id, True)
        self.assertEqual(deleted[0]['value'], a.id)
        self.assertEqual(deleted[4], 'A content')
        empty = self.ns['delete_notebook'](a.id, True)
        self.assertIsNone(empty[0]['value'])
        self.assertEqual(empty[4:6], ('', None))


if __name__ == '__main__':
    unittest.main()
