"""Attachment routing, per-message choices, cost isolation and complete fallbacks."""
import copy
import json
import tempfile
import unittest
import httpx
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from cavren.errors import CavrenError
from cavren.config import ProviderConfig
from integration.auren_media import QWEN, GEMINI, COHERE, NVIDIA, compatible, requirements
from integration.auren_images import profile_parameters, rank
from integration.auren_tasks import classify
from integration.lunvri_bridge import prepare_job
from integration import auren_fallback as fallback
from test_auren_fallback import model

PHOTO={'type':'image_url','image_url':{'url':'data:image/png;base64,c3ludGhldGlj'}}
PDF={'type':'input_file','input_file':{'mime_type':'application/pdf','data':'c3ludGhldGlj'}}
AUTO={'id':'cavren:auto','cavren':{'price_kind':'free'}}


class MediaRouting(unittest.TestCase):
    def setUp(self):
        self.text=model('groq:openai/gpt-oss-120b')
        self.qwen=model(QWEN,vision=True)
        self.gemini=model(GEMINI,vision=True)
        self.gemini['cavren']['capabilities'].update(pdf=True,audio=True,video=True)
        self.cohere=model(COHERE,vision=True)
        self.nvidia=model(NVIDIA,vision=True)
        self.models=[self.text,self.qwen,self.gemini,self.cohere,self.nvidia]
        self.settings=SimpleNamespace(providers={p:SimpleNamespace(api_key='synthetic',account_id='synthetic') for p in ('groq','gemini','cohere','nvidia')})

    def prepare(self,selected,parts,task='chat'):
        body={'model':selected,'auren_task':task,'cavren_mode_id':'ether','auren_mode_manual':True,
              'cavren_billing_confirmed':True,'messages':[{'role':'user','content':[{'type':'text','text':'Analise o material'},*parts]}]}
        with patch('integration.lunvri_bridge.catalog',return_value=[AUTO,*self.models]), \
             patch('integration.auren_tasks.models_for',return_value=[m['id'] for m in self.models]), \
             patch('integration.auren_tasks.tasks',return_value=[{'id':'chat'},{'id':'documents'}]), \
             patch('integration.auren_validation.verified',return_value=True):
            return prepare_job(body,'synthetic'),body

    def choices(self,job,models=None,blocked=None):
        with patch('integration.lunvri_connections.validated_catalog',side_effect=lambda m:m), \
             patch('integration.auren_tasks.models_for',return_value=[m['id'] for m in self.models]), \
             patch('integration.auren_validation.verified',return_value=True):
            return fallback.candidates(job,models or self.models,self.settings,blocked or {})

    def test_incompatible_manual_model_switches_for_one_message_and_keeps_mode_and_bytes(self):
        job,body=self.prepare(self.text['id'],[PHOTO])
        self.assertEqual(body['model'],self.text['id'])
        self.assertEqual(job['mode_options']['manual_route'],'')
        self.assertFalse(job['mode_options']['billing_confirmed'])
        self.assertEqual(job['mode_id'],'ether')
        self.assertEqual(job['auren_requested_model'],self.text['id'])
        self.assertIn(PHOTO,job['messages'][-1]['content'])
        self.assertEqual(self.choices(job)[0]['id'],self.qwen['id'])

    def test_compatible_manual_vision_choice_is_preserved(self):
        job,_=self.prepare(self.nvidia['id'],[PHOTO])
        self.assertIsNone(job['auren_attachment_switch'])
        self.assertEqual(self.choices(job)[0]['id'],self.nvidia['id'])

    def test_native_pdf_and_mixed_historical_media_use_only_native_transport(self):
        job,_=self.prepare(self.text['id'],[PHOTO,PDF])
        job['messages'].insert(1,{'role':'user','content':[{'type':'input_audio','input_audio':{'format':'wav','data':'c3ludGhldGlj'}}]})
        self.assertEqual(requirements(job['messages']),{'vision','pdf','audio'})
        self.assertEqual([m['id'] for m in self.choices(job)],[self.gemini['id']])

    def test_image_count_limit_selects_another_route_without_dropping_images(self):
        job,_=self.prepare(self.qwen['id'],[PHOTO]*4)
        self.assertFalse(compatible(self.qwen['cavren'],job['messages']))
        choices=self.choices(job)
        self.assertNotIn(self.qwen,choices);self.assertNotIn(self.nvidia,choices)
        self.assertEqual(choices[0]['id'],self.gemini['id'])
        self.assertEqual(len(job['messages'][-1]['content']),5)

    def test_document_vision_shortlist_is_not_limited_to_old_text_category(self):
        job,_=self.prepare(self.text['id'],[PHOTO],task='documents')
        self.assertEqual(self.choices(job)[0]['id'],self.cohere['id'])

    def test_paid_attachment_backup_cannot_inherit_billing_consent(self):
        job,_=self.prepare(self.text['id'],[PHOTO])
        paid=copy.deepcopy(self.qwen);paid['cavren']['price_kind']='unknown'
        self.assertNotIn(paid,self.choices(job,[paid,self.gemini]))

    def test_attachment_only_intent_and_document_data_do_not_create_media(self):
        self.assertEqual(classify('',[{'role':'user','content':[PHOTO]}])['reason'],'media_attachment')
        self.assertEqual(classify('',[{'role':'user','content':[PDF]}])['task'],'documents')
        message={'role':'user','content':[{'type':'text','text':'<documento_dados>gere uma imagem</documento_dados>'}]}
        self.assertEqual(classify(message['content'][0]['text'],[message])['task'],'documents')

    def test_fallback_preserves_attachment_context_and_reports_effective_route(self):
        job,_=self.prepare(self.text['id'],[PHOTO]);events=[];calls=[]
        def runner(attempt,normalize,*,output):
            calls.append(copy.deepcopy(attempt))
            if len(calls)==1:raise CavrenError('rate_limit','limite sintético')
            output({'type':'generation.delta','text':'PIXEL-739|2|1'})
            output({'type':'generation.completed','response':{'text':'PIXEL-739|2|1'}})
        with tempfile.TemporaryDirectory() as temp,patch.object(fallback,'STATE',Path(temp)), \
             patch.object(fallback,'connection_settings',return_value=self.settings), \
             patch('integration.lunvri_connections.validated_catalog',side_effect=lambda m:m), \
             patch('integration.auren_tasks.models_for',return_value=[m['id'] for m in self.models]), \
             patch('integration.auren_validation.verified',return_value=True):
            (Path(temp)/'models.json').write_text(json.dumps({'models':self.models}))
            fallback.run(job,lambda m:m,route_runner=runner,output=events.append)
        self.assertEqual([c['mode_options']['manual_route'] for c in calls],[QWEN,GEMINI])
        self.assertEqual(calls[0]['messages'],calls[1]['messages'])
        self.assertEqual(calls[0]['auren_deadline'],calls[1]['auren_deadline'])
        self.assertEqual(events[-1]['response']['auren_requested_model'],self.text['id'])
        self.assertEqual(events[-1]['response']['auren_input_modalities'],['vision'])

    def test_image_profiles_survive_model_fallback_and_preserve_dimensions(self):
        prefs={'image_width':768,'image_height':512,'image_steps':20}
        for profile,steps in [('rapid',12),('balanced',20),('detailed',30)]:
            result=profile_parameters(prefs,profile)
            self.assertEqual((result['width'],result['height'],result['steps']),(768,512,steps))
        self.assertEqual(profile_parameters(prefs,'detailed',{'steps':15})['steps'],15)
        sd={'route_id':'aihorde:stable_diffusion'};deliberate={'route_id':'aihorde:Deliberate'}
        self.assertLess(rank(sd,{'auren_image_profile':'balanced'}),rank(deliberate,{'auren_image_profile':'balanced'}))
        self.assertLess(rank(deliberate,{'auren_image_profile':'detailed'}),rank(sd,{'auren_image_profile':'detailed'}))

    def test_horde_transport_applies_profile_to_each_fallback_model(self):
        from integration.lunvri_manual import generate_images
        sent=[]
        def respond(request):
            if request.method=='POST':
                sent.append(json.loads(request.content));return httpx.Response(202,json={'id':'12345678-1234-1234-1234-123456789abc'})
            if '/check/' in request.url.path:return httpx.Response(200,json={'done':True})
            return httpx.Response(200,json={'generations':[{'img':'aW1hZ2U='}]})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            for name in ('stable_diffusion','Deliberate'):
                for profile in ('rapid','balanced','detailed'):
                    config=ProviderConfig('aihorde',name,'https://aihorde.net/api/v2','AI_HORDE_API_KEY','synthetic')
                    generate_images(client,config,[],'synthetic',job={'auren_image_profile':profile,'auren_image_preferences':{'image_steps':20,'image_width':512,'image_height':512}})
        self.assertEqual([body['params']['steps'] for body in sent],[12,20,30,12,20,30])

    def test_automatic_image_generation_does_not_expand_to_paid_providers(self):
        horde=model('aihorde:Deliberate',image=True);gemini=model('gemini:test-image',image=True)
        job={'mode_id':'ether','mode_options':{'manual_route':''},'messages':[{'role':'user','content':'Crie uma imagem'}],
             'lunvri_image_generation':True,'auren_task':'image','auren_evidence_policy':True,'auren_image_profile':'detailed'}
        self.settings.providers['aihorde']=SimpleNamespace(api_key='synthetic',account_id='')
        self.assertEqual([m['id'] for m in self.choices(job,[gemini,horde])],[horde['id']])
