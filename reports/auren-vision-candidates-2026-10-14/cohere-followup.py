"""Check Cohere vision through Auren's compatibility transport and current Command A+."""
import base64,hashlib,json,re,sys,time,unicodedata
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[2]; FIXTURE=ROOT/'reports/auren-gemini-groq-2026-10-14-r2/fixtures/vision.png';raw=FIXTURE.read_bytes();uri='data:image/png;base64,'+base64.b64encode(raw).decode()
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT.parent/'cavren-nextchat'/'src'))
from integration.lunvri_connections import connection_settings
cfg=connection_settings().providers['cohere'];prompt='Leia o identificador impresso na imagem, conte os círculos vermelhos e os quadrados azuis. Responda somente no formato identificador|quantidade_de_circulos|quantidade_de_quadrados.'
cases=[('command-a-vision-07-2025','compatibility_v1',cfg.base_url.rstrip('/')+'/chat/completions'),('command-a-plus-05-2026','native_v2','https://api.cohere.com/v2/chat')]
records=[]
def text_of(data,kind):
 if kind=='native_v2':return ''.join(p.get('text','') for p in data.get('message',{}).get('content',[]) if isinstance(p,dict))
 try:return str(data['choices'][0]['message'].get('content') or '')
 except (KeyError,IndexError,TypeError,AttributeError):return ''
def semantic(text):
 n=''.join(c for c in unicodedata.normalize('NFD',text.upper()) if unicodedata.category(c)!='Mn');m=re.search(r'PIXEL\s*[-–—]?\s*739',n);nums=re.findall(r'\d+',n[m.end():]) if m else [];return len(nums)>=2 and nums[:2]==['2','1']
with httpx.Client(trust_env=False,timeout=35) as client:
 for model,kind,url in cases:
  body={'model':model,'messages':[{'role':'user','content':[{'type':'text','text':prompt},{'type':'image_url','image_url':{'url':uri}}]}]}
  if kind=='native_v2':body['max_tokens']=48
  else:body['max_tokens']=48;body['stream']=False
  rec={'provider':'cohere','model':model,'operation':'vision/image-understanding','transport':kind,'real_call':True,'output_token_cap':48,'fixture_sha256':hashlib.sha256(raw).hexdigest(),'prompt':prompt,'cost_class':'unknown_actual_cost'}
  start=time.monotonic()
  try:
   response=client.post(url,headers={'Authorization':'Bearer '+cfg.api_key,'Content-Type':'application/json'},json=body);rec['http_status']=response.status_code
   try:data=response.json()
   except ValueError:data={}
   if response.status_code<400:
    text=text_of(data,kind);usage=data.get('usage',{});rec.update(result='valid' if semantic(text) else 'semantic_check_failed',semantic_pass=semantic(text),response_excerpt=text[:240],response_sha256=hashlib.sha256(text.encode()).hexdigest())
    if isinstance(usage,dict):
     tokens=usage.get('billed_units') or usage.get('tokens') or {};rec['usage_tokens']={k:v for k,v in tokens.items() if k in ('input_tokens','output_tokens') and isinstance(v,(int,float))}
   else:
    err=data.get('error',data.get('message','')) if isinstance(data,dict) else ''
    if isinstance(err,dict):err=err.get('message') or err.get('type') or ''
    rec.update(result='provider_rejected',error_excerpt=str(err)[:240])
  except Exception as e:rec.update(result='transport_error',error_type=type(e).__name__)
  rec['seconds']=round(time.monotonic()-start,3);records.append(rec);print(model,rec.get('result'),rec.get('http_status'),flush=True);time.sleep(3.2)
Path(__file__).with_name('cohere-followup.json').write_text(json.dumps({'created_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'records':records},ensure_ascii=False,indent=2)+'\n')
