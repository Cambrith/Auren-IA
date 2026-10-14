"""One-shot vision checks for shortlisted Auren providers; never exports credentials."""
import base64, hashlib, json, re, sys, time, unicodedata
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'reports/auren-gemini-groq-2026-10-14-r2/fixtures/vision.png'
OUT=Path(__file__).with_name('results.json')
PROMPT='Leia o identificador impresso na imagem, conte os círculos vermelhos e os quadrados azuis. Responda somente no formato identificador|quantidade_de_circulos|quantidade_de_quadrados.'
EXPECTED='PIXEL-739|2|1'
raw=FIXTURE.read_bytes(); b64=base64.b64encode(raw).decode(); uri='data:image/png;base64,'+b64

sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT.parent/'cavren-nextchat'/'src'))
from integration.lunvri_connections import connection_settings
settings=connection_settings(); records=[]

def result_text(data, provider):
    if provider=='cloudflare':
        r=data.get('result',{})
        if isinstance(r,dict): return r.get('response') or r.get('result') or r.get('text') or ''
    if provider=='cohere':
        msgs=data.get('message',{}).get('content',[])
        return ''.join(x.get('text','') for x in msgs if isinstance(x,dict))
    try: return data['choices'][0]['message'].get('content') or ''
    except (KeyError,IndexError,TypeError,AttributeError): return ''

def check_semantics(text):
    normalized=''.join(c for c in unicodedata.normalize('NFD',str(text).upper()) if unicodedata.category(c)!='Mn')
    m=re.search(r'PIXEL\s*[-–—]?\s*739',normalized)
    if not m:return False
    nums=re.findall(r'\d+',normalized[m.end():])
    return len(nums)>=2 and nums[0]=='2' and nums[1]=='1'

def usage_summary(data, provider):
    if provider=='cohere':
        u=data.get('usage',{})
        return u.get('billed_units') or u.get('tokens') or {}
    if provider=='cloudflare':
        u=data.get('result',{}).get('usage',{}) if isinstance(data.get('result'),dict) else {}
        if not u:u=data.get('usage',{})
        return u
    return data.get('usage',{}) if isinstance(data.get('usage'),dict) else {}

cases=[
    ('groq','qwen/qwen3.8-27b','groq'),
    ('cohere','command-a-vision-07-2025','cohere'),
    ('nvidia','meta/llama-3.2-11b-vision-instruct','nvidia'),
    ('cloudflare','@cf/qwen/qwen3.8-27b','cloudflare'),
    ('cloudflare','@cf/meta/llama-3.2-11b-vision-instruct','cloudflare'),
]
with httpx.Client(trust_env=False,timeout=35,follow_redirects=False) as client:
  for provider,model,case in cases:
    cfg=settings.providers.get(provider); rec={'provider':provider,'model':model,'operation':'vision/image-understanding','real_call':False,'cost_class':'unknown','fixture_sha256':hashlib.sha256(raw).hexdigest(),'fixture_bytes':len(raw),'prompt':PROMPT,'output_token_cap':48,'retries':0}
    if not cfg or not cfg.api_key:
      rec.update(result='not_tested',blocker='credential_missing');records.append(rec);continue
    if provider=='cohere':
      url='https://api.cohere.com/v2/chat'; headers={'Authorization':'Bearer '+cfg.api_key,'Content-Type':'application/json'}
      body={'model':model,'messages':[{'role':'user','content':[{'type':'text','text':PROMPT},{'type':'image_url','image_url':{'url':uri}}]}],'max_tokens':48}
    elif provider=='cloudflare':
      url=cfg.base_url.rstrip('/')+'/chat/completions';headers={'Authorization':'Bearer '+cfg.api_key,'Content-Type':'application/json'}
      body={'model':model,'messages':[{'role':'user','content':[{'type':'text','text':PROMPT},{'type':'image_url','image_url':{'url':uri}}]}],'max_tokens':48,'stream':False}
      if model=='@cf/qwen/qwen3.8-27b':body['reasoning_effort']='low'
    else:
      url=cfg.base_url.rstrip('/')+'/chat/completions';headers={'Authorization':'Bearer '+cfg.api_key,'Content-Type':'application/json'}
      body={'model':model,'messages':[{'role':'user','content':[{'type':'text','text':PROMPT},{'type':'image_url','image_url':{'url':uri}}]}],'stream':False}
      if provider=='groq':body.update(max_completion_tokens=48,reasoning_effort='none')
      else:body['max_tokens']=48
    started=time.monotonic();rec.update(real_call=True,endpoint_kind='native_cohere_v2_chat' if case=='cohere' else 'openai_compatible_chat_completions')
    try:
      response=client.post(url,headers=headers,json=body)
      rec.update(http_status=response.status_code,seconds=round(time.monotonic()-started,3))
      try:data=response.json()
      except ValueError:data={}
      usage=usage_summary(data,provider)
      safe_usage={k:v for k,v in usage.items() if k in ('prompt_tokens','completion_tokens','total_tokens','input_tokens','output_tokens','billable_input_tokens','billable_output_tokens') and isinstance(v,(int,float))}
      if safe_usage:rec['usage_tokens']=safe_usage
      if response.status_code<400:
        text=result_text(data,provider);rec.update(result='valid' if check_semantics(text) else 'semantic_check_failed',semantic_pass=check_semantics(text),response_excerpt=str(text)[:220],response_sha256=hashlib.sha256(str(text).encode()).hexdigest(),resolved_model=data.get('model') or data.get('meta',{}).get('api_version'))
        # Estimate only when provider returns usage and official per-token prices are published.
        p_in=safe_usage.get('prompt_tokens',safe_usage.get('input_tokens'));p_out=safe_usage.get('completion_tokens',safe_usage.get('output_tokens'))
        rates={'groq':(.80,4.00),'cloudflare':(.45,3.20)}
        if provider=='cloudflare' and model=='@cf/meta/llama-3.2-11b-vision-instruct':rates['cloudflare']=(.0485,.676)
        if case in rates and p_in is not None and p_out is not None:
          ri,ro=rates[case];rec['estimated_cost_usd']=(p_in*ri+p_out*ro)/1_000_000;rec['cost_class']='positive_estimate' if rec['estimated_cost_usd']>0 else 'zero_estimate'
        elif case in ('cohere','nvidia'):
          rec['cost_class']='unknown_actual_cost'
      else:
        # Keep only bounded, key-redacted error text; never save response headers or credentials.
        err=data.get('error',data.get('message','')) if isinstance(data,dict) else ''
        if isinstance(err,dict):err=err.get('message') or err.get('type') or err.get('code') or str(err)
        err=re.sub(re.escape(cfg.api_key),'[REDACTED]',str(err),flags=re.I)[:280]
        rec.update(result='provider_rejected',error_excerpt=err,cost_class='unknown_after_rejection')
    except Exception as e:
      rec.update(result='transport_error',error_type=type(e).__name__,seconds=round(time.monotonic()-started,3),cost_class='unknown_after_transport_error')
    records.append(rec);print(provider,model,rec.get('result'),rec.get('http_status'),flush=True)
    time.sleep(3.2)
OUT.write_text(json.dumps({'created_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'fixture':str(FIXTURE.relative_to(ROOT)),'fixture_sha256':hashlib.sha256(raw).hexdigest(),'prompt':PROMPT,'max_output_tokens':48,'attempt_limit_per_model':1,'records':records},ensure_ascii=False,indent=2)+'\n')
