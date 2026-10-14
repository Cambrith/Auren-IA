# Auren — verificação delimitada Gemini/Groq, r2

Consolidação: 2026-10-14T17:18:30.115402+00:00. Catálogos atuais + IDs exatos anteriores + IDs adicionais documentados. **77 IDs, 492 combinações de provedor/modelo/operação**.

**Não foram todos testados.** 71 IDs tiveram operação nativa chamada; 284 combinações receberam 338 tentativas, mais 35 chamadas auxiliares de reconhecimento de voz. Os áudios de referência foram reutilizados; duas gerações de fixtures da rodada anterior não são chamadas novas. Todas as 492 linhas terminaram com resultado ou impedimento explícito.

| Estado | Combinações |
|---|---:|
| not_tested | 208 |
| valid | 70 |
| failed | 186 |
| inconclusive | 14 |
| partial_validity | 14 |

Custos positivos informados: 0 respostas. Zero informado: 0. Custo desconhecido: 338 tentativas principais, além das auxiliares sem preço informado. **Isso não é uma fatura de US$ 0.** Limites curtos de tempo/tokens foram usados; cabeçalhos ausentes e erros 429 não medem a cota máxima.

## IDs sem nova chamada nativa

- gemini:deep-research-max-preview-04-2026
- gemini:deep-research-preview-04-2026
- gemini:deep-research-pro-preview-12-2025
- gemini:gemini-omni-1.1-flash
- gemini:gemini-omni-flash-preview
- gemini:nano-banana-pro-preview

Os três Deep Research já receberam a única tentativa de planejamento autorizada na r1. Omni precisa de contrato/preço de vídeo correto; Nano Banana Pro Preview não teve teto verificável nesta rodada. Estes impedimentos não são provas de mau desempenho. Batch, cache, contagem de tokens e pesquisa completa permanecem não testados nesta rodada; chat genérico não foi usado para aprovar outras modalidades.

## Implantação e limites

Éter: Qwen Groq com esforço high, confirmado no worker. Ímpeto: Qwen sem raciocínio para rapidez. Kimi continua candidato efetivo de profundidade; Gemini 3.8 não recebe aprovação por benchmark. Gemini 3.5 Flash-Lite passou no adaptador da Auren para conversa, código, documentos e pesquisa; o worker confirmou também um PDF sintético com identificador não fornecido no pedido. Whisper v3/Turbo foram integrados como alternativas de transcrição e passaram na Auren. Voz pt-BR mantém Magpie; não há segundo transporte de voz pt-BR aprovado no produto. A ordem de todos os 23 perfis está em ../auren-scoped-selection-2026-10-14.json.

O Automático mantém regras locais e usa Qwen com JSON e prazo de 3 s para intenções de ação não reconhecidas. Erro, cota ou JSON inválido retorna à decisão local; não libera cobrança, não executa ferramentas e não envia bytes de anexos ao classificador. Não é garantia de compreender todo pedido.

Imagens: a primeira linha mostra tempo decorrido, posição e estimativa apenas quando disponíveis; a segunda mantém a animação e a etapa. O build passou. Os quatro modelos AI Horde historicamente integrados receberam novas sondagens práticas: quatro imagens de Deliberate/Stable Diffusion falharam na aderência visual, duas AbsoluteReality foram retidas e duas Abyss OrangeMix não concluíram no prazo. Nenhum novo gerador foi aprovado nesta rodada. A elegibilidade anterior de transporte foi preservada para não desativar os perfis; ela não representa aprovação de qualidade atual. Gemini imagem recebeu recusas 429; OpenRouter não mostrou saldo positivo. Tetos financeiros autorizados não foram habilitados como consumo automático.

O navegador integrado não acessou a prévia devido à proteção de acesso local. Não se reduziu esta proteção; a confirmação visual em uma sessão da Auren no computador do usuário permanece pendente. Testes locais de contrato, filtros e apresentação + build são evidências separadas.

A tentativa de agente que continuava pendente no prazo não foi aprovada. O cancelamento recebeu 400, a exclusão do ambiente próprio recebeu 200 e a consulta final retornou 404; isto não comprova conclusão nem custo zero. Nenhuma ferramenta de função foi executada pelo harness. A evidência está em remote-final-check.json.

A rodada exaustiva geral r1 permanece pausada. Cofre, conversas e alterações locais foram preservados. Os custos desconhecidos são mantidos separados; não houve compra de créditos, cadastro de cartão ou ativação de faturamento.

## Inventário por ID

| Provedor | Modelo | Operações chamadas | Estados das operações |
|---|---|---:|---|
| gemini | antigravity-preview-05-2026 | 3/5 | not_tested: 2, partial_validity: 2, valid: 1 |
| gemini | antigravity-preview-09-2026 | 12/14 | not_tested: 2, partial_validity: 7, inconclusive: 5 |
| gemini | antigravity-preview-latest | 3/5 | not_tested: 2, partial_validity: 1, inconclusive: 1, valid: 1 |
| gemini | aqa | 1/1 | valid: 1 |
| gemini | deep-research-max-preview-04-2026 | 0/3 | not_tested: 3 |
| gemini | deep-research-preview-04-2026 | 0/3 | not_tested: 3 |
| gemini | deep-research-pro-preview-12-2025 | 0/3 | not_tested: 3 |
| gemini | gemini-2.5-computer-use-preview-10-2025 | 3/4 | failed: 3, not_tested: 1 |
| gemini | gemini-2.5-flash | 9/12 | failed: 9, not_tested: 3 |
| gemini | gemini-2.5-flash-image | 2/13 | not_tested: 11, failed: 2 |
| gemini | gemini-2.5-flash-lite | 9/12 | failed: 9, not_tested: 3 |
| gemini | gemini-2.5-flash-native-audio-latest | 1/2 | not_tested: 1, valid: 1 |
| gemini | gemini-2.5-flash-native-audio-preview-09-2025 | 1/2 | not_tested: 1, valid: 1 |
| gemini | gemini-2.5-flash-native-audio-preview-12-2025 | 1/2 | not_tested: 1, valid: 1 |
| gemini | gemini-2.5-flash-preview-tts | 1/2 | not_tested: 1, valid: 1 |
| gemini | gemini-2.5-pro | 9/12 | failed: 9, not_tested: 3 |
| gemini | gemini-2.5-pro-preview-tts | 1/3 | not_tested: 2, failed: 1 |
| gemini | gemini-3-flash-preview | 9/12 | valid: 4, not_tested: 3, inconclusive: 1, failed: 4 |
| gemini | gemini-3-pro-image | 2/13 | not_tested: 11, failed: 2 |
| gemini | gemini-3-pro-image-preview | 2/13 | not_tested: 11, failed: 2 |
| gemini | gemini-3.1-flash-image | 2/13 | not_tested: 11, failed: 2 |
| gemini | gemini-3.1-flash-image-preview | 2/13 | not_tested: 11, failed: 2 |
| gemini | gemini-3.1-flash-lite | 9/12 | failed: 9, not_tested: 3 |
| gemini | gemini-3.1-flash-lite-image | 2/13 | not_tested: 11, failed: 2 |
| gemini | gemini-3.1-flash-lite-preview | 9/12 | failed: 9, not_tested: 3 |
| gemini | gemini-3.1-flash-live-preview | 1/1 | valid: 1 |
| gemini | gemini-3.1-flash-tts-preview | 1/3 | not_tested: 2, valid: 1 |
| gemini | gemini-3.1-pro-preview | 9/12 | failed: 9, not_tested: 3 |
| gemini | gemini-3.1-pro-preview-customtools | 9/12 | failed: 9, not_tested: 3 |
| gemini | gemini-3.5-flash | 9/12 | failed: 9, not_tested: 3 |
| gemini | gemini-3.5-flash-lite | 9/12 | valid: 8, not_tested: 3, failed: 1 |
| gemini | gemini-3.5-live-translate-preview | 1/1 | failed: 1 |
| gemini | gemini-3.5-transcribe | 1/2 | not_tested: 1, failed: 1 |
| gemini | gemini-3.5-transcribe-live | 1/1 | valid: 1 |
| gemini | gemini-3.6-flash | 9/12 | failed: 9, not_tested: 3 |
| gemini | gemini-3.7-flash | 9/12 | failed: 9, not_tested: 3 |
| gemini | gemini-3.8-flash | 9/12 | failed: 8, not_tested: 3, inconclusive: 1 |
| gemini | gemini-3.8-flash-lite-tts | 1/3 | not_tested: 2, failed: 1 |
| gemini | gemini-3.8-flash-tts | 1/3 | not_tested: 2, valid: 1 |
| gemini | gemini-3.8-live | 1/1 | valid: 1 |
| gemini | gemini-3.8-live-extended-thinking | 1/1 | failed: 1 |
| gemini | gemini-4-argon | 9/11 | failed: 9, not_tested: 2 |
| gemini | gemini-embedding-001 | 1/4 | not_tested: 3, valid: 1 |
| gemini | gemini-embedding-2 | 7/10 | not_tested: 3, valid: 7 |
| gemini | gemini-embedding-2-preview | 7/10 | not_tested: 3, valid: 7 |
| gemini | gemini-flash-latest | 9/12 | failed: 9, not_tested: 3 |
| gemini | gemini-flash-lite-latest | 9/12 | valid: 8, not_tested: 3, failed: 1 |
| gemini | gemini-nano-banana-2.1 | 2/13 | not_tested: 11, failed: 2 |
| gemini | gemini-omni-1.1-flash | 0/10 | not_tested: 10 |
| gemini | gemini-omni-flash-preview | 0/10 | not_tested: 10 |
| gemini | gemini-pro-latest | 9/12 | failed: 9, not_tested: 3 |
| gemini | gemini-robotics-er-2-preview | 9/12 | valid: 6, not_tested: 3, failed: 3 |
| gemini | gemini-robotics-er-2-streaming-preview | 1/1 | failed: 1 |
| gemini | gemma-4-26b-a4b-it | 3/4 | failed: 3, not_tested: 1 |
| gemini | gemma-4-31b-it | 3/4 | valid: 2, not_tested: 1, failed: 1 |
| gemini | lyria-3-clip-preview | 1/2 | not_tested: 1, failed: 1 |
| gemini | lyria-3-pro-preview | 1/2 | not_tested: 1, failed: 1 |
| gemini | lyria-3.5 | 1/2 | not_tested: 1, failed: 1 |
| gemini | lyria-realtime-exp | 1/1 | partial_validity: 1 |
| gemini | nano-banana-pro-preview | 0/7 | not_tested: 7 |
| gemini | veo-3.1-fast-generate-preview | 1/1 | failed: 1 |
| gemini | veo-3.1-generate-preview | 1/1 | failed: 1 |
| gemini | veo-3.1-lite-generate-preview | 1/1 | failed: 1 |
| groq | allam-2-7b | 5/6 | not_tested: 1, valid: 1, failed: 2, inconclusive: 2 |
| groq | canopylabs/orpheus-arabic-saudi | 1/1 | inconclusive: 1 |
| groq | canopylabs/orpheus-v1-english | 1/1 | inconclusive: 1 |
| groq | llama-3.1-8b-instant | 5/6 | not_tested: 1, failed: 5 |
| groq | llama-3.3-70b-versatile | 5/6 | not_tested: 1, failed: 5 |
| groq | meta-llama/llama-prompt-guard-2-22m | 1/1 | partial_validity: 1 |
| groq | meta-llama/llama-prompt-guard-2-86m | 1/1 | partial_validity: 1 |
| groq | minimaxai/minimax-m2.7 | 5/6 | not_tested: 1, failed: 5 |
| groq | openai/gpt-oss-120b | 5/6 | not_tested: 1, valid: 4, inconclusive: 1 |
| groq | openai/gpt-oss-20b | 5/6 | not_tested: 1, valid: 3, failed: 1, inconclusive: 1 |
| groq | openai/gpt-oss-safeguard-20b | 1/1 | partial_validity: 1 |
| groq | qwen/qwen3.8-27b | 5/6 | not_tested: 1, valid: 5 |
| groq | whisper-large-v3 | 2/2 | failed: 1, valid: 1 |
| groq | whisper-large-v3-turbo | 1/2 | not_tested: 1, valid: 1 |

As evidências e parâmetros de cada tentativa estão em complete.json; complete.csv contém uma linha por operação. model-summary.json conserva todos os impedimentos por ID. benchmark-sources-current.json contém consulta por ID e ausência de score confirmado. A análise de fontes primárias revisadas está em ../AUREN-BENCHMARKS-GEMINI-GROQ-2026-10-14.md. As sondagens posteriores do adaptador/worker e de imagem têm relatórios separados, não estão misturadas nas 338 tentativas acima.

Retomada: executar run no mesmo diretório conserva tentativas concluídas; não remover blockers nem repetir cobranças sem motivo e limites verificáveis. Arquivos auxiliares herdados de outros provedores servem ao harness; não representam sondagens novas desses provedores.
