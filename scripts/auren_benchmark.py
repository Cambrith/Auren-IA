"""Authorized real measurements, using vault credentials and zero paid fallback.

Only synthetic prompts are sent. Reports contain no keys or returned conversations.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import json
import signal
import time
import uuid
from decimal import Decimal, InvalidOperation
import httpx
from cavren.models import Message
from cavren.errors import CavrenError
from integration.lunvri_connections import connection_settings, STATE
from integration.lunvri_manual import PreparedChatProvider, generate_images

RESULTS = STATE / 'validation_results.json'

def save(data):
    path=RESULTS.with_suffix('.tmp'); path.write_text(json.dumps(data, ensure_ascii=False, indent=2));path.chmod(0o600);path.replace(RESULTS)

def safe_policy(info, policy, live_free):
    provider=info.get('provider'); name=info.get('model_id','')
    if provider == 'aihorde': return 'community_kudos'
    if provider in ('cohere','nvidia') and policy.get(provider+'_trial') is True: return 'configured_trial'
    if provider == 'cloudflare' and policy.get('cloudflare_workers_free') is True: return 'configured_free_plan'
    if provider == 'openrouter' and name in live_free: return 'live_zero_price'
    if provider == 'mistral' and policy.get('mistral_free_plan') is True: return 'configured_free_plan'
    if provider == 'zai' and name == 'glm-4.5-flash': return 'documented_free_model'
    return None

def sanitized(error, secrets):
    text=str(error)
    for secret in secrets:
        if secret: text=text.replace(secret,'[redigido]')
    return text[:300]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=['image','text'],required=True);parser.add_argument('--timeout',type=int,default=75)
    parser.add_argument('--calibrate-first', action='store_true')
    parser.add_argument('--calibrate-only', action='store_true', help='Measure selected profiles without repeating the whole catalog')
    parser.add_argument('--retest', action='store_true', help='Append new samples instead of reusing earlier measurements')
    parser.add_argument('--provider', help='Measure only this configured provider')
    parser.add_argument('--cancel-long-queue', action='store_true', help='Cancel after repeated provider estimates exceed twice the measurement budget; this is not a model failure')
    args=parser.parse_args()
    global RESULTS
    if args.kind=='text': RESULTS=STATE/'validation_text_results.json'
    models=json.loads((STATE/'models.json').read_text())['models']
    settings=connection_settings(); policy=json.loads((STATE/'provider_policy.json').read_text())
    from cavren.nextchat_server import preferences
    policy.update({k:v for k,v in preferences().items() if k in ('mistral_free_plan','cloudflare_workers_free')})
    secrets=[value for c in settings.providers.values() for value in (c.api_key,getattr(c,'account_id','')) if value]
    live_free=set(); openrouter=settings.providers.get('openrouter')
    with httpx.Client(trust_env=False,timeout=20) as client:
        if openrouter and openrouter.api_key:
            try:
                resp=client.get('https://openrouter.ai/api/v1/models',headers={'Authorization':'Bearer '+openrouter.api_key})
                for raw in resp.json().get('data',[]):
                    prices=raw.get('pricing') or {}
                    if prices and all(Decimal(str(v)) == 0 for v in prices.values()): live_free.add(raw['id'])
            except (httpx.HTTPError,ValueError,InvalidOperation): pass
    try: data=json.loads(RESULTS.read_text())
    except (OSError,ValueError): data={'date':datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),'records':{}}
    records=data['records']
    # Populate every advertised record so skipped models remain visible in the report.
    for m in models:
        info=m.get('cavren',{})
        if not info.get('provider'): continue
        kinds = (['image'] if info.get('capabilities',{}).get('image_generation') else []) + (['text'] if not info.get('image_only') else [])
        for kind in kinds:
            record_key=kind+':'+m['id']
            records.setdefault(record_key, {'id':m['id'],'provider':info['provider'],'model':info['model_id'],'kind':kind,
                              'status':'not_tested','cost':'not_verified','reason':'Ainda não testado','samples':[]})
            safety=safe_policy(info,policy,live_free)
            if not safety:
                records[record_key].update(reason='Sem confirmação de rota sem cobrança; não chamado para respeitar a restrição de gastos.')
    save(data)
    eligible=[m for m in models if m.get('cavren',{}).get('provider') and
              (m['cavren'].get('capabilities',{}).get('image_generation') if args.kind=='image' else not m['cavren'].get('image_only'))]
    # Retain the initial snapshot when a refresh temporarily omits a Horde worker.
    if args.kind == 'image':
        known={m['id'] for m in eligible}
        for record in list(records.values()):
            if record['kind']=='image' and record['provider']=='aihorde' and record['id'] not in known:
                eligible.append({'id':record['id'],'cavren':{'provider':'aihorde','model_id':record['model']}})
    # Start with existing curated defaults, then keep catalog order. No simultaneous generations.
    eligible.sort(key=lambda m: (m['id']!='cavren:aihorde:stable_diffusion', m['id']!='cavren:nvidia:nvidia/nemotron-3.5-lightning-30b-a3b'))
    if (args.calibrate_first or args.calibrate_only) and args.kind == 'image':
        from integration.auren_images import rank
        from integration.auren_validation import verified
        measured=[m for m in eligible if verified(m['id'], 'image')]
        calibration=[]
        for profile in ('rapid','detailed'):
            selected=min(measured, key=lambda m: rank(dict(m['cavren'], route_id=m['id'].removeprefix('cavren:')), {'auren_image_profile':profile})) if measured else None
            if selected:
                calibrated=dict(selected, benchmark_profile=profile)
                key='profile:'+profile+':'+selected['id']
                records.setdefault(key,dict(records['image:'+selected['id']], kind='profile', profile=profile, samples=[], status='not_tested', mean_seconds=None))
                calibration.append(calibrated)
        eligible=calibration if args.calibrate_only else calibration+eligible
        save(data)
    def expired(sig,frame): raise CavrenError('benchmark_timeout','Medição atingiu o prazo; pedido pendente cancelado quando o provedor permite.')
    signal.signal(signal.SIGALRM,expired)
    for position,m in enumerate(eligible):
        info=m['cavren'];profile=m.get('benchmark_profile','balanced');key=('profile:'+profile if m.get('benchmark_profile') else args.kind)+':'+m['id'];record=records[key];safety=safe_policy(info,policy,live_free)
        if not safety or args.provider and info['provider']!=args.provider: continue
        cfg=settings.providers.get(info['provider'])
        if not cfg or not cfg.api_key:
            record.update(reason='Credencial ausente no cofre.');save(data);continue
        cfg=replace(cfg,model=info['model_id'])
        count=(len(record['samples']) if args.retest else 0)+(2 if args.kind=='image' else 1)
        if len(record['samples']) >= count: continue
        for sample in range(len(record['samples']),count):
            while (STATE/'image-benchmark.pause').exists() and args.kind=='image':time.sleep(.5)
            started=time.monotonic();progress={}; row={'date':datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()}
            try:
                signal.setitimer(signal.ITIMER_REAL,args.timeout)
                with httpx.Client(trust_env=False) as client:
                    if args.kind=='image':
                        row['parameters']={'width':512,'height':512,'steps':(12 if profile=='rapid' else 30 if profile=='detailed' else 20) if cfg.model=='stable_diffusion' else 20,'n':1} if cfg.name=='aihorde' else {'native_defaults':True}
                        job={'generation_id':str(uuid.uuid4()),'auren_deadline':started+args.timeout+5,
                             'auren_image_profile':profile,'auren_image_preferences':{'image_width':512,'image_height':512,'image_steps':20}}
                        long_queue=[]
                        def status(event):
                            for k in ('queue_position','wait_time','eligible_workers','state'):
                                if event.get(k) is not None: progress[k]=event[k]
                            estimate=event.get('wait_time')
                            if args.cancel_long_queue and event.get('state')=='queued' and isinstance(estimate,(int,float)) and estimate>args.timeout*2:
                                long_queue.append(time.monotonic())
                                if len(long_queue)>=2 and long_queue[-1]-long_queue[0]>=5:
                                    raise CavrenError('benchmark_queue_budget','Não concluiu: a espera estimada pelo provedor excedeu duas vezes o orçamento de medição em consultas repetidas; pedido cancelado. Isso não comprova falha do modelo.')
                            elif event.get('state') in ('processing','queued'):
                                long_queue.clear()
                        # Measure repeated actual checks even when the visible status is unchanged.
                        def check_response(response):
                            if not args.cancel_long_queue or cfg.name!='aihorde' or '/generate/check/' not in response.request.url.path or response.status_code!=200:return
                            response.read()
                            try: check=response.json()
                            except ValueError:return
                            if check.get('done') or check.get('faulted'):return
                            status({**{k:check.get(k) for k in ('queue_position','wait_time','eligible_workers')},'state':'processing' if check.get('processing',0) else 'queued'})
                        client.event_hooks['response'].append(check_response)
                        files,text=generate_images(client,cfg,[Message('user','A blue sphere on a plain white background, simple illustration.')],
                             'A blue sphere on a plain white background, simple illustration.',progress=status,job=job)
                        ok=bool(files)
                    else:
                        tuned=replace(settings,max_tokens=256,retries=0,timeout=min(args.timeout,30),reasoning_effort='default')
                        response=PreparedChatProvider(cfg,tuned,client).generate([Message('user','Responda apenas o resultado de 17 × 23, sem explicação.')],trace_id='measurement')
                        ok=bool(response.text.strip());row['semantic_check']='391' in response.text
                        row['parameters']={'max_tokens':256}
                row.update(ok=ok,code='ok' if ok else 'empty_response')
            except KeyboardInterrupt:
                row.update(ok=False,code='benchmark_interrupted',error='Medição interrompida localmente; pedido cancelado quando o provedor permite.')
                row['seconds']=round(time.monotonic()-started,3);row['progress']=progress
                record.setdefault('interruptions',[]).append(row)
                save(data)
                raise
            except (CavrenError,httpx.HTTPError) as error:
                row.update(ok=False,code=getattr(error,'code',type(error).__name__),error=sanitized(error,secrets),http_status=getattr(error,'http_status',None))
            except Exception as error:
                row.update(ok=False,code=type(error).__name__,error=sanitized(error,secrets))
            finally:
                signal.setitimer(signal.ITIMER_REAL,0)
            row['seconds']=round(time.monotonic()-started,3);row['progress']=progress;record['samples'].append(row)
            successes=[r['seconds'] for r in record['samples'] if r.get('ok')]
            record.update(status='working' if successes else 'failed',cost='free_with_limits' if successes else 'not_verified',
                safety=safety, reason='' if successes else row.get('error','Falha'),mean_seconds=round(sum(successes)/len(successes),3) if successes else None,
                verified_at=row['date'])
            save(data)
            print(json.dumps({'kind':record['kind'],'profile':profile,'position':position+1,'total':len(eligible),'model':info['model_id'], 'sample':sample+1,'ok':row['ok'],'seconds':row['seconds'],'code':row['code']}),flush=True)
            # Respect trial RPM; no retries or implicit model substitutions.
            time.sleep(3 if cfg.name in ('cohere','nvidia','openrouter') else .2)
    data[('profile' if args.calibrate_only else args.kind)+'_completed_at']=datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat();save(data)

if __name__=='__main__':main()
