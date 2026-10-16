# Auren — continuação ordenada dos testes restantes

Rodada iniciada em 2026-10-15T08:21:47.834731-03:00. Atualizada em 2026-10-15T09:48:12.252745-03:00.

**Não foram todos testados.** Operações sem chamada permanecem identificadas no CSV/JSON.

Ordem obrigatória: Gemini → Groq → Z.ai → Ollama Cloud → Cohere → Mistral. Outros provedores somente depois.

Esta rodada retoma operações sem chamada ou inconclusivas e consulta novamente os catálogos. Sucessos e recusas históricos, incluindo as rodadas posteriores de visão e imagem de 14/10, ficam separados em `coverage.csv`; não são apresentados como chamadas novas.

## Etapas

| Provedor | Estado | Operações restantes |
|---|---|---:|
| gemini | reconciled | 24 |
| groq | reconciled | 14 |
| zai | reconciled | 2 |
| ollama | reconciled | 0 |
| cohere | reconciled | 23 |
| mistral | reconciled | 10 |
| deepseek | reconciled | 0 |
| cloudflare | reconciled | 64 |
| nvidia | reconciled | 90 |
| openrouter | reconciled | 16952 |
| aihorde | window_ended_with_pending | 521 |

## Contagem desta continuação

- 17700 combinações de provedor/modelo/operação na matriz de pendências.
- 810 tentativas principais novas; 14 chamadas auxiliares/precondições novas.
- Estados: {"inconclusive": 302, "valid": 38, "not_tested": 17182, "failed": 177, "partial_validity": 1}.
- Custo positivo retornado: US$ 0. Custo desconhecido em 774 tentativas principais. Ausência de preço não significa zero.

## Contratos e limites

A ambiguidade do pedido de ferramentas foi corrigida: o modelo deve emitir a chamada, e o harness não executa funções. Na Z.ai/GLM-4.5, o teste curto usa thinking.type=disabled, conforme o contrato oficial. Classificação Mistral usa /v1/classifications, em vez de chat. Llama Guard e NemoGuard são classificadores; não recebem provas de programação. LLaVA usa pixels no campo image; MeloTTS usa prompt e MP3. PaliGemma exige image_url como string. AI Horde texto usa o contrato assíncrono de prompt bruto, com limite de 128 tokens e contexto de 1024, sem crescimento automático.

Recusas explícitas de recurso não suportado, termos pendentes e operações de treinamento permanecem como impedimentos. Deep Research não é reenviado: a autorização de um planejamento por rota já foi usada. Jobs assíncronos antigos não são duplicados automaticamente. Conferências finais de pedidos síncronos interrompidos exigem revisão do tempo, ausência de ID assíncrono e limite de saída; ficam identificadas em final-followups.json. O custo antigo incerto permanece separado.

Limites herdados de imagem (US$ 20 total, US$ 0,50/chamada) e vídeo (US$ 40 total, US$ 2/chamada) não são reiniciados. A reserva anterior de imagem é US$ 0,78. Custos positivos anteriores são descontados do limite técnico do ensaio; esse controle e o teto de tokens não garantem uma fatura quando o provedor não retorna preço. Há ainda limite de 100 chamadas aceitas com custo desconhecido por provedor nesta continuação.

Nenhum dado pessoal é enviado. Fixtures são sintéticas ou públicas e herdadas, sem novas gerações para construí-las. Não se comprou crédito, aceitou termos, alterou faturamento, promoveu modelos ao automático, modificou a interface ou publicou esta rodada no GitHub.

AI Horde informa concorrência de 30 para esta conta; o ensaio usa no máximo duas tarefas simultâneas, com filas disjuntas por chave e salvamento atômico. As demais etapas usam uma tarefa por provedor. Imagens eventualmente entregues na resposta de cancelamento são decodificadas e contabilizadas; não são descartadas nem aprovadas apenas pelo HTTP 200. Kudos retornados são registrados na unidade nativa e não convertidos em dólares.

## Evidências e retomada

`complete.csv`/`complete.json`: matriz das pendências e tentativas desta rodada. `coverage.csv`: reconciliação com todo o universo histórico. `results.json`: cada tentativa atômica. `order.json`: sequência e conclusão das etapas. `historical-coverage.json`: referências dos resultados anteriores.

Retome com scripts/auren_remaining_probe.py provider --provider NOME --run reports/auren-restantes-2026-10-15-r3; etapas reconciliadas não repetem chamadas. O runner impede avançar enquanto o provedor anterior tiver operações não contabilizadas.

Benchmarks e ordem dos perfis não foram reavaliados nem alterados. Aprovação de uma operação curta não aprova todo o modelo, seu contexto máximo ou suas cotas.

Fontes primárias: [Gemini Batch](https://ai.google.dev/gemini-api/docs/batch-api), [Gemini cache](https://ai.google.dev/gemini-api/docs/caching), [Groq Batch](https://console.groq.com/docs/batch), [Groq voz](https://console.groq.com/docs/text-to-speech), [Z.ai GLM-4.5](https://docs.z.ai/guides/llm/glm-4.5), [Ollama Cloud](https://docs.ollama.com/cloud), [Cohere Chat](https://docs.cohere.com/reference/chat), [Mistral classificadores](https://docs.mistral.ai/api/endpoint/classifiers).
