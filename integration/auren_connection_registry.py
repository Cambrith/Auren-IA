"""Connection metadata only. No credentials, model routing or account data."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Field:
    id: str
    label: str
    vault: str
    required: bool = True

@dataclass(frozen=True)
class Connection:
    name: str
    key: str
    docs: str
    endpoint: str = ''
    auth: str = 'bearer'
    kind: str = 'api'
    extra: tuple[Field, ...] = ()

CONNECTIONS = {
 'aihorde': Connection('AI Horde','AI_HORDE_API_KEY','https://aihorde.net/api/','https://aihorde.net/api/v2/find_user','apikey'),
 'bedrock': Connection('Amazon Bedrock','AWS_BEARER_TOKEN_BEDROCK','https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html',extra=(Field('region','Região AWS da chave','AWS_REGION'),Field('base_url','Base URL AWS','AUREN_BEDROCK_BASE_URL',False))),
 'anthropic': Connection('Anthropic API (Claude)','ANTHROPIC_API_KEY','https://platform.claude.com/docs/en/api/models/list','https://api.anthropic.com/v1/models','anthropic'),
 'assemblyai': Connection('AssemblyAI API','ASSEMBLYAI_API_KEY','https://www.assemblyai.com/docs/pre-recorded-audio/api-reference/transcripts/list','https://api.assemblyai.com/v2/transcript?limit=1','raw'),
 'canva': Connection('Canva Connect','CANVA_CLIENT_SECRET','https://www.canva.dev/docs/apps/rest-apis/authentication/','https://api.canva.com/rest/v1/users/me','oauth','oauth',
                    (Field('client_id','Client ID','CANVA_CLIENT_ID'),Field('redirect_uri','Redirect URL cadastrada no Canva','CANVA_REDIRECT_URI'))),
 'cartesia': Connection('Cartesia API','CARTESIA_API_KEY','https://docs.cartesia.ai/api-reference/voices/list','https://api.cartesia.ai/voices?limit=1','cartesia'),
 'cerebras': Connection('Cerebras Inference API','CEREBRAS_API_KEY','https://inference-docs.cerebras.ai/api-reference/models/list-models','https://api.cerebras.ai/v1/models'),
 'cloudflare': Connection('Cloudflare Workers AI','CLOUDFLARE_API_TOKEN','https://developers.cloudflare.com/workers-ai/get-started/rest-api/','https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/models/search?per_page=1',extra=(Field('account_id','Identificador da conta Cloudflare','CLOUDFLARE_ACCOUNT_ID'),)),
 'cohere': Connection('Cohere API','COHERE_API_KEY','https://docs.cohere.com/v2/reference/list-models','https://api.cohere.com/v1/models?page_size=1'),
 'deepgram': Connection('Deepgram API','DEEPGRAM_API_KEY','https://developers.deepgram.com/reference/manage/projects/list','https://api.deepgram.com/v1/projects','token'),
 'deepinfra': Connection('DeepInfra API','DEEPINFRA_API_KEY','https://deepinfra.com/docs/openai_api','https://api.deepinfra.com/v1/openai/models'),
 'deepseek': Connection('DeepSeek API','DEEPSEEK_API_KEY','https://api-docs.deepseek.com/api/list-models','https://api.deepseek.com/models'),
 'elevenlabs': Connection('ElevenLabs API','ELEVENLABS_API_KEY','https://elevenlabs.io/docs/api-reference/user/get','https://api.elevenlabs.io/v1/user','xi-api-key'),
 'fal': Connection('fal API (fal.ai)','FAL_KEY','https://fal.ai/docs/platform-apis/v1/models','https://api.fal.ai/v1/models?limit=1','Key'),
 'fireworks': Connection('Fireworks AI API','FIREWORKS_API_KEY','https://docs.fireworks.ai/api-reference/list-models','https://api.fireworks.ai/inference/v1/models'),
 'gemini': Connection('Google Gemini API','GEMINI_API_KEY','https://ai.google.dev/api/models','https://generativelanguage.googleapis.com/v1beta/models?pageSize=1','x-goog-api-key'),
 'groq': Connection('GroqCloud API','GROQ_API_KEY','https://console.groq.com/docs/api-reference','https://api.groq.com/openai/v1/models'),
 'huggingface': Connection('Hugging Face Inference Providers','HUGGINGFACE_API_KEY','https://huggingface.co/docs/hub/api','https://huggingface.co/api/whoami-v2'),
 'hyperbolic': Connection('Hyperbolic API','HYPERBOLIC_API_KEY','https://www.hyperbolic.ai/docs/api-reference/balances/get-the-current-user-or-organization-accounts-balance','https://api.hyperbolic.ai/v2/customer/balance'),
 'mistral': Connection('Mistral AI API','MISTRAL_API_KEY','https://docs.mistral.ai/api/endpoint/models','https://api.mistral.ai/v1/models'),
 'nvidia': Connection('NVIDIA NIM API','NVIDIA_API_KEY','https://docs.api.nvidia.com/nim/reference/models-1','https://integrate.api.nvidia.com/v1/models'),
 'novita': Connection('Novita AI API','NOVITA_API_KEY','https://docs.novita.ai/api-reference/basic-get-user-balance','https://api.novita.ai/openapi/v1/billing/balance/detail'),
 'ollama': Connection('Ollama Cloud API','OLLAMA_API_KEY','https://docs.ollama.com/cloud','https://ollama.com/api/tags'),
 'openai': Connection('OpenAI API','OPENAI_API_KEY','https://developers.openai.com/api/reference/resources/models/methods/list','https://api.openai.com/v1/models'),
 'openrouter': Connection('OpenRouter API','OPENROUTER_API_KEY','https://openrouter.ai/docs/api-reference/authentication','https://openrouter.ai/api/v1/key'),
 'replicate': Connection('Replicate API','REPLICATE_API_TOKEN','https://replicate.com/docs/reference/http','https://api.replicate.com/v1/account'),
 'stability': Connection('Stability AI API','STABILITY_API_KEY','https://platform.stability.ai/docs/api-reference','https://api.stability.ai/v1/user/balance'),
 'voyage': Connection('Voyage AI API','VOYAGE_API_KEY','https://docs.voyageai.com/reference/embeddings-api','https://api.voyageai.com/v1/embeddings'),
 'xai': Connection('xAI API','XAI_API_KEY','https://docs.x.ai/developers/rest-api-reference/inference/other','https://api.x.ai/v1/api-key'),
 'zai': Connection('Z.ai API','ZAI_API_KEY','https://docs.z.ai/guides/overview/quick-start','https://api.z.ai/api/paas/v4/models'),
}
CONNECTION_NAMES = {id: spec.name for id, spec in CONNECTIONS.items()}
SERVICE_TYPES = {id:'Modelos de linguagem' for id in CONNECTIONS}
SERVICE_TYPES.update({'aihorde':'Geração de imagens comunitária','assemblyai':'Áudio: transcrição',
 'canva':'Design: integração OAuth 2.0','cartesia':'Áudio: voz e transcrição','deepgram':'Áudio: voz e transcrição',
 'elevenlabs':'Áudio: voz e transcrição','fal':'Imagens, áudio e vídeo','hyperbolic':'Infraestrutura e conta',
 'replicate':'Hospedagem de modelos e inferência','stability':'Geração de imagens','voyage':'Embeddings e reranking',
 'bedrock':'Catálogo regional de modelos AWS','huggingface':'Roteamento de provedores de inferência'})
PROVIDER_KEYS = {id: spec.key for id, spec in CONNECTIONS.items()}
VAULT_NAMES = {name for spec in CONNECTIONS.values() for name in (spec.key, *(f.vault for f in spec.extra))}
VAULT_NAMES |= {'CANVA_ACCESS_TOKEN', 'CANVA_REFRESH_TOKEN', 'CANVA_TOKEN_EXPIRES_AT'}


def fields(provider):
    spec = CONNECTIONS[provider]
    return [{'id':'key','label':'Client secret' if spec.kind == 'oauth' else 'Chave de API (Bearer)' if provider == 'bedrock' else 'Nova chave de API','required':True},
            *[{'id':f.id,'label':f.label,'required':f.required} for f in spec.extra]]
