import base64
import json
import unittest
from unittest.mock import patch

from integration.lunvri_connections import parse_credentials, public_model
from integration.lunvri_manual import image_files, generate_images
from integration import lunvri_bridge as bridge
from cavren.config import ProviderConfig
from cavren.errors import CavrenError
from cavren.models import Message


class MediaTests(unittest.TestCase):
    def test_credentials_parser_accepts_known_labels_only(self):
        self.assertEqual(
            parse_credentials('Mistral: test-secret\nGEMINI_API_KEY=other-secret\nUnknown: ignored'),
            {'MISTRAL_API_KEY': 'test-secret', 'GEMINI_API_KEY': 'other-secret'},
        )

    def test_capabilities_come_from_provider_metadata(self):
        text = public_model(
            'openrouter',
            {'id': 'test/text', 'architecture': {'input_modalities': ['text'], 'output_modalities': ['text']}},
        )
        image = public_model(
            'openrouter',
            {
                'id': 'test/image',
                'architecture': {'input_modalities': ['text', 'image'], 'output_modalities': ['image']},
            },
        )
        self.assertFalse(text['cavren']['capabilities']['vision'])
        self.assertFalse(text['cavren']['capabilities']['image_generation'])
        self.assertTrue(image['cavren']['image_only'])
        self.assertTrue(image['cavren']['capabilities']['image_generation'])
        self.assertTrue(text['cavren']['capabilities']['file_upload'])

    def test_video_is_translated_to_openrouter_format(self):
        from integration.lunvri_worker import OpenAIChatPromptAdapter

        messages = [
            Message('user', [{'type': 'input_video', 'input_video': {'mime_type': 'video/mp4', 'data': 'dmlkZW8='}}])
        ]
        payload = OpenAIChatPromptAdapter().adapt(messages, provider='openrouter')
        self.assertEqual(
            payload[0]['content'][0], {'type': 'video_url', 'video_url': {'url': 'data:video/mp4;base64,dmlkZW8='}}
        )

    def test_zero_token_price_does_not_authorize_image_cost(self):
        model = public_model(
            'openrouter',
            {
                'id': 'test/image',
                'architecture': {'output_modalities': ['image']},
                'pricing': {'prompt': '0', 'completion': '0'},
            },
        )
        self.assertEqual(model['cavren']['price_kind'], 'unknown')

    def test_retired_provider_and_proxy_models_are_excluded(self):
        self.assertEqual(parse_credentials('DeepSeek: removed-secret'), {})
        for provider, model_id in [
            ('deepseek', 'test-chat'),
            ('openrouter', 'deepseek/test-chat'),
            ('cloudflare', '@cf/deepseek-ai/test-chat'),
        ]:
            self.assertIsNone(public_model(provider, {'id': model_id}))

    def test_specialized_models_are_not_chat_options(self):
        self.assertIsNone(
            public_model('gemini', {'name': 'models/embedding', 'supportedGenerationMethods': ['embedContent']})
        )
        self.assertIsNone(public_model('groq', {'id': 'whisper-large-v3'}))

    def test_manual_cost_and_image_support_are_enforced_before_worker(self):
        models = [
            {
                'id': 'cavren:mistral:test-chat',
                'cavren': {'integrated': False, 'price_kind': 'unknown', 'capabilities': {'image_generation': False}},
            }
        ]
        body = {'model': models[0]['id'], 'messages': [{'role': 'user', 'content': 'Teste'}]}
        with patch.object(bridge, 'catalog', return_value=models):
            with self.assertRaisesRegex(ValueError, 'custo'):
                bridge.prepare_job(body, 'test')
            job = bridge.prepare_job({**body, 'cavren_billing_confirmed': True}, 'test')
            self.assertTrue(job['lunvri_direct'])
            self.assertEqual(job['mode_options']['manual_route'], 'mistral:test-chat')
            with self.assertRaisesRegex(ValueError, 'suporte'):
                bridge.prepare_job({**body, 'cavren_billing_confirmed': True, 'lunvri_image_generation': True}, 'test')

    def test_image_outputs_are_validated_and_mapped(self):
        data = base64.b64encode(b'test-image').decode()
        files, text = image_files(
            'gemini',
            {
                'candidates': [
                    {
                        'content': {
                            'parts': [{'text': 'Pronto'}, {'inlineData': {'mimeType': 'image/png', 'data': data}}]
                        }
                    }
                ]
            },
        )
        self.assertEqual(text, 'Pronto')
        self.assertEqual(files[0]['url'], 'data:image/png;base64,' + data)
        files, _ = image_files('openrouter', {'data': [{'b64_json': data, 'media_type': 'image/webp'}]})
        self.assertTrue(files[0]['url'].startswith('data:image/webp;'))
        with self.assertRaises(CavrenError):
            image_files('openrouter', {'data': []})

    def test_image_request_keeps_credentials_in_headers(self):
        import httpx

        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={'data': [{'b64_json': base64.b64encode(b'image').decode()}]})

        config = ProviderConfig(
            'openrouter', 'test/image', 'https://openrouter.ai/api/v1', 'OPENROUTER_API_KEY', 'private-secret'
        )
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            generate_images(client, config, [Message('user', 'Crie uma paisagem')], 'Crie uma paisagem')
        request = requests[0]
        self.assertEqual(str(request.url), 'https://openrouter.ai/api/v1/images')
        self.assertNotIn('private-secret', request.content.decode())
        self.assertEqual(json.loads(request.content)['n'], 1)


if __name__ == '__main__':
    unittest.main()
