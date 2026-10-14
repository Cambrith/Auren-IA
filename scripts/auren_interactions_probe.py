"""Bounded managed-agent probes. Never execute tools or capture private reasoning."""
import base64, hashlib, json, time

def public_outputs(data):
    text=data.get('output_text') or ''
    has_summary=bool(text)
    calls=[]
    outputs=list(data.get('outputs',[]))
    outputs.extend(step for step in data.get('steps',[]) if isinstance(step,dict) and step.get('type')=='function_call')
    outputs.extend(part for step in data.get('steps',[]) if isinstance(step,dict) and step.get('type')=='model_output' for part in step.get('content',[]) if isinstance(part,dict))
    for output in outputs:
        if not isinstance(output,dict):continue
        if output.get('type')=='text' and not has_summary:text+=output.get('text','')
        if output.get('type')=='function_call':calls.append({'name':output.get('name'),'arguments':output.get('arguments')})
    return text,calls

def probe(client,row,sample,cfg,asset,run):
    import auren_exhaustive_probe as audit
    start=time.monotonic();op=row['agent_test_operation'];model=row.get('agent_underlying_model')
    result={'at':audit.now(),'sample':sample,'real_call':False,'success':False,'cost_class':'unknown','states':[], 'budget_control':'best_effort_total_tokens_2048_not_financial_cap','tools_executed':False,'environment_requested':False}
    prompt='Crie apenas um plano curto de duas etapas para comparar informações de fontes oficiais sobre os formatos PNG e JPEG. Aguarde minha confirmação antes de pesquisar.' if op=='planning' else audit.PROMPTS[op][sample];input_value=prompt
    if op=='vision':input_value=[{'type':'text','text':prompt},{'type':'image','mime_type':'image/png','data':base64.b64encode((asset/'vision.png').read_bytes()).decode()}]
    body={'agent':row['requested_model'],'input':input_value,'background':True,'store':True,'tools':[{'type':'function',**audit.FUNCTION}],'agent_config':{'type':'antigravity','max_total_tokens':2048}}
    if op=='planning':
        body={'agent':row['requested_model'],'input':input_value,'background':True,'store':True,'agent_config':{'type':'deep-research','collaborative_planning':True,'thinking_summaries':'none','visualization':'off'}}
        result.update(budget_control='Explicit user authorization for one planning-only call per route, unknown cost, thirty-second follow-up window. No research approval.',research_execution_called=False,phase='planning_only')
    if row.get('native_agent_environment'):
        body['environment']={'type':'remote','network':'disabled','sources':[]}
        result.update(environment_requested=True,environment_network='disabled',environment_compute_price='preview_not_billed_per_official_documentation')
    if model:body['agent_config']['model']=model;result['underlying_model_requested']=model
    result['request_sha256']=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
    path=run/'remote'/('interaction-'+hashlib.sha256(row['key'].encode()).hexdigest()[:20]+f'-{sample}.json');prior=audit.read(path,{});remote=prior.get('remote_id');url=row['endpoint'];headers=audit.headers('gemini',cfg)
    status=None;environment_id=prior.get('environment_id')
    try:
        if remote:
            response=client.get(url+'/'+remote,headers=headers,timeout=15);data=response.json();result['polling_only']=True
        else:
            result['real_call']=True;response=client.post(url,headers=headers,json=body,timeout=20);data=response.json()
        result.update(audit.safe_response(response,data,cfg))
        if response.status_code>=400:
            result['result']={400:'contract_error',401:'authentication_denied',403:'permission_denied',404:'route_unavailable',429:'rate_or_quota_limit'}.get(response.status_code,'provider_error');return result
        remote=data.get('id') or remote;result['remote_id']=remote
        environment_id=data.get('environment_id') or environment_id
        if remote:audit.atomic(path,{'remote_id':remote,'environment_id':environment_id,'row':row['key'],'at':audit.now(),'status':data.get('status')})
        while True:
            status=data.get('status');result['states'].append({'at':audit.now(),'status':status})
            if status not in ['in_progress','queued'] or time.monotonic()-start>=30:break
            if not remote:break
            time.sleep(1);response=client.get(url+'/'+remote,headers=headers,timeout=10);data=response.json();result.update(audit.safe_response(response,data,cfg))
            if response.status_code>=400:result['result']='remote_poll_denied';return result
        text,calls=public_outputs(data)
        equivalent={'choices':[{'message':{'content':text,'tool_calls':calls},'finish_reason':None}]}
        if op=='planning':
            tool_steps=[step.get('type') for step in data.get('steps',[]) if isinstance(step,dict) and str(step.get('type','')).endswith('_call')]
            ok=20<=len(text)<=6000 and 'png' in text.casefold() and 'jpeg' in text.casefold() and not tool_steps and not calls
            code='native_planning_check_failed';evidence={'response_sha256':hashlib.sha256(text.encode()).hexdigest(),'text_characters':len(text),'research_tool_steps':tool_steps,'topic_terms_present':'png' in text.casefold() and 'jpeg' in text.casefold(),'research_approval_sent':False}
        else:ok,code,evidence=audit.evaluate(equivalent,'openrouter',op,sample)
        result.update(success=ok,result='valid_native_agent_'+op if ok else 'native_agent_budget_incomplete' if status=='incomplete' else 'accepted_pending_completion' if status in ['in_progress','queued'] else code,evidence=evidence,interaction_status=status,semantic_pending=ok and status=='incomplete',agent_completion_verified=status=='completed',output_types=[v.get('type') for v in data.get('outputs',[]) if isinstance(v,dict)],step_types=[v.get('type') for v in data.get('steps',[]) if isinstance(v,dict)])
    except Exception as error:result['result']=type(error).__name__
    finally:
        if remote and status in ['in_progress','queued','requires_action']:
            try:
                cancel=client.post(url+'/'+remote+'/cancel',headers=headers,json={},timeout=10);result['cancel_http_status']=cancel.status_code
                if cancel.status_code<400:result['cancel_status']=cancel.json().get('status')
            except Exception as error:result['cancel_error']=type(error).__name__
        result['seconds']=round(time.monotonic()-start,3)
        if environment_id:
            try:result['environment_delete_http_status']=client.delete(url.rsplit('/',1)[0]+'/environments/'+environment_id,headers=headers,timeout=10).status_code
            except Exception as error:result['environment_delete_error']=type(error).__name__
        if remote:audit.atomic(path,{'remote_id':remote,'environment_id':environment_id,'row':row['key'],'at':audit.now(),'status':result.get('cancel_status') or status,'result':result.get('result'),'environment_delete_http_status':result.get('environment_delete_http_status')})
    return result
