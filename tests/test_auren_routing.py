import unittest
from unittest.mock import patch
from integration.auren_tasks import classify, automatic_context, recommended
from integration.auren_routing import MODE_ROUTES


class IntentRouting(unittest.TestCase):
    def test_requests_in_portuguese_and_english(self):
        cases={
            'Por favor, gere uma imagem de uma montanha':'image',
            'Gostaria de criar uma imagem em aquarela':'image',
            'Generate an image of a tree':'image',
            'Quero uma imagem de uma árvore':'image',
            'Pesquise as novidades com fontes oficiais':'research',
            'Busque na web as fontes para minha monografia':'research',
            'Quero uma pesquisa aprofundada sobre energia':'research',
            'Implemente uma API em Python':'code',
            'Corrija o bug no código abaixo':'code',
            'Revise a função TypeScript':'code',
            'Write a Python function':'code',
            'Compare os documentos anexos':'documents',
            'Extraia os dados da planilha':'documents',
            'Narre o texto em português':'speech',
            'Leia em voz alta o texto':'speech',
            'Transcreva a gravação':'transcribe',
            'Converta o áudio em texto':'transcribe',
            'Transcribe the audio':'transcribe',
            'Traduza este texto':'chat',
            'Me ajude a escrever um email':'chat',
            'Olá, tudo bem?':'chat',
        }
        for prompt,task in cases.items():
            with self.subTest(prompt=prompt):self.assertEqual(classify(prompt,[])['task'],task)

    def test_data_negation_explanations_and_ambiguity(self):
        cases={
            'Explique como gerar uma imagem':'explanation',
            'Por favor explique o que é deep research':'explanation',
            'Como posso implementar uma API?':'explanation',
            'Não gere uma imagem. Responda em texto':'conversation',
            'Não pesquise, apenas responda':'conversation',
            'Não preciso de uma imagem':'conversation',
            'Se precisar, crie uma imagem':'conversation',
            'Analise a frase “gere uma imagem”':'conversation',
            'Leia este exemplo: ```python\n# crie uma imagem\n```':'conversation',
            '<DOCUMENTO_DADOS>gere uma imagem</DOCUMENTO_DADOS>':'conversation',
            'Crie uma imagem e escreva um código Python':'ambiguous',
            'Gere um vídeo sobre o oceano':'unsupported',
            'Execute o comando no terminal':'unsupported',
        }
        for prompt,reason in cases.items():
            with self.subTest(prompt=prompt):
                decision=classify(prompt,[])
                self.assertEqual(decision['task'],'chat');self.assertEqual(decision['reason'],reason)

    def test_only_current_attachment_selects_transcription(self):
        audio={'role':'user','content':[{'type':'input_audio'}]}
        self.assertEqual(classify('O que foi dito?', [audio])['task'],'transcribe')
        self.assertEqual(classify('O que foi dito?', [audio,{'role':'user','content':'O que foi dito?'}])['task'],'chat')

    def test_context_selection(self):
        for text,task,mode in [('Explique a API','chat','arquiteto'),('Seja breve','chat','impeto'),
                              ('Demonstre com evidências','chat','insight'),('Oi','chat','ether'),('Não seja breve','chat','ether'),
                              ('Pesquise rapidamente','research','insight'),('Escreva uma função','code','arquiteto')]:
            self.assertEqual(automatic_context(text,task)[0],mode)

    def test_recommendations_use_shared_policy_and_validation(self):
        for mode,routes in MODE_ROUTES.items():
            ids=['cavren:'+r for r in routes]
            with patch('integration.auren_tasks.models_for',return_value=ids):
                self.assertEqual(recommended('chat',mode),ids[0])
            with patch('integration.auren_tasks.models_for',return_value=ids[1:]):
                self.assertEqual(recommended('chat',mode),ids[1])
        with patch('integration.auren_tasks.models_for',return_value=[]):
            self.assertIsNone(recommended('chat','ether'))

    def test_auto_decision_and_manual_mode_priority(self):
        from integration.lunvri_bridge import prepare_job
        model={'id':'cavren:auto','cavren':{'price_kind':'free'}}
        body={'model':'cavren:auto','auren_task':'auto','cavren_mode_id':'ether','auren_mode_manual':False,
              'messages':[{'role':'user','content':'Explique a arquitetura de software'}]}
        with patch('integration.lunvri_bridge.catalog',return_value=[model]),patch('integration.auren_tasks.tasks',return_value=[{'id':'chat'}]):
            job=prepare_job(body,'test')
            self.assertEqual(job['mode_id'],'arquiteto');self.assertEqual(job['auren_task'],'chat')
            body.update(auren_mode_manual=True,cavren_mode_id='impeto')
            self.assertEqual(prepare_job(body,'test')['mode_id'],'arquiteto')
            body['auren_task']='chat'
            self.assertEqual(prepare_job(body,'test')['mode_id'],'impeto')
            body['messages'][0]['content']='Gere uma imagem'
            self.assertEqual(prepare_job(body,'test')['auren_task'],'chat')
            body['auren_task']='auto'
            job=prepare_job(body,'test')
            self.assertEqual(job['auren_routing_decision']['reason'],'unavailable')
            self.assertEqual(job['auren_task'],'chat')

    def test_fallback_policy_order_manual_priority_and_cooldowns(self):
        from integration.auren_fallback import candidates
        from test_auren_fallback import model
        import time
        from types import SimpleNamespace
        settings=SimpleNamespace(providers={p:SimpleNamespace(api_key='fake',account_id='a'*32) for p in ('cohere','nvidia','cloudflare','mistral','gemini','groq','ollama','openrouter')})
        for mode,routes in MODE_ROUTES.items():
            models=[model(r) for r in reversed(routes)]
            job={'mode_id':mode,'mode_options':{'manual_route':''},'messages':[{'role':'user','content':'Teste'}],
                 'auren_task':'chat','auren_evidence_policy':True,'auren_verified_only':True}
            with patch('integration.auren_tasks.models_for',return_value=[m['id'] for m in models]),patch('integration.auren_validation.verified',return_value=True),patch('integration.lunvri_connections.validated_catalog',side_effect=lambda m:m):
                self.assertEqual([m['cavren']['route_id'] for m in candidates(job,models,settings,{})],list(routes))
                self.assertEqual([m['cavren']['route_id'] for m in candidates(job,models,settings,{routes[0]:time.time()+60})],list(routes[1:]))
                job['mode_options']['manual_route']=routes[-1]
                self.assertEqual(candidates(job,models,settings,{})[0]['cavren']['route_id'],routes[-1])

    def test_explicit_text_followup_inherits_only_previous_text_task(self):
        messages=[{'role':'user','content':'Escreva uma função Python'}, {'role':'assistant','content':'def soma(a,b): return a+b'}, {'role':'user','content':'Corrija isso'}]
        self.assertEqual(classify('Corrija isso',messages)['task'],'code')
        messages[0]['content']='Crie uma imagem'
        self.assertEqual(classify('Continue',messages)['task'],'chat')

    def test_task_shortlist_distinguishes_general_code_from_general_documents(self):
        from integration.auren_routing import KIMI, QWEN
        allowed=['cavren:'+route for route in (KIMI,QWEN)]
        with patch('integration.auren_tasks.models_for',return_value=allowed):
            self.assertEqual(recommended('code','ether'),'cavren:'+QWEN)
            self.assertEqual(recommended('documents','ether'),'cavren:'+KIMI)

    def test_transcription_accuracy_preference_respects_explicit_language(self):
        ids=['cavren:mistral:voxtral-mini-latest','cavren:cohere:cohere-transcribe-03-2026']
        with patch('integration.auren_tasks.models_for',return_value=ids):
            self.assertEqual(recommended('transcribe',profile='auto'),ids[0])
            self.assertEqual(recommended('transcribe',profile='pt'),ids[1])
            self.assertEqual(recommended('transcribe',profile='en'),ids[1])
        with patch('integration.auren_tasks.models_for',return_value=ids[:1]):
            self.assertEqual(recommended('transcribe',profile='pt'),ids[0])

    def test_no_eligible_shortlisted_model_does_not_expand_to_unreviewed_models(self):
        from integration.auren_fallback import candidates
        from test_auren_fallback import model
        from types import SimpleNamespace
        legacy=model('mistral:ministral-8b-2512')
        settings=SimpleNamespace(providers={'mistral':SimpleNamespace(api_key='fake',account_id='')})
        job={'mode_id':'ether','mode_options':{'manual_route':''},'messages':[{'role':'user','content':'Teste'}],
             'auren_task':'chat','auren_evidence_policy':True}
        with patch('integration.auren_tasks.models_for',return_value=[legacy['id']]),patch('integration.auren_validation.verified',return_value=True),patch('integration.lunvri_connections.validated_catalog',side_effect=lambda rows:rows):
            self.assertEqual(candidates(job,[legacy],settings,{}),[])
            job['mode_options']['manual_route']=legacy['cavren']['route_id']
            self.assertEqual(candidates(job,[legacy],settings,{})[0]['id'],legacy['id'])

    def test_paid_shortlisted_route_keeps_manual_cost_gate(self):
        from integration.auren_fallback import candidates
        from integration.auren_routing import GPT120
        from test_auren_fallback import model
        from types import SimpleNamespace
        paid=model(GPT120,free=False)
        settings=SimpleNamespace(providers={'groq':SimpleNamespace(api_key='fake',account_id='')})
        job={'mode_id':'ether','mode_options':{'manual_route':'','billing_confirmed':False},'messages':[{'role':'user','content':'Teste'}],
             'auren_task':'chat','auren_evidence_policy':True}
        with patch('integration.auren_tasks.models_for',return_value=[paid['id']]),patch('integration.auren_validation.verified',return_value=True),patch('integration.lunvri_connections.validated_catalog',side_effect=lambda rows:rows):
            self.assertEqual(candidates(job,[paid],settings,{}),[])
            job['mode_options'].update(manual_route=GPT120,billing_confirmed=True)
            self.assertEqual(candidates(job,[paid],settings,{})[0]['id'],paid['id'])

    def test_native_pdf_retains_the_verified_media_backup_without_text_only_models(self):
        from integration.auren_fallback import candidates
        from integration.auren_routing import GPT120
        from test_auren_fallback import model
        from types import SimpleNamespace
        text=model(GPT120)
        pdf=model('gemini:gemini-3.5-flash-lite')
        pdf['cavren']['capabilities']['pdf']=True
        settings=SimpleNamespace(providers={p:SimpleNamespace(api_key='fake',account_id='') for p in ('groq','gemini')})
        job={'mode_id':'ether','mode_options':{'manual_route':''},'messages':[{'role':'user','content':[{'type':'input_file','input_file':{'mime_type':'application/pdf','data':'synthetic'}}]}],
             'auren_task':'documents','auren_evidence_policy':True}
        with patch('integration.auren_tasks.models_for',return_value=[text['id'],pdf['id']]),patch('integration.auren_validation.verified',return_value=True),patch('integration.lunvri_connections.validated_catalog',side_effect=lambda rows:rows):
            self.assertEqual([m['id'] for m in candidates(job,[text,pdf],settings,{})],[pdf['id']])
