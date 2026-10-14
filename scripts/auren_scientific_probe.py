"""Tiny documented scientific native calls; no chat substitution or biology claims."""
import hashlib,json,math,re,time

def acyclic_smiles_valid(smiles):
 """Check the neutral acyclic subset; unsupported rings/charges stay unverified."""
 if not isinstance(smiles,str) or not smiles:return False
 tokens=re.findall(r'Cl|Br|[CNOBFPSI]|[()=#-]',smiles)
 if ''.join(tokens)!=smiles:return None
 limits={'C':4,'N':3,'O':2,'B':3,'F':1,'P':5,'S':6,'I':1,'Cl':1,'Br':1};atoms=[];bonds=[];stack=[];current=None;order=1;previous=None
 for token in tokens:
  if token in limits:
   index=len(atoms);atoms.append(token);bonds.append(0)
   if current is not None:bonds[current]+=order;bonds[index]+=order
   current=index;order=1
  elif token=='(':
   if current is None or previous in ['(','=','#','-']:return False
   stack.append(current)
  elif token==')':
   if not stack or previous in ['(','=','#','-']:return False
   current=stack.pop()
  else:
   if current is None or previous in ['(','=','#','-']:return False
   order={'=':2,'#':3,'-':1}[token]
  previous=token
 return bool(atoms) and not stack and previous not in ['(','=','#','-'] and all(b<=limits[a] for a,b in zip(atoms,bonds))

def probe(client,row,sample,cfg,asset,run):
 if row['requested_model'] in ['colabfold/msa-search','deepmind/alphafold2','deepmind/alphafold2-multimer','openfold/openfold2','openfold/openfold3','mit/boltz2','ipd/rfdiffusion','ipd/proteinmpnn']:
  from auren_protein_probe import probe as protein_probe
  return protein_probe(client,row,sample,cfg,asset,run)
 if row['requested_model'] in ['nvidia/cuOpt','nvidia/corrdiff','nvidia/fourcastnet']:
  from auren_nvidia_bounded_probe import probe as bounded_probe
  return bounded_probe(client,row,sample,cfg,asset,run)
 import auren_exhaustive_probe as audit
 start=time.monotonic();out={'at':audit.now(),'sample':sample,'real_call':False,'success':False,'cost_class':'unknown'}
 model=row['requested_model']
 contracts={
  'arc/evo2-40b':('https://health.api.nvidia.com/v1/biology/arc/evo2-40b/generate',{'sequence':'ACGTACGTACGTACGT','num_tokens':16,'temperature':.1,'top_k':1,'top_p':1,'random_seed':7,'enable_logits':False,'enable_sampled_probs':False}),
  'nvidia/molmim':('https://health.api.nvidia.com/v1/biology/nvidia/molmim/generate',{'algorithm':'none','smi':'CCO','num_molecules':1,'iterations':1,'particles':2,'min_similarity':.7,'scaled_radius':0}),
  'nvidia/genmol':('https://health.api.nvidia.com/v1/biology/nvidia/genmol/generate',{'smiles':'CCO','num_molecules':1,'temperature':.1,'noise':0,'step_size':1,'scoring':'QED','unique':True}),
  'arc/evo2-7b-forward':('https://health.api.nvidia.com/v1/biology/arc/evo2-7b/forward',{'sequence':'ACGT','output_layers':['embedding_layer']})}
 if model not in contracts:return {**out,'result':'native_scientific_contract_pending','seconds':0}
 url,body=contracts[model];out.update(real_call=True,parameters=body,request_sha256=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest())
 try:
  response=client.post(url,headers=audit.headers('nvidia',cfg),json=body,timeout=30)
  try:data=response.json()
  except ValueError:data={}
  out.update(audit.safe_response(response,data,cfg))
  if response.status_code>=400:out['result']={400:'contract_error',401:'authentication',402:'credit_or_payment_required',403:'permission_or_plan',404:'route_unavailable',410:'native_endpoint_retired',422:'contract_error',429:'rate_or_quota_limit'}.get(response.status_code,'provider_error')
  else:
   out['response_sha256']=hashlib.sha256(response.content).hexdigest();out['response_keys']=list(data) if isinstance(data,dict) else []
   if model=='arc/evo2-40b':
    sequence=next((data.get(k) for k in ['sequence','generated_sequence','generated_seq'] if isinstance(data.get(k),str)),None)
    ok=bool(sequence and re.fullmatch('[ACGT]+',sequence) and len(sequence) in [16,32]);out.update(success=ok,result='valid_native_dna_syntax' if ok else 'scientific_output_schema_review_pending',generated_characters=len(sequence) if sequence else None,semantic_pending=not ok)
   elif model=='arc/evo2-7b-forward':
    import base64,subprocess,tempfile,zipfile,io
    encoded=data.get('data','');out['tensor_encoding']={'type':type(encoded).__name__,'characters':len(encoded) if isinstance(encoded,str) else None,'whitespace_count':sum(c.isspace() for c in encoded) if isinstance(encoded,str) else None,'bytes_repr':isinstance(encoded,str) and encoded.startswith("b'") and encoded.endswith("'")}
    if out['tensor_encoding']['bytes_repr']:encoded=encoded[2:-1]
    raw=base64.b64decode(''.join(encoded.split()),validate=True)
    if not raw or len(raw)>5_000_000:out['result']='native_tensor_missing_or_output_budget';return out
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
     if sum(item.file_size for item in archive.infolist())>20_000_000:out['result']='native_tensor_uncompressed_budget';return out
    with tempfile.NamedTemporaryFile(dir=audit.STATE,suffix='.npz') as tensor:
     tensor.write(raw);tensor.flush();code='import sys,json,numpy as np; z=np.load(sys.argv[1],allow_pickle=False); result=[{"key":k,"shape":list(z[k].shape),"finite":bool(np.isfinite(z[k]).all()),"nonzero":bool(np.any(z[k]))} for k in z.files];print(json.dumps(result))';process=subprocess.run([str(audit.ROOT/'.cavren/venv/bin/python'),'-c',code,tensor.name],text=True,capture_output=True,timeout=10,check=True);arrays=json.loads(process.stdout)
    ok=bool(arrays) and all(item['finite'] and item['nonzero'] and 4 in item['shape'] for item in arrays);out.update(success=ok,result='valid_native_forward_numpy_tensor' if ok else 'native_forward_tensor_check_failed',tensor_sha256=hashlib.sha256(raw).hexdigest(),arrays=arrays,semantic_pending=False)
   else:
    molecules=data.get('molecules');out['molecule_output_structure']=type(molecules).__name__;out['synthetic_output_excerpt']=json.dumps(molecules,ensure_ascii=False)[:500]
    if isinstance(molecules,str):molecules=json.loads(molecules)
    entry=molecules[0] if isinstance(molecules,list) and len(molecules)==1 else {};smiles=entry.get('sample',entry.get('smiles'));score=entry.get('score');graph=acyclic_smiles_valid(smiles);valid=type(score) in (int,float) and math.isfinite(score) and 0<=score<=1 and bool(smiles);ok=valid and graph is True
    out.update(success=ok or valid and graph is None,result='valid_native_acyclic_molecule_and_score' if ok else 'valid_molecule_schema_graph_semantics_pending' if valid and graph is None else 'scientific_output_schema_review_pending',semantic_pending=not ok,control='One molecule; parsed neutral acyclic atom graph, bond valences and finite score. No drug/property quality claim.')
 except Exception as error:out['result']=type(error).__name__;out['validation_error']=str(error)[:300] if model=='arc/evo2-7b-forward' else None
 finally:out['seconds']=round(time.monotonic()-start,3)
 return out
