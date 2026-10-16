# Auren — revalidação de conexões — 15/10/2026

30 conexões cadastradas: 24 sucessos, 2 falhas e 4 pendências. O objetivo de tornar todas operacionais ainda depende dos seis impedimentos descritos abaixo. Nenhum estado foi convertido artificialmente em sucesso.

## O que foi corrigido

- Novita: validação pela consulta autenticada de saldo, substituindo o catálogo público. Valores financeiros foram descartados.
- Hyperbolic: consulta autenticada de conta na API atual /v2/customer/balance. Confirma somente acesso à conta; não há evidência de inferência disponível. Nenhuma GPU ou armazenamento foi provisionado.
- NVIDIA: catálogo usado apenas para selecionar um modelo de embeddings publicado; uma palavra sintética no endpoint de embeddings comprova autenticação. O modelo antigo E5 devolveu HTTP 410; o modelo atual publicado nemotron-3-embed-1b respondeu com embedding válido.
- Ollama Cloud: modelo gemma4:31b confirmado no catálogo atual; mensagem sintética Hi com saída limitada a 1 token comprovou inferência autenticada.
- Cloudflare: chave atual do documento validada em Workers AI com o identificador da conta previamente configurado no cofre. A listagem de contas com o token atual não disponibilizou IDs. Nenhuma chave antiga foi reutilizada.
- Cartesia: corrigidos Authorization Bearer e Cartesia-Version 2026-08-14 conforme documentação oficial atual. A chave atual ainda foi recusada com HTTP 401.
- xAI: consulta da própria chave detecta flags de chave desativada ou conta/equipe bloqueada mesmo quando o HTTP é 200. Essa condição é reportada como falha.
- Bedrock: quando a região for preenchida, o botão consulta ListFoundationModels no endpoint regional, sem geração. Sem região não é feita tentativa em regiões aleatórias.
- Importação: reimportar os mesmos valores não regrava credenciais, invalida resultados nem apaga tokens OAuth existentes. Campos configurados podem ser reutilizados explicitamente; uma chave ausente nunca é completada por credencial legada.

## Resultado real por conexão

| Conexão | Estado | Evidência sanitizada |
|---|---|---|
| AI Horde | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Amazon Bedrock | Pendente | Pendente: informe a região AWS em que a chave foi emitida. |
| Anthropic API (Claude) | Pendente | Pendente: credencial não cadastrada. |
| AssemblyAI API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Canva Connect | Pendente | Pendente: configure a Redirect URL e conclua a autorização OAuth no Canva. |
| Cartesia API | Falha | Falha: credencial ou permissão recusada pelo serviço. |
| Cerebras Inference API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Cloudflare Workers AI | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
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
| Hyperbolic API | Sucesso | Conta autenticada; disponibilidade de inferência não comprovada. |
| Mistral AI API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| NVIDIA NIM API | Sucesso | Inferência mínima autenticada concluída; não confirma todos os modelos ou tarefas. |
| Novita AI API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Ollama Cloud API | Sucesso | Inferência mínima autenticada concluída; não confirma todos os modelos ou tarefas. |
| OpenAI API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| OpenRouter API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Replicate API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Stability AI API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Voyage AI API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| xAI API | Falha | Falha: chave desativada ou conta/equipe bloqueada no painel do provedor. |
| Z.ai API | Sucesso | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |

## Impedimentos que permanecem

- Anthropic e Fireworks: campos do documento sem chave utilizável; credenciais antigas não são testadas.
- Bedrock: região da chave ausente no documento e na configuração atual.
- Canva: Client ID e client secret presentes; Redirect URL e consentimento OAuth ainda ausentes. É necessário cadastrar a URL local no painel e concluir a autorização. Credencial OAuth não é tratada como chave de inferência.
- Cartesia: chave com formato atual, mas recusada pelo endpoint oficial com autenticação e versão atuais (401). Conferir a chave ativa no painel e atualizar o documento local.
- xAI: consulta autenticada confirma bloqueio/desativação da chave ou conta/equipe. Regularização depende do painel do serviço.

## Fontes oficiais para as correções

- [Novita: saldo](https://docs.novita.ai/api-reference/basic-get-user-balance)
- [Hyperbolic: conta](https://www.hyperbolic.ai/docs/api-reference/balances/get-the-current-user-or-organization-accounts-balance)
- [NVIDIA: embeddings atuais](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-embed-1b-infer)
- [Ollama: nuvem](https://docs.ollama.com/cloud) e [API compatível](https://docs.ollama.com/api/openai-compatibility)
- [Cartesia: vozes, autenticação e versão](https://docs.cartesia.ai/api-reference/voices/list)
- [xAI: consulta de chave e flags](https://docs.x.ai/developers/rest-api-reference/inference/other)
- [AWS: uso de chaves](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-use.html) e [ListFoundationModels](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_ListFoundationModels.html)

## Limites e segurança

Os 24 sucessos confirmam os endpoints indicados, não todos os modelos ou tarefas de cada plataforma. NVIDIA e Ollama receberam testes mínimos de inferência nesta rodada; os demais serviços usam consultas adequadas de catálogo, conta, identidade, saldo, vozes ou similares, além do embedding mínimo Voyage já previsto. Respostas, cabeçalhos, valores de conta e segredos não foram persistidos. A chave usada em cada chamada veio do documento atual, cuja rotação foi confirmada pelo usuário. Valores existentes omitidos no inventário foram preservados. Nenhum envio ao Google Drive.

## Arquivos de código alterados nesta continuação

- integration/auren_connection_registry.py
- integration/auren_connection_validation.py
- scripts/auren_connection_inventory.py
- src/lib/components/chat/Settings/AurenConnections.svelte
- tests/test_auren_connections.py

As demais alterações preexistentes no checkout foram preservadas. A interface recebeu apenas mensagens curtas de estado; a aparência, a grade e a ordenação foram mantidas.

## Verificações

- 26 testes específicos de conexões passaram, incluindo respostas 200 de conta bloqueada, contratos de saldo, catálogo público, limites de inferência, associação de credenciais e preservação de tokens OAuth ao reimportar valores iguais.
- Mais 47 testes de configurações, provedores preparados, fallback, ponte e validação passaram (73 testes Python distintos no total).
- 50 testes frontend passaram.
- ESLint do componente alterado e git diff --check passaram.
- Compilação de produção passou (Wrote site to build). A primeira tentativa atingiu o limite de heap do Node; a repetição com 8192 MB concluiu.
- 20 verificações nativas Qt WebEngine passaram: grade de 3/2/1 colunas, ausência de overflow, arraste real, teclado, vínculo de campos/credenciais/estado ao cartão, persistência em disco e após recarga, Canva OAuth e API autenticada com 30 conexões. Testes usam backend temporário e credenciais sintéticas, sem gravação de preferências em produção.
- Serviço lunvri.service reiniciado após confirmar ausência de worker de geração ativo. O frontend compilado está disponível.
- Varredura de 4974 arquivos de código, testes, relatórios, build, metadados e logs: nenhuma correspondência com os valores atuais do inventário. Nenhum segredo apareceu nos artefatos desta rodada; nenhum envio ao Google Drive.
