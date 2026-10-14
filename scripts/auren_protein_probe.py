"""Small synthetic native protein/MSA protocol checks; no biological quality claim."""
import hashlib,json,math,re,subprocess,time
SEQUENCE='ACDEFGHIKLMNPQRSTVWY'

def synthetic_ca_pdb():
    """Twenty alanine alpha carbons; synthetic geometry, no biological target."""
    atoms=[]
    for index in range(20):
        angle=math.radians(index*100);x=2.3*math.cos(angle);y=2.3*math.sin(angle);z=index*1.5
        atoms.append(f'ATOM  {index+1:5d}  CA  ALA A{index+1:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C  ')
    return '\n'.join(atoms)+'\nTER\nEND\n'

def contract(model):
    msa={'synthetic':{'a3m':{'alignment':'>synthetic\n'+SEQUENCE+'\n','format':'a3m'}}}
    contracts={
      'colabfold/msa-search':('/biology/colabfold/msa-search/predict',{'sequence':SEQUENCE,'databases':['Uniref30_2302'],'iterations':1,'max_msa_sequences':1,'output_alignment_formats':['a3m']}),
      'deepmind/alphafold2':('/protein-structure/alphafold2/predict-structure-from-sequence',{'sequence':SEQUENCE,'algorithm':'jackhmmer','databases':['uniref90'],'iterations':1,'relax_prediction':False,'structure_models_to_relax':'none','selected_models':[1],'num_predictions_per_model':1,'max_msa_sequences':1,'skip_template_search':True}),
      'deepmind/alphafold2-multimer':('/protein-structure/alphafold2/multimer/predict-structure-from-sequences',{'sequences':[SEQUENCE,SEQUENCE],'algorithm':'jackhmmer','databases':['uniref90'],'iterations':1,'relax_prediction':False,'structure_models_to_relax':'none','num_predictions_per_model':1,'max_msa_sequences':1}),
      'openfold/openfold2':('/biology/openfold/openfold2/predict-structure-from-msa-and-template',{'sequence':SEQUENCE,'input_id':'auren-synthetic','alignments':msa,'selected_models':[1],'relax_prediction':False,'use_templates':False}),
      'openfold/openfold3':('/biology/openfold/openfold3/predict',{'request_id':'auren-synthetic','inputs':[{'input_id':'auren-synthetic','molecules':[{'type':'protein','id':'A','sequence':SEQUENCE,'msa':{'synthetic':{'csv':{'alignment':'key,sequence\n-1,'+SEQUENCE+'\n','format':'csv'}}}}],'diffusion_samples':1,'output_format':'pdb'}]}),
      'mit/boltz2':('/biology/mit/boltz2/predict',{'polymers':[{'id':'A','molecule_type':'protein','sequence':SEQUENCE,'cyclic':False,'msa':msa}],'recycling_steps':1,'sampling_steps':10,'diffusion_samples':1}),
      'ipd/rfdiffusion':('/biology/ipd/rfdiffusion/generate',{'input_pdb':synthetic_ca_pdb(),'contigs':'20','diffusion_steps':1,'random_seed':7}),
      'ipd/proteinmpnn':('/biology/ipd/proteinmpnn/predict',{'input_pdb':synthetic_ca_pdb(),'ca_only':True,'input_pdb_chains':['A'],'random_seed':7,'num_seq_per_target':1,'sampling_temp':[.1],'fixed_positions_jsonl':json.dumps({'input':{'A':list(range(1,21))}})}),
    }
    return contracts.get(model)

def inspect_alignment(data):
    records=[record for formats in data.get('alignments',{}).values() for record in formats.values()]
    counts=[]
    for record in records:
        lines=record.get('alignment','').splitlines();sequences=[];current=''
        for line in lines:
            if line.startswith('>'):
                if current:sequences.append(current);current=''
            elif not line.startswith('#'):current+=line.strip()
        if current:sequences.append(current)
        if not sequences or sequences[0].replace('-','')!=SEQUENCE or not all(re.fullmatch('[A-Za-z-]+',seq) for seq in sequences):return False,{}
        counts.append(len(sequences))
    return bool(counts),{'alignment_records':len(counts),'sequence_counts':counts,'query_roundtrip_verified':bool(counts)}

def inspect_structure(text,fmt):
    import auren_exhaustive_probe as audit
    script='''import sys,json,math,gemmi
a=json.load(sys.stdin)
s=gemmi.make_structure_from_block(gemmi.cif.read_string(a['text']).sole_block()) if a['format'] in ['mmcif','cif'] else gemmi.read_pdb_string(a['text'])
atoms=[at for model in s for chain in model for res in chain for at in res]
seqs=[''.join(gemmi.find_tabulated_residue(res.name).one_letter_code for res in chain if any(at.name=='CA' for at in res)) for chain in s[0]] if len(s) else []
print(json.dumps({'atoms':len(atoms),'finite':all(math.isfinite(v) for at in atoms for v in [at.pos.x,at.pos.y,at.pos.z]),'chain_sequences':seqs}))
'''
    p=subprocess.run([str(audit.ROOT/'.cavren/audit-riva-runtime/bin/python'),'-c',script],input=json.dumps({'text':text,'format':fmt}),capture_output=True,text=True,timeout=10,check=True)
    return json.loads(p.stdout)

def probe(client,row,sample,cfg,asset,run):
    import auren_exhaustive_probe as audit
    start=time.monotonic();out={'at':audit.now(),'sample':sample,'real_call':False,'success':False,'cost_class':'unknown','biological_quality_tested':False,'states':[]};chosen=contract(row['requested_model'])
    if not chosen:return {**out,'result':'native_protein_contract_pending','seconds':0}
    path,body=chosen;url='https://health.api.nvidia.com/v1'+path;headers={**audit.headers('nvidia',cfg),'NVCF-POLL-SECONDS':'5'};job=run/'remote'/('protein-'+hashlib.sha256(row['key'].encode()).hexdigest()[:20]+'.json');prior=audit.read(job,{});remote=prior.get('remote_id');out.update(parameters=body,request_sha256=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest())
    try:
        if remote:response=client.get('https://health.api.nvidia.com/v1/status/'+remote,headers=headers,timeout=15);out['polling_only']=True
        else:out['real_call']=True;response=client.post(url,headers=headers,json=body,timeout=30)
        for index in range(3):
            remote=response.headers.get('nvcf-reqid') or remote
            if remote:
                out['remote_id']=remote;audit.atomic(job,{'remote_id':remote,'row':row['key'],'at':audit.now(),'status_http':response.status_code})
            out['states'].append({'at':audit.now(),'http_status':response.status_code})
            if response.status_code!=202 or not remote:break
            out['accepted']=True;response=client.get('https://health.api.nvidia.com/v1/status/'+remote,headers=headers,timeout=15)
        try:data=response.json()
        except ValueError:data={}
        out.update(audit.safe_response(response,data,cfg));out.update(response_sha256=hashlib.sha256(response.content).hexdigest(),response_keys=list(data) if isinstance(data,dict) else [],response_bytes=len(response.content))
        if response.status_code>=400:out['result']={400:'contract_error',404:'route_unavailable',422:'contract_error',429:'rate_or_quota_limit',504:'native_provider_deadline'}.get(response.status_code,'provider_error');return out
        if response.status_code==202:out['result']='accepted_pending_completion';return out
        if row['requested_model']=='colabfold/msa-search':ok,evidence=inspect_alignment(data)
        elif row['requested_model']=='ipd/proteinmpnn':
            out['synthetic_response_keys']=list(data) if isinstance(data,dict) else []
            candidates=[]
            def visit(value):
                if isinstance(value,dict):
                    for child in value.values():visit(child)
                elif isinstance(value,list):
                    for child in value:visit(child)
                elif isinstance(value,str):
                    for line in value.splitlines():
                        if re.fullmatch('[ACDEFGHIKLMNPQRSTVWY]{20}',line):candidates.append(line)
            visit(data);ok=bool(candidates) and all(value=='A'*20 for value in candidates);evidence={'fixed_residue_roundtrip':ok,'sequence_outputs':len(candidates),'control':'All 20 alanines fixed; no functional sequence optimization.'}
        else:
            records=[]
            if isinstance(data,list):records=data
            elif row['requested_model']=='openfold/openfold2':records=data.get('structures_in_ranked_order',[])
            elif row['requested_model']=='openfold/openfold3':records=[v for output in data.get('outputs',[]) for v in output.get('structures_with_scores',[])]
            elif row['requested_model']=='mit/boltz2':records=data.get('structures',[])
            elif data.get('output_pdb'):records=[{'structure':data['output_pdb'],'format':'pdb'}]
            evidence=[]
            for record in records:
                text=record if isinstance(record,str) else record.get('structure',record.get('pdb',''));fmt=record.get('format','pdb') if isinstance(record,dict) else 'pdb'
                if not text or len(text)>5_000_000:continue
                checked=inspect_structure(text,fmt);seqs=checked.pop('chain_sequences');checked['chain_lengths']=[len(v) for v in seqs];checked['sequence_roundtrip']=all(v==SEQUENCE for v in seqs) if row['requested_model']!='ipd/rfdiffusion' else all(len(v)==20 for v in seqs);checked['sha256']=hashlib.sha256(text.encode()).hexdigest();evidence.append(checked)
            ok=bool(evidence) and all(v['atoms']>0 and v['finite'] and v['sequence_roundtrip'] for v in evidence)
        out.update(success=ok,result='valid_native_fixed_sequence_roundtrip' if ok and row['requested_model']=='ipd/proteinmpnn' else 'valid_native_synthetic_alignment' if ok and row['requested_model']=='colabfold/msa-search' else 'valid_native_structure_format_and_sequence' if ok else 'native_protein_output_check_pending',evidence=evidence,semantic_pending=not ok)
    except Exception as error:out['result']=type(error).__name__
    finally:out['seconds']=round(time.monotonic()-start,3)
    return out
