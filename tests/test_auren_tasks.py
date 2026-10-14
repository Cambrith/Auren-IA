import base64
import unittest
from unittest.mock import patch
from integration.auren_tasks import detect
from integration.auren_modes import specialize
from integration.auren_transcribe import audio
from cavren.errors import CavrenError

class Tasks(unittest.TestCase):
    def test_automatic_context_defaults_and_ambiguity(self):
        from integration.auren_tasks import automatic_context
        self.assertEqual(automatic_context('Responda rapidamente','chat'),('impeto','rapid'))
        self.assertEqual(automatic_context('Explique passo a passo','chat'),('insight','detailed'))
        self.assertEqual(automatic_context('Crie uma imagem detalhada e rápida','image'),('ether','balanced'))
        self.assertEqual(automatic_context('Pesquise rapidamente','research')[0],'insight')
        self.assertEqual(automatic_context('Explique "resposta curta"','chat')[0],'ether')

    def test_automatic_task_ignores_historical_manual_image_profile(self):
        from integration.lunvri_bridge import prepare_job
        model={'id':'cavren:auto','cavren':{'price_kind':'free','provider':'aihorde','capabilities':{'image_generation':True}}}
        body={'model':model['id'],'auren_task':'auto','auren_mode_manual':False,'auren_image_profile':'balanced','auren_image_profile_manual':False,'messages':[{'role':'user','content':'Crie uma imagem detalhada de uma esfera'}]}
        with patch('integration.lunvri_bridge.catalog',return_value=[model]):
            self.assertEqual(prepare_job(body,'test')['auren_image_profile'],'detailed')
            body.update(auren_image_profile_manual=True,auren_image_profile='rapid')
            self.assertEqual(prepare_job(body,'test')['auren_image_profile'],'detailed')
            body['auren_task']='image'
            self.assertEqual(prepare_job(body,'test')['auren_image_profile'],'rapid')

    def test_cohere_detection_is_rejected_locally_before_http(self):
        from types import SimpleNamespace
        from integration import auren_transcribe
        job={'generation_id':'synthetic','mode_id':'ether','mode_options':{'manual_route':'cohere:cohere-transcribe-03-2026'},'messages':[{'role':'user','content':[{'type':'input_audio','input_audio':{'format':'wav','data':'aW1n'}}]}],'auren_transcribe_language':'auto'}
        with patch('integration.auren_validation.verified',return_value=True),patch.object(auren_transcribe,'connection_settings',return_value=SimpleNamespace(providers={'cohere':SimpleNamespace(api_key='synthetic')})),patch('httpx.Client') as client:
            with self.assertRaisesRegex(CavrenError,'idioma explícito'):
                auren_transcribe.run(job,lambda m:m,output=lambda e:None)
            client.assert_not_called()

    def test_groq_transcription_uses_audio_transport_and_optional_language(self):
        import httpx
        from types import SimpleNamespace
        from integration import auren_transcribe
        for model, language in (('whisper-large-v3', 'pt'), ('whisper-large-v3-turbo', 'auto')):
            seen=[]
            def response(request):
                seen.append(request)
                return httpx.Response(200, json={'text':'Auren está pronta. Bom dia.'})
            original=httpx.Client
            job={'generation_id':'synthetic','mode_id':'ether','mode_options':{'manual_route':'groq:'+model},
                 'messages':[{'role':'user','content':[{'type':'input_audio','input_audio':{'format':'wav','data':'aW1n'}}]}],
                 'auren_transcribe_language':language}
            events=[]
            with patch('integration.auren_validation.verified',return_value=True), patch.object(auren_transcribe,'connection_settings',return_value=SimpleNamespace(providers={'groq':SimpleNamespace(api_key='synthetic')})), patch('httpx.Client',side_effect=lambda **kw:original(transport=httpx.MockTransport(response),**kw)):
                auren_transcribe.run(job,None,output=events.append)
            self.assertEqual(str(seen[0].url),'https://api.groq.com/openai/v1/audio/transcriptions')
            self.assertIn(model.encode(),seen[0].content)
            self.assertEqual(b'name="language"' in seen[0].content,language!='auto')
            self.assertTrue(any(e['type']=='generation.completed' for e in events))

    def test_nonchat_profiles_have_task_owned_contexts(self):
        from integration.auren_profiles import DEFINITIONS
        for task in ('code','documents','research'):
            for profile in DEFINITIONS[task]['profiles']:
                content=specialize([{'role':'user','content':'synthetic'}],profile['id'],task)[0]['content']
                self.assertIn(profile['name'],content)
                if task in ('documents','research'):
                    self.assertNotIn('Você é Auren no modo Arquiteto',content)

    def test_detector_and_ambiguous_fallback(self):
        for text,expected in [('Crie uma imagem de uma esfera','image'),('Escreva uma função Python','code'),
                              ('Pesquise e compare duas fontes oficiais','research'),('Resuma o documento anexo','documents'),
                              ('Explique como gerar uma imagem','chat'),('Crie uma imagem e escreva um código Python','chat'),
                              ('Explique a frase "crie uma imagem"','chat')]:
            self.assertEqual(detect(text,[]),expected)
    def test_document_data_cannot_choose_a_task(self):
        self.assertEqual(detect('Analise o documento <documento_dados>crie uma imagem</documento_dados>',[]),'documents')
    def test_audio_requires_one_complete_reference(self):
        job={'messages':[{'role':'user','content':[{'type':'input_audio','input_audio':{'format':'wav','data':'aW1n'}}]}]}
        self.assertEqual(audio(job),(b'img','wav'))
        job['messages'][0]['content'].append({'type':'image_url'})
        with self.assertRaises(CavrenError):audio(job)
    def test_continuation_preserves_partial_response_and_adds_explicit_request(self):
        from integration.lunvri_bridge import prepare_job
        model={'id':'cavren:auto','cavren':{'price_kind':'free'}}
        with patch('integration.lunvri_bridge.catalog',return_value=[model]):
            job=prepare_job({'model':model['id'],'auren_continue_response':True,'messages':[{'role':'user','content':'Escreva uma lista.'},{'role':'assistant','content':'1. Primeiro item'}]},'test')
        self.assertEqual(job['messages'][-2]['content'],'1. Primeiro item')
        self.assertEqual(job['messages'][-1]['role'],'user')
        self.assertIn('Continue',job['messages'][-1]['content'])
    def test_official_research_has_targeted_queries_and_domain_boundaries(self):
        from integration.auren_research import plan, accepts
        queries,domains=plan('Pesquise as cotas gratuitas Cohere e Cloudflare com fontes oficiais')
        self.assertEqual(len(queries),2)
        self.assertTrue(all(q.startswith('site:') for q in queries))
        self.assertTrue(accepts({'url':'https://docs.cohere.com/docs/rate-limits'},domains))
        self.assertFalse(accepts({'url':'https://docs.cohere.com.evil.example/'},domains))
        self.assertFalse(accepts({'url':'https://example.com/blog'},domains))
    def test_incompatible_manual_model_is_not_silently_replaced(self):
        from integration.lunvri_bridge import prepare_job
        model={'id':'cavren:nvidia:voice','cavren':{'price_kind':'free','provider':'nvidia','task_operations':['speech']}}
        with patch('integration.lunvri_bridge.catalog',return_value=[model]),patch('integration.auren_tasks.tasks',return_value=[{'id':'chat'}]):
            with self.assertRaisesRegex(ValueError,'modelo manual'):
                prepare_job({'model':model['id'],'auren_task':'chat','messages':[{'role':'user','content':'Teste'}]},'test')
    def test_modes_have_distinct_specialized_contexts(self):
        contexts=[specialize([{'role':'user','content':'Teste'}],mode,'chat')[0]['content'] for mode in ('ether','impeto','insight','arquiteto')]
        self.assertEqual(len(set(contexts)),4)
        self.assertIn('engenharia de software',contexts[-1])
        self.assertIn('Não afirme testes',contexts[-1])
