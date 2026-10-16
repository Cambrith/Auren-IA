"""Manual provider routes and native image generation, using local credentials."""

from dataclasses import replace
import base64
import json
import time

import httpx

from cavren.context_builder import build_generation_context, with_web_results, ContextBudget
from cavren.errors import CavrenError
from cavren.generation import GenerationEvent, GenerationKind
from cavren.gemini_native import GeminiNativeProvider, needs_native_gemini
from cavren.models import Message, ModelResponse, Usage
from cavren.prompt_adapter import GeminiPromptAdapter
from cavren.providers import ChatCompletionsProvider, http_error
from cavren.effort import EFFORTS
for _provider in ('cohere', 'nvidia', 'ollama', 'zai', 'openai', 'anthropic', 'deepseek', 'xai', 'huggingface','bedrock','cerebras','deepinfra','novita','fireworks'):
    EFFORTS.setdefault(_provider, ('default',))
from cavren.web_search import WebSearchService, DEFAULT_SEARCH_URL
from integration.lunvri_connections import connection_settings, cached_model


class PreparedChatProvider(ChatCompletionsProvider):
    """Current chat limits and model-specific Groq reasoning contracts."""
    def __init__(self, *args, free_only=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.free_only = free_only

    def _payload(self, messages, *, stream):
        payload = super()._payload(messages, stream=stream)
        if self.config.name == 'openrouter' and self.free_only:
            # Official server-side price cap, including provider fallback selection.
            payload['provider'] = {'max_price': {'prompt': 0, 'completion': 0, 'request': 0, 'image': 0}}
        if self.config.name in ('openai', 'groq'):
            payload['max_completion_tokens'] = payload.pop('max_tokens')
        if self.config.name == 'groq' and self.config.model in ('openai/gpt-oss-120b','openai/gpt-oss-20b'):
            # GPT-OSS does not use Qwen's reasoning_format contract.
            payload.pop('reasoning_format',None)
            payload['include_reasoning'] = False
        return payload


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def image_files(provider, payload):
    files, text = [], []
    if provider == 'gemini':
        for candidate in payload.get('candidates', []):
            for part in candidate.get('content', {}).get('parts', []):
                if part.get('text'):
                    text.append(part['text'])
                image = part.get('inlineData') or part.get('inline_data')
                if image and image.get('data'):
                    mime = image.get('mimeType', image.get('mime_type', 'image/png'))
                    files.append({'type': 'image', 'url': f'data:{mime};base64,{image["data"]}', 'name': 'Auren.png'})
    else:
        for image in payload.get('data', []):
            if image.get('b64_json'):
                mime = image.get('media_type', 'image/png')
                files.append({'type': 'image', 'url': f'data:{mime};base64,{image["b64_json"]}', 'name': 'Auren.png'})
    for file in files:
        mime, data = file['url'][5:].split(';base64,', 1)
        if mime not in ('image/png', 'image/jpeg', 'image/webp') or len(data) > 40_000_000:
            raise CavrenError('image', 'O provedor retornou uma imagem em formato não suportado.')
        base64.b64decode(data, validate=True)
        file['name'] = 'Auren.' + {'image/png':'png','image/jpeg':'jpg','image/webp':'webp'}[mime]
    if not files:
        raise CavrenError('image', 'O provedor não retornou uma imagem. Revise o pedido e os limites da conta.')
    return files, '\n'.join(text) or 'Imagem gerada.'


def generate_images(client, config, messages, prompt, *, progress=None, job=None):
    job = job or {}
    started_at = time.time()
    global_deadline = job.get('auren_deadline', time.monotonic() + 480)
    def remaining(limit):
        budget = global_deadline - time.monotonic()
        if budget <= 0:
            raise CavrenError('timeout', 'O prazo global de geração foi atingido.', retryable=True)
        return min(limit, budget)
    def report(description, **data):
        if progress:
            progress({'type': 'generation.image_status', 'description': config.model + ' · ' + config.name + ' · ' + description,
                      'generation_id': job.get('generation_id'), 'attempt_id': job.get('auren_attempt_id'),
                      'provider': config.name, 'effective_model': config.model, 'started_at':started_at, **data})
    report('Preparando geração.', state='preparing')
    if config.name == 'gemini':
        contents, systems = GeminiPromptAdapter().adapt(messages)
        body = {'contents': contents, 'generationConfig': {'responseModalities': ['TEXT', 'IMAGE']}}
        if systems:
            body['systemInstruction'] = {'parts': systems}
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{config.model}:generateContent'
        headers = {'x-goog-api-key': config.api_key}
    elif config.name == 'openrouter':
        body = {'model': config.model, 'prompt': prompt, 'n': 1}
        if not job.get('mode_options',{}).get('billing_confirmed'):
            body['provider'] = {'max_price': {'prompt':0,'completion':0,'request':0,'image':0}}
        references = [
            part
            for m in messages
            if m.role == 'user' and isinstance(m.content, list)
            for part in m.content
            if part.get('type') == 'image_url'
        ]
        if references:
            body['input_references'] = references
        url = 'https://openrouter.ai/api/v1/images'
        headers = {'Authorization': 'Bearer ' + config.api_key}
    elif config.name == 'aihorde':
        headers = {'apikey': config.api_key, 'Client-Agent': 'Auren:1.0:local'}
        from integration.auren_settings import preferences
        params = job.get('auren_image_preferences') or preferences()
        from integration.auren_images import profile_parameters
        image_params = profile_parameters(params, job.get('auren_image_profile', 'balanced'), job.get('auren_image_parameters'))
        response = client.post(config.base_url + '/generate/async', headers=headers,
                               json={'prompt': prompt, 'models': [config.model], 'params': image_params, 'r2': False, 'shared': False}, timeout=remaining(30))
        if response.status_code != 202:
            raise http_error(response.status_code, provider=config.name)
        request_id = response.json()['id']
        from uuid import UUID
        try:
            request_id = str(UUID(request_id))
        except (ValueError, TypeError):
            raise CavrenError('invalid_response', 'A fila de imagens retornou um identificador inválido.')
        finished = False
        last_status = None
        try:
            report('Pedido aceito; aguardando a fila.', state='queued', remote_id=request_id)
            deadline = min(global_deadline - 5, time.monotonic() + 240)
            while time.monotonic() < deadline:
                check = client.get(config.base_url + '/generate/check/' + request_id, headers=headers, timeout=remaining(20))
                if check.status_code != 200:
                    raise http_error(check.status_code, provider=config.name)
                status = check.json()
                fields = {k: status.get(k) for k in ('queue_position', 'wait_time', 'eligible_workers')}
                phase = 'processing' if status.get('processing', 0) else 'queued'
                snapshot = (phase, *fields.values())
                if not status.get('done') and snapshot != last_status:
                    def value(key, suffix=''):
                        raw = fields[key]
                        return str(raw) + suffix if type(raw) in (int, float) and raw >= 0 else 'indisponível'
                    report(('Processando' if phase == 'processing' else 'Na fila') +
                           ' · posição ' + value('queue_position') +
                           ' · espera estimada ' + value('wait_time', ' s') +
                           ' · trabalhadores elegíveis ' + value('eligible_workers'),
                           state=phase, remote_id=request_id, **fields)
                    last_status = snapshot
                if status.get('faulted'):
                    raise CavrenError('unavailable', 'A fila de geração de imagens falhou.', retryable=True)
                if status.get('done'):
                    result = client.get(config.base_url + '/generate/status/' + request_id, headers=headers, timeout=remaining(20))
                    if result.status_code != 200:
                        raise http_error(result.status_code, provider=config.name)
                    finished = True
                    generations=result.json().get('generations', [])
                    usable=[image for image in generations if image.get('img') and not image.get('censored')]
                    if not usable:
                        if any(image.get('censored') for image in generations):
                            raise CavrenError('image_censored','O provedor concluiu o pedido, mas reteve a imagem pelo filtro de conteúdo. Nenhuma imagem foi entregue.')
                        raise CavrenError('invalid_response','O provedor declarou conclusão, mas não retornou uma imagem utilizável.',retryable=True)
                    report('Geração concluída.', state='completed', remote_id=request_id, done=True)
                    return image_files('aihorde', {'data': [{'b64_json': image['img'], 'media_type': 'image/webp'} for image in usable]})
                time.sleep(max(0, min(3, deadline - time.monotonic())))
            raise CavrenError('timeout', 'A fila de imagens excedeu o tempo de espera.', retryable=True)
        finally:
            if not finished:
                try:
                    client.delete(config.base_url + '/generate/status/' + request_id, headers=headers, timeout=5)
                except httpx.HTTPError:
                    pass
    else:
        raise CavrenError('image', 'Este provedor não tem geração de imagens integrada.')
    response = client.post(url, headers=headers, json=body, timeout=remaining(300))
    if response.status_code != 200:
        raise http_error(response.status_code, provider=config.name)
    result = image_files(config.name, response.json())
    report('Geração concluída.', state='completed', done=True)
    return result


def run(job, normalize_messages, *, output=emit):
    emit = output
    if job.get('auren_task') == 'speech':
        from integration.auren_speech import run as speak
        return speak(job, normalize_messages, output=output)
    if job.get('auren_task') == 'transcribe':
        from integration.auren_transcribe import run as transcribe
        return transcribe(job, normalize_messages, output=output)
    id = job['generation_id']
    model = cached_model('cavren:' + job['mode_options']['manual_route'])
    if not model:
        raise CavrenError('model', 'Atualize o catálogo e selecione um modelo disponível.')
    info = model['cavren']
    if info['price_kind'] != 'free' and not job['mode_options'].get('billing_confirmed'):
        raise CavrenError('cost', 'Confirme o possível custo deste modelo antes de usá-lo.')
    settings = connection_settings()
    config = replace(settings.providers[info['provider']], model=info['model_id'])
    if not config.api_key:
        raise CavrenError('missing_key', 'Configure a conexão do provedor.')
    settings = replace(
        settings,
        retries=0,
        max_tokens=min(int(job.get('max_tokens') or settings.max_tokens), int(info.get('output_limit') or 4096)),
    )
    if job.get('lunvri_image_generation'):
        from integration.auren_images import validate
        validate(job, info)
    messages = [Message(m['role'], m['content']) for m in job['messages']]
    from cavren.modes import routes_for
    route = None if job.get('lunvri_image_generation') else next((r for r in routes_for(job['mode_id']) if r.route_id == info['route_id']), None)
    from integration.auren_routing import effort_for
    curated_effort = effort_for(info['route_id'],job['mode_id'])
    if curated_effort is not None:
        settings = replace(settings,reasoning_effort=curated_effort)
    elif route:
        effort = route.effort if route.effort in route.model.reasoning_levels else 'default'
        settings = replace(settings, reasoning_effort=effort)
    context = None if job.get('lunvri_image_generation') else job.get('auren_context') or build_generation_context(job, messages, max_output_tokens=settings.max_tokens, settings=settings, budget=ContextBudget(int(info.get('context_window') or 32000) - settings.max_tokens - 4096))
    sequence = 0
    with httpx.Client(trust_env=False) as client:
        if not job.get('lunvri_image_generation') and (job['mode_options'].get('web_search') or job.get('auren_task')=='research') and not job.get('auren_context'):
            sequence += 1
            emit(GenerationEvent(GenerationKind.SEARCHING, id, sequence=sequence).to_dict())
            import os

            service = WebSearchService(client, os.environ.get('CAVREN_SEARXNG_URL', DEFAULT_SEARCH_URL))
            queries = [job['prompt']]
            from integration.auren_research import model_plan, accepts
            domains = ()
            if job.get('auren_task') == 'research':
                emit({'type':'generation.task_status','description':'Planejando consultas de pesquisa', 'generation_id':id})
                queries, domains, agent_planned = model_plan(client, config, job['prompt'], job.get('auren_deadline',time.monotonic()+480))
                emit({'type':'generation.task_status','description':'Consultas escolhidas pelo modelo' if agent_planned else 'Consultas do plano inicial', 'generation_id':id})
            sources = []
            seen = set()
            for index, query in enumerate(queries):
                if time.monotonic() >= job.get('auren_deadline', float('inf')):
                    raise CavrenError('timeout', 'O prazo da pesquisa foi atingido.')
                emit({'type':'generation.task_status','description':f'Pesquisando etapa {index+1}/{len(queries)}', 'generation_id':id})
                try:
                    result = service.search(query)
                except CavrenError as error:
                    if error.code not in ('search_empty','search_irrelevant'):raise
                    emit({'type':'generation.task_status','description':f'Consulta {index+1}: sem fontes utilizáveis', 'generation_id':id})
                    continue
                for source in result.sources:
                    if accepts(source, domains) and source['url'] not in seen and len(sources) < 12:
                        sources.append(source); seen.add(source['url'])
            if not sources:raise CavrenError('search_empty','Não foram encontradas fontes utilizáveis para este pedido. Nenhuma resposta pesquisada foi produzida.')
            context = with_web_results(context, tuple(sources), query=job['prompt'])
            sequence += 1
            emit(GenerationEvent(GenerationKind.SOURCES, id, sequence=sequence, sources=tuple(sources)).to_dict())
        job['auren_context'] = context
        if job.get('lunvri_image_generation'):
            if not info['capabilities']['image_generation']:
                raise CavrenError('image', 'O modelo selecionado não gera imagens.')
            files, text = generate_images(client, config, normalize_messages(messages), job['prompt'], progress=emit, job=job)
            emit({'type': 'generation.files', 'files': files})
            sequence += 1
            emit(GenerationEvent(GenerationKind.DELTA, id, sequence=sequence, text=text).to_dict())
            response = ModelResponse(
                text, config.name, config.model, Usage(), 'stop', id, 0, public_mode=job['mode_id']
            )
            emit(GenerationEvent(GenerationKind.COMPLETED, id, sequence=sequence + 1, response=response).to_dict())
        else:
            messages = normalize_messages(context.messages)
            provider = (
                GeminiNativeProvider(config, settings, client)
                if config.name == 'gemini' and (needs_native_gemini(messages) or any(
                    isinstance(m.content, list) and any(p.get('type') == 'image_url' for p in m.content) for m in messages))
                else PreparedChatProvider(config, settings, client, reasoning_hidden=bool(route and route.reasoning_hidden), free_only=info['price_kind']=='free')
            )
            for item in provider.stream(messages, trace_id=id, generation_id=id):
                sequence += 1
                emit(replace(item, sequence=sequence).to_dict())
    return 0
