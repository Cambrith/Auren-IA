# Amazon Bedrock — São Paulo — 15/10/2026

Região: sa-east-1
Base URL configurada: https://bedrock-runtime.sa-east-1.amazonaws.com/openai/v1

A nova chave autenticou a consulta regional ListFoundationModels. O catálogo retornou 66 modelos com saída de texto. ListInferenceProfiles também respondeu 200 e retornou 30 perfis de sistema sanitizados. Essas consultas não invocaram modelos nem comprovaram permissão/saldo de inferência.

O endpoint runtime não implementa GET /models. O catálogo é consultado no control plane da mesma região. A seleção manual usa somente os IDs cuja compatibilidade Chat Completions + runtime foi confirmada na documentação; o bloqueio de custo existente permanece obrigatório. Modelos que exigem API nativa não são enviados como chat completions.

A documentação confirmou 42 entradas compatíveis com Chat Completions no runtime, 20 que requerem APIs nativas, 2 que exigem Mantle e 2 cuja compatibilidade não foi confirmada. A aplicação conserva 39 desses modelos no catálogo manual: as políticas preexistentes filtraram uma rota DeepSeek e duas rotas de salvaguarda, sem remover os 66 itens do inventário regional. Nenhuma geração ou alteração de faturamento foi realizada.

A alternativa documentada em São Paulo é https://bedrock-mantle.sa-east-1.api.aws/v1. Ela não foi selecionada nem usada para inferência. GPT 5.4 e GPT 5.5 aparecem como Mantle na tabela de endpoints consultada. GPT OSS funciona em Chat Completions no runtime; Responses para GPT OSS exige Mantle. Outras famílias, como Claude, exigem Converse/Invoke/Messages conforme o modelo.

## Catálogo e compatibilidade

| Modelo | ID retornado | Chat no runtime | Responses no runtime | Classificação |
|---|---|---|---|---|
| Claude 3 Haiku | anthropic.claude-3-haiku-20240307-v1:0 | Não | Não | API nativa necessária |
| Claude 3 Sonnet | anthropic.claude-3-sonnet-20240229-v1:0 | Não confirmado | Não confirmado | Não confirmado |
| Claude Fable 5 | anthropic.claude-fable-5 | Não | Não | API nativa necessária |
| Claude Fable 5.1 | anthropic.claude-fable-5-1 | Não | Não | API nativa necessária |
| Claude Haiku 4.5 | anthropic.claude-haiku-4-5-20251001-v1:0 | Não | Não | API nativa necessária |
| Claude Haiku 5.5 | anthropic.claude-haiku-5-5 | Não | Não | API nativa necessária |
| Claude Opus 4.5 | anthropic.claude-opus-4-5-20251101-v1:0 | Não | Não | API nativa necessária |
| Claude Opus 4.6 | anthropic.claude-opus-4-6-v1 | Não | Não | API nativa necessária |
| Claude Opus 4.7 | anthropic.claude-opus-4-7 | Não | Não | API nativa necessária |
| Claude Opus 4.8 | anthropic.claude-opus-4-8 | Não | Não | API nativa necessária |
| Claude Opus 5 | anthropic.claude-opus-5 | Não | Não | API nativa necessária |
| Claude Opus 5.5 | anthropic.claude-opus-5-5 | Não | Não | API nativa necessária |
| Claude Sonnet 4.5 | anthropic.claude-sonnet-4-5-20250929-v1:0 | Não | Não | API nativa necessária |
| Claude Sonnet 4.6 | anthropic.claude-sonnet-4-6 | Não | Não | API nativa necessária |
| Claude Sonnet 5 | anthropic.claude-sonnet-5 | Não | Não | API nativa necessária |
| Claude Sonnet 5.5 | anthropic.claude-sonnet-5-5 | Não | Não | API nativa necessária |
| DeepSeek V3.2 | deepseek.v3.2 | Sim | Não | OpenAI no runtime documentado |
| Devstral 2 123B | mistral.devstral-2-123b | Sim | Não | OpenAI no runtime documentado |
| Gemma 3 12B IT | google.gemma-3-12b-it | Sim | Não | OpenAI no runtime documentado |
| Gemma 3 27B PT | google.gemma-3-27b-it | Sim | Não | OpenAI no runtime documentado |
| Gemma 3 4B IT | google.gemma-3-4b-it | Sim | Não | OpenAI no runtime documentado |
| GLM 4.7 | zai.glm-4.7 | Sim | Não | OpenAI no runtime documentado |
| GLM 4.7 Flash | zai.glm-4.7-flash | Sim | Não | OpenAI no runtime documentado |
| GLM 5 | zai.glm-5 | Sim | Não | OpenAI no runtime documentado |
| GLM 5.3 | zai.glm-5.3 | Sim | Sim | OpenAI no runtime documentado |
| GPT 5.4 | openai.gpt-5.4 | Não | Não | Mantle necessário |
| GPT 5.5 | openai.gpt-5.5 | Não | Não | Mantle necessário |
| GPT OSS Safeguard 120B | openai.gpt-oss-safeguard-120b | Sim | Não | OpenAI no runtime documentado |
| GPT OSS Safeguard 20B | openai.gpt-oss-safeguard-20b | Sim | Não | OpenAI no runtime documentado |
| GPT-5.6 Luna | openai.gpt-5.6-luna | Sim | Sim | OpenAI no runtime documentado |
| GPT-5.6 Sol | openai.gpt-5.6-sol | Sim | Sim | OpenAI no runtime documentado |
| GPT-5.6 Terra | openai.gpt-5.6-terra | Sim | Sim | OpenAI no runtime documentado |
| GPT-6 Astra | openai.gpt-6-astra | Sim | Sim | OpenAI no runtime documentado |
| GPT-6 Luna | openai.gpt-6-luna | Sim | Sim | OpenAI no runtime documentado |
| GPT-6 Sol | openai.gpt-6-sol | Sim | Sim | OpenAI no runtime documentado |
| GPT-6.1 Sol | openai.gpt-6.1-sol | Sim | Sim | OpenAI no runtime documentado |
| gpt-oss-120b | openai.gpt-oss-120b-1:0 | Sim | Não | OpenAI no runtime documentado |
| gpt-oss-20b | openai.gpt-oss-20b-1:0 | Sim | Não | OpenAI no runtime documentado |
| Grok 4.6 | xai.grok-4.6 | Sim | Sim | OpenAI no runtime documentado |
| Grok 4.7 | xai.grok-4.7 | Sim | Sim | OpenAI no runtime documentado |
| Kimi K2 Thinking | moonshot.kimi-k2-thinking | Não | Não | API nativa necessária |
| Kimi K2.5 | moonshotai.kimi-k2.5 | Sim | Não | OpenAI no runtime documentado |
| Kimi K3 | moonshotai.kimi-k3 | Sim | Sim | OpenAI no runtime documentado |
| Magistral Small 2509 | mistral.magistral-small-2509 | Sim | Não | OpenAI no runtime documentado |
| MiniMax M2 | minimax.minimax-m2 | Sim | Não | OpenAI no runtime documentado |
| MiniMax M2.1 | minimax.minimax-m2.1 | Sim | Não | OpenAI no runtime documentado |
| MiniMax M2.5 | minimax.minimax-m2.5 | Sim | Não | OpenAI no runtime documentado |
| Ministral 14B 3.0 | mistral.ministral-3-14b-instruct | Sim | Não | OpenAI no runtime documentado |
| Ministral 3 8B | mistral.ministral-3-8b-instruct | Sim | Não | OpenAI no runtime documentado |
| Ministral 3B | mistral.ministral-3-3b-instruct | Sim | Não | OpenAI no runtime documentado |
| Mistral 7B Instruct | mistral.mistral-7b-instruct-v0:2 | Não | Não | API nativa necessária |
| Mistral Large (24.02) | mistral.mistral-large-2402-v1:0 | Não | Não | API nativa necessária |
| Mistral Large 3 | mistral.mistral-large-3-675b-instruct | Sim | Não | OpenAI no runtime documentado |
| Mixtral 8x7B Instruct | mistral.mixtral-8x7b-instruct-v0:1 | Não | Não | API nativa necessária |
| Nemotron Nano 3 30B | nvidia.nemotron-nano-3-30b | Sim | Não | OpenAI no runtime documentado |
| NVIDIA Nemotron 3 Super 120B A12B | nvidia.nemotron-super-3-120b | Sim | Não | OpenAI no runtime documentado |
| NVIDIA Nemotron Nano 12B v2 VL BF16 | nvidia.nemotron-nano-12b-v2 | Sim | Não | OpenAI no runtime documentado |
| NVIDIA Nemotron Nano 9B v2 | nvidia.nemotron-nano-9b-v2 | Sim | Não | OpenAI no runtime documentado |
| Pegasus v1.2 | twelvelabs.pegasus-1-2-v1:0 | Não | Não | API nativa necessária |
| Pegasus v1.5 | twelvelabs.pegasus-1-5-v1:0 | Não confirmado | Não confirmado | Não confirmado |
| Qwen3 32B (dense) | qwen.qwen3-32b-v1:0 | Sim | Não | OpenAI no runtime documentado |
| Qwen3 Next 80B A3B | qwen.qwen3-next-80b-a3b | Sim | Não | OpenAI no runtime documentado |
| Qwen3 VL 235B A22B | qwen.qwen3-vl-235b-a22b | Sim | Não | OpenAI no runtime documentado |
| Qwen3-Coder-30B-A3B-Instruct | qwen.qwen3-coder-30b-a3b-v1:0 | Sim | Não | OpenAI no runtime documentado |
| Voxtral Mini 3B 2507 | mistral.voxtral-mini-3b-2507 | Sim | Não | OpenAI no runtime documentado |
| Voxtral Small 24B 2507 | mistral.voxtral-small-24b-2507 | Sim | Não | OpenAI no runtime documentado |

## Fontes oficiais

- [Chat Completions](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-chat-completions.html)
- [Responses, limitações e regiões](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-responses-api.html)
- [Compatibilidade por API](https://docs.aws.amazon.com/bedrock/latest/userguide/models-api-compatibility.html)
- [Disponibilidade por endpoint](https://docs.aws.amazon.com/bedrock/latest/userguide/models-endpoint-availability.html)
- [MiniMax M2.5](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-minimax-minimax-m2-5.html)
- [Nemotron Super](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-nvidia-nemotron-super-3-120b.html)

A disponibilidade de catálogo/documentação não substitui uma chamada de inferência autorizada. Permissões de uso, quotas e cobrança continuam sujeitos à conta AWS. Nenhuma credencial, ARN privado, cabeçalho ou URL com token está neste relatório.
