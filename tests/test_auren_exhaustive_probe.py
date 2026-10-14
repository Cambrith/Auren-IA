"""Synthetic regressions for the audit harness; no vault/API calls."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('auren_exhaustive_probe',ROOT/'scripts/auren_exhaustive_probe.py');probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
class AuditTests(unittest.TestCase):
 def test_embeddings_never_chat(self):
  e={'provider':'mistral','model':'codestral-embed','metadata':{'capabilities':{'completion_chat':False}}};self.assertEqual(probe.operations(e),['embeddings'])
 def test_batch_alias_never_sync_chat(self):
  e={'provider':'openrouter','model':'x/test:batch','metadata':{'architecture':{'output_modalities':['text']}}};self.assertEqual(probe.operations(e),['batch'])
 def test_cohere_every_announced_endpoint(self):
  e={'provider':'cohere','model':'x','metadata':{'endpoints':['embed','rerank','parse']}};self.assertEqual(probe.operations(e),['embeddings','parse','rerank'])
 def test_gemini_live_never_chat(self):
  e={'provider':'gemini','model':'gemini-live','metadata':{'supportedGenerationMethods':['bidiGenerateContent']}};self.assertEqual(probe.operations(e),['live'])
 def test_code_is_structurally_checked(self):
  self.assertTrue(probe.check_code('def soma(a,b):\n return a+b'));self.assertFalse(probe.check_code('def soma(a,b):\n return 7'));self.assertFalse(probe.check_code('import os\ndef soma(a,b):\n return a+b'))
 def test_two_complementary_text_checks(self):
  d={'choices':[{'message':{'content':'AZUL|VERDE'},'finish_reason':'stop'}]};self.assertTrue(probe.evaluate(d,'openrouter','text',0)[0]);self.assertFalse(probe.evaluate(d,'openrouter','text',1)[0])
 def test_truncation_inconclusive(self):
  d={'choices':[{'message':{'content':'AZUL|VERDE'},'finish_reason':'length'}]};self.assertEqual(probe.evaluate(d,'openrouter','text',0)[1],'truncated_inconclusive')
 def test_cloudflare_embeddings_array(self):
  d={'result':{'data':[[1.,0.],[1.,0.],[0.,1.]]}};ok,_,ev=probe.evaluate(d,'cloudflare','embeddings',0);self.assertTrue(ok);self.assertEqual(ev['dimensions'],2)
 def test_embeddings_invalid_dimensions(self):
  d={'data':[{'embedding':[1.]},{'embedding':[1.,0.]},{'embedding':[0.,1.]}]};self.assertFalse(probe.evaluate(d,'openrouter','embeddings',0)[0])
 def test_tools_without_execution(self):
  d={'choices':[{'message':{'tool_calls':[{'function':{'name':'registrar','arguments':json.dumps({'cidade':'Lima','quantidade':7})}}]}}]};self.assertTrue(probe.evaluate(d,'openrouter','tools',0)[0])
 def test_semantic_json_not_only_valid_json(self):
  d={'choices':[{'message':{'content':'{}'}}]};self.assertFalse(probe.evaluate(d,'openrouter','json',0)[0])
 def test_error_sanitization(self):
  class Response:status_code=401;headers={}
  cfg=SimpleNamespace(api_key='secret-synthetic-key',account_id='synthetic-account');d={'error':'secret-synthetic-key synthetic-account'};out=probe.safe_response(Response(),d,cfg);self.assertNotIn(cfg.api_key,json.dumps(out));self.assertNotIn(cfg.account_id,json.dumps(out))
 def test_atomic_complete_json(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'result.json';probe.atomic(path,{'a':1});probe.atomic(path,{'a':2});self.assertEqual(json.loads(path.read_text()),{'a':2});self.assertEqual(len(list(Path(tmp).iterdir())),1)
 def test_price_does_not_remove_route(self):
  e={'provider':'openrouter','model':'expensive','metadata':{'architecture':{'output_modalities':['text']},'pricing':{'completion':'100'}}};self.assertIn('text',probe.operations(e))
 def test_gemini_tool_schema(self):
  row={'provider':'gemini','requested_model':'x','operation':'tools','endpoint':'https://example.invalid'}
  _,body,_=probe.request_body(row,0,SimpleNamespace(account_id=''),Path('.'));self.assertNotIn('additionalProperties',body['tools'][0]['functionDeclarations'][0]['parameters'])
 def test_nvidia_ocr_native_image_endpoint(self):
  with tempfile.TemporaryDirectory() as tmp:
   asset=Path(tmp);(asset/'vision.png').write_bytes(b'synthetic-image')
   row={'provider':'nvidia','requested_model':'nvidia/nemotron-parse-2.0','operation':'ocr','endpoint':probe.endpoint('nvidia','nvidia/nemotron-parse-2.0','ocr')}
   url,body,_=probe.request_body(row,0,SimpleNamespace(account_id=''),asset)
   self.assertTrue(url.endswith('/chat/completions'));self.assertEqual(body['messages'][0]['content'][1]['type'],'image_url');self.assertNotIn('document',body)
 def test_visual_embeddings_use_pixels_and_duplicate_control(self):
  with tempfile.TemporaryDirectory() as tmp:
   asset=Path(tmp);(asset/'vision.png').write_bytes(b'image-one');(asset/'mask.png').write_bytes(b'image-two')
   row={'provider':'nvidia','requested_model':'nvidia/llama-nemotron-embed-vl-1b-v2','operation':'image_embeddings','endpoint':probe.endpoint('nvidia','x','image_embeddings')}
   url,body,_=probe.request_body(row,0,SimpleNamespace(account_id=''),asset)
   self.assertTrue(url.endswith('/embeddings'));self.assertEqual(len(body['input']),3);self.assertEqual(body['input'][0],body['input'][1]);self.assertNotEqual(body['input'][0],body['input'][2]);self.assertTrue(body['input'][0].startswith('data:image/'));self.assertEqual(body['input_type'],'passage')
 def test_batch_resume_never_resubmits(self):
  with tempfile.TemporaryDirectory() as tmp:
   run=Path(tmp);key='openrouter:x:batch::batch';name='batch-'+probe.hashlib.sha256(key.encode()).hexdigest()[:20]+'.json'
   probe.atomic(run/'remote'/name,{'remote_id':'synthetic-existing-job'})
   class Response:
    status_code=200;headers={}
    def json(self):return {'status':'failed'}
   class Client:
    def post(self,*args,**kwargs):raise AssertionError('Existing job must never be posted again')
    def get(self,*args,**kwargs):return Response()
   row={'provider':'openrouter','requested_model':'x:batch','key':key,'endpoint':'https://example.invalid/batches'}
   result=probe.batch_probe(Client(),row,0,SimpleNamespace(api_key='synthetic',account_id=''),run,run)
   self.assertFalse(result['real_call']);self.assertTrue(result['polling_only']);self.assertEqual(result['result'],'batch_failed')
 def test_nvidia_rerank_is_native_query_passages(self):
  row={'provider':'nvidia','requested_model':'nvidia/llama-3.2-nv-rerankqa-1b-v2','operation':'rerank','endpoint':probe.endpoint('nvidia','nvidia/llama-3.2-nv-rerankqa-1b-v2','rerank')}
  url,body,_=probe.request_body(row,0,SimpleNamespace(account_id=''),Path('.'))
  self.assertIn('llama-3_2-nv-rerankqa-1b-v2/reranking',url);self.assertIsInstance(body['query'],dict);self.assertEqual(len(body['passages']),2);self.assertNotIn('documents',body)
 def test_batch_schema_ignores_description_and_tool_parameters(self):
  from auren_cloudflare_batch_probe import properties
  self.assertNotIn('requests',properties({'properties':{'description':{'description':'requests run here'},'tools':{'items':{'properties':{'requests':{}}}}}}))
  self.assertIn('requests',properties({'oneOf':[{'oneOf':[{'properties':{'requests':{'type':'array'}}}]}]}))
if __name__=='__main__':unittest.main()
