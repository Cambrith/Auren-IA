"""Native specialized controls: HTTP200 and null/NaN output never validate."""
import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import auren_exhaustive_probe as audit
import auren_nvidia_specialized_probe as specialized
class Response:
 status_code=200;headers={};content=b'synthetic'
 def __init__(self,data):self.data=data
 def json(self):return self.data
class Tests(unittest.TestCase):
 def test_budget_reservation_releases_denial_but_keeps_timeout_and_accepted_job(self):
  denied={'real_call':True,'http_status':402,'cost_class':'unknown','estimated_request_upper_usd':1.5}
  self.assertEqual(audit.reserved_request_upper(denied),0);self.assertEqual(denied['cost_class'],'unknown')
  self.assertEqual(audit.reserved_request_upper({**denied,'http_status':None}),1.5)
  self.assertEqual(audit.reserved_request_upper({**denied,'accepted':True,'remote_id':'synthetic'}),1.5)
  self.assertEqual(audit.reserved_request_upper({**denied,'reported_cost_usd':.03}),1.5)
 def test_calibration_extracts_known_values_even_with_markdown_and_rejects_wrong_minima(self):
  def response(value):return {'choices':[{'message':{'content':'```json\n'+json.dumps(value)+'\n```'},'finish_reason':'stop'}]}
  self.assertTrue(audit.evaluate(response({'marker':'CAL-482','dip_frequencies_ghz':[4,2]}),'nvidia','calibration',0)[0])
  self.assertFalse(audit.evaluate(response({'marker':'CAL-482','dip_frequencies_ghz':[3,4]}),'nvidia','calibration',0)[0])
 def call(self,operation,prediction):
  class Client:
   def post(self,*args,**kwargs):return Response({'data':[prediction]})
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp);(path/'vision.png').write_bytes(b'synthetic-input');return specialized.probe(Client(),{'requested_model':'synthetic','endpoint':'https://example.invalid','operation':operation},0,SimpleNamespace(api_key='synthetic',account_id=''),path,path)
 def test_null_face_list_does_not_equal_verified_no_faces(self):
  self.assertFalse(self.call('deepfake_detection',{'index':0,'status':'SUCCESS','bounding_boxes':None})['success'])
  self.assertTrue(self.call('deepfake_detection',{'index':0,'status':'SUCCESS','bounding_boxes':[]})['success'])
 def test_probability_nan_or_out_of_range_never_valid(self):
  for probability in [float('nan'),1.2,True]:
   self.assertFalse(self.call('image_authenticity',{'index':0,'status':'SUCCESS','is_ai_generated':probability,'possible_sources':{}})['success'])
 def test_content_filtered_is_not_success(self):
  self.assertFalse(self.call('deepfake_detection',{'index':0,'status':'CONTENT_FILTERED','bounding_boxes':[]})['success'])
if __name__=='__main__':unittest.main()

class ScientificTests(unittest.TestCase):
 def test_acyclic_molecule_graph_rejects_valence_and_branch_errors(self):
  from auren_scientific_probe import acyclic_smiles_valid
  for smiles in ['CCO','CCOC(O)OCCOC','CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCOCC']:
   self.assertTrue(acyclic_smiles_valid(smiles))
  for smiles in ['CC-','C()','CO#C','C(C)(C)(C)(C)C','C(OC']:
   self.assertFalse(acyclic_smiles_valid(smiles))
  self.assertIsNone(acyclic_smiles_valid('c1ccccc1'))
