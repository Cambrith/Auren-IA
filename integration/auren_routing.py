"""Shortlist by task, published benchmarks and proven application contracts.

Scores guide this product policy; they are not a universal ranking or evidence
of deployment quality. Account, task and modality checks still gate each route.
See reports/AUREN-SELECAO-MODELOS-2026-10-14.md.
"""
GEMINI = 'gemini:gemini-3.8-flash'
GEMINI_LITE = 'gemini:gemini-3.5-flash-lite'
QWEN = 'groq:qwen/qwen3.8-27b'
GPT120 = 'groq:openai/gpt-oss-120b'
GPT20 = 'groq:openai/gpt-oss-20b'
KIMI = 'nvidia:moonshotai/kimi-k3'
GLM = 'nvidia:z-ai/glm-5.3'
COMMAND = 'cohere:command-a-plus-05-2026'
QWEN_CF = 'cloudflare:@cf/qwen/qwen3.8-27b'

MODE_ROUTES = {
    'ether': (QWEN, GEMINI, KIMI, GPT120, GEMINI_LITE, COMMAND, QWEN_CF),
    'impeto': (QWEN, GPT20, GEMINI_LITE, GEMINI, GPT120, QWEN_CF),
    'insight': (GEMINI, KIMI, GPT120, GLM, COMMAND, QWEN, GEMINI_LITE, QWEN_CF),
    'arquiteto': (GEMINI, KIMI, GLM, QWEN, GPT120, GEMINI_LITE, QWEN_CF),
}

# Distinct priorities for the existing task profiles; no new public mode IDs.
TASK_ROUTES = {
    'code': {
        'ether': (GEMINI, QWEN, KIMI, GPT120, GLM, QWEN_CF),
        'impeto': (QWEN, GPT20, GEMINI, GPT120, QWEN_CF),
        'insight': (GEMINI, KIMI, GLM, QWEN, GPT120, QWEN_CF),
        'arquiteto': (GEMINI, KIMI, GLM, QWEN, GPT120, QWEN_CF),
    },
    'documents': {
        'ether': (GEMINI, KIMI, GPT120, COMMAND, QWEN, QWEN_CF),
        'impeto': (QWEN, GPT20, GEMINI, GPT120, QWEN_CF),
        'insight': (GEMINI, KIMI, GPT120, COMMAND, QWEN, QWEN_CF),
        'arquiteto': (GEMINI, KIMI, GPT120, COMMAND, QWEN, QWEN_CF),
    },
    'research': {
        'ether': (GEMINI, KIMI, COMMAND, GPT120, QWEN, QWEN_CF),
        'impeto': (QWEN, GPT20, GEMINI, COMMAND, GPT120),
        'insight': (GEMINI, KIMI, COMMAND, GPT120, QWEN, QWEN_CF),
        'arquiteto': (GEMINI, KIMI, COMMAND, GPT120, QWEN, QWEN_CF),
    },
}

def effort_for(route, mode):
    """Documented Groq efforts; Qwen Éter high is an explicit product preference."""
    if route==QWEN:
        return 'none' if mode=='impeto' else 'high'
    if route in (GPT120,GPT20):
        return {'ether':'medium','impeto':'low','insight':'high','arquiteto':'high'}.get(mode,'medium')
    return None


def ordered_models(task, mode, required=()):
    """No paid/unverified alias is promoted by a benchmark or model name."""
    from integration.auren_tasks import models_for
    allowed = set(models_for(task))
    if required:
        from integration.auren_media import routes as media_routes
        # Media checks prove input grounding; ordinary text/category evidence
        # and the existing cost policy still gate execution.
        allowed.update(models_for('chat'))
        return ['cavren:' + route for route in media_routes(required, task, mode)
                if 'cavren:' + route in allowed]
    preferences = TASK_ROUTES.get(task, MODE_ROUTES)
    routes = ['cavren:' + route for route in preferences.get(mode, preferences['ether'])]
    if set(required).intersection(('pdf','audio','video')):
        # Current native probes pass on Lite; the old 3.6 path is unavailable.
        routes.append('cavren:' + GEMINI_LITE)
    elif task in TASK_ROUTES:
        routes.append('cavren:' + GEMINI_LITE)
    return [route for route in routes if route in allowed]
