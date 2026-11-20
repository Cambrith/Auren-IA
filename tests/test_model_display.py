import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('model_ids', Path(__file__).resolve().parents[1] / 'backend/open_webui/utils/model_ids.py')
ids = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ids)


class ModelDisplayNames(unittest.TestCase):
    def test_provider_label_uses_host_then_prefix(self):
        self.assertEqual(ids.provider_label('https://api.groq.com/openai/v1', 'groq'), 'Groq')
        self.assertEqual(ids.provider_label('https://generativelanguage.googleapis.com/v1beta/openai', 'gemini'), 'Gemini')
        self.assertEqual(ids.provider_label('https://exemplo.dev/v1', 'meu'), 'meu')
        self.assertEqual(ids.provider_label('http://[::1', 'x'), 'x')

    def test_display_name_drops_technical_leads_and_adds_provider(self):
        self.assertEqual(ids.display_model_name('models/gemini-2.5-flash', 'Gemini'), 'gemini-2.5-flash · Gemini')
        self.assertEqual(ids.display_model_name('@cf/meta/llama-3.1-8b-instruct-fp8', 'Cloudflare'), 'meta/llama-3.1-8b-instruct-fp8 · Cloudflare')
        self.assertEqual(ids.display_model_name('Google: Gemma 4 (free)', 'OpenRouter'), 'Google: Gemma 4 (free) · OpenRouter')

    def test_display_name_is_idempotent(self):
        once = ids.display_model_name('llama', 'Groq')
        self.assertEqual(ids.display_model_name(once, 'Groq'), once)

    def test_strip_prefix_still_returns_the_real_model_id(self):
        self.assertEqual(ids.strip_provider_model_prefix('gemini.models/gemini-2.5-flash', 'gemini'), 'models/gemini-2.5-flash')


if __name__ == '__main__':
    unittest.main()
