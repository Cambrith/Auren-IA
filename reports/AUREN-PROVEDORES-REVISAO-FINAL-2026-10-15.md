# Auren — revisão final dos provedores — 15/10/2026

## Resultado observado

30 provedores preservados e organizados alfabeticamente no documento local. 23 consultas autenticadas atuais passaram. NVIDIA, Ollama e Voyage conservaram evidência de sucesso anterior com as mesmas credenciais, mas não receberam novo teste de inferência nesta rodada, pois não foi autorizado consumo. Anthropic e Fireworks ficam reservados sem credenciais; xAI permanece bloqueada; Canva aguarda consentimento real após a correção de abertura do formulário/navegador.

## Alterações funcionais

- Cartesia Standard API Key importada e validada no endpoint oficial de vozes (HTTP 200). Chave Admin não é usada nos endpoints convencionais.
- Bedrock: nova chave, região sa-east-1 e Base URL exata informada pelo usuário. Catálogo regional autenticado com 66 modelos de texto; lista de 30 perfis de sistema obtida sem inferência. Compatibilidade detalhada em AUREN-BEDROCK-SA-EAST-1-2026-10-15.md.
- Foram identificados 42 modelos do catálogo com Chat Completions/runtime documentado, 20 com APIs nativas, 2 Mantle e 2 sem confirmação. Não se configurou Mantle automaticamente.
- Catálogos manuais novos: Bedrock (39; de 42 contratos documentados, com três modelos filtrados pelas políticas preexistentes), Cerebras (2), DeepInfra (153) e Novita (81). Fireworks preparado no mesmo contrato, sem chave. Rotas pagas exigem confirmação de custo; nenhum novo provedor foi incluído automaticamente nos perfis gratuitos. Catálogo e contrato não equivalem a inferência testada.
- Serviços de voz, transcrição, embeddings, imagens, hospedagem e OAuth continuam com seus tipos próprios e validações adequadas. A autenticação de uma conta não habilita automaticamente todas as operações de geração, nem substitui adaptadores de tarefas existentes.
- Anthropic/Fireworks/xAI são excluídos das configurações ativas de execução, mantendo os segredos no cofre e os cartões disponíveis.
- Importador usa campos reconhecidos; status, notas e endpoints não sobrescrevem uma chave. Referências de cofre são aceitas somente para o próprio provedor/campo.
- Validação padrão não executa geração nem embeddings. NVIDIA/Ollama usam somente catálogo com controle negativo; Voyage não executa embeddings sem autorização explícita.
- Canva: formulário recebe foco e rolagem após o clique; autorização usa navegação externa compatível com o Qt, evitando popup silencioso. PKCE S256, state, callback local, token exchange e renovação permanecem no backend; tokens exclusivamente no cofre. Recebimento e renovação de tokens reais dependem do consentimento do titular.

## Documento e credenciais

O documento /home/cambrith/Documentos/Chaves de API - Auren foi reescrito com 30 seções em ordem alfabética, nomes padronizados, tipo de serviço, tipo de credencial, autenticação, Base URL, campos extras, estado real e links oficiais. Os valores das chaves foram substituídos por referências ao cofre após conferência de leitura de cada valor importado. A cópia integral anterior está arquivada exclusivamente no mesmo cofre. O arquivo local continua com permissões 0600. Nenhuma chave foi apagada apenas por indisponibilidade do provedor. Credenciais não relacionadas foram preservadas.

## Marcas e interface

30 provedores com arquivos locais associados. 28 recursos obtidos diretamente dos sites oficiais; AI Horde conserva o favicon oficial anterior e OpenAI conserva o SVG atribuído existente como fallback. Manifesto: static/brand-icons/provider-sources.json. A inspeção visual eliminou imagens de parceiros que apareciam nas páginas oficiais; foram priorizados os ícones declarados de cada site. Nenhum logotipo foi inventado.

As marcas mantêm cores e proporções originais em cartões e seletores. Dimensões dos badges, alinhamento e espaçamento foram preservados; há fundos neutros para contraste. A grade continua responsiva em 3/2/1 colunas e com ordenação persistente por ID.

## Estados por conexão

| Provedor | Estado nesta rodada | Observação |
|---|---|---|
| AI Horde | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Amazon Bedrock | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Anthropic API (Claude) | Pendente | Reservado: sem credencial; ativação futura depende do painel do provedor. |
| AssemblyAI API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Canva Connect | Pendente | Pendente: configure a Redirect URL e conclua a autorização OAuth no Canva. |
| Cartesia API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Cerebras Inference API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Cloudflare Workers AI | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Cohere API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Deepgram API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| DeepInfra API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| DeepSeek API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| ElevenLabs API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| fal API (fal.ai) | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Fireworks AI API | Pendente | Reservado: sem credencial; ativação futura depende do painel do provedor. |
| Google Gemini API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| GroqCloud API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Hugging Face Inference Providers | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Hyperbolic API | Sucesso atual | Conta autenticada; disponibilidade de inferência não comprovada. |
| Mistral AI API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Novita AI API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| NVIDIA NIM API | Pendente | Pendente: catálogo público acessível; autenticação não confirmada. Sucesso anterior preservado: 2026-10-15T21:52:23.951886+00:00 |
| Ollama Cloud API | Pendente | Pendente: catálogo público acessível; autenticação não confirmada. Sucesso anterior preservado: 2026-10-15T22:22:59.320632+00:00 |
| OpenAI API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| OpenRouter API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Replicate API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Stability AI API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |
| Voyage AI API | Pendente | Pendente: comprovação exige inferência; nenhuma operação com consumo foi autorizada nesta rodada. Sucesso anterior preservado: 2026-10-15T21:52:29.060802+00:00 |
| xAI API | Indisponível | Falha: chave desativada ou conta/equipe bloqueada no painel do provedor. |
| Z.ai API | Sucesso atual | Consulta autenticada concluída; não confirma capacidade de geração ou saldo. |

## Verificações

- 82 testes Python distintos aprovados (73 existentes/específicos e 9 novos contratos de revisão).
- 50 testes frontend aprovados.
- ESLint dos arquivos frontend alterados aprovado.
- Compilação de produção aprovada com 8192 MB de heap (Wrote site to build).
- 27 verificações Qt WebEngine aprovadas, incluindo 30 imagens carregadas, cores sem filtros, temas claro/escuro, grade, reordenação com mouse/teclado, persistência após recarga, associação de campos/credenciais/estado e envio/navegação OAuth com destino simulado sem concessão de acesso. A primeira execução offscreen perdeu o contexto gráfico; a repetição com GPU desativada passou.
- Callback, state, PKCE, troca e renovação de tokens são cobertos por testes sintéticos. Não há alegação de OAuth real concluído.
- API de produção sem autenticação devolveu 401; verificação autenticada confirmou as 30 conexões.
- Varredura final de 9.039 arquivos: nenhuma correspondência com as credenciais atuais, Client ID ou identificador de conta. O documento usa referências ao cofre. Não houve chamada de inferência paga nem envio ao Google Drive.

## Ação manual restante

Após recarregar a Auren (Ctrl+R), abrir Configurações → Conexões → Canva Connect → Configurar OAuth → Autorizar Canva. A janela nativa entrega a autorização ao navegador do sistema. Conferir o escopo profile:read e aprovar no Canva; depois retornar e validar a conexão. Anthropic e Fireworks só exigirão configuração quando o titular decidir contratar/obter chaves. xAI depende de desbloqueio e créditos no painel; nenhuma tentativa de contorno foi feita.

## Arquivos de código desta continuação

- integration/auren_bedrock.py
- integration/auren_connection_registry.py
- integration/auren_connection_validation.py
- integration/auren_settings.py
- integration/lunvri_connections.py
- integration/lunvri_manual.py
- scripts/auren_connection_inventory.py
- scripts/auren_finalize_inventory.py
- scripts/auren_provider_icons.py
- src/lib/apis/auren/index.ts
- src/lib/components/common/AurenProviderBadge.svelte
- src/lib/components/chat/Settings/AurenConnections.svelte
- src/lib/utils/providerIcons.ts
- static/brand-icons/README.md
- static/brand-icons/provider-sources.json e arquivos em providers/
- tests/check_auren_connections_ui.py
- tests/test_auren_connections.py
- tests/test_auren_prepared_providers.py
- tests/test_auren_provider_review.py

As demais alterações preexistentes foram preservadas. Nenhum commit, push ou sincronização com Google Drive foi realizado.
