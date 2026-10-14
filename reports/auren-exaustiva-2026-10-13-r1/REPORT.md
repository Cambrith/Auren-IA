# Auren — rodada exaustiva r1 (em reconciliação)

Snapshot: 2026-10-13T14:53:41.339877-03:00. Consolidação: 2026-10-14T07:35:09.206411-03:00. Fuso America/Sao_Paulo.

**A validação exaustiva ainda não está concluída.** 6348 linhas para 1590 rotas; 5797 linhas com chamada real e 7343 tentativas concluídas registradas. Nenhuma evidência histórica foi contada como chamada desta rodada.

| Estado | Linhas |
|---|---:|
| failed | 4669 |
| in_progress | 3 |
| inconclusive | 651 |
| not_tested | 559 |
| partial_validity | 18 |
| valid | 448 |

Custos positivos retornados: **US$ 0.10158795**, em 155 respostas. Custos ausentes: **7176 tentativas reais**. Zero informado: 15 respostas. Não são valores de fatura e não provam plano gratuito.

Autorizações: sondagens pequenas já autorizadas; imagens até US$ 20 no total e US$ 0,50 por chamada, com preços verificáveis. Não se comprou crédito, adicionou cartão ou ativou faturamento.

## Universo, contratos e metodologia

União do catálogo local, inventário histórico, registro do motor, catálogos oficiais sem filtros da interface e candidatos documentados. IDs exatos e aliases permanecem distintos por provedor. Cloudflare usa o nome @cf/…; UUID de cadastro não é ID de inferência. Cohere foi consultada sem filtro de endpoint chat. OpenRouter inclui catálogos separados de imagens e embeddings.

Cada operação tem critério em complete.json/CSV. Texto exige duas provas complementares. Código é inspecionado por AST sem execução. Visão/PDF usam bytes sintéticos com identificadores omitidos do prompt. Embeddings exigem vetores finitos, dimensões e comparação. Ferramentas sintéticas não são executadas. HTTP 200 isolado não aprova.

Erros do próprio ensaio permanecem no histórico de tentativas; correções limitadas são anexadas. Truncamento, fila e transporte não implementado permanecem inconclusivos ou não testados. Custos desconhecidos e limites ausentes não são convertidos em zero ou ausência de quota.

## Preservação e verificação

O executável de auditoria é independente; não altera elegibilidade, perfis, cofre, conversas, interface ou adaptadores de produção. Estado privado existente não é exportado. Credenciais são lidas do cofre e jamais gravadas no journal. O diff contém apenas o novo harness, testes e artefatos desta rodada.

Verificações atuais são registradas em verification.json. Não se exige rebuild da interface quando não há mudança frontend.

## Comparação com o histórico e benchmarks

Cada linha contém historical_probe separado; versões e provedores não herdam acesso, gratuidade ou pontuação. Os números de benchmarks anteriores permanecem históricos. Nesta rodada, benchmark=not_confirmed_for_exact_version_in_new_round até revisão de fonte/metodologia específica. Uma página disponível ou palavra de avaliação não confirma score.

Não foi alterada a ordem dos perfis. Sugestões condicionais serão consolidadas a partir de operações válidas, preços confirmados, compatibilidade e latência; nenhuma aprovação curta implica ranking universal ou qualidade ampla.

## Retomada

Execute a partir do checkout da interface, com o Python existente do motor e PYTHONPATH apontando ao src do motor. O comando run reutiliza o mesmo diretório e pula operações terminadas. Pedidos interrompidos com intenção gravada ficam inconclusivos e não são reenviados automaticamente. Jobs assíncronos têm IDs em remote/; consulte antes de qualquer novo envio. Não execute discover/plan sobre uma rodada com chamadas: use diretório novo para novo universo.

```bash
PYTHONPATH=../cavren-nextchat/src ../cavren-nextchat/.venv/bin/python scripts/auren_exhaustive_probe.py run --run reports/auren-exaustiva-2026-10-13-r1 --max-seconds 3600
PYTHONPATH=../cavren-nextchat/src ../cavren-nextchat/.venv/bin/python scripts/auren_exhaustive_probe.py report --run reports/auren-exaustiva-2026-10-13-r1
```

## Impedimentos contabilizados

| Motivo | Linhas |
|---|---:|
| sem bloqueio específico | 958 |
| native_image_price_bound_unverified | 18 |
| wrong_operation_for_system_one | 9 |
| wrong_operation_for_native_websocket | 1 |
| interrupted_request_unknown | 5 |
| research_agent | 6 |
| contract_review | 31 |
| finetune | 8 |
| official_endpoint_deprecated | 2 |
| deprecated_downloadable_nim_no_configured_endpoint | 3 |
| image_per_call_ceiling | 4 |
| image_units_not_bounded_by_verified_contract | 41 |
| inventory_correction_music_text_is_lyrics | 20 |
| estimated_request_cost | 37 |
| inventory_correction_documentation_category_not_operation | 25 |
| transport_not_implemented | 1 |
| inventory_correction_no_native_batch_operation | 17 |
| configured_realtime_gateway_permission_denied | 1 |
| native_video_price_review | 8 |
| canonical_image_price_contract_pending | 14 |
| verified_vietnamese_fixture_pending | 1 |

Toda linha permanece no CSV/JSON, incluindo operações nunca chamadas. Transporte pendente é lacuna de implementação, não impedimento externo comprovado. A ausência de credenciais OpenAI/Anthropic não retira suas rotas se forem descobertas localmente.

## Fontes oficiais consultadas

- [Contratos OpenRouter](https://openrouter.ai/docs/api_reference/overview), [Batch](https://openrouter.ai/docs/batch-quickstart).
- [Gemini API](https://ai.google.dev/api), [preços](https://ai.google.dev/gemini-api/docs/pricing), [Batch](https://ai.google.dev/gemini-api/docs/batch-api).
- [Mistral API](https://docs.mistral.ai/api), [FIM](https://docs.mistral.ai/api/endpoint/fim), [embeddings](https://docs.mistral.ai/api/endpoint/embeddings).
- [Cohere Embed](https://docs.cohere.com/reference/embed), [Rerank](https://docs.cohere.com/reference/rerank), [Parse](https://docs.cohere.com/reference/parse), [transcrição](https://docs.cohere.com/reference/create-audio-transcription).
- [Groq modelos](https://console.groq.com/docs/models), [voz](https://console.groq.com/docs/text-to-speech).
- [NVIDIA voz](https://build.nvidia.com/nvidia/magpie-tts-multilingual/api), [embeddings](https://docs.api.nvidia.com/nim/reference/nvidia-nv-embedqa-e5-v5-infer).
- [Cloudflare modelos](https://developers.cloudflare.com/workers-ai/models/), [Clef](https://developers.cloudflare.com/ai/models/%40cf/cloudflare/clef-flash/).
