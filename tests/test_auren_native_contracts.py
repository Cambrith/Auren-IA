"""Independent regressions for native decoding, public outputs and async control."""
import io,struct,unittest,zipfile
from auren_interactions_probe import public_outputs
from auren_nvidia_bounded_probe import inspect_solver,inspect_stl,inspect_archive
from auren_protein_probe import SEQUENCE,contract,inspect_alignment
from auren_exhaustive_probe import declared_zero_price,semantic_pending,submitted_batch_model

class NativeContractTests(unittest.TestCase):
 def test_private_reasoning_is_excluded(self):
  data={'outputs':[{'type':'thought','text':'private'},{'type':'text','text':'AZUL|'}],'steps':[{'type':'thought','content':[{'type':'text','text':'private'}]},{'type':'model_output','content':[{'type':'thought','text':'private'},{'type':'text','text':'VERDE'}]}]}
  self.assertEqual(public_outputs(data),('AZUL|VERDE',[]))
 def test_summary_not_duplicated_and_tool_args_preserved(self):
  data={'output_text':'answer','outputs':[{'type':'text','text':'answer'},{'type':'function_call','name':'registrar','arguments':{'cidade':'Lima','quantidade':7}}]}
  text,calls=public_outputs(data);self.assertEqual(text,'answer');self.assertEqual(calls[0]['arguments']['quantidade'],7)
 def test_mesh_requires_finite_coordinates_and_exact_size(self):
  raw=b'\0'*80+struct.pack('<I',1)+struct.pack('<12f',*([0.]*12))+b'\0\0'
  self.assertTrue(inspect_stl(raw));self.assertFalse(inspect_stl(raw+b'extra'))
  bad=bytearray(raw);bad[84:88]=struct.pack('<f',float('nan'));self.assertFalse(inspect_stl(bytes(bad)))
 def test_solver_cannot_pass_by_status_alone(self):
  result={'response':{'solver_response':{'status':0,'num_vehicles':1,'solution_cost':2,'vehicle_data':{'auren-synthetic-vehicle':{'route':[0,1,0]}}}}}
  self.assertTrue(inspect_solver(result)[0]);result['response']['solver_response']['vehicle_data']['auren-synthetic-vehicle']['route']=[0,0];self.assertFalse(inspect_solver(result)[0])
 def test_msa_requires_original_query_not_nonempty_output(self):
  result={'alignments':{'synthetic':{'a3m':{'alignment':'>query\n'+SEQUENCE+'\n','format':'a3m'}}}}
  self.assertTrue(inspect_alignment(result)[0]);result['alignments']['synthetic']['a3m']['alignment']='>query\nAAAAAAAA\n';self.assertFalse(inspect_alignment(result)[0])
 def test_native_protein_requests_control_repetition(self):
  _,body=contract('mit/boltz2');self.assertEqual(body['diffusion_samples'],1);self.assertEqual(body['sampling_steps'],10);self.assertNotIn('ligands',body)
  _,body=contract('deepmind/alphafold2');self.assertEqual(body['selected_models'],[1]);self.assertFalse(body['relax_prediction'])
 def test_archive_nesting_does_not_expand_arbitrarily(self):
  def packed(value):
   out=io.BytesIO()
   with zipfile.ZipFile(out,'w') as z:z.writestr('output.response',value)
   return out.getvalue()
  with self.assertRaises(ValueError):inspect_archive(packed(packed(packed(b''))))
 def test_batch_variant_preserves_openrouter_routing_suffix(self):
  self.assertEqual(submitted_batch_model('vendor/model:batch:nitro'),'vendor/model:nitro')
  self.assertEqual(submitted_batch_model('vendor/model:nitro:batch'),'vendor/model:nitro')
 def test_unknown_or_missing_modality_price_is_not_zero(self):
  self.assertTrue(declared_zero_price({'input':0,'output':0}))
  self.assertFalse(declared_zero_price({'input':0,'image':None}))
  self.assertFalse(declared_zero_price({'input':0,'output':'unknown'}))
 def test_semantic_review_handles_native_list_evidence(self):
  self.assertTrue(semantic_pending({'evidence':[{'sha256':'x'}],'semantic_pending':True}))
  self.assertFalse(semantic_pending({'evidence':[{'sha256':'x'}]}))
  self.assertTrue(semantic_pending({'evidence':{'semantic_review_pending':True}}))

if __name__=='__main__':unittest.main()
