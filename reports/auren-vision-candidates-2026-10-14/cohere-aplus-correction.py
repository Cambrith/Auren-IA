"""One bounded follow-up after the first Command A+ output hit its 48-token cap."""
import base64,hashlib,json,re,sys,time,unicodedata
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[2];fixture=ROOT/'reports/auren-gemini-groq-2026-10-14-r2/fixtures/vision.png';raw=fixture.read_bytes();uri='data:image/png;base64,'+base64.b64encode(raw).decode()
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT.parent/'cavren-nextchat'/'src'))
from integration.lunvri_connections import connection_settings
cfg=connection_settings().providers['cohere'];model='command-a-plus-05-2026';prompt='Leia o identificador impresso na imagem, conte os círculos vermelhos e os quadrados azuis. Responda somente no formato identificador|quantidade_de_circulos|quantidade_de_quadrados.'
body={'model':model,'messages':[{'role':'user','content':[{'type':'text','text':prompt},{'type':'image_url','image_url':{'url':uri}}]}],'max_tokens':512}
rec={'provider':'cohere','model':model,'operation':'vision/image-understanding','transport':'native_v2','attempt':'corrected_output_cap','real_call':True,'output_token_cap':512,'retries':0,'fixture_sha256':hashlib.sha256(raw).hexdigest(),'cost_class':'unknown_actual_cost'};start=time.monotonic()
try:
 with httpx.Client(trust_env=False,timeout=35) as client:r=client.post('https://api.cohere.com/v2/chat',headers={'Authorization':'Bearer '+cfg.api_key,'Content-Type':'application/json'},json=body)
 rec['http_status']=r.status_code
 try:data=r.json()
 except ValueError:data={}
 if r.status_code<400:
  text=''.join(p.get('text','') for p in data.get('message',{}).get('content',[]) if isinstance(p,dict));n=''.join(c for c in unicodedata.normalize('NFD',text.upper()) if unicodedata.category(c)!='Mn');m=re.search(r'PIXEL\s*[-–—]?\s*739',n);nums=re.findall(r'\d+',n[m.end():]) if m else [];ok=len(nums)>=2 and nums[:2]==['2','1'];u=data.get('usage',{});usage=u.get('billed_units') or u.get('tokens') or {};rec.update(result='valid' if ok else 'semantic_check_failed',semantic_pass=ok,response_excerpt=text[:260],response_sha256=hashlib.sha256(text.encode()).hexdigest(),finish_reason=data.get('finish_reason'),usage_tokens={k:v for k,v in usage.items() if k in ('input_tokens','output_tokens') and isinstance(v,(int,float))})
 else:rec.update(result='provider_rejected',error_excerpt=str(data.get('message',data.get('error','')))[:240])
except Exception as e:rec.update(result='transport_error',error_type=type(e).__name__)
rec['seconds']=round(time.monotonic()-start,3);Path(__file__).with_name('cohere-aplus-correction.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n');print(rec.get('result'),rec.get('http_status'),rec.get('semantic_pass'))
