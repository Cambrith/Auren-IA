"""Local evidence from authorized real requests. Never infer success from catalogs."""
import json
from datetime import datetime, timezone
from pathlib import Path

# Independent of connection imports, so public catalogs can use the same evidence.
STATE = Path(__file__).resolve().parents[1] / '.cavren'
_cache = {}
_stamp = None

def evidence():
    global _cache, _stamp
    paths=[STATE/'validation_results.json', STATE/'validation_text_results.json']
    try:
        stamp=tuple((str(path), path.stat().st_mtime_ns if path.exists() else 0) for path in paths)
        if stamp != _stamp:
            records={}
            for index,path in enumerate(paths):
                if path.exists():
                    raw=json.loads(path.read_text()).get('records', {})
                    records.update({k:v for k,v in raw.items() if index==0 or k.startswith('text:')})
            _cache=records; _stamp=stamp
        return _cache
    except (OSError, ValueError, AttributeError):
        return {}

def model_evidence(model_id, kind):
    if kind in ('transcribe','speech'):
        try:
            tasks=json.loads((STATE/'validation_tasks.json').read_text()).get('tasks',{})
            match=next((r for k,r in tasks.items() if (k.startswith('transcribe_') if kind=='transcribe' else k=='speech') and r.get('model')==model_id and r.get('ok')), {})
            return {'id':model_id,'status':'working' if match else 'not_tested','cost':'free_with_limits' if match else 'not_verified',
                    'verified_at':match.get('date'),'samples':match.get('samples',[{'ok':True}]) if match else [],'mean_seconds':match.get('seconds'),'safety':match.get('safety')}
        except (OSError,ValueError,AttributeError):return {}
    return evidence().get(kind + ':' + model_id, {})

def verified(model_id, kind):
    record=model_evidence(model_id,kind)
    samples=record.get('samples',[])
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(record['verified_at'])).total_seconds()
        if age < 0: return False
        path=STATE/'provider_policy.json'
        policy=json.loads(path.read_text()) if path.exists() else {}
        provider=model_id.removeprefix('cavren:').split(':',1)[0]
        safety=record.get('safety')
        if safety=='configured_trial' and policy.get(provider+'_trial') is not True:return False
        if safety=='configured_free_plan':
            if provider in ('gemini','groq','ollama') and policy.get(provider+'_free_plan') is not True:return False
            if provider=='cloudflare' and policy.get('cloudflare_workers_free') is not True:return False
            if provider=='mistral':
                from cavren.nextchat_server import preferences
                if preferences().get('mistral_free_plan') is not True:return False
        revision=policy.get('validation_not_before', {}).get(provider)
        if revision and datetime.fromisoformat(record['verified_at']) < datetime.fromisoformat(revision):return False
        if revision:
            samples=[sample for sample in samples if datetime.fromisoformat(sample.get('date') or record['verified_at'])>=datetime.fromisoformat(revision)]
    except (KeyError, ValueError, TypeError, OSError, AttributeError): return False
    required=2 if kind in ('image','speech') else 1
    return record.get('status')=='working' and record.get('cost')=='free_with_limits' and sum(s.get('ok') is True and (kind!='text' or s.get('semantic_check') is not False) for s in samples)>=required

def measured_seconds(model_id, kind):
    if not verified(model_id,kind):return None
    value=model_evidence(model_id,kind).get('mean_seconds')
    return value if isinstance(value,(int,float)) else None


def save_category(model_id, task, row):
    """Merge an actual category probe atomically across independent testers."""
    if task not in ('code','documents','research'):raise ValueError('Categoria de validação inválida.')
    import fcntl
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (STATE/'validation_categories.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=STATE/'validation_categories.json'
        try:data=json.loads(path.read_text())
        except (OSError,ValueError):data={'records':{}}
        # Whitelist: never store provider responses, prompts, headers or credentials.
        fields=('ok','date','code','seconds','safety','check')
        data.setdefault('records',{})[task+':'+model_id]={'id':model_id,'task':task,**{k:row[k] for k in fields if k in row}}
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temporary.chmod(0o600);temporary.replace(path)
