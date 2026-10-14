"""Native modal regressions with synthetic responses; no network/vault access."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import auren_exhaustive_probe as audit
import auren_native_media_probe as media
CFG=SimpleNamespace(api_key='synthetic-secret',account_id='')
class Response:
 def __init__(self,data,status=200):self.data=data;self.status_code=status;self.headers={}
 def json(self):return self.data
class MediaTests(unittest.TestCase):
 def test_image_price_counts_only_requested_resolution_and_no_absent_reference(self):
  with tempfile.TemporaryDirectory() as tmp:
   run=Path(tmp);model='synthetic/image'
   audit.atomic(run/'snapshot.json',{'models':{'openrouter:'+model:{'metadata':{'supported_parameters':{'resolution':{'values':['768','1K','4K']}}}}}})
   audit.atomic(run/'image-endpoints.json',[{'model':model,'metadata':{'endpoints':[{'provider_slug':'synthetic','pricing':[{'billable':'output_image','unit':'image','variant':'768','cost_usd':.041},{'billable':'output_image','unit':'image','variant':'1k','cost_usd':.048},{'billable':'output_image','unit':'image','variant':'4k','cost_usd':.607},{'billable':'input_image','unit':'token','cost_usd':.001}]}]}}])
   cost,parameters,blocker=audit.image_budget({'provider':'openrouter','requested_model':model,'operation':'image'},run)
  self.assertAlmostEqual(cost,.048);self.assertEqual(parameters['resolution'],'1K');self.assertIsNone(blocker)
 def test_cloudflare_completed_results_are_parsed_without_resubmission(self):
  from auren_cloudflare_batch_probe import batch_probe
  class Client:
   def post(self,url,**kwargs):
    self.assertion=kwargs['json'];assert set(self.assertion)=={'request_id'}
    return Response({'success':True,'result':{'results':[{'index':0,'success':True,'result':{'choices':[{'message':{'content':'AZUL|VERDE'},'finish_reason':'stop'}]}}]}})
  row={'provider':'cloudflare','requested_model':'@cf/qwen/synthetic','operation':'batch','key':'cloudflare:synthetic::batch'}
  with tempfile.TemporaryDirectory() as tmp:
   run=Path(tmp);audit.atomic(run/'cloudflare-all-schemas.json',{row['requested_model']:{'schema':{'input':{'properties':{'requests':{}}}}}});audit.atomic(run/'remote'/('cf-batch-'+audit.hashlib.sha256(row['key'].encode()).hexdigest()[:20]+'.json'),{'remote_id':'synthetic-existing'})
   result=batch_probe(Client(),row,0,CFG,run,run)
  self.assertTrue(result['success']);self.assertFalse(result['real_call']);self.assertTrue(result['polling_only'])
 def test_independent_asr_normalizes_both_expected_and_observed_text(self):
  settings=SimpleNamespace(providers={'mistral':CFG})
  with patch.object(audit,'connection_settings',return_value=settings),patch.object(audit.httpx,'post',return_value=Response({'text':'Auren is ready. Good morning.'})):
   result=audit.verify_speech(b'synthetic-audio','en','Auren is ready. Good morning.')
  self.assertTrue(result['success']);self.assertEqual(result['token_coverage'],1)
 def test_documented_seedance_tokens_are_bounded_using_requested_dimensions(self):
  from auren_openrouter_video_probe import price_bound
  meta={'id':'bytedance/seedance-2.0','supported_durations':[4,15],'supported_resolutions':['480p','720p'],'supported_sizes':['480x480','854x480'],'pricing_skus':{'video_tokens_without_audio':'0.000007'}}
  cost,parameters,blocker=price_bound(meta,'video_first_frame')
  self.assertAlmostEqual(cost,.1512);self.assertEqual(parameters['aspect_ratio'],'1:1');self.assertFalse(parameters['generate_audio']);self.assertIsNone(blocker)
  meta['id']='bytedance/seedance-2.5';meta['pricing_skus']={'video_tokens_without_audio':'0.0000107'}
  cost,parameters,blocker=price_bound(meta)
  self.assertAlmostEqual(cost,.411201);self.assertEqual(parameters['size'],'854x480');self.assertIsNone(blocker)
 def test_image_batch_uses_image_contract_and_rejects_text_only_completion(self):
  class Client:
   request=None
   def post(self,url,**kwargs):self.request=kwargs['json'];return Response({'name':'batches/synthetic'})
   def get(self,*args,**kwargs):return Response({'done':True,'response':{'inlinedResponses':{'inlinedResponses':[{'response':{'candidates':[{'content':{'parts':[{'text':'AZUL|VERDE'}]}}]}}]}}})
  client=Client();row={'provider':'gemini','requested_model':'gemini-2.5-flash-image','operation':'batch','key':'gemini:synthetic::batch','endpoint':'https://example.invalid','batch_modality':'image'}
  with tempfile.TemporaryDirectory() as tmp:result=audit.batch_probe(client,row,0,CFG,Path(tmp),Path(tmp))
  request=client.request['batch']['input_config']['requests']['requests'][0]['request']
  self.assertEqual(request['generationConfig']['responseModalities'],['IMAGE']);self.assertFalse(result['success']);self.assertEqual(result['result'],'batch_image_missing_output')
 def test_speech_batch_requires_audio_then_independent_semantic_check(self):
  class Client:
   def post(self,*args,**kwargs):return Response({'name':'batches/synthetic'})
   def get(self,*args,**kwargs):return Response({'done':True,'response':{'inlinedResponses':{'inlinedResponses':[{'response':{'candidates':[{'content':{'parts':[{'inlineData':{'mimeType':'audio/pcm;rate=24000','data':audit.base64.b64encode(b'\x00\x00'*24000).decode()}}]}}]}}]}}})
  row={'provider':'gemini','requested_model':'synthetic-tts','operation':'batch','key':'gemini:synthetic::batch','endpoint':'https://example.invalid','batch_modality':'speech'}
  with tempfile.TemporaryDirectory() as tmp,patch.object(audit,'verify_speech',return_value={'real_call':True,'success':False,'result':'semantic_asr_failed'}):result=audit.batch_probe(Client(),row,0,CFG,Path(tmp),Path(tmp))
  self.assertFalse(result['success']);self.assertEqual(result['auxiliary_call_count'],1);self.assertEqual(result['native_modality'],'speech')
 def test_music_200_without_audio_never_valid(self):
  class Client:
   def post(self,*args,**kwargs):return Response({'candidates':[{'content':{'parts':[{'text':'Music ready'}]}}]})
  row={'provider':'gemini','requested_model':'lyria-3.5','operation':'music','endpoint':'https://example.invalid'}
  with tempfile.TemporaryDirectory() as tmp:result=media.media_probe(Client(),row,0,CFG,Path(tmp),Path(tmp))
  self.assertFalse(result['success']);self.assertEqual(result['result'],'missing_music_audio')
 def test_cache_hit_and_grounding_then_delete(self):
  class Client:
   deleted=False
   def post(self,url,**kwargs):
    if url.endswith(':countTokens'):return Response({'totalTokens':6000})
    if url.endswith('/cachedContents'):return Response({'name':'cachedContents/synthetic','expireTime':'synthetic'})
    return Response({'usageMetadata':{'cachedContentTokenCount':6000},'candidates':[{'content':{'parts':[{'text':'Lima|7|NL'}]},'finishReason':'STOP'}]})
   def delete(self,*args,**kwargs):self.deleted=True;return Response({},204)
  client=Client();row={'provider':'gemini','requested_model':'synthetic','operation':'cache','key':'gemini:synthetic::cache'}
  with tempfile.TemporaryDirectory() as tmp:result=media.media_probe(client,row,0,CFG,Path(tmp),Path(tmp))
  self.assertTrue(result['success']);self.assertTrue(client.deleted);self.assertEqual(result['delete_http_status'],204)
 def test_video_existing_job_never_resubmitted(self):
  class Client:
   def post(self,*args,**kwargs):raise AssertionError('Never resubmit existing video job')
   def get(self,*args,**kwargs):return Response({'done':False})
  row={'provider':'gemini','requested_model':'veo-3.1-lite-generate-preview','operation':'video','key':'gemini:synthetic::video','endpoint':'https://example.invalid','estimated_media_upper_usd':.2}
  with tempfile.TemporaryDirectory() as tmp,patch.object(media.time,'sleep'):
   run=Path(tmp);audit.atomic(run/'remote'/('video-'+audit.hashlib.sha256(row['key'].encode()).hexdigest()[:20]+'.json'),{'remote_id':'operations/synthetic'})
   result=media.media_probe(Client(),row,0,CFG,run,run)
  self.assertFalse(result['real_call']);self.assertTrue(result['polling_only']);self.assertEqual(result['result'],'accepted_pending_completion')
 def test_invalid_media_bytes_never_pass_container(self):
  with self.assertRaises(ValueError):media.inspect_media(b'<html>HTTP 200 is not audio</html>','.mp3')
if __name__=='__main__':unittest.main()
