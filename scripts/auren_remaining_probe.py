"""Ordered continuation of uncalled/inconclusive routes; no app-state mutations."""
from __future__ import annotations

import argparse
import base64
import copy
import contextlib
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import httpx
import auren_exhaustive_probe as audit

ROOT = audit.ROOT
ORDER = ['gemini', 'groq', 'zai', 'ollama', 'cohere', 'mistral',
         'deepseek', 'cloudflare', 'nvidia', 'openrouter', 'aihorde']
SOURCES = ['auren-exaustiva-2026-10-13-r1', 'auren-gemini-groq-2026-10-14-r2']
BASE_REQUEST_BODY = audit.request_body
BASE_EXTRACT = audit.extract
BASE_PROBE = audit.probe
BASE_EVALUATE = audit.evaluate
BASE_IMAGE_PROBE = audit.image_probe


def corrected_request_body(row, sample, config, assets):
    url, body, extra = BASE_REQUEST_BODY(row, sample, config, assets)
    if row['provider'] == 'zai' and row['requested_model'].startswith('glm-4.5') and isinstance(body, dict):
        body['thinking'] = {'type': 'disabled'}
    if row['provider'] == 'cloudflare' and row['requested_model'] == '@cf/llava-hf/llava-1.5-7b-hf' and row['operation'] == 'vision':
        body = {'image': list((assets / 'vision.png').read_bytes()),
                'prompt': audit.PROMPTS['vision'][0], 'max_tokens': 512}
    if row['provider'] == 'cloudflare' and row['requested_model'] == '@cf/myshell-ai/melotts' and row['operation'] == 'speech':
        body = {'prompt': 'Good morning.', 'lang': 'en'}
    if row['provider'] == 'nvidia' and row['operation'] == 'moderation_chat':
        content = 'Hello, have a nice day.'
        if 'nemoguard' in row['requested_model']:
            content = ('Task: Check the safety of the user message. Return only a JSON object with User Safety as safe or unsafe. '
                       '<BEGIN UNSAFE CONTENT CATEGORIES>S1: Violence. S2: Hate.<END UNSAFE CONTENT CATEGORIES>'
                       '<BEGIN CONVERSATION>user: Hello, have a nice day.<END CONVERSATION>')
        body = {'model': row['requested_model'], 'messages': [{'role': 'user', 'content': content}],
                'max_tokens': 128, 'stream': False}
    if row['provider'] == 'nvidia' and row['requested_model'] == 'google/paligemma' and row['operation'] == 'vision':
        for message in body.get('messages', []):
            if not isinstance(message.get('content'), list): continue
            for part in message['content']:
                if part.get('type') == 'image_url' and isinstance(part.get('image_url'), dict):
                    part['image_url'] = part['image_url']['url']
    return url, body, extra


def corrected_extract(data, provider):
    if provider == 'cloudflare' and isinstance(data.get('result'), dict) and isinstance(data['result'].get('description'), str):
        return data['result']['description'], [], None
    text, calls, finish = BASE_EXTRACT(data, provider)
    if isinstance(text, dict) and set(text) == {'cidade', 'quantidade', 'preco'}:
        return json.dumps(text, ensure_ascii=False), calls, finish
    return (text if isinstance(text, str) else ''), calls, finish


def corrected_evaluate(data, provider, operation, sample):
    if provider == 'nvidia' and operation == 'moderation_chat':
        text, _, finish = corrected_extract(data, provider)
        label = text.strip().lower()
        try: label = json.loads(text).get('User Safety', '').lower()
        except (ValueError, AttributeError): pass
        ok = label == 'safe' and finish not in ['length', 'MAX_TOKENS']
        return ok, 'valid_benign_safety_label' if ok else 'safety_label_check_failed', {
            'response_sha256': hashlib.sha256(text.encode()).hexdigest(), 'finish_reason': finish,
            'known_benign_input': True, 'label_verified': ok,
            'scope': 'One harmless-input classification; unsafe-content accuracy is not certified.'}
    return BASE_EVALUATE(data, provider, operation, sample)


def corrected_probe(client, row, sample, config, assets, run):
    if row['provider'] == 'aihorde' and row['operation'] == 'text':
        return horde_text_probe(client, row, sample, config, run)
    if not (row['provider'] == 'cloudflare' and row['requested_model'] == '@cf/myshell-ai/melotts' and row['operation'] == 'speech'):
        return BASE_PROBE(client, row, sample, config, assets, run)
    from auren_native_media_probe import inspect_media
    started = time.monotonic()
    result = dict(at=audit.now(), sample=sample, real_call=False, success=False, cost_class='unknown')
    try:
        url, body, _ = corrected_request_body(row, sample, config, assets)
        result['request_sha256'] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        result['real_call'] = True
        response = client.post(url, headers=audit.headers('cloudflare', config), json=body, timeout=30)
        try: data = response.json()
        except ValueError: data = {}
        result.update(audit.safe_response(response, data, config))
        if response.status_code >= 400 or data.get('success') is False:
            result['result'] = 'provider_denial'; return result
        encoded = data.get('result', {}).get('audio') if isinstance(data.get('result'), dict) else None
        raw = base64.b64decode(encoded) if encoded else response.content
        if len(raw) > 2_000_000: raise ValueError('Audio byte budget')
        media = inspect_media(raw, '.mp3'); result['media'] = media
        wav = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-t', '10', '-f', 'wav', '-ar', '16000', '-ac', '1', 'pipe:1'],
                             input=raw, capture_output=True, timeout=10, check=True).stdout
        asr = audit.verify_speech(wav, 'en', 'good morning')
        result.update(semantic_asr=asr, auxiliary_call_count=int(asr.get('real_call', False)),
                      success=0 < media['duration_seconds'] < 10 and bool(asr.get('success')),
                      result='valid_native_mp3_and_asr' if asr.get('success') else 'native_mp3_semantics_pending',
                      semantic_pending=not asr.get('success'))
    except Exception as error: result['result'] = type(error).__name__
    finally: result['seconds'] = round(time.monotonic()-started, 3)
    return result


def horde_text_probe(client, row, sample, config, run):
    from uuid import UUID
    started = time.monotonic(); deadline = started+30; remote = None; done = False
    result = dict(at=audit.now(), sample=sample, real_call=False, success=False,
                  cost_class='community_kudos_usd_not_reported', queue_events=[],
                  native_contract='AI Horde asynchronous raw text prompt')
    body = {'prompt': '### Instruction:\n'+audit.PROMPTS['text'][sample]+'\n### Response:\n',
            'models': [row['requested_model']], 'params': {'n': 1, 'max_length': 128,
            'max_context_length': 1024, 'temperature': .1, 'frmtrmspch': False},
            'allow_downgrade': False, 'context_fit': 'reject'}
    result['parameters'] = body['params']
    result['request_sha256'] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    base = 'https://aihorde.net/api/v2/generate/text'
    try:
        result['real_call'] = True
        response = client.post(base+'/async', headers=audit.headers('aihorde', config), json=body, timeout=10)
        data = response.json(); result.update(audit.safe_response(response, data, config))
        if response.status_code != 202:
            result['result'] = {400: 'contract_error', 401: 'authentication', 403: 'permission_or_kudos', 429: 'rate_or_quota_limit'}.get(response.status_code, 'provider_error')
            return result
        remote = str(UUID(data['id'])); result['remote_id'] = remote
        path = run / 'remote' / ('horde-text-'+hashlib.sha256(row['key'].encode()).hexdigest()[:20]+f'-{sample}.json')
        audit.atomic(path, {'provider': 'aihorde', 'row': row['key'], 'remote_id': remote, 'at': audit.now(), 'status': 'accepted'})
        while time.monotonic() < deadline-4:
            response = client.get(base+'/status/'+remote, headers=audit.headers('aihorde', config), timeout=8)
            data = response.json()
            result['queue_events'].append({'seconds': round(time.monotonic()-started, 3), 'http_status': response.status_code,
                **{key: data.get(key) for key in ['queue_position', 'wait_time', 'processing', 'waiting', 'done', 'faulted', 'is_possible']}})
            if response.status_code != 200: result['result'] = 'remote_poll_denied'; return result
            if data.get('done'):
                done = True; generations = data.get('generations', [])
                text = generations[0].get('text', '') if generations else ''
                equivalent = {'choices': [{'message': {'content': text}, 'finish_reason': None}]}
                ok, code, evidence = corrected_evaluate(equivalent, 'aihorde', 'text', sample)
                result.update(success=ok, result=code, evidence=evidence, kudos=data.get('kudos'),
                              resolved_model=generations[0].get('model') if generations else None)
                return result
            if data.get('is_possible') is False:
                result['result'] = 'no_eligible_workers_inconclusive'; return result
            if type(data.get('wait_time')) in (int, float) and data['wait_time'] > deadline-time.monotonic():
                result['result'] = 'queue_budget_inconclusive'; return result
            time.sleep(2)
        result['result'] = 'queue_budget_inconclusive'
    except Exception as error: result['result'] = type(error).__name__
    finally:
        if remote and not done:
            try: result['cancel_http_status'] = client.delete(base+'/status/'+remote, headers=audit.headers('aihorde', config), timeout=8).status_code
            except Exception as error: result['cancel_error'] = type(error).__name__
        result['seconds'] = round(time.monotonic()-started, 3)
    return result


def corrected_image_probe(client, row, sample, config, assets, run):
    cancelled = []; delivered = []
    class CaptureCancellation:
        def __getattr__(self, name): return getattr(client, name)
        def get(self, *args, **kwargs):
            response = client.get(*args, **kwargs)
            if response.status_code == 200 and '/generate/status/' in str(args[0]):
                try: delivered.append(response.json())
                except ValueError: pass
            return response
        def delete(self, *args, **kwargs):
            response = client.delete(*args, **kwargs)
            if response.status_code == 200:
                try: cancelled.append(response.json())
                except ValueError: pass
            return response
    wrapped = CaptureCancellation() if row['provider'] == 'aihorde' else client
    result = BASE_IMAGE_PROBE(wrapped, row, sample, config, assets, run)
    if row['provider'] == 'aihorde' and result.get('real_call'):
        result.update(cost_class='community_kudos_usd_not_reported', billing_unit='kudos')
        observed = cancelled[-1] if cancelled else delivered[-1] if delivered else None
        if observed:
            censored = sum(bool(item.get('censored')) for item in observed.get('generations', []))
            if censored:
                result['censored_generations'] = censored
                if censored == len(observed.get('generations', [])):
                    result.update(success=False, result='censored')
        if cancelled:
            data = cancelled[-1]
            if type(data.get('kudos')) in (int, float) and 0 <= data['kudos'] <= 1e9:
                result['kudos'] = data['kudos']; result['kudos_source'] = 'native_cancel_response'
            generations = data.get('generations', [])
            result['cancel_reported_generations'] = len(generations)
            if generations and not result.get('success'):
                try:
                    files = [audit.decode_image(base64.b64decode(generation['img'], validate=True), run)
                             for generation in generations if generation.get('img') and not generation.get('censored')]
                    if len(files) == 1 and len(generations) == 1:
                        result.update(success=True, result='valid_file_received_during_cancel', files=files,
                                      generation_delivered_on_cancel=True,
                                      resolved_models=[generation.get('model') for generation in generations])
                except Exception as error: result['cancel_image_decode_error'] = type(error).__name__
        if len(result.get('resolved_models', [])) == 1:
            result['resolved_model'] = result['resolved_models'][0]
    return result


def merge_provider_journals(run):
    """Recover atomic provider checkpoints even after an interrupted process."""
    journal = audit.read(run / 'results.json', {'started_at': audit.now(), 'records': {}, 'control': {}})
    for path in sorted((run / 'journals').glob('*.json')):
        part = audit.read(path, {})
        for key, record in part.get('records', {}).items():
            if key.startswith(path.stem+':'): journal['records'][key] = record
        journal.setdefault('control', {}).update(part.get('control', {}))
    return journal


def import_additional_history(run):
    """Reconcile later vision/image evidence without counting it as new calls."""
    history = audit.read(run / 'historical-coverage.json')
    for folder, name, operation in [
        ('auren-vision-candidates-2026-10-14', 'results.json', 'vision'),
        ('auren-image-round-2026-10-14', 'aihorde-real.jsonl', 'image'),
        ('auren-image-round-2026-10-14', 'gemini-real.jsonl', 'image'),
        ('auren-image-round-2026-10-14', 'openrouter-zero-real.jsonl', 'image')]:
        path = ROOT / 'reports' / folder / name
        if not path.exists(): continue
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if name.endswith('.jsonl') else audit.read(path).get('records', [])
        for record in records:
            if not record.get('real_call') or not record.get('provider') or not record.get('model'): continue
            key = record['provider']+':'+record['model']+'::'+operation
            result = '|'.join(str(record.get(field, '')) for field in ['result', 'error_code', 'error_type', 'code']).lower()
            valid = record.get('semantic_pass') is True or (operation == 'image' and record.get('success') is True)
            status = 'valid' if valid else 'inconclusive' if any(word in result for word in ['queue', 'timeout', 'deadline', 'budget', 'inconclusive', 'pending']) else 'failed'
            old = history.setdefault(key, {})
            old.update(source=folder, evidence_file='../'+folder+'/'+name, native_called=True,
                       status=status, terminal=True, additional_historical_evidence=True)
    audit.atomic(run / 'historical-coverage.json', history)


def execute_checkpointed(run, provider, seconds):
    """Avoid rewriting thousands of other providers' immutable blockers per call."""
    original_atomic = audit.atomic
    latest = merge_provider_journals(run)
    original_atomic(run / 'results.json', latest)
    def checkpoint(path, value):
        nonlocal latest
        if path == run / 'results.json':
            latest = value
            part = {**value, 'records': {key: record for key, record in value['records'].items() if key.startswith(provider+':')}}
            original_atomic(run / 'journals' / (provider+'.json'), part)
        else: original_atomic(path, value)
    audit.atomic = checkpoint
    concurrency = audit.read(run / 'horde-concurrency-current.json', {})
    parallel = 2 if provider == 'aihorde' and concurrency.get('http_status') == 200 and type(concurrency.get('concurrency')) is int and concurrency['concurrency'] >= 4 else 1
    try: audit.execute(run, SimpleNamespace(providers=provider, operations=None, max_seconds=seconds,
                                          provider_workers={provider: parallel}))
    finally:
        audit.atomic = original_atomic
        original_atomic(run / 'results.json', latest)


def prepare(run):
    if (run / 'matrix.json').exists():
        return
    rows, coverage, models, providers = {}, {}, {}, {}
    for source in SOURCES:
        base = ROOT / 'reports' / source
        snapshot = audit.read(base / 'snapshot.json')
        models.update(snapshot['models']); providers.update(snapshot['providers'])
        matrix = audit.read(base / 'matrix.json')
        journal = audit.read(base / 'results.json')['records']
        complete = {r['key']: r for r in audit.read(base / 'complete.json')['rows']}
        for row in matrix['rows']:
            key = row['key']; rec = journal.get(key, {})
            called = any(s.get('real_call') and s.get('contract_valid') is not False for s in rec.get('samples', []))
            if key not in rows or called:
                rows[key] = copy.deepcopy(row)
            if key not in coverage or called:
                result = complete.get(key, {})
                coverage[key] = {'source': source, 'status': result.get('status', rec.get('status', 'not_tested')),
                                 'native_called': called, 'terminal': rec.get('terminal', False),
                                 'interrupted': bool(rec.get('in_flight') or rec.get('blocker') == 'interrupted_request_unknown'),
                                 'blocker': rec.get('blocker') or row.get('blocker'),
                                 'sample_results': [s.get('result') for s in rec.get('samples', [])]}
    budget = copy.deepcopy(audit.read(ROOT / 'reports' / SOURCES[1] / 'matrix.json')['budget'])
    budget.update(unknown_cost_call_limit_per_provider=100,
                  continuation_policy='Only uncalled and inconclusive routes. Historical failures retained, no blind denial retries. At most 100 accepted unknown-price calls per provider in this continuation.')
    selected = []
    for key, row in rows.items():
        previous = coverage[key]
        if not previous['native_called'] or previous['status'] in ('inconclusive', 'in_progress'):
            row['prior_evidence'] = previous
            # Prior scoped omissions must not exclude an operation from this continuation.
            if row.get('blocker') in ('operation_outside_scoped_functionality_check', 'planning_authorization_already_used'):
                row['blocker'] = None
            if previous['interrupted']:
                row.update(blocker='prior_interrupted_request_unknown', pending='Previous request outcome/cost unknown; no automatic duplicate submission.')
            if row['operation'] == 'research_agent':
                row.update(blocker=previous['blocker'] or 'full_research_not_authorized_by_planning_only_approval')
            if row['operation'] == 'agent_planning' and 'deep-research' in row['requested_model']:
                row.update(blocker='planning_authorization_already_used')
            selected.append(row)
    run.mkdir(parents=True, exist_ok=True)
    audit.atomic(run / 'historical-coverage.json', coverage)
    audit.atomic(run / 'snapshot.json', {'started_at': audit.now(), 'models': models,
                 'providers': providers, 'catalogs': {}, 'scope': 'Remaining uncalled/inconclusive operations; historical evidence remains separate.'})
    audit.atomic(run / 'matrix.json', {'snapshot_at': audit.now(), 'rows': selected, 'budget': budget})
    audit.atomic(run / 'order.json', {'order': ORDER, 'stages': {}, 'created_at': audit.now()})
    shutil.copytree(ROOT / 'reports' / SOURCES[0] / 'fixtures', run / 'fixtures', dirs_exist_ok=True)
    for name in ['image-endpoints.json', 'mistral-voices.json']:
        shutil.copy2(ROOT / 'reports' / SOURCES[0] / name, run / name)
    print('Prepared', len(selected), 'remaining operations;', dict(Counter(r['provider'] for r in selected)), flush=True)


def refresh(run, provider, cfg):
    """Read one official provider catalogue only when its ordered stage starts."""
    snapshot = audit.read(run / 'snapshot.json'); matrix = audit.read(run / 'matrix.json')
    url = cfg.base_url.rstrip('/') + '/models'; params = {}
    if provider == 'gemini': url = 'https://generativelanguage.googleapis.com/v1beta/models'; params = {'pageSize': 1000}
    if provider == 'cohere': url = 'https://api.cohere.com/v1/models'; params = {'page_size': 1000}
    if provider == 'ollama': url = 'https://ollama.com/api/tags'
    if provider == 'cloudflare':
        url = 'https://api.cloudflare.com/client/v4/accounts/'+cfg.account_id+'/ai/models/search'
        params = {'per_page': 100}
    if provider == 'aihorde': url = 'https://aihorde.net/api/v2/status/models'
    public_url = url.replace(cfg.account_id, '<account>') if cfg.account_id else url
    calls, items = [], []
    with httpx.Client(timeout=25, trust_env=False) as client:
        for _ in range(100):
            response = client.get(url, headers=audit.headers(provider, cfg), params=params)
            calls.append({'at': audit.now(), 'endpoint': public_url, 'http_status': response.status_code})
            if response.status_code != 200: break
            data = response.json()
            values = data if isinstance(data, list) else data.get('data', data.get('models', data.get('result', [])))
            if isinstance(values, dict): values = values.get('models', [])
            items.extend(audit.safe_model(item) for item in values if isinstance(item, dict))
            token = data.get('nextPageToken') or data.get('next_page_token') if isinstance(data, dict) else None
            if token:
                params['pageToken' if provider == 'gemini' else 'page_token'] = token
                continue
            pages = data.get('result_info', {}) if isinstance(data, dict) else {}
            if pages.get('total_pages', 1) > pages.get('page', 1):
                params['page'] = pages.get('page', 1)+1
                continue
            break
        if provider == 'openrouter':
            for extra_url in ['https://openrouter.ai/api/v1/images/models', 'https://openrouter.ai/api/v1/embeddings/models']:
                response = client.get(extra_url, headers=audit.headers(provider, cfg))
                calls.append({'at': audit.now(), 'endpoint': extra_url, 'http_status': response.status_code})
                if response.status_code == 200:
                    values = response.json().get('data', [])
                    items.extend({**audit.safe_model(item), '_source': extra_url} for item in values if isinstance(item, dict))
        if provider == 'aihorde':
            for item in items: item['type'] = 'image'
            response = client.get(url, headers=audit.headers(provider, cfg), params={'type': 'text', 'model_state': 'all'})
            calls.append({'at': audit.now(), 'endpoint': public_url, 'params': {'type': 'text', 'model_state': 'all'}, 'http_status': response.status_code})
            if response.status_code == 200:
                items.extend({**audit.safe_model(item), 'type': 'text', '_source': public_url+'?type=text&model_state=all'} for item in response.json() if isinstance(item, dict))
    aliases = []
    for item in items:
        for alias in item.get('aliases', []) or []:
            if isinstance(alias, str): aliases.append({**item, 'id': alias, 'alias_of': item.get('id') or item.get('name')})
    items.extend(aliases)
    unique_items = {}
    for item in items:
        identity = (item.get('name') if provider == 'cloudflare' else item.get('id')) or item.get('name') or item.get('model')
        if identity: unique_items.setdefault(identity, item)
    items = list(unique_items.values())
    all_keys = set(audit.read(run / 'historical-coverage.json')) | {r['key'] for r in matrix['rows']}
    for item in items:
        model = (item.get('name') if provider == 'cloudflare' else item.get('id')) or item.get('name') or item.get('model')
        if not model: continue
        if provider == 'gemini': model = model.removeprefix('models/')
        route = provider + ':' + model
        entry = snapshot['models'].setdefault(route, {'provider': provider, 'model': model, 'metadata': {}, 'sources': []})
        entry['metadata'].update(item)
        entry['sources'] = sorted(set(entry['sources'] + [public_url]))
        for op in audit.operations(entry):
            key = route + '::' + op
            if key in all_keys: continue
            blocker = op if op in audit.BLOCKERS else None
            if op.startswith('native_'): blocker = 'contract_review'
            row = {'key': key, 'provider': provider, 'requested_model': model,
                'operation': op, 'endpoint': audit.endpoint(provider, model, op),
                'contract_source': audit.DOCS[provider], 'provenance': [public_url],
                'criterion': audit.CRITERIA.get(op, 'Native schema and semantics must be reviewed.'),
                'required_samples': 2 if op in ['text', 'image', 'image_reference', 'image_mask', 'transcribe'] else 1,
                'blocker': blocker, 'status': 'not_tested', 'pending': 'New operation from current official catalogue.',
                'declared_price': item.get('pricing'), 'benchmark': 'not_reassessed'}
            if provider == 'aihorde' and op == 'text':
                row.update(endpoint='https://aihorde.net/api/v2/generate/text/async',
                           contract_source='https://aihorde.net/api/swagger.json', native_horde_text=True,
                           criterion='Two complementary fixed raw-prompt text checks via native async submission/status/cancellation. No chat-completions transport.')
            matrix['rows'].append(row)
            all_keys.add(key)
    snapshot['catalogs'][provider] = items
    snapshot['providers'][provider] = {'credential_available': True, 'catalog_calls': calls, 'documentation': audit.DOCS.get(provider)}
    audit.atomic(run / 'snapshot.json', snapshot); audit.atomic(run / 'matrix.json', matrix)
    print(provider, 'current catalogue', len(items), 'HTTP', [c['http_status'] for c in calls], flush=True)


def execute_provider(run, provider, seconds):
    order = audit.read(run / 'order.json')
    for earlier in ORDER[:ORDER.index(provider)]:
        if order['stages'].get(earlier, {}).get('status') != 'reconciled':
            raise SystemExit('Earlier provider not reconciled: ' + earlier)
    if order['stages'].get(provider, {}).get('status') == 'reconciled':
        print(provider, 'already reconciled; no repeated calls'); return
    # Native decoders refer to reviewed public contracts from the original run.
    base = ROOT / 'reports' / SOURCES[0]
    for pattern in ['cloudflare-*.json', 'nvidia-*.json', 'audio-unit-pricing-review.json', 'video-minimum-price-review.json']:
        for source in base.glob(pattern):
            target = run / source.name
            if not target.exists(): shutil.copy2(source, target)
    selected_keys = {row['key'] for row in audit.read(run / 'matrix.json')['rows'] if row['provider'] == provider}
    for folder in SOURCES:
        for source in (ROOT / 'reports' / folder / 'remote').rglob('*.json'):
            metadata = audit.read(source, {})
            if metadata.get('row') not in selected_keys: continue
            relative = source.relative_to(ROOT / 'reports' / folder)
            target = run / relative
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
    settings = audit.audit_settings(); cfg = settings.providers.get(provider)
    stage = order['stages'].setdefault(provider, {'started_at': audit.now()})
    if cfg and cfg.api_key and not stage.get('discovery_done'):
        refresh(run, provider, cfg); stage['discovery_done'] = True
    matrix = audit.read(run / 'matrix.json')
    snapshot = audit.read(run / 'snapshot.json')
    for folder in SOURCES:
        for route, entry in audit.read(ROOT / 'reports' / folder / 'supplemental-discovery.json', {}).get('models', {}).items():
            snapshot['models'].setdefault(route, entry)
    for row in matrix['rows']:
        route = row['provider']+':'+row['requested_model']
        snapshot['models'].setdefault(route, {'provider': row['provider'], 'model': row['requested_model'],
            'metadata': {'pricing': row.get('declared_price')}, 'sources': row.get('provenance', [])})
    audit.atomic(run / 'snapshot.json', snapshot)
    if provider == 'openrouter' and cfg and cfg.api_key:
        funding = {'at': audit.now(), 'endpoint': 'https://openrouter.ai/api/v1/credits'}
        with httpx.Client(timeout=20, trust_env=False) as client:
            response = client.get(funding['endpoint'], headers=audit.headers(provider, cfg))
        funding['http_status'] = response.status_code
        if response.status_code == 200:
            balance = response.json().get('data', {})
            if type(balance.get('total_credits')) in (int, float) and type(balance.get('total_usage')) in (int, float):
                funding['remaining_credits_usd'] = balance['total_credits']-balance['total_usage']
        audit.atomic(ROOT / '.cavren/audit-private' / run.name / 'openrouter-funding.json', funding)
        public_funding = {key: value for key, value in funding.items() if key != 'remaining_credits_usd'}
        public_funding['positive_remaining_balance'] = funding.get('remaining_credits_usd', 0) > 0 if 'remaining_credits_usd' in funding else None
        public_funding['numeric_values_exported'] = False
        audit.atomic(run / 'openrouter-funding-current.json', public_funding)
        for row in matrix['rows']:
            if row['provider'] != provider: continue
            if funding.get('remaining_credits_usd', 1) <= 0 and not audit.declared_zero_price(row.get('declared_price') or {}):
                row.update(blocker=row.get('blocker') or 'verified_openrouter_paid_balance_absent',
                           funding_evidence='openrouter-funding-current.json',
                           pending='Current credits endpoint verifies no positive paid balance; nonzero/unknown-price inference not submitted. This row remains NOT TESTED.')
            elif funding.get('remaining_credits_usd', 0) > 0 and row.get('blocker') == 'verified_openrouter_paid_balance_absent':
                row['blocker'] = None
    for row in matrix['rows']:
        if row['provider'] != provider: continue
        model, operation = row['requested_model'], row['operation']
        if provider == 'gemini' and operation.startswith('agent_') and row.get('prior_evidence', {}).get('native_called'):
            row.update(blocker='previous_agent_session_ended_unresolved',
                       pending='Previous scoped agent session was terminated/cleaned up. Preserve incomplete tool/vision evidence; do not launch a duplicate autonomous job.')
        if provider == 'gemini' and operation == 'batch' and model == 'gemini-nano-banana-2.1':
            row.update(blocker=None, batch_modality='image', required_samples=2,
                       contract_source='https://ai.google.dev/gemini-api/docs/batch-api')
        if provider == 'groq' and operation == 'audio_translation' and model.endswith('turbo'):
            row.update(blocker='native_translation_not_supported', pending='Whisper Turbo does not support translations per official speech-to-text documentation.')
        if provider == 'groq' and operation == 'speech' and not row.get('fresh_prerequisite_check'):
            row.update(blocker='model_terms_required', pending='Prior API response explicitly requires organization admin terms acceptance; no terms accepted by this audit.')
        if provider == 'groq' and model == 'allam-2-7b' and operation == 'json':
            row.update(blocker='native_json_schema_not_supported', pending='Prior native HTTP 400 explicitly rejects json_schema. Generic JSON prompting is a different operation.')
        if provider == 'cohere' and operation == 'image_embeddings' and 'v3.0-image' in model:
            row.update(blocker='native_image_embeddings_not_supported', pending='Previous native API resolves this alias to a model explicitly rejecting image embeddings.')
        if provider == 'cohere' and operation == 'json':
            previous = audit.read(ROOT / 'reports' / SOURCES[0] / 'results.json')['records'].get(row['key'], {})
            if any('response_format is not supported' in s.get('provider_error', '') for s in previous.get('samples', [])):
                row.update(blocker='native_response_format_not_supported',
                           pending='Previous HTTP 400 explicitly rejects response_format for this exact model. No identical unsupported request repeated.')
        if provider == 'mistral' and operation == 'classification':
            row.update(endpoint='https://api.mistral.ai/v1/classifications',
                       contract_source='https://docs.mistral.ai/api/endpoint/classifiers')
        if provider == 'nvidia' and model in ['meta/llama-guard-4-12b', 'nvidia/llama-3.1-nemoguard-8b-content-safety'] and operation in ['text', 'code', 'documents']:
            row.update(blocker='safety_classifier_not_general_completion',
                       pending='Official model card defines safety classification, not general text/code/document generation. Canonical moderation_chat operation is tested separately.')
        if provider == 'aihorde':
            advertised = next((entry for entry in snapshot['catalogs'].get(provider, []) if (entry.get('name') or entry.get('id')) == model), {})
            if type(advertised.get('count')) is int and advertised['count'] == 0:
                row.update(blocker='no_workers_in_current_official_status',
                           pending='Current official model status explicitly reports count=0 workers. No generation submitted; availability may change.',
                           availability_evidence='snapshot.json#catalogs.aihorde')
    if provider == 'nvidia':
        model = 'nvidia/llama-3.1-nemoguard-8b-content-safety'; key = 'nvidia:'+model+'::moderation_chat'
        if not any(row['key'] == key for row in matrix['rows']):
            matrix['rows'].append({'key': key, 'provider': 'nvidia', 'requested_model': model,
                'operation': 'moderation_chat', 'endpoint': audit.endpoint('nvidia', model, 'moderation_chat'),
                'contract_source': 'https://build.nvidia.com/nvidia/llama-3_1-nemoguard-8b-content-safety/modelcard',
                'provenance': ['official_native_safety_classifier_contract_correction'],
                'criterion': 'Known harmless message must receive native safe label; no classification by nonempty output alone.',
                'required_samples': 1, 'blocker': None, 'status': 'not_tested', 'pending': 'Awaiting native classifier probe.',
                'declared_price': None, 'benchmark': 'not_reassessed'})
    # Carry forward observed positive costs; do not silently reset the small
    # non-media audit budget on continuation. This is not an invoice bound.
    historical_positive = 0.0
    seen_samples = set()
    for source in SOURCES:
        history = audit.read(ROOT / 'reports' / source / 'results.json')['records']
        for key, record in history.items():
            for sample in record.get('samples', []):
                fingerprint = (key, sample.get('at'), sample.get('sample'), sample.get('request_sha256'))
                if fingerprint in seen_samples: continue
                seen_samples.add(fingerprint)
                historical_positive += max(sample.get('reported_cost_usd') or 0, 0)
    matrix['budget'].update(max_positive_reported_usd=max(0, .5-historical_positive),
                            prior_positive_reported_usd=historical_positive)
    if provider == 'aihorde':
        concurrency = audit.read(run / 'horde-concurrency-current.json', {})
        parallel = 2 if concurrency.get('http_status') == 200 and type(concurrency.get('concurrency')) is int and concurrency['concurrency'] >= 4 else 1
        matrix['budget']['provider_concurrency_overrides'] = {'aihorde': parallel}
        matrix['budget']['community_accounting'] = ('Native kudos unit is tracked separately from unknown USD billing. Two fixed samples per operation, '
            'one image at 256x256/eight steps or 128 output text tokens, at most two simultaneous requests within verified account concurrency, '
            'thirty-second queue window and cancellation. Missing USD price is not zero.')
    audit.atomic(run / 'matrix.json', matrix)
    # Ask for a call. The harness itself never executes it. The former wording
    # told models not to call the tool, invalidating that comparison.
    audit.PROMPTS['tools'] = ['Emita uma chamada da função registrar com cidade Lima e quantidade 7.']
    audit.request_body = corrected_request_body
    audit.extract = corrected_extract
    audit.probe = corrected_probe
    audit.evaluate = corrected_evaluate
    audit.image_probe = corrected_image_probe
    audit.atomic(run / 'order.json', order)
    # Bulk-account verified blockers once. Saving a growing 17k-row journal for
    # every unchanged blocker would add needless disk writes, not evidence.
    journal = audit.read(run / 'results.json', {'started_at': audit.now(), 'records': {}, 'control': {}})
    for row in matrix['rows']:
        if row['provider'] != provider or not row.get('blocker'): continue
        journal['records'].setdefault(row['key'], {'samples': [], 'status': 'not_tested',
            'blocker': row['blocker'], 'pending': row.get('pending') or 'Native contract or prerequisite remains unresolved; no request submitted.',
            'terminal': True})
    audit.atomic(run / 'results.json', journal)
    execute_checkpointed(run, provider, seconds)
    matrix = audit.read(run / 'matrix.json'); journal = audit.read(run / 'results.json')
    rows = [r for r in matrix['rows'] if r['provider'] == provider]
    unfinished = [r['key'] for r in rows if not journal['records'].get(r['key'], {}).get('terminal')]
    stage.update(status='reconciled' if not unfinished else 'window_ended_with_pending',
                 updated_at=audit.now(), operations=len(rows), unfinished=len(unfinished))
    audit.atomic(run / 'order.json', order)
    export_report(run)
    print(provider, stage, flush=True)


def export_report(run):
    import_additional_history(run)
    audit.atomic(run / 'results.json', merge_provider_journals(run))
    with contextlib.redirect_stdout(io.StringIO()): audit.report(run)
    data = audit.read(run / 'complete.json'); summary = data['summary']
    history = audit.read(run / 'historical-coverage.json')
    journal = audit.read(run / 'results.json', {'records': {}})
    samples = [s for record in journal['records'].values() for s in record.get('samples', [])]
    transport_errors = {'ReadError', 'WriteError', 'ConnectError', 'RemoteProtocolError', 'LocalProtocolError',
                        'PoolTimeout', 'ConnectTimeout', 'WriteTimeout', 'ProxyError'}
    for row in data['rows']:
        if row['status'] == 'failed' and any(code in transport_errors for code in row.get('sample_results', [])):
            row.update(status='inconclusive', pending='Transport interruption; output not validated. This is not proof of model incapability.')
    summary['by_status'] = dict(Counter(row['status'] for row in data['rows']))
    summary['by_provider'] = {provider: dict(Counter(row['status'] for row in data['rows'] if row['provider'] == provider))
                              for provider in {row['provider'] for row in data['rows']}}
    summary.update(routes=len({row['provider']+':'+row['requested_model'] for row in data['rows']}),
                   historical_universe_routes=len({key.split('::')[0] for key in history}),
                   auxiliary_real_calls=sum(s.get('auxiliary_call_count', 0) for s in samples),
                   fixture_generation_calls_new=0,
                   scope='Remaining uncalled/inconclusive operations, plus new catalogue discoveries. Historical denials and successes are not repeated.',
                   provider_stages=audit.read(run / 'order.json')['stages'],
                   valid_with_new_inference_rows=sum(row['status'] == 'valid' and row.get('native_real_call', False) for row in data['rows']),
                   valid_existing_job_polling_rows=sum(row['status'] == 'valid' and not row.get('native_real_call', False) for row in data['rows']),
                   all_rows_terminal=all(journal['records'].get(r['key'], {}).get('terminal', False) for r in data['rows']))
    for row in data['rows']:
        previous = history.get(row['key'], {})
        resolved = set(row.get('resolved_models', []))
        for sample in journal['records'].get(row['key'], {}).get('samples', []):
            resolved.update(value for value in sample.get('resolved_models', []) if isinstance(value, str))
        row['resolved_models'] = sorted(resolved)
        row['historical_native_call'] = previous.get('native_called', False)
        row['historical_status'] = previous.get('status')
        row['historical_evidence'] = previous.get('source')
        row['auxiliary_or_precondition_called'] = any(s.get('auxiliary_call_count', 0) for s in journal['records'].get(row['key'], {}).get('samples', []))
    audit.atomic(run / 'complete.json', data); audit.atomic(run / 'summary.json', summary)
    columns = sorted({key for row in data['rows'] for key in row})
    with (run / 'complete.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader()
        for row in data['rows']:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value for key, value in row.items()})
    current = {row['key']: row for row in data['rows']}
    with (run / 'coverage.csv').open('w', newline='') as stream:
        columns = ['provider', 'model', 'operation', 'historical_status', 'historical_native_call', 'historical_source', 'continuation_status', 'new_native_call', 'blocker', 'evidence']
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader()
        for key in sorted(set(history) | set(current)):
            route, operation = key.rsplit('::', 1); provider, model = route.split(':', 1)
            old = history.get(key, {}); new = current.get(key, {})
            writer.writerow({'provider': provider, 'model': model, 'operation': operation,
                'historical_status': old.get('status'), 'historical_native_call': old.get('native_called', False),
                'historical_source': old.get('source'), 'continuation_status': new.get('status', 'historical_result_retained'),
                'new_native_call': new.get('native_real_call', False), 'blocker': new.get('blocker', old.get('blocker')),
                'evidence': 'complete.json#'+key if new else old.get('evidence_file', '../'+old.get('source', '')+'/results.json')+'#'+key})
    lines = ['# Auren — continuação ordenada dos testes restantes', '',
        'Rodada iniciada em '+summary['snapshot_at']+'. Atualizada em '+summary['reported_at']+'.', '',
        '**Não foram todos testados.** Operações sem chamada permanecem identificadas no CSV/JSON.', '',
        'Ordem obrigatória: Gemini → Groq → Z.ai → Ollama Cloud → Cohere → Mistral. Outros provedores somente depois.', '',
        'Esta rodada retoma operações sem chamada ou inconclusivas e consulta novamente os catálogos. Sucessos e recusas históricos, incluindo as rodadas posteriores de visão e imagem de 14/10, ficam separados em `coverage.csv`; não são apresentados como chamadas novas.', '',
        '## Etapas', '', '| Provedor | Estado | Operações restantes |', '|---|---|---:|']
    stages = summary['provider_stages']
    lines.extend('| '+provider+' | '+stages.get(provider, {}).get('status', 'aguardando sua vez')+' | '+str(stages.get(provider, {}).get('operations', ''))+' |' for provider in ORDER)
    lines += ['', '## Contagem desta continuação', '',
        '- '+str(summary['operations'])+' combinações de provedor/modelo/operação na matriz de pendências.',
        '- '+str(summary['real_attempts'])+' tentativas principais novas; '+str(summary['auxiliary_real_calls'])+' chamadas auxiliares/precondições novas.',
        '- Estados: '+json.dumps(summary['by_status'], ensure_ascii=False)+'.',
        '- Custo positivo retornado: US$ '+str(summary['positive_reported_usd'])+'. Custo desconhecido em '+str(summary['unknown_cost_attempts'])+' tentativas principais. Ausência de preço não significa zero.', '',
        '## Contratos e limites', '',
        'A ambiguidade do pedido de ferramentas foi corrigida: o modelo deve emitir a chamada, e o harness não executa funções. Na Z.ai/GLM-4.5, o teste curto usa thinking.type=disabled, conforme o contrato oficial. Classificação Mistral usa /v1/classifications, em vez de chat. Llama Guard e NemoGuard são classificadores; não recebem provas de programação. LLaVA usa pixels no campo image; MeloTTS usa prompt e MP3. PaliGemma exige image_url como string. AI Horde texto usa o contrato assíncrono de prompt bruto, com limite de 128 tokens e contexto de 1024, sem crescimento automático.', '',
        'Recusas explícitas de recurso não suportado, termos pendentes e operações de treinamento permanecem como impedimentos. Deep Research não é reenviado: a autorização de um planejamento por rota já foi usada. Jobs assíncronos antigos não são duplicados automaticamente. Conferências finais de pedidos síncronos interrompidos exigem revisão do tempo, ausência de ID assíncrono e limite de saída; ficam identificadas em final-followups.json. O custo antigo incerto permanece separado.', '',
        'Limites herdados de imagem (US$ 20 total, US$ 0,50/chamada) e vídeo (US$ 40 total, US$ 2/chamada) não são reiniciados. A reserva anterior de imagem é US$ 0,78. Custos positivos anteriores são descontados do limite técnico do ensaio; esse controle e o teto de tokens não garantem uma fatura quando o provedor não retorna preço. Há ainda limite de 100 chamadas aceitas com custo desconhecido por provedor nesta continuação.', '',
        'Nenhum dado pessoal é enviado. Fixtures são sintéticas ou públicas e herdadas, sem novas gerações para construí-las. Não se comprou crédito, aceitou termos, alterou faturamento, promoveu modelos ao automático, modificou a interface ou publicou esta rodada no GitHub.', '',
        'AI Horde informa concorrência de 30 para esta conta; o ensaio usa no máximo duas tarefas simultâneas, com filas disjuntas por chave e salvamento atômico. As demais etapas usam uma tarefa por provedor. Imagens eventualmente entregues na resposta de cancelamento são decodificadas e contabilizadas; não são descartadas nem aprovadas apenas pelo HTTP 200. Kudos retornados são registrados na unidade nativa e não convertidos em dólares.', '',
        '## Evidências e retomada', '',
        '`complete.csv`/`complete.json`: matriz das pendências e tentativas desta rodada. `coverage.csv`: reconciliação com todo o universo histórico. `results.json`: cada tentativa atômica. `order.json`: sequência e conclusão das etapas. `historical-coverage.json`: referências dos resultados anteriores.', '',
        'Retome com scripts/auren_remaining_probe.py provider --provider NOME --run '+str(run)+'; etapas reconciliadas não repetem chamadas. O runner impede avançar enquanto o provedor anterior tiver operações não contabilizadas.', '',
        'Benchmarks e ordem dos perfis não foram reavaliados nem alterados. Aprovação de uma operação curta não aprova todo o modelo, seu contexto máximo ou suas cotas.', '',
        'Fontes primárias: [Gemini Batch](https://ai.google.dev/gemini-api/docs/batch-api), [Gemini cache](https://ai.google.dev/gemini-api/docs/caching), [Groq Batch](https://console.groq.com/docs/batch), [Groq voz](https://console.groq.com/docs/text-to-speech), [Z.ai GLM-4.5](https://docs.z.ai/guides/llm/glm-4.5), [Ollama Cloud](https://docs.ollama.com/cloud), [Cohere Chat](https://docs.cohere.com/reference/chat), [Mistral classificadores](https://docs.mistral.ai/api/endpoint/classifiers).']
    (run / 'REPORT.md').write_text('\n'.join(lines)+'\n')
    print('Remaining report:', summary['real_attempts'], 'new attempts;', summary['by_status'], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'provider', 'report'])
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--provider', choices=ORDER)
    parser.add_argument('--max-seconds', type=int, default=1800)
    args = parser.parse_args()
    if args.action == 'prepare': prepare(args.run)
    elif args.action == 'provider': execute_provider(args.run, args.provider, args.max_seconds)
    else: export_report(args.run)


if __name__ == '__main__': main()
