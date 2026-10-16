"""Safety checks for continuation order and no-duplicate resumption."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timedelta
from unittest.mock import patch
from unittest.mock import Mock
import httpx
import base64

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import auren_remaining_probe as remaining
import auren_remaining_followups as followups


class RemainingAuditTests(unittest.TestCase):
    def test_final_followups_only_review_old_bounded_sync_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); run = root / 'round'
            now = datetime.fromisoformat(remaining.audit.now())
            rows = []
            records = {}
            for name, operation, minutes, remote in [('old', 'text', 120, False), ('recent', 'text', 1, False), ('async', 'batch', 120, False), ('remote', 'text', 120, True)]:
                key = 'zai:'+name+'::'+operation
                rows.append({'key': key, 'provider': 'zai', 'operation': operation, 'blocker': 'prior_interrupted_request_unknown', 'prior_evidence': {'source': 'old'}})
                records[key] = {'in_flight': {'at': (now-timedelta(minutes=minutes)).isoformat()}, 'samples': [{'remote_id': 'old-job'}] if remote else []}
            remaining.audit.atomic(run / 'matrix.json', {'rows': rows})
            remaining.audit.atomic(root / 'reports/old/results.json', {'records': records})
            with patch.object(remaining.audit, 'ROOT', root):
                choices = followups.candidates(run)
            self.assertEqual([item['key'] for item in choices], ['zai:old::text'])

    def test_final_followups_cannot_start_before_primary_order_finishes(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            remaining.audit.atomic(run / 'order.json', {'stages': {}})
            with patch.object(sys, 'argv', ['followups', '--run', str(run)]), patch.object(remaining, 'execute_provider') as execute:
                with self.assertRaisesRegex(SystemExit, 'ordered primary pass'):
                    followups.main()
                execute.assert_not_called()

    def test_parallel_queues_never_duplicate_rows_and_keep_default_serial(self):
        groups = {'aihorde': list(range(7)), 'groq': [7, 8]}
        self.assertEqual(len(remaining.audit.execution_groups(groups)), 2)
        queues = remaining.audit.execution_groups(groups, {'aihorde': 30})
        horde = [rows for provider, rows in queues if provider == 'aihorde']
        self.assertEqual(len(horde), 2)
        flattened = [value for rows in horde for value in rows]
        self.assertEqual(sorted(flattened), list(range(7)))
        self.assertEqual(len(flattened), len(set(flattened)))

    def test_horde_completed_image_in_cancel_response_is_not_discarded(self):
        client = Mock(); image = base64.b64encode(b'known-image').decode()
        client.delete.return_value = httpx.Response(200, json={'kudos': 1.25,
            'generations': [{'img': image, 'model': 'model-test', 'censored': False}]})
        def cancelled(proxy, *args):
            proxy.delete('https://aihorde.net/api/v2/generate/status/test')
            return {'real_call': True, 'success': False, 'result': 'queue_budget_inconclusive'}
        with patch.object(remaining, 'BASE_IMAGE_PROBE', side_effect=cancelled), patch.object(remaining.audit, 'decode_image', return_value={'format': 'PNG', 'width': 1, 'height': 1}) as decode:
            result = remaining.corrected_image_probe(client, {'provider': 'aihorde'}, 0, None, None, Path('/synthetic'))
            self.assertTrue(result['success'])
            self.assertTrue(result['generation_delivered_on_cancel'])
            self.assertEqual(result['kudos'], 1.25)
            self.assertEqual(result['resolved_model'], 'model-test')
            decode.assert_called_once_with(b'known-image', Path('/synthetic'))

    def test_horde_text_uses_native_async_and_semantic_check(self):
        with tempfile.TemporaryDirectory() as temp:
            client = Mock()
            client.post.return_value = httpx.Response(202, json={'id': '00000000-0000-0000-0000-000000000001'})
            client.get.return_value = httpx.Response(200, json={'done': True, 'generations': [{'text': 'AZUL|VERDE', 'model': 'horde-test'}], 'kudos': 1})
            row = {'key': 'aihorde:horde-test::text', 'requested_model': 'horde-test'}
            result = remaining.horde_text_probe(client, row, 0, SimpleNamespace(api_key='synthetic', account_id=''), Path(temp))
            self.assertTrue(result['success'])
            self.assertTrue(client.post.call_args.args[0].endswith('/generate/text/async'))
            body = client.post.call_args.kwargs['json']
            self.assertNotIn('messages', body)
            self.assertEqual(body['params']['max_length'], 128)
            self.assertFalse(body['allow_downgrade'])
            client.delete.assert_not_called()

    def test_horde_accepted_without_worker_is_not_approved_and_is_cancelled(self):
        with tempfile.TemporaryDirectory() as temp:
            client = Mock()
            client.post.return_value = httpx.Response(202, json={'id': '00000000-0000-0000-0000-000000000001'})
            client.get.return_value = httpx.Response(200, json={'done': False, 'is_possible': False})
            client.delete.return_value = httpx.Response(200, json={})
            row = {'key': 'aihorde:horde-test::text', 'requested_model': 'horde-test'}
            result = remaining.horde_text_probe(client, row, 0, SimpleNamespace(api_key='synthetic', account_id=''), Path(temp))
            self.assertFalse(result['success'])
            self.assertEqual(result['result'], 'no_eligible_workers_inconclusive')
            self.assertEqual(result['cancel_http_status'], 200)
            client.delete.assert_called_once()

    def test_melotts_uses_native_prompt_and_language(self):
        row = dict(provider='cloudflare', requested_model='@cf/myshell-ai/melotts', operation='speech', endpoint='https://test')
        _, body, _ = remaining.corrected_request_body(row, 0, SimpleNamespace(account_id=''), Path('/unused'))
        self.assertEqual(body, {'prompt': 'Good morning.', 'lang': 'en'})

    def test_native_structured_object_is_validated_as_json(self):
        data = {'result': {'response': {'cidade': 'Lima', 'quantidade': 7, 'preco': None}}}
        text, _, _ = remaining.corrected_extract(data, 'cloudflare')
        self.assertEqual(json.loads(text), {'cidade': 'Lima', 'quantidade': 7, 'preco': None})
        unknown = {'result': {'response': {'unrecognized': {'private': 'omit'}}}}
        self.assertEqual(remaining.corrected_extract(unknown, 'cloudflare')[0], '')

    def test_safety_classifier_is_not_approved_from_nonempty_text(self):
        def response(text): return {'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}]}
        self.assertFalse(remaining.corrected_evaluate(response('Hello there'), 'nvidia', 'moderation_chat', 0)[0])
        self.assertTrue(remaining.corrected_evaluate(response('safe'), 'nvidia', 'moderation_chat', 0)[0])
        self.assertTrue(remaining.corrected_evaluate(response('{"User Safety":"safe"}'), 'nvidia', 'moderation_chat', 0)[0])
        self.assertFalse(remaining.corrected_evaluate(response('unsafe'), 'nvidia', 'moderation_chat', 0)[0])

    def test_provider_checkpoint_recovers_intent_and_preserves_other_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            remaining.audit.atomic(run / 'results.json', {'records': {'gemini:x::text': {'terminal': True}}, 'control': {}})
            remaining.audit.atomic(run / 'journals/groq.json', {'records': {
                'groq:y::text': {'in_flight': {'sample': 0}},
                'gemini:x::text': {'should_not_override_other_provider': True}}, 'control': {}})
            recovered = remaining.merge_provider_journals(run)
            self.assertIn('in_flight', recovered['records']['groq:y::text'])
            self.assertEqual(recovered['records']['gemini:x::text'], {'terminal': True})

    def test_provider_checkpoint_is_durable_before_exception(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp); original_atomic = remaining.audit.atomic
            remaining.audit.atomic(run / 'results.json', {'records': {'gemini:x::text': {'terminal': True}}, 'control': {}})
            def interrupt(path, args):
                value = remaining.audit.read(path / 'results.json')
                value['records']['groq:y::text'] = {'in_flight': {'sample': 0}}
                remaining.audit.atomic(path / 'results.json', value)
                self.assertTrue((path / 'journals/groq.json').exists())
                raise RuntimeError('Synthetic interruption')
            with patch.object(remaining.audit, 'execute', side_effect=interrupt):
                with self.assertRaisesRegex(RuntimeError, 'Synthetic interruption'):
                    remaining.execute_checkpointed(run, 'groq', 1)
            self.assertIs(remaining.audit.atomic, original_atomic)
            recovered = remaining.merge_provider_journals(run)
            self.assertIn('in_flight', recovered['records']['groq:y::text'])
            self.assertTrue(recovered['records']['gemini:x::text']['terminal'])

    def test_native_llava_uses_pixels_and_description_instead_of_chat(self):
        with tempfile.TemporaryDirectory() as temp:
            assets = Path(temp); (assets / 'vision.png').write_bytes(b'\x89PNG')
            row = dict(provider='cloudflare', requested_model='@cf/llava-hf/llava-1.5-7b-hf', operation='vision', endpoint='https://test/<account>')
            url, body, _ = remaining.corrected_request_body(row, 0, SimpleNamespace(account_id='account'), assets)
            self.assertEqual(body['image'], [137, 80, 78, 71])
            self.assertNotIn('messages', body)
            self.assertNotIn('PIXEL-739', body['prompt'])
            self.assertEqual(remaining.corrected_extract({'result': {'description': 'PIXEL-739|2|1'}}, 'cloudflare')[0], 'PIXEL-739|2|1')

    def test_small_zai_test_disables_thinking_without_expanding_token_limit(self):
        row = dict(provider='zai', requested_model='glm-4.5-flash', operation='documents', endpoint='https://test')
        _, body, _ = remaining.corrected_request_body(row, 0, SimpleNamespace(account_id=''), Path('/unused'))
        self.assertEqual(body['thinking'], {'type': 'disabled'})
        self.assertEqual(body['max_tokens'], 512)

    def test_exact_requested_order(self):
        self.assertEqual(remaining.ORDER[:6], ['gemini', 'groq', 'zai', 'ollama', 'cohere', 'mistral'])

    def test_later_provider_cannot_read_credentials_or_call_network(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            remaining.audit.atomic(run / 'order.json', {'stages': {}})
            with patch.object(remaining.audit, 'audit_settings') as settings:
                with self.assertRaisesRegex(SystemExit, 'gemini'):
                    remaining.execute_provider(run, 'groq', 1)
                settings.assert_not_called()

    def test_completed_stage_does_not_repeat_calls(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            remaining.audit.atomic(run / 'order.json', {'stages': {'gemini': {'status': 'reconciled'}}})
            with patch.object(remaining.audit, 'audit_settings') as settings:
                remaining.execute_provider(run, 'gemini', 1)
                settings.assert_not_called()

    def test_prepare_never_overwrites_existing_round(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp); sentinel = {'existing': 'evidence'}
            remaining.audit.atomic(run / 'matrix.json', sentinel)
            remaining.prepare(run)
            self.assertEqual(remaining.audit.read(run / 'matrix.json'), sentinel)

    def test_report_counts_only_new_auxiliary_calls_and_supports_different_row_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            summary = dict(snapshot_at='start', reported_at='end', operations=2,
                           real_attempts=1, auxiliary_real_calls=777, by_status={'not_tested': 2},
                           positive_reported_usd=0, unknown_cost_attempts=1)
            rows = [dict(key='gemini:x::text', provider='gemini', requested_model='x', status='not_tested'),
                    dict(key='groq:y::batch', provider='groq', requested_model='y', status='not_tested', batch_modality='text')]
            remaining.audit.atomic(run / 'complete.json', {'summary': summary, 'rows': rows})
            remaining.audit.atomic(run / 'historical-coverage.json', {'gemini:x::text': {'source': 'prior', 'native_called': True}})
            remaining.audit.atomic(run / 'results.json', {'records': {'gemini:x::text': {'terminal': True, 'samples': [{'auxiliary_call_count': 3}]}}})
            remaining.audit.atomic(run / 'order.json', {'stages': {}})
            with patch.object(remaining.audit, 'report'):
                remaining.export_report(run)
            result = remaining.audit.read(run / 'summary.json')
            self.assertEqual(result['auxiliary_real_calls'], 3)
            self.assertEqual(result['fixture_generation_calls_new'], 0)
            self.assertEqual(result['routes'], 2)
            self.assertFalse(result['all_rows_terminal'])
            self.assertIn('batch_modality', (run / 'complete.csv').read_text())


if __name__ == '__main__': unittest.main()
