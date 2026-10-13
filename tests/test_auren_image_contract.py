"""Image contracts with fake models, keys and HTTP; no provider network."""
import copy
import unittest
from unittest.mock import patch
import httpx
from cavren.config import ProviderConfig, load_settings
from cavren.errors import CavrenError
from cavren.models import Message
from integration.auren_images import validate, rank
from integration.lunvri_manual import generate_images
from integration.lunvri_bridge import prepare_job
from integration.auren_fallback import candidates


def image(provider='aihorde', name='standard', vision=False, free=True):
    return {'id': f'cavren:{provider}:{name}', 'cavren': {
        'provider': provider, 'model_id': name, 'route_id': f'{provider}:{name}', 'label': name,
        'available': True, 'image_only': True, 'price_kind': 'free' if free else 'unknown',
        'capabilities': {'image_generation': True, 'vision': vision}}}


class ImageContracts(unittest.TestCase):
    def setUp(self):
        self.models = [{'id': 'cavren:auto'}, image(), image('gemini', 'image-native', True)]
        self.job = {'messages': [{'role': 'user', 'content': 'teste'}], 'mode_id': 'insight',
                    'mode_options': {'manual_route': 'aihorde:standard'}, 'lunvri_image_generation': True}
        self.reference = [{'type': 'text', 'text': 'Desenhe'},
                          {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLttAAAAABJRU5ErkJggg=='}}]
    def test_legacy_chat_defaults_and_motor_enum(self):
        with patch('integration.lunvri_bridge.catalog', return_value=self.models):
            job = prepare_job({'model': 'cavren:auto', 'messages': self.job['messages']}, 'new')
        self.assertEqual(job['auren_task'], 'chat')
        self.assertEqual(job['task_kind'], 'chat')
    def test_auto_image_has_own_task_and_preserves_chat_mode(self):
        with patch('integration.lunvri_bridge.catalog', return_value=self.models):
            job = prepare_job({'model': 'cavren:auto', 'messages': self.job['messages'],
                               'auren_task': 'image', 'cavren_mode_id': 'arquiteto',
                               'cavren_web_search': True, 'auren_image_profile': 'rapid'}, 'new')
        self.assertEqual(job['mode_id'], 'arquiteto')
        self.assertEqual(job['task_kind'], 'chat')
        self.assertFalse(job['mode_options']['web_search'])
        self.assertEqual(job['auren_image_profile'], 'rapid')
    def test_horde_reference_rejected_before_worker(self):
        with patch('integration.lunvri_bridge.catalog', return_value=self.models):
            with self.assertRaisesRegex(ValueError, 'referências'):
                prepare_job({'model': self.models[1]['id'], 'messages': [{'role': 'user', 'content': self.reference}]}, 'new')
    def test_auto_reference_routes_only_complete_adapters(self):
        settings = load_settings({'AI_HORDE_API_KEY': 'fake', 'GEMINI_API_KEY': 'fake'})
        job = dict(self.job, auren_image_operation='reference',
                   messages=[{'role': 'user', 'content': self.reference}])
        choices = candidates(job, self.models[1:], settings, {})
        self.assertEqual([m['cavren']['provider'] for m in choices], ['gemini'])
    def test_invalid_parameters_masks_and_tasks(self):
        body = {'model': self.models[1]['id'], 'messages': self.job['messages']}
        with patch('integration.lunvri_bridge.catalog', return_value=self.models):
            for extra in ({'mask': 'fake'}, {'auren_image_parameters': {'width': 123}},
                          {'auren_image_parameters': {'steps': True}}, {'auren_image_parameters': {'seed': 1}},
                          {'auren_task': 'video'}, {'auren_image_profile': 'unknown'}):
                with self.subTest(extra=extra), self.assertRaises(ValueError):
                    prepare_job({**body, **extra}, 'new')
    def test_manual_strict_and_paid_route_confirmation(self):
        settings = load_settings({'GEMINI_API_KEY': 'fake'})
        models = [image('gemini', 'paid', True, False), image('gemini', 'free', True)]
        job = dict(self.job, auren_image_fallback=False,
                   mode_options={'manual_route': 'gemini:paid', 'billing_confirmed': True})
        self.assertEqual([m['cavren']['model_id'] for m in candidates(job, models, settings, {})], ['paid'])
        job['auren_image_fallback'] = True
        self.assertEqual([m['cavren']['model_id'] for m in candidates(job, models, settings, {})], ['paid', 'free'])
        job['mode_options']['billing_confirmed'] = False
        self.assertEqual([m['cavren']['model_id'] for m in candidates(job, models, settings, {})], ['free'])
    def test_profile_ranks_snapshot_workers_without_name_heuristics(self):
        a = {'image_workers': 2, 'route_id': 'aihorde:z'}
        b = {'image_workers': 8, 'route_id': 'aihorde:a'}
        self.assertLess(rank(b, {'auren_image_profile': 'rapid'}), rank(a, {'auren_image_profile': 'rapid'}))
    def test_recent_profile_failure_is_not_hidden_by_old_fast_average(self):
        records={'profile:rapid:cavren:aihorde:fast':{'verified_at':'2026-10-12T19:00:00-03:00','samples':[{'ok':False},{'ok':False}]},'image:cavren:aihorde:fast':{'verified_at':'2026-10-12T18:00:00-03:00'}}
        with patch('integration.auren_validation.evidence',return_value=records),patch('integration.auren_validation.measured_seconds',side_effect=lambda id,kind:10 if id.endswith('fast') else 30):
            self.assertLess(rank({'route_id':'aihorde:available'},{'auren_image_profile':'rapid'}),rank({'route_id':'aihorde:fast'},{'auren_image_profile':'rapid'}))
    def test_new_successful_profile_pair_can_recover_after_older_failure(self):
        records={'profile:rapid:cavren:aihorde:recovered':{'verified_at':'2026-10-12T19:00:00-03:00','samples':[{'ok':False},{'ok':True,'seconds':12},{'ok':True,'seconds':14}]},'image:cavren:aihorde:recovered':{'verified_at':'2026-10-12T18:00:00-03:00'}}
        with patch('integration.auren_validation.evidence',return_value=records),patch('integration.auren_validation.measured_seconds',return_value=30):
            score=rank({'route_id':'aihorde:recovered'},{'auren_image_profile':'rapid'})
            self.assertEqual(score[:3],(0,0,13))
    def test_unsupported_media_never_discarded(self):
        job = dict(self.job, messages=[{'role': 'user', 'content': [{'type': 'input_audio'}]}])
        with self.assertRaisesRegex(CavrenError, 'anexos'):
            validate(job, self.models[1]['cavren'])
    def test_invalid_image_bytes_and_private_urls_fail_before_transport(self):
        for url in ('data:image/png;base64,aW1n','http://127.0.0.1/image.png','https://user:secret@example.com/image.png'):
            job=dict(self.job,auren_image_operation='reference',messages=[{'role':'user','content':[{'type':'image_url','image_url':{'url':url}}]}])
            with self.assertRaises(CavrenError):validate(job,image('openrouter','reference',True)['cavren'])
    def test_openrouter_keeps_every_reference(self):
        calls = []
        def handle(request):
            import json
            calls.append(json.loads(request.content))
            return httpx.Response(200, json={'data': [{'b64_json': 'aW1n'}]})
        cfg = ProviderConfig('openrouter', 'native-image', 'https://openrouter.ai/api/v1', 'OPENROUTER_API_KEY', 'fake')
        parts = self.reference + self.reference[1:] * 9
        with httpx.Client(transport=httpx.MockTransport(handle)) as client:
            generate_images(client, cfg, [Message('user', parts)], 'Desenhe')
        self.assertEqual(len(calls[0]['input_references']), 10)
    def test_completed_horde_request_without_image_has_explicit_error(self):
        cfg=ProviderConfig('aihorde','standard','https://aihorde.net/api/v2','AI_HORDE_API_KEY','fake')
        for generations,code in (([],'invalid_response'),([{'img':'aW1n','censored':True}],'image_censored')):
            def handle(request):
                if request.method=='POST':return httpx.Response(202,json={'id':'11111111-1111-4111-8111-111111111111'})
                if '/check/' in request.url.path:return httpx.Response(200,json={'done':True})
                return httpx.Response(200,json={'generations':generations})
            with self.subTest(code=code),httpx.Client(transport=httpx.MockTransport(handle)) as client:
                with self.assertRaises(CavrenError) as caught:generate_images(client,cfg,[],'Synthetic blue sphere')
                self.assertEqual(caught.exception.code,code)
    def test_queue_fields_missing_values_and_interrupt_cancel(self):
        cfg = ProviderConfig('aihorde', 'standard', 'https://aihorde.net/api/v2', 'AI_HORDE_API_KEY', 'fake')
        class Response:
            def __init__(self, data, code=200): self.data=data; self.status_code=code
            def json(self): return self.data
        class Client:
            cancelled=False
            checks=0
            def post(self, *args, **kw): return Response({'id':'12345678-1234-1234-1234-123456789abc'},202)
            def get(self, *args, **kw):
                self.checks += 1
                return Response({'queue_position': 4, 'wait_time': 12, 'eligible_workers': 2} if self.checks == 1 else {'queue_position':4, 'processing':1})
            def delete(self, *args, **kw): self.cancelled=True
        client=Client(); events=[]
        def report(event):
            events.append(event)
            if event.get('state') == 'processing': raise KeyboardInterrupt
        with patch('integration.lunvri_manual.time.sleep'), self.assertRaises(KeyboardInterrupt):
            generate_images(client,cfg,[],'test',progress=report,job={'generation_id':'new','auren_attempt_id':'new:0'})
        self.assertTrue(client.cancelled)
        queue=next(e for e in events if e.get('queue_position') == 4 and e['state'] == 'queued')
        self.assertEqual(queue['eligible_workers'],2)
        self.assertIn('indisponível',events[-1]['description'])
        self.assertEqual(events[-1]['remote_id'],'12345678-1234-1234-1234-123456789abc')
