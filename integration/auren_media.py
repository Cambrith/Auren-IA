"""Operation-specific attachment routing, independent of the selected chat model.

These routes passed synthetic pixel/native-media checks on 2026-10-14.
Account, price, credentials and cooldown checks remain in auren_fallback.
Evidence: reports/auren-vision-candidates-2026-10-14 and Gemini/Groq r2.
"""

QWEN = 'groq:qwen/qwen3.8-27b'
GEMINI = 'gemini:gemini-3.5-flash-lite'
COHERE = 'cohere:command-a-vision-07-2025'
NVIDIA = 'nvidia:meta/llama-3.2-11b-vision-instruct'
CLOUDFLARE = 'cloudflare:@cf/qwen/qwen3.8-27b'
COHERE_PLUS = 'cohere:command-a-plus-05-2026'

TESTED_INPUTS = {
    QWEN: {'vision'}, GEMINI: {'vision', 'pdf', 'audio', 'video'},
    COHERE: {'vision'}, NVIDIA: {'vision'}, CLOUDFLARE: {'vision'}, COHERE_PLUS: {'vision'},
}
IMAGE_LIMITS = {QWEN: 3, COHERE: 20, NVIDIA: 1, GEMINI: 3600}
PART_CAPS = {'image_url': 'vision', 'input_video': 'video', 'video_url': 'video',
             'input_audio': 'audio', 'input_file': 'pdf', 'file': 'pdf'}


def requirements(messages):
    return {PART_CAPS[p['type']] for m in messages if isinstance(m.get('content'), list)
            for p in m['content'] if p.get('type') in PART_CAPS}


def compatible(info, messages):
    required = requirements(messages)
    caps = info.get('capabilities', {})
    if not all(caps.get(cap) for cap in required):
        return False
    native = required.intersection({'pdf', 'audio', 'video'})
    if native and not native <= TESTED_INPUTS.get(info.get('route_id'), set()):
        return False
    limit = IMAGE_LIMITS.get(info.get('route_id'))
    images = sum(p.get('type') == 'image_url' for m in messages
                 if isinstance(m.get('content'), list) for p in m['content'])
    return limit is None or images <= limit


def routes(required, task='chat', mode='ether'):
    required = set(required)
    if not required:
        return ()
    if required.intersection({'pdf', 'audio', 'video'}):
        order = (GEMINI,)
    elif task == 'documents':
        order = (COHERE, COHERE_PLUS, GEMINI, QWEN, NVIDIA, CLOUDFLARE)
    elif mode == 'impeto':
        order = (QWEN, NVIDIA, GEMINI, COHERE, COHERE_PLUS, CLOUDFLARE)
    elif mode in ('insight', 'arquiteto'):
        order = (QWEN, COHERE_PLUS, GEMINI, COHERE, NVIDIA, CLOUDFLARE)
    else:
        order = (QWEN, GEMINI, COHERE, COHERE_PLUS, NVIDIA, CLOUDFLARE)
    return tuple(route for route in order if required <= TESTED_INPUTS[route])


def describe(required):
    names = {'vision': 'imagem', 'pdf': 'PDF', 'audio': 'áudio', 'video': 'vídeo'}
    return ', '.join(names[cap] for cap in sorted(required) if cap in names)
