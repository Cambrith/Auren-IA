import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from integration import auren_intent as intent
from integration.auren_tasks import classify
from integration.auren_routing import effort_for,QWEN,GPT120

class SemanticIntent(unittest.TestCase):
    def probe(self,result,status=200,prompt='Monte um banner para a feira de ciências'):
        requests=[]
        def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(status,json={'choices':[{'message':{'content':json.dumps(result)}}]})
        real=httpx.Client
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'provider_policy.json').write_text(json.dumps({'groq_free_plan':True}))
            cfg=SimpleNamespace(api_key='synthetic',base_url='https://api.groq.com/openai/v1')
            with patch.object(intent,'STATE',root),patch.object(intent,'verified',return_value=True),patch.object(intent,'connection_settings',return_value=SimpleNamespace(providers={'groq':cfg})),patch.object(intent.httpx,'Client',side_effect=lambda **kw:real(transport=httpx.MockTransport(respond),**kw)):
                result=intent.refine(prompt,[{'role':'user','content':prompt}],classify(prompt,[]))
        return result,requests

    def test_supported_paraphrase_uses_validated_bounded_json_decision(self):
        result,requests=self.probe({'task':'image','mode':'ether'})
        self.assertEqual(result['task'],'image');self.assertEqual(result['reason'],'semantic_request')
        body=requests[0];self.assertEqual(body['max_completion_tokens'],128);self.assertEqual(body['reasoning_effort'],'none');self.assertNotIn('tools',body)

    def test_invalid_output_and_provider_failure_keep_local_decision(self):
        for output,status in [({'task':'terminal','mode':'arquiteto'},200),({'task':'image','mode':'all-knowing'},200),({'task':'image','mode':'ether'},429)]:
            result,_=self.probe(output,status)
            self.assertEqual(result['task'],'chat');self.assertEqual(result['reason'],'conversation')

    def test_negation_and_quoted_media_never_authorize_generation(self):
        for prompt in ('Não desenhe um coelho','Explique como criar um banner','Analise a frase “crie uma imagem”','Crie uma imagem e escreva código Python'):
            result,requests=self.probe({'task':'image','mode':'ether'},prompt=prompt)
            self.assertEqual(result['task'],'chat');self.assertEqual(requests,[])

    def test_simple_drawing_and_profile_effort_are_explicit(self):
        self.assertEqual(classify('Desenhe um coelho',[])['task'],'image')
        self.assertEqual(effort_for(QWEN,'ether'),'high')
        self.assertEqual(effort_for(QWEN,'impeto'),'none')
        self.assertEqual(effort_for(GPT120,'insight'),'high')
