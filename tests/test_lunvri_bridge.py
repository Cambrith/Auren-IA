"""Bridge contract/security checks, without provider calls or real credentials."""

import http.client
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from integration import lunvri_bridge as bridge
from integration.lunvri_worker import normalize_context
from cavren.context_builder import GenerationContext
from cavren.models import Message
from cavren.core import Cavren
from cavren.prompt_adapter import OpenAIChatPromptAdapter

MODELS = [
    {"id": "cavren:auto", "name": "Lunvri"},
    {"id": "cavren:groq:qwen/qwen3-32b", "name": "Lunvri"},
]


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.catalog = patch.object(bridge, 'catalog', return_value=MODELS)
        self.catalog.start()
        self.server = bridge.BridgeServer('test-local-token')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.headers = {'Authorization': 'Bearer test-local-token', 'Content-Type': 'application/json'}

    def tearDown(self):
        self.server.shutdown()
        self.server.close_workers()
        self.server.server_close()
        self.thread.join()
        self.catalog.stop()

    def request(self, method, path, body=None, headers=None):
        client = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        client.request(method, path, json.dumps(body) if body else None, headers or self.headers)
        response = client.getresponse()
        data = response.read().decode()
        status = response.status
        client.close()
        return status, data

    def test_missing_auth_and_browser_origin_are_rejected(self):
        for headers in ({'Authorization': 'Bearer wrong'}, {**self.headers, 'Origin': 'http://127.0.0.1:5179'}):
            status, data = self.request('GET', '/v1/models', headers=headers)
            self.assertEqual(status, 401)
            self.assertNotIn('test-local-token', data)

    def test_dns_rebinding_host_is_rejected(self):
        status, _ = self.request('GET', '/v1/models', headers={**self.headers, 'Host': 'evil.example'})
        self.assertEqual(status, 401)

    def test_catalog_is_authenticated_and_keeps_identity(self):
        status, data = self.request('GET', '/v1/models')
        self.assertEqual(status, 200)
        self.assertTrue(all(model['name'] == 'Lunvri' for model in json.loads(data)['data']))

    def test_mode_and_manual_model_remain_independent(self):
        body = {
            'model': MODELS[1]['id'],
            'cavren_mode_id': 'insight',
            'cavren_web_search': True,
            'cavren_billing_confirmed': True,
            'messages': [{'role': 'user', 'content': 'Teste'}],
        }
        job = bridge.prepare_job(body, 'generation-1')
        self.assertEqual(job['mode_id'], 'insight')
        self.assertEqual(job['mode_options']['manual_route'], 'groq:qwen/qwen3-32b')
        self.assertTrue(job['mode_options']['web_search'])
        self.assertTrue(job['mode_options']['billing_confirmed'])
        body['model'] = 'cavren:auto'
        self.assertEqual(bridge.prepare_job(body, 'generation-2')['mode_options']['manual_route'], '')

    def test_unknown_mode_model_and_invalid_messages_never_spawn_worker(self):
        body = {'model': 'cavren:auto', 'messages': [{'role': 'user', 'content': 'Teste'}]}
        for invalid in (
            {'cavren_mode_id': 'unknown'},
            {'model': 'unapproved-paid-model'},
            {'messages': [{'role': 'tool', 'content': 'unexpected'}]},
            {'max_tokens': True},
        ):
            with patch.object(bridge.subprocess, 'Popen') as spawn:
                status, _ = self.request('POST', '/v1/chat/completions', {**body, **invalid})
                self.assertEqual(status, 400)
                spawn.assert_not_called()

    def test_stream_and_nonstream_map_real_worker_events(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = Path(directory) / 'worker.py'
            worker.write_text('''import json, sys
job = json.load(sys.stdin)
print(json.dumps({"type": "generation.searching"}), flush=True)
print(json.dumps({"type": "generation.sources", "sources": [{"title": "Fonte de teste", "url": "https://example.org", "snippet": "Trecho de teste"}]}), flush=True)
print(json.dumps({"type": "generation.delta", "text": "Olá, Lunvri!"}), flush=True)
print(json.dumps({"type": "generation.completed", "response": {"text": "Olá, Lunvri!", "provider": "test", "model": "test", "public_mode": job["mode_id"], "fallback_index": 0, "usage": {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7}}}), flush=True)
''')
            with (
                patch.object(bridge, 'WORKER', worker),
                patch.object(bridge, 'worker_env', return_value=os.environ.copy()),
            ):
                body = {
                    'model': 'cavren:auto',
                    'cavren_mode_id': 'arquiteto',
                    'messages': [{'role': 'user', 'content': 'Teste'}],
                }
                status, data = self.request('POST', '/v1/chat/completions', body)
                self.assertEqual(status, 200)
                payload = json.loads(data)
                self.assertEqual(payload['choices'][0]['message']['content'], 'Olá, Lunvri!')
                self.assertEqual(payload['cavren']['public_mode'], 'arquiteto')
                self.assertEqual(payload['usage']['total_tokens'], 7)
                status, data = self.request('POST', '/v1/chat/completions', {**body, 'stream': True})
                self.assertEqual(status, 200)
                self.assertIn('Olá, Lunvri!', data)
                self.assertIn('data: [DONE]', data)
                self.assertIn('"finish_reason": "stop"', data)
                self.assertIn('"type": "source"', data)
                self.assertIn('https://example.org', data)
        self.assertFalse(self.server.active)

    def test_disconnect_terminates_the_generation_process(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = Path(directory) / 'waiting.py'
            worker.write_text('import json, sys, time\njson.load(sys.stdin)\ntime.sleep(60)\n')
            with (
                patch.object(bridge, 'WORKER', worker),
                patch.object(bridge, 'worker_env', return_value=os.environ.copy()),
            ):
                client = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
                body = {
                    'model': 'cavren:auto',
                    'stream': True,
                    'messages': [{'role': 'user', 'content': 'Teste de interrupção'}],
                }
                client.request('POST', '/v1/chat/completions', json.dumps(body), self.headers)
                connection = client.sock
                response = client.getresponse()
                response.fp.readline()
                self.assertTrue(self.server.active)
                processes = tuple(self.server.active)
                connection.shutdown(socket.SHUT_RDWR)
                response.close()
                client.close()
                deadline = time.monotonic() + 12
                while self.server.active and time.monotonic() < deadline:
                    time.sleep(0.1)
                self.assertFalse(self.server.active)
                self.assertTrue(all(process.poll() is not None for process in processes))

    def test_context_has_only_one_leading_system_message(self):
        context = GenerationContext(
            (Message('system', 'Identidade'), Message('user', 'Pergunta'), Message('system', 'Contexto externo')),
            (),
            (),
            20,
        )
        result = normalize_context(lambda: context)()
        self.assertEqual([m.role for m in result.messages], ['system', 'user'])
        self.assertEqual(result.messages[0].content, 'Identidade\n\nContexto externo')
        self.assertEqual(result.estimated_input_tokens, 20)

    def test_final_provider_payload_merges_runtime_system_message(self):
        core = Cavren(None, {}, runtime_prompts={'route0': Message('system', 'Modelo atual')})
        messages = [
            Message('system', 'Identidade Cavren'),
            Message('user', 'Fontes externas'),
            Message('user', 'Pergunta'),
        ]
        routed = core._messages_for('route0', messages)
        self.assertEqual([m.role for m in routed], ['system', 'system', 'user', 'user'])
        payload = OpenAIChatPromptAdapter().adapt(routed, provider='cloudflare')
        self.assertEqual([m['role'] for m in payload], ['system', 'user', 'user'])
        self.assertEqual(payload[0]['content'], 'Identidade Lunvri\n\nModelo atual')
        self.assertEqual(payload[-1]['content'], 'Pergunta')


if __name__ == '__main__':
    unittest.main()
