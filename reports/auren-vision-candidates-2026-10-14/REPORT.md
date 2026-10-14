# Teste prático de modelos que recebem imagens — Auren

**Data:** 14/10/2026. **Operação testada:** imagem de entrada → resposta textual fundamentada nos pixels (`vision/image-understanding`). Este relatório não avalia geração/edição de imagem, OCR especializado em documentos nem vídeos.

## Resultado

Foi usada a mesma imagem sintética em todas as chamadas, com um identificador e formas que não aparecem no prompt. O critério foi reconhecer `PIXEL-739`, contar dois círculos vermelhos e um quadrado azul. Uma chamada só passou se o conteúdo da resposta trouxesse os três elementos corretos. HTTP 200 sozinho não foi considerado sucesso.

| Provedor · modelo · operação | Resultado do teste | Situação da rota Auren | Custo registrado |
|---|---|---|---|
| Gemini · `gemini-3.5-flash-lite` · `generateContent:vision` | **Passou**; respondeu `PIXEL-739|2|1`. | Capacidade `vision` reconhecida. O teste veio da rodada prática anterior deste mesmo dia, não de um novo envio. | **Desconhecido** na resposta do teste; a chamada não forneceu custo/uso suficiente para fechar valor faturado. |
| Gemini · `gemini-flash-lite-latest` · `generateContent:vision` | **Passou**; o provedor resolveu o alias para `gemini-3.5-flash-lite` e respondeu corretamente. | Alias chega ao mesmo modelo estável. | **Desconhecido** na resposta do teste. |
| Groq · `qwen/qwen3.8-27b` · `chat/completions` com `image_url` | **Passou**; identificador e contagens corretos. | Catálogo atual marca `vision=true`; o contrato de imagem é compatível com o usado pelo Auren. | Estimativa por tokens e preço público: **US$ 0,0007056**. Não é comprovante de cobrança. |
| Cohere · `command-a-vision-07-2025` · `v2/chat` | **Passou**; identificador e contagens corretos. | Modelo visual reconhecido pelo catálogo. | **Desconhecido** como custo efetivamente debitado. A Cohere informa acesso gratuito até atingir limites para chaves de avaliação. |
| Cohere · `command-a-vision-07-2025` · `compatibility/v1/chat/completions` | **Passou** também pelo transporte de compatibilidade usado pela integração do Auren. | Esta chamada confirma o caminho de API utilizado pelo Auren para esse modelo. | **Desconhecido** como custo efetivamente debitado. |
| NVIDIA · `meta/llama-3.2-11b-vision-instruct` · `chat/completions` com `image_url` | **Passou**; identificador e contagens corretos. | Catálogo atual marca `vision=true`. | A NVIDIA anuncia endpoint de protótipo gratuito; a resposta não trouxe valor faturado. O débito efetivo fica **desconhecido**. |
| Cloudflare · `@cf/qwen/qwen3.8-27b` · `chat/completions` com `image_url` | **Passou** na tentativa corrigida, com saída suficiente. As duas tentativas anteriores ficaram sem resultado semântico avaliável: uma falha no leitor do relatório e outra atingiu o limite de saída. | Catálogo marca `vision=true`. A integração o considera gratuito, mas a tabela oficial publica preço por tokens; tratei o preço positivo como referência e não presumi franquia gratuita. | Três estimativas pela tabela oficial: **US$ 0,00025035 + US$ 0,00050635 + US$ 0,00052875 = US$ 0,00128545**. Não é comprovante de cobrança. |
| Cohere · `command-a-plus-05-2026` · `v2/chat` | **Passou** na chamada corrigida com saída maior. A tentativa inicial de 48 tokens não chegou a produzir uma resposta final avaliável. | **Auren bloqueia essa modalidade no catálogo atual**: modelo aparece disponível, mas `vision=false`; o filtro de anexos não o libera para mensagens com imagem. | **Desconhecido** como débito. A Cohere informa acesso gratuito até os limites para este modelo. |
| Cloudflare · `@cf/meta/llama-3.2-11b-vision-instruct` · `chat/completions` com `image_url` | **Impedido**: HTTP 403. | O catálogo atual também marca `vision=false`, então a rota é filtrada antes de receber uma imagem no Auren. Não aceitei a licença Meta em nome do usuário; a documentação pede uma ação separada de aceite. O 403 não foi detalhado o bastante para atribuir uma causa única. | **Desconhecido** após a recusa; nenhum custo foi inferido como zero. |

As estimativas positivas que têm tokens e preços públicos totalizam **US$ 0,00199105**. Separadamente, há chamadas com custo efetivo desconhecido. Os valores calculados são referências de preço por token, não extratos de faturamento nem prova de que a conta usou ou não uma franquia gratuita.

## Outros IDs Gemini da lista de candidatos

Estes resultados vieram das sondagens visuais registradas no arquivo `auren-gemini-groq-2026-10-14-r2/complete.csv`. Eles são chamadas reais com imagem, mas **recusa de rota/cota não significa incapacidade visual do modelo**. São impedimentos para confirmar funcionamento na conta naquele momento.

| Modelo Gemini · operação `vision` | Evidência registrada | Conclusão |
|---|---|---|
| `gemini-2.5-flash` | HTTP 404 | Rota não encontrada nessa chamada. |
| `gemini-2.5-flash-lite` | HTTP 404 | Rota não encontrada nessa chamada. |
| `gemini-2.5-pro` | HTTP 404 | Rota não encontrada nessa chamada. |
| `gemini-3-flash-preview` | HTTP 429 | Cota/limite; visão não confirmada. |
| `gemini-3.1-flash-lite` | HTTP 503 | Erro temporário do provedor; visão não confirmada. |
| `gemini-3.1-flash-lite-preview` | HTTP 429 | Cota/limite; visão não confirmada. |
| `gemini-3.1-pro-preview` | HTTP 429 | Cota/limite; visão não confirmada. |
| `gemini-3.1-pro-preview-customtools` | HTTP 429 | Cota/limite; visão não confirmada. |
| `gemini-3.5-flash` | HTTP 429 | Cota/limite; visão não confirmada. |
| `gemini-3.6-flash` | HTTP 429 | Cota/limite; visão não confirmada. |
| `gemini-3.7-flash` | HTTP 429 | Cota/limite; visão não confirmada. |
| `gemini-3.8-flash` | HTTP 429 | Cota/limite; visão não confirmada. |
| `gemini-4-argon` | HTTP 429 | Cota/limite; visão não confirmada naquela chamada. |
| `gemini-flash-latest` | HTTP 429 | Cota/limite; visão não confirmada. |
| `gemini-pro-latest` | HTTP 429 | Cota/limite; visão não confirmada. |
| `gemini-robotics-er-2-preview` | HTTP 429 | Cota/limite; visão não confirmada. |

Há também IDs de Gemini voltados a **gerar imagens** — por exemplo, Nano Banana e variantes `*-image`. Eles ficaram explicitamente como **não testados para compreensão visual**: chamar a operação de geração para tentar obter resposta textual seria misturar contratos. Os modelos `gemini-omni-*` também permanecem **não testados** nesta tarefa; o inventário anterior deixou a chamada pendente de revisão do contrato nativo correspondente.

## Condições e limites

- As chamadas novas usaram uma imagem sintética local, não uma imagem pessoal. O prompt não continha o identificador esperado.
- Cada tentativa direta foi limitada a uma chamada, sem repetição automática, com saída de 48 tokens (512 no seguimento do Qwen/Cloudflare e do Command A+ depois que o limite menor não permitiu avaliar uma resposta final). O endpoint e a modalidade correspondem a entrada visual de chat; não foi aplicado teste de chat a geradores de imagem.
- Cohere Command A Vision foi testado tanto no endpoint nativo quanto no endpoint de compatibilidade que o Auren usa. Nos demais modelos de chat, foram usados contratos OpenAI-compatible documentados pelo respectivo provedor. Gemini foi avaliado pelo resultado de `generateContent` registrado na rodada do dia.
- Estes são testes práticos de API com fixture sintética. Não representam um teste E2E na janela do navegador da Auren.
- O modelo Command A+ passou pela API, mas a configuração atual do Auren não o aceita para anexos porque não sinaliza `vision`. O Llama Vision da Cloudflare também não foi liberado pelo filtro e recebeu 403 no teste.
- Não houve alteração de perfis, interface, adaptadores de produção, cofre, credenciais ou conversas. O checkout já tinha muitas mudanças locais; elas foram preservadas. Os únicos arquivos novos desta tarefa estão neste diretório de relatório.

## Artefatos e reprodução

- `results.json`: chamadas iniciais novas e resumo sanitizado por rota.
- `cloudflare-qwen-correction.json` e `cloudflare-qwen-correction-512.json`: tentativas de correção do Qwen/Cloudflare; a inicial é preservada.
- `cohere-followup.json` e `cohere-aplus-correction.json`: teste de compatibilidade Cohere e tentativa corrigida de Command A+.
- `probe.py`, `cloudflare-qwen-correction.py`, `cohere-followup.py` e `cohere-aplus-correction.py`: sondas limitadas. Lêem a credencial em memória do cofre configurado e não a escrevem no relatório.
- Fixture usada: `reports/auren-gemini-groq-2026-10-14-r2/fixtures/vision.png`; o SHA-256 consta nos JSONs de resultado.

## Fontes oficiais

- [Gemini: compreensão de imagens](https://ai.google.dev/gemini-api/docs/image-understanding), [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [preços Gemini](https://ai.google.dev/gemini-api/docs/pricing).
- [Groq: visão](https://console.groq.com/docs/vision), [Qwen 3.8 na Groq e preço](https://console.groq.com/docs/model/qwen/qwen3.8-27b).
- [Cohere Command A Vision](https://docs.cohere.com/v1/docs/command-a-vision), [Command A+](https://docs.cohere.com/docs/command-a-plus), [API de compatibilidade](https://docs.cohere.com/docs/compatibility-api).
- [NVIDIA NIM: Llama 3.2 11B Vision](https://build.nvidia.com/meta/llama-3.2-11b-vision-instruct).
- [Cloudflare: Qwen 3.8](https://developers.cloudflare.com/workers-ai/models/qwen3.8-27b/), [preços Workers AI](https://developers.cloudflare.com/workers-ai/platform/pricing/), [Cloudflare: Llama 3.2 11B Vision e licença](https://developers.cloudflare.com/workers-ai/models/llama-3.2-11b-vision-instruct/).
