import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from cavren.config import load_settings, ProviderConfig
from cavren.errors import CavrenError
from integration import auren_fallback as fallback
from integration.lunvri_connections import parse_credentials, display_name


def model(route, *, free=True, vision=False, image=False):
    provider, name = route.split(':',1)
    return {'id':'cavren:'+route, 'cavren': {'route_id':route, 'provider':provider, 'model_id':name,
        'label':name, 'price_kind':'free' if free else 'unknown', 'available':True,
        'context_window':128000, 'output_limit':4096, 'image_only':image,
        'capabilities': {'vision':vision, 'image_generation':image}}}


class FallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name)
        self.patch = patch.object(fallback,'STATE',self.state);self.patch.start()
        self.settings = load_settings({'GROQ_API_KEY':'fake','GEMINI_API_KEY':'fake','OPENROUTER_API_KEY':'fake'})
        self.models = [model('groq:qwen/qwen3-32b'),model('gemini:gemini-2.5-flash',vision=True),model('openrouter:qwen/test:free')]
        (self.state/'models.json').write_text(json.dumps({'models':self.models}))
        self.job={'generation_id':'test','mode_id':'ether','mode_options':{'manual_route':'','billing_confirmed':False},'messages':[{'role':'user','content':'teste'}], 'max_tokens':4096}
    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()
    def test_markdown_and_legacy_credentials_without_heading_leak(self):
        values=parse_credentials('### Cohere (julgamento)\n- Chave de API: `fake-one`\n### NVIDIA NIM\n- Chave de API: `fake-two`\n### DeepSeek\n- Chave de API: `removed`\nGEMINI_API_KEY=fake-three')
        self.assertEqual(values,{'COHERE_API_KEY':'fake-one','NVIDIA_API_KEY':'fake-two','DEEPSEEK_API_KEY':'removed','GEMINI_API_KEY':'fake-three'})
    def test_clean_names_keep_model_size(self):
        self.assertEqual(display_name('qwen/qwen3-32b:free'),'Qwen3 32B')
    def test_all_modes_have_free_backup_and_preserve_mode(self):
        for mode in ('ether','impeto','insight','arquiteto'):
            job=dict(self.job,mode_id=mode)
            output=[];calls=[]
            def runner(attempt, normalize, *, output):
                calls.append(attempt['mode_options']['manual_route'])
                if len(calls)==1: raise CavrenError('rate_limit','limite',retryable=True,retry_after=120)
                output({'type':'generation.delta','text':'resposta'})
                output({'type':'generation.completed','response':{'text':'resposta'}})
            with patch.object(fallback,'connection_settings',return_value=self.settings):
                fallback.run(job,lambda x:x,route_runner=runner,output=output.append)
            self.assertEqual(len(calls),2)
            self.assertEqual(output[-1]['response']['public_mode'],mode)
            self.assertEqual(output[-1]['response']['fallback_index'],1)
            self.assertIn('generation.fallback',[e['type'] for e in output])
            (self.state/'route_cooldowns.json').unlink()
    def test_images_have_backups_in_every_conversation_mode(self):
        images = [model('gemini:plain-image-a', image=True), model('gemini:plain-image-b', image=True)]
        for mode in ('ether', 'impeto', 'insight', 'arquiteto'):
            job = dict(self.job, mode_id=mode, lunvri_image_generation=True,
                       mode_options={'manual_route': 'gemini:plain-image-a'})
            choices = fallback.candidates(job, images, self.settings, {})
            self.assertEqual([m['cavren']['model_id'] for m in choices], ['plain-image-a', 'plain-image-b'])

    def test_deadline_is_shared_and_stale_events_are_ignored(self):
        calls = []; events = []
        def runner(job, normalize, *, output):
            calls.append(job['auren_deadline'])
            output({'type': 'generation.delta', 'text': 'antigo', 'generation_id': 'old'})
            if len(calls) == 1:
                raise CavrenError('network', 'falha', retryable=True)
            output({'type': 'generation.completed', 'response': {'text': 'ok'}})
        with patch.object(fallback, 'connection_settings', return_value=self.settings):
            fallback.run(self.job, lambda x: x, route_runner=runner, output=events.append)
        self.assertEqual(calls[0], calls[1])
        self.assertFalse(any(e.get('text') == 'antigo' for e in events))

    def test_partial_answer_never_switches(self):
        calls=[];output=[]
        def runner(job,normalize,*,output):
            calls.append(1);output({'type':'generation.delta','text':'parte importante'})
            raise CavrenError('network','interrompido',retryable=True)
        with patch.object(fallback,'connection_settings',return_value=self.settings),self.assertRaises(CavrenError):
            fallback.run(self.job,lambda x:x,route_runner=runner,output=output.append)
        self.assertEqual(len(calls),1)
        self.assertEqual(output[0]['text'],'parte importante')
    def test_attachments_cost_and_cooldowns_filter_routes(self):
        job=copy.deepcopy(self.job);job['messages'][0]['content']=[{'type':'image_url','image_url':{'url':'data:image/png;base64,eA=='}}]
        choices=fallback.candidates(job,self.models+[model('openrouter:paid',free=False,vision=True)],self.settings,{})
        self.assertEqual([m['cavren']['provider'] for m in choices],['gemini'])
        choices=fallback.candidates(self.job,self.models,self.settings,{'groq:*':time.time()+200})
        self.assertNotIn('groq',[m['cavren']['provider'] for m in choices])
    def test_expired_cooldown_recovers(self):
        (self.state/'route_cooldowns.json').write_text(json.dumps({'old':time.time()-1}))
        self.assertEqual(fallback.cooldowns(),{})
    def test_rejected_paid_manual_does_not_enter_backup(self):
        job=copy.deepcopy(self.job);job['mode_options']['manual_route']='openrouter:paid'
        choices=fallback.candidates(job,[model('openrouter:paid',free=False)],self.settings,{})
        self.assertEqual(choices,[])

class HordeTests(unittest.TestCase):
    def test_queue_completion_and_timeout_cancel(self):
        from integration.lunvri_manual import generate_images
        from cavren.config import ProviderConfig
        cfg = ProviderConfig('aihorde','test-model','https://aihorde.net/api/v2','AI_HORDE_API_KEY','fake')
        class Response:
            status_code=200
            def __init__(self,data,status=200): self.data=data;self.status_code=status
            def json(self): return self.data
        class Client:
            cancelled=False
            def post(self,*args,**kwargs): return Response({'id':'12345678-1234-1234-1234-123456789abc'},202)
            def get(self,url,**kwargs):
                return Response({'done':True}) if '/check/' in url else Response({'generations':[{'img':'aW1hZ2U='}]})
            def delete(self,*args,**kwargs): self.cancelled=True
        c=Client();files,text=generate_images(c,cfg,[],'imagem de teste')
        self.assertEqual(len(files),1);self.assertFalse(c.cancelled)
        with patch('integration.lunvri_manual.time.monotonic',side_effect=[0,0,0,500]),self.assertRaises(CavrenError):
            generate_images(c,cfg,[],'imagem de teste')
        self.assertTrue(c.cancelled)
