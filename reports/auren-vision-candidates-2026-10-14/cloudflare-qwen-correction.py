"""Correct one Cloudflare Qwen response parse; preserves the first attempt separately."""
import base64,hashlib,json,re,sys,time,unicodedata
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'reports/auren-gemini-groq-2026-10-14-r2/fixtures/vision.png'
raw=FIXTURE.read_bytes();uri='data:image/png;base64,'+base64.b64encode(raw).decode()
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT.parent/'cavren-nextchat'/'src'))
from integration.lunvri_connections import connection_settings
cfg=connection_settings().providers['cloudflare']; model='@cf/qwen/qwen3.8-27b'
prompt='Leia o identificador impresso na imagem, conte os círculos vermelhos e os quadrados azuis. Responda somente no formato identificador|quantidade_de_circulos|quantidade_de_quadrados.'
body={'model':model,'messages':[{'role':'user','content':[{'type':'text','text':prompt},{'type':'image_url','image_url':{'url':uri}}]}],'max_tokens':512,'stream':False,'reasoning_effort':'low'}
started=time.monotonic(); rec={'provider':'cloudflare','model':model,'operation':'vision/image-understanding','attempt':'correction_after_output_cap','real_call':True,'max_output_tokens':512,'retries':0,'fixture_sha256':hashlib.sha256(raw).hexdigest(),'estimated_price_usd_per_million':{'input':0.45,'output':3.20}}
try:
 with httpx.Client(trust_env=False,timeout=35) as client:r=client.post(cfg.base_url.rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+cfg.api_key,'Content-Type':'application/json'},json=body)
 rec['http_status']=r.status_code
 try:data=r.json()
 except ValueError:data={}
 rec['response_shape_keys']=sorted(data.keys()) if isinstance(data,dict) else [type(data).__name__]
 if r.status_code<400:
  try:text=data['choices'][0]['message'].get('content') or ''
  except (KeyError,IndexError,TypeError,AttributeError):
   result=data.get('result',{}) if isinstance(data,dict) else {}
   text=(result.get('response') or result.get('text') or '') if isinstance(result,dict) else ''
  text=str(text);norm=''.join(c for c in unicodedata.normalize('NFD',text.upper()) if unicodedata.category(c)!='Mn');m=re.search(r'PIXEL\s*[-–—]?\s*739',norm);nums=re.findall(r'\d+',norm[m.end():]) if m else []
  ok=len(nums)>=2 and nums[:2]==['2','1'];rec.update(result='valid' if ok else 'semantic_check_failed',semantic_pass=ok,response_excerpt=text[:260],response_sha256=hashlib.sha256(text.encode()).hexdigest())
  usage=data.get('usage',{});u={k:v for k,v in usage.items() if k in ('prompt_tokens','completion_tokens','total_tokens') and isinstance(v,(int,float))} if isinstance(usage,dict) else {}
  if u:
   rec['usage_tokens']=u;rec['estimated_cost_usd']=(u.get('prompt_tokens',0)*.45+u.get('completion_tokens',0)*3.2)/1_000_000;rec['cost_class']='positive_estimate' if rec['estimated_cost_usd']>0 else 'zero_estimate'
  else:rec['cost_class']='unknown_actual_cost'
 else:
  rec.update(result='provider_rejected',cost_class='unknown_after_rejection');errs=data.get('errors',data.get('error',data.get('message',''))) if isinstance(data,dict) else ''
  if isinstance(errs,list):errs='; '.join(str(x.get('message') or x.get('code') or '') for x in errs if isinstance(x,dict))
  rec['error_excerpt']=str(errs)[:260]
except Exception as e:rec.update(result='transport_error',error_type=type(e).__name__,cost_class='unknown_after_transport_error')
rec['seconds']=round(time.monotonic()-started,3)
Path(__file__).with_name('cloudflare-qwen-correction-512.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n')
print(rec.get('result'),rec.get('http_status'),rec.get('semantic_pass'),rec.get('estimated_cost_usd'))
