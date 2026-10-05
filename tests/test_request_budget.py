import unittest
from unittest.mock import patch
from types import SimpleNamespace
from request_budget import fit_context, limits, size, interleave_sources

class RequestBudgetTests(unittest.TestCase):
    def test_multilingual_context(self):
        for text in ['English text ' * 5000, '中文资料😀' * 5000]:
            prompt, selected, limited = fit_context('Instructions\n', [('SOURCE: page 1', text)])
            self.assertLessEqual(size(prompt), limits()[0])
            self.assertIn('SOURCE: page 1', prompt)
            self.assertEqual(selected, [0])
            self.assertTrue(limited)
            self.assertNotIn('\ufffd', prompt)
    def test_small_context(self):
        prompt, selected, limited = fit_context('Question\n', [('[S1]', 'Answer'), ('[S2]', 'Evidence')])
        self.assertIn('[S2]\nEvidence', prompt)
        self.assertEqual(selected, [0, 1])
        self.assertFalse(limited)
    def test_huge_question(self):
        with self.assertRaisesRegex(ValueError, 'too long'):
            fit_context('x' * 6000, [('[S1]', 'text')])
    def test_labels_not_cut(self):
        with self.assertRaisesRegex(ValueError, 'No source excerpt'):
            fit_context('Instructions', [('x' * 6000, 'body')])
    def test_output_reservation(self):
        with patch.dict('os.environ', {'GROQ_REQUEST_TOKEN_BUDGET':'7500', 'GROQ_MAX_COMPLETION_TOKENS':'2000'}):
            a, b = limits()
            self.assertEqual(a + b + 500, 7500)
    def test_invalid_configuration(self):
        with patch.dict('os.environ', {'GROQ_REQUEST_TOKEN_BUDGET':'2000', 'GROQ_MAX_COMPLETION_TOKENS':'2000'}):
            with self.assertRaises(ValueError):
                limits()
    def test_round_robin(self):
        items = [SimpleNamespace(metadata={'source_name':x}, text=y) for x,y in [('a','a1'),('a','a2'),('b','b1')]]
        self.assertEqual([x.text for x in interleave_sources(items)], ['a1','b1','a2'])
