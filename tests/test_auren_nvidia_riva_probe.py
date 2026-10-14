"""Native Riva adapter evidence checks; no credentials or network."""
import json,subprocess,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import auren_nvidia_riva_probe as riva
class RivaTests(unittest.TestCase):
 def row(self):return {'operation':'transcribe','native_function_id':'synthetic-function','native_language':'en-US'}
 def test_transcript_checked_against_gold_and_secret_never_returned(self):
  response=SimpleNamespace(stdout=json.dumps({'real_call':True,'success':False,'transcript':'Auren is ready. Good morning.'}))
  with patch.object(subprocess,'run',return_value=response):result=riva.probe(self.row(),0,SimpleNamespace(api_key='synthetic-private-key'),Path('.'))
  self.assertTrue(result['success']);self.assertNotIn('synthetic-private-key',json.dumps(result));self.assertNotIn('transcript',result)
 def test_empty_transcript_not_valid(self):
  with patch.object(subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps({'real_call':True,'transcript':''}))):result=riva.probe(self.row(),0,SimpleNamespace(api_key='synthetic'),Path('.'))
  self.assertFalse(result['success'])
 def test_deadline_preserves_unknown_execution(self):
  with patch.object(subprocess,'run',side_effect=subprocess.TimeoutExpired('synthetic',30)):result=riva.probe(self.row(),0,SimpleNamespace(api_key='synthetic'),Path('.'))
  self.assertTrue(result['real_call']);self.assertFalse(result['success']);self.assertEqual(result['cost_class'],'unknown')
 def test_chinese_segmentation_does_not_require_word_spaces(self):
  row=self.row();row.update(native_expected_text='你好 早上好')
  with patch.object(subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps({'real_call':True,'transcript':'你好，早上好。'}))):result=riva.probe(row,0,SimpleNamespace(api_key='synthetic'),Path('.'))
  self.assertTrue(result['success']);self.assertEqual(result['metric'],'normalized_character_similarity')
if __name__=='__main__':unittest.main()
