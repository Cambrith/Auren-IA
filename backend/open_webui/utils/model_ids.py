def strip_provider_model_prefix(model_id: str, prefix_id: str | None) -> str:
    if prefix_id and model_id.startswith(f'{prefix_id}.'):
        return model_id[len(f'{prefix_id}.') :]
    return model_id


PROVIDER_LABELS = {
    'api.openai.com': 'OpenAI',
    'generativelanguage.googleapis.com': 'Gemini',
    'api.groq.com': 'Groq',
    'openrouter.ai': 'OpenRouter',
    'api.cerebras.ai': 'Cerebras',
    'integrate.api.nvidia.com': 'NVIDIA',
    'api.cohere.ai': 'Cohere',
    'api.cohere.com': 'Cohere',
    'router.huggingface.co': 'Hugging Face',
    'api.cloudflare.com': 'Cloudflare',
    'api.anthropic.com': 'Anthropic',
    'api.deepseek.com': 'DeepSeek',
    'api.mistral.ai': 'Mistral',
    'api.x.ai': 'xAI',
    'api.fireworks.ai': 'Fireworks',
    'api.deepinfra.com': 'DeepInfra',
}


def provider_label(url: str, prefix_id: str | None) -> str:
    """Nome curto do provedor para exibir ao lado do modelo."""
    from urllib.parse import urlsplit

    try:
        host = urlsplit(url).hostname or ''
    except ValueError:
        host = ''
    return PROVIDER_LABELS.get(host) or (prefix_id or host or '').strip()


def display_model_name(raw_name: str, label: str) -> str:
    """Nome legível: sem 'models/' ou '@cf/' no começo e com o provedor no final."""
    name = (raw_name or '').strip()
    for lead in ('models/', '@cf/', '@hf/'):
        if name.startswith(lead):
            name = name[len(lead) :]
    if label and not name.lower().endswith(f'· {label}'.lower()):
        name = f'{name} · {label}'
    return name
