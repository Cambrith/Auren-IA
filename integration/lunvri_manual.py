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
for _provider in ('cohere', 'nvidia', 'ollama', 'zai', 'openai', 'anthropic'):
    EFFORTS.setdefault(_provider, ('default',))
from cavren.web_search import WebSearchService, DEFAULT_SEARCH_URL
from integration.lunvri_connections import connection_settings, cached_model


class PreparedChatProvider(ChatCompletionsProvider):
    """OpenAI chat limit adapter; Anthropic uses its documented compatibility API."""
    def _payload(self, messages, *, stream):
        payload = super()._payload(messages, stream=stream)
        if self.config.name == 'openai':
            payload['max_completion_tokens'] = payload.pop('max_tokens')
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


def generate_images(client, config, messages, prompt, *, progress=None):
    if config.name == 'gemini':
        contents, systems = GeminiPromptAdapter().adapt(messages)
        body = {'contents': contents, 'generationConfig': {'responseModalities': ['TEXT', 'IMAGE']}}
        if systems:
            body['systemInstruction'] = {'parts': systems}
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{config.model}:generateContent'
        headers = {'x-goog-api-key': config.api_key}
    elif config.name == 'openrouter':
        body = {'model': config.model, 'prompt': prompt, 'n': 1}
        references = [
            part
            for m in messages
            if m.role == 'user' and isinstance(m.content, list)
            for part in m.content
            if part.get('type') == 'image_url'
        ]
        if references:
            body['input_references'] = references[-8:]
        url = 'https://openrouter.ai/api/v1/images'
        headers = {'Authorization': 'Bearer ' + config.api_key}
    elif config.name == 'aihorde':
        headers = {'apikey': config.api_key, 'Client-Agent': 'Auren:1.0:local'}
        from integration.auren_settings import preferences
        params = preferences()
        response = client.post(config.base_url + '/generate/async', headers=headers,
                               json={'prompt': prompt, 'models': [config.model], 'params': {'n': 1, 'width': params.get('image_width',512), 'height': params.get('image_height',512), 'steps': params.get('image_steps',20)}, 'r2': False, 'shared': False}, timeout=30)
        if response.status_code != 202:
            raise http_error(response.status_code, provider=config.name)
        request_id = response.json()['id']
        from uuid import UUID
        try:
            request_id = str(UUID(request_id))
        except (ValueError, TypeError):
            raise CavrenError('invalid_response', 'A fila de imagens retornou um identificador inválido.')
        if progress: progress({'type':'generation.image_status','description':'Pedido aceito; aguardando a fila de imagens.'})
        finished = False
        last_queue = None
        try:
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline:
                check = client.get(config.base_url + '/generate/check/' + request_id, headers=headers, timeout=20)
                if check.status_code != 200:
                    raise http_error(check.status_code, provider=config.name)
                status = check.json()
                queue = status.get('queue_position', 'a confirmar')
                if progress and not status.get('done') and queue != last_queue:
                    progress({'type':'generation.image_status','description':f'Na fila de imagens · posição {queue}'})
                    last_queue = queue
                if status.get('faulted'):
                    raise CavrenError('unavailable', 'A fila de geração de imagens falhou.', retryable=True)
                if status.get('done'):
                    result = client.get(config.base_url + '/generate/status/' + request_id, headers=headers, timeout=20)
                    if result.status_code != 200:
                        raise http_error(result.status_code, provider=config.name)
                    finished = True
                    if progress: progress({'type':'generation.image_status','description':'Geração de imagem concluída.','done':True})
                    return image_files('aihorde', {'data': [{'b64_json': image['img'], 'media_type': 'image/webp'} for image in result.json().get('generations', []) if image.get('img') and not image.get('censored')]})
                time.sleep(3)
            raise CavrenError('timeout', 'A fila de imagens excedeu o tempo de espera.', retryable=True)
        finally:
            if not finished:
                try:
                    client.delete(config.base_url + '/generate/status/' + request_id, headers=headers, timeout=5)
                except httpx.HTTPError:
                    pass
    else:
        raise CavrenError('image', 'Este provedor não tem geração de imagens integrada.')
    response = client.post(url, headers=headers, json=body, timeout=300)
    if response.status_code != 200:
        raise http_error(response.status_code, provider=config.name)
    return image_files(config.name, response.json())


def run(job, normalize_messages, *, output=emit):
    emit = output
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
    messages = [Message(m['role'], m['content']) for m in job['messages']]
    from cavren.modes import routes_for
    route = next((r for r in routes_for(job['mode_id']) if r.route_id == info['route_id']), None)
    if route:
        effort = route.effort if route.effort in route.model.reasoning_levels else 'default'
        settings = replace(settings, reasoning_effort=effort)
    context = job.get('auren_context') or build_generation_context(job, messages, max_output_tokens=settings.max_tokens, settings=settings, budget=ContextBudget(int(info.get('context_window') or 32000) - settings.max_tokens - 4096))
    sequence = 0
    with httpx.Client(trust_env=False) as client:
        if job['mode_options'].get('web_search') and not job.get('auren_context'):
            sequence += 1
            emit(GenerationEvent(GenerationKind.SEARCHING, id, sequence=sequence).to_dict())
            import os

            result = WebSearchService(client, os.environ.get('CAVREN_SEARXNG_URL', DEFAULT_SEARCH_URL)).search(
                job['prompt']
            )
            context = with_web_results(context, result.sources, query=result.query)
            sequence += 1
            emit(GenerationEvent(GenerationKind.SOURCES, id, sequence=sequence, sources=result.sources).to_dict())
        job['auren_context'] = context
        if job.get('lunvri_image_generation'):
            if not info['capabilities']['image_generation']:
                raise CavrenError('image', 'O modelo selecionado não gera imagens.')
            files, text = generate_images(client, config, normalize_messages(context.messages), job['prompt'], progress=emit)
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
                if config.name == 'gemini' and needs_native_gemini(messages)
                else PreparedChatProvider(config, settings, client, reasoning_hidden=bool(route and route.reasoning_hidden))
            )
            for item in provider.stream(messages, trace_id=id, generation_id=id):
                sequence += 1
                emit(replace(item, sequence=sequence).to_dict())
    return 0
