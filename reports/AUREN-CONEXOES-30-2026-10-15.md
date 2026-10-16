# Auren — 30 conexões — 15/10/2026

30 conexões cadastradas. Resultado real sanitizado: 19 sucessos, 3 falhas e 8 pendências. Não houve incompatibilidade de endpoint nesta rodada.

O usuário confirmou nesta conversa que todas as credenciais foram rotacionadas e que o inventário local foi atualizado. As chamadas desta rodada usaram exclusivamente os valores atuais do documento; campos ausentes não foram completados com credenciais antigas do histórico, ambiente ou cofre.

Foram importadas credenciais de 28 conexões para o cofre Auren/Secret Service/KWallet. Anthropic e Fireworks não forneceram valores utilizáveis no documento. Campos e credenciais existentes omitidos na importação, assim como os segredos não relacionados, foram preservados. Nenhum segredo foi copiado para este relatório, código, armazenamento comum ou Google Drive.

## Resultado por conexão

| Conexão | Resultado | Motivo sanitizado |
|---|---|---|
| AI Horde | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Amazon Bedrock | Pendente | Pendente: informe a região AWS em que a chave foi emitida. |
| Anthropic API (Claude) | Pendente | Pendente: credencial não cadastrada. |
| AssemblyAI API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Canva Connect | Pendente | Pendente: configure a Redirect URL e conclua a autorização OAuth no Canva. |
| Cartesia API | Falha | Falha: credencial ou permissão recusada pelo serviço. |
| Cerebras Inference API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Cloudflare Workers AI | Pendente | Pendente: informe o identificador da conta Cloudflare. |
| Cohere API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Deepgram API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| DeepInfra API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| DeepSeek API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| ElevenLabs API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| fal API (fal.ai) | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Fireworks AI API | Pendente | Pendente: credencial não cadastrada. |
| Google Gemini API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| GroqCloud API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Hugging Face Inference Providers | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Hyperbolic API | Falha | Falha: credencial ou permissão recusada pelo serviço. |
| Mistral AI API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Novita AI API | Pendente | Pendente: catálogo público acessível; autenticação não confirmada. |
| NVIDIA NIM API | Pendente | Pendente: catálogo público acessível; autenticação não confirmada. |
| Ollama Cloud API | Pendente | Pendente: catálogo público acessível; autenticação não confirmada. |
| OpenAI API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| OpenRouter API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Replicate API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Stability AI API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Voyage AI API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| xAI API | Falha | Falha: credencial ou permissão recusada pelo serviço. |
| Z.ai API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |

## Campos, autenticação e fontes oficiais

Os cartões identificam as conexões; os nomes de modelos permanecem nos seletores existentes. Cloudflare usa Workers AI, conforme a implementação atual, e mantém um único cartão. Canva Connect é uma integração OAuth e não participa do catálogo de modelos nem das rotas de inferência.

| Conexão | Campos necessários | Autenticação | Documentação oficial consultada |
|---|---|---|---|
| AI Horde | Chave de API | apikey | [Documentação](https://aihorde.net/api/) |
| Amazon Bedrock | Chave de API, Região AWS da chave | Authorization Bearer | [Documentação](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html) |
| Anthropic API (Claude) | Chave de API | x-api-key e anthropic-version | [Documentação](https://platform.claude.com/docs/en/api/models/list) |
| AssemblyAI API | Chave de API | Authorization com chave direta | [Documentação](https://www.assemblyai.com/docs/pre-recorded-audio/api-reference/transcripts/list) |
| Canva Connect | Client secret, Client ID, Redirect URL cadastrada no Canva | OAuth 2.0 Authorization Code + PKCE (S256) | [Documentação](https://www.canva.dev/docs/apps/rest-apis/authentication/) |
| Cartesia API | Chave de API | X-API-Key e Cartesia-Version | [Documentação](https://docs.cartesia.ai/api-reference/voices/list) |
| Cerebras Inference API | Chave de API | Authorization Bearer | [Documentação](https://inference-docs.cerebras.ai/api-reference/models/list-models) |
| Cloudflare Workers AI | Chave de API, Identificador da conta Cloudflare | Authorization Bearer | [Documentação](https://developers.cloudflare.com/workers-ai/get-started/rest-api/) |
| Cohere API | Chave de API | Authorization Bearer | [Documentação](https://docs.cohere.com/v2/reference/list-models) |
| Deepgram API | Chave de API | Authorization Token | [Documentação](https://developers.deepgram.com/reference/manage/projects/list) |
| DeepInfra API | Chave de API | Authorization Bearer | [Documentação](https://deepinfra.com/docs/openai_api) |
| DeepSeek API | Chave de API | Authorization Bearer | [Documentação](https://api-docs.deepseek.com/api/list-models) |
| ElevenLabs API | Chave de API | xi-api-key | [Documentação](https://elevenlabs.io/docs/api-reference/user/get) |
| fal API (fal.ai) | Chave de API | Authorization Key | [Documentação](https://fal.ai/docs/platform-apis/v1/models) |
| Fireworks AI API | Chave de API | Authorization Bearer | [Documentação](https://docs.fireworks.ai/api-reference/list-models) |
| Google Gemini API | Chave de API | x-goog-api-key | [Documentação](https://ai.google.dev/api/models) |
| GroqCloud API | Chave de API | Authorization Bearer | [Documentação](https://console.groq.com/docs/api-reference) |
| Hugging Face Inference Providers | Chave de API | Authorization Bearer | [Documentação](https://huggingface.co/docs/hub/api) |
| Hyperbolic API | Chave de API | Authorization Bearer | [Documentação](https://www.hyperbolic.ai/docs/overview/overview) |
| Mistral AI API | Chave de API | Authorization Bearer | [Documentação](https://docs.mistral.ai/api/endpoint/models) |
| Novita AI API | Chave de API | Authorization Bearer | [Documentação](https://docs.novita.ai/api-reference/model-apis-llm-list-models) |
| NVIDIA NIM API | Chave de API | Authorization Bearer | [Documentação](https://docs.api.nvidia.com/nim/reference/models-1) |
| Ollama Cloud API | Chave de API | Authorization Bearer | [Documentação](https://docs.ollama.com/cloud) |
| OpenAI API | Chave de API | Authorization Bearer | [Documentação](https://developers.openai.com/api/reference/resources/models/methods/list) |
| OpenRouter API | Chave de API | Authorization Bearer | [Documentação](https://openrouter.ai/docs/api-reference/authentication) |
| Replicate API | Chave de API | Authorization Bearer | [Documentação](https://replicate.com/docs/reference/http) |
| Stability AI API | Chave de API | Authorization Bearer | [Documentação](https://platform.stability.ai/docs/api-reference) |
| Voyage AI API | Chave de API | Authorization Bearer | [Documentação](https://docs.voyageai.com/reference/embeddings-api) |
| xAI API | Chave de API | Authorization Bearer | [Documentação](https://docs.x.ai/developers/rest-api-reference/inference/models) |
| Z.ai API | Chave de API | Authorization Bearer | [Documentação](https://docs.z.ai/guides/overview/quick-start) |

## Limites dos testes reais

- 25 conexões receberam chamadas reais; cinco foram bloqueadas antes de qualquer requisição por campos/credenciais ausentes ou consentimento OAuth. As três consultas a catálogos públicos continuam pendentes para autenticação.
- Foram usadas consultas mínimas de catálogo, conta, saldo, vozes, projetos, transcrições ou identidade conforme o serviço. Respostas e dados de conta foram descartados em memória.
- Voyage recebeu somente a palavra sintética `test` no endpoint oficial de embeddings, com `voyage-4-lite`. Não houve geração de texto, imagem, áudio ou vídeo nesta rodada.
- NVIDIA, Novita e Ollama responderam ao catálogo inclusive com uma credencial sintética inválida; por isso a chave real não foi considerada validada.
- Um sucesso confirma somente a consulta autenticada correspondente. Hugging Face confirma identidade do token; permissões de inferência e modelos específicos exigem validação própria.
- Bedrock aguarda região da chave e seleção do contrato regional apropriado. O formulário cobre a chave Bearer existente no inventário; credenciais IAM SigV4 não foram inventadas nem convertidas em chave de inferência.
- Cloudflare aguarda o identificador da conta no inventário atualizado. O identificador existente no cofre foi preservado e não foi usado nesta rodada.
- Canva aguarda cadastro da Redirect URL no painel e consentimento do usuário. O fluxo implementado usa PKCE, validação de state, callback HTTP exclusivamente local, tokens no cofre e renovação por refresh token; o fluxo real não foi autorizado nesta rodada.
- A confirmação de credencial nova é registrada como metadado sem valores secretos. Credenciais legadas sem confirmação ficam impedidas de entrar no novo teste de conexão.

## Interface e persistência

Os cartões usam as superfícies, bordas, raio, preenchimento e espaçamento existentes. A grade tem três colunas em telas largas, duas até 900 px e uma até 650 px. A ordem inicial é alfabética; a preferência salva usa IDs estáveis. A alça permite arraste vertical com mouse/toque e reordenação com setas no teclado.

A ordem é gravada atomicamente em `auren_preferences.json`, sem credenciais, preservando as preferências de imagens. IDs repetidos e desconhecidos são rejeitados. Campos vazios preservam os valores já guardados; atualizações de múltiplos campos têm reversão em caso de falha do cofre.

As novas conexões não foram adicionadas automaticamente às rotas de geração ou aos perfis existentes. Nenhuma dependência de produção foi adicionada.

## Verificação técnica

- 66 testes Python de conexões, configurações, provedores preparados, ponte, alternativas e evidências: passaram.
- 6 testes da API autenticada, em banco temporário isolado: passaram.
- 50 testes frontend, incluindo ordenação por ID, recarga, anexação de novos cartões e limites de movimento: passaram.
- ESLint dos arquivos frontend alterados: passou.
- Compilação Python dos módulos alterados: passou.
- Compilação final de produção: passou (`Wrote site to "build"`).
- Verificação nativa no Qt WebEngine: 20 verificações aprovadas, incluindo arraste com mouse, teclado, associação de campos/credencial/validação, persistência em disco e após recarga, grade de 3/2/1 colunas em 1440/800/520 px, ausência de transbordamento e Canva com três campos OAuth. A gravação foi feita em backend temporário, preservando a ordem de uso normal. Evidência: `auren-connections-30-ui-2026-10-15.json`.
- Varredura final: 1.675 arquivos de código, build, metadados, relatórios e logs comparados em memória com os valores atuais do inventário; nenhuma correspondência. Evidência: `auren-connections-30-security-2026-10-15.json`.

## Arquivos da tarefa

- [backend/open_webui/routers/auren.py](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/backend/open_webui/routers/auren.py)
- [integration/auren_canva_oauth.py](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/integration/auren_canva_oauth.py)
- [integration/auren_connection_registry.py](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/integration/auren_connection_registry.py)
- [integration/auren_connection_validation.py](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/integration/auren_connection_validation.py)
- [integration/auren_credentials.py](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/integration/auren_credentials.py)
- [integration/auren_settings.py](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/integration/auren_settings.py)
- [integration/lunvri_bridge.py](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/integration/lunvri_bridge.py)
- [scripts/auren_connection_inventory.py](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/scripts/auren_connection_inventory.py)
- [src/lib/apis/auren/index.ts](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/src/lib/apis/auren/index.ts)
- [src/lib/components/chat/Settings/AurenConnections.svelte](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/src/lib/components/chat/Settings/AurenConnections.svelte)
- [src/lib/utils/aurenConnections.test.ts](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/src/lib/utils/aurenConnections.test.ts)
- [src/lib/utils/aurenConnections.ts](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/src/lib/utils/aurenConnections.ts)
- [src/lunvri.css](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/src/lunvri.css)
- [tests/auren.vitest.config.mjs](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/tests/auren.vitest.config.mjs)
- [tests/check_auren_connections_ui.py](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/tests/check_auren_connections_ui.py)
- [tests/test_auren_api.py](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/tests/test_auren_api.py)
- [tests/test_auren_connections.py](/home/cambrith/.codex/.chatgpt-projects/g-p-6aa1781aa48c81919924bcaa9a4f38eb/cavren-openwebui/tests/test_auren_connections.py)

As demais alterações que já estavam no checkout foram preservadas. Nenhum commit, envio ao GitHub ou sincronização com Google Drive foi feito nesta tarefa.

O serviço local `lunvri.service` foi reiniciado sem worker de geração ativo. A API de produção autenticada devolveu as 30 conexões e identificou Canva como OAuth; a chamada sem autenticação recebeu 401. Nenhuma chamada de geração foi realizada pela verificação de interface.

Artefatos locais adicionais: `auren-connections-30-2026-10-15.json` (resultado dos 30 serviços), `auren-connections-30-ui-2026-10-15.json` (20 verificações de interface), `auren-connections-30-security-2026-10-15.json` (varredura sanitizada) e capturas `auren-connections-30-wide-2026-10-15.png` / `auren-connections-30-narrow-2026-10-15.png`, produzidas com dados sintéticos em perfil isolado.
