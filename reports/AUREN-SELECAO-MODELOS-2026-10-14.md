# Auren — seleção de modelos por tarefa

**Registro da etapa anterior de seleção curta.** A rodada posterior Gemini/Groq e o ajuste de imagens estão em [REPORT.md](auren-gemini-groq-2026-10-14-r2/REPORT.md). A configuração atual prioriza Qwen high no Éter e Gemini 3.5 Flash-Lite para entrada multimodal; a tabela abaixo registra a seleção anterior, não a configuração final.

Data: 14/10/2026. A auditoria exaustiva permanece pausada por solicitação do usuário. Esta etapa implementa uma lista curta de candidatos fortes, sem varrer modelos inferiores.

## Critério de decisão

Benchmarks publicados orientam a adequação por tarefa; a implantação só participa do automático se a política de conta existente, a validação real da categoria, a credencial, a compatibilidade dos anexos e a disponibilidade permitirem. Não foi criado um placar universal entre testes com ferramentas, esforço, datasets ou duração diferentes. Os benchmarks não foram reproduzidos localmente.

| Modelo candidato | Evidência publicada | Uso nesta seleção |
|---|---|---|
| Gemini 3.8 Flash | [Model card oficial](https://deepmind.google/models/model-cards/gemini-3-8-flash/): DeepSWE v1.1 73,7%; Terminal-Bench 2.1 89,4%; GDP.PDF 35% all pass | Primeiro candidato em perfis de qualidade, mas a chamada atual devolveu indisponibilidade. Ainda excluído do automático por falta de texto validado nesta rota. |
| Kimi K3 / NVIDIA | [Card do fabricante](https://huggingface.co/moonshotai/Kimi-K3): GPQA Diamond 93,5%; DeepSWE v1.1 67,5%, com esforço máximo e harness Kimi Code | Preferência efetiva de profundidade, engenharia, pesquisa e leitura de texto; demonstrou streaming e preservação dos fatos em documento sintético. Pode demorar mais. |
| Qwen 3.8 27B / Groq | [Card Qwen](https://huggingface.co/Qwen/Qwen3.8-27B): GPQA Diamond 89,2%; LiveCodeBench v6 90,3% | Preferência de rapidez e código geral; passou os quatro contratos selecionados. Preview pode sofrer alterações do provedor. |
| GLM 5.3 / NVIDIA | [Card do fabricante](https://huggingface.co/zai-org/GLM-5.3): TB2.1 88,2%; DeepSWE v1.1 66,9%, em harnesses distintos | Alternativa de engenharia somente quando os filtros de categoria e disponibilidade aprovam a rota; timeout prévio não foi convertido em aprovação. |
| GPT-OSS 120B e 20B / Groq | [Modelos de produção](https://console.groq.com/docs/models), contrato de raciocínio e streaming | Alternativas operacionais. Não escolhidos como líderes universais de benchmark. O teste estrito de função desta etapa falhou; essa categoria não foi promovida a partir dele. |

Os números da tabela pertencem aos fabricantes e às configurações indicadas; não medem os pesos, a quantização, a cota, o esforço ou a qualidade desta implantação.

## Principais efetivos nos 23 perfis

| Tarefa | Perfil preservado | Principal elegível no momento |
|---|---|---|
| chat | Éter | cavren:nvidia:moonshotai/kimi-k3 |
| chat | Ímpeto | cavren:groq:qwen/qwen3.8-27b |
| chat | Insight | cavren:nvidia:moonshotai/kimi-k3 |
| chat | Arquiteto | cavren:nvidia:moonshotai/kimi-k3 |
| image | Centelha | cavren:aihorde:Deliberate |
| image | Aurora | cavren:aihorde:stable_diffusion |
| image | Prisma | cavren:aihorde:stable_diffusion |
| code | Oficina | cavren:groq:qwen/qwen3.8-27b |
| code | Faísca | cavren:groq:qwen/qwen3.8-27b |
| code | Nexo | cavren:nvidia:moonshotai/kimi-k3 |
| code | Forja | cavren:nvidia:moonshotai/kimi-k3 |
| documents | Prisma | cavren:nvidia:moonshotai/kimi-k3 |
| documents | Lente | cavren:groq:qwen/qwen3.8-27b |
| documents | Atlas | cavren:nvidia:moonshotai/kimi-k3 |
| documents | Cartógrafo | cavren:nvidia:moonshotai/kimi-k3 |
| research | Trama | cavren:nvidia:moonshotai/kimi-k3 |
| research | Radar | cavren:groq:qwen/qwen3.8-27b |
| research | Horizonte | cavren:nvidia:moonshotai/kimi-k3 |
| research | Observatório | cavren:nvidia:moonshotai/kimi-k3 |
| speech | Vox | cavren:nvidia:magpie-tts-multilingual |
| transcribe | Escuta | cavren:mistral:voxtral-mini-latest |
| transcribe | Lusofonia | cavren:cohere:cohere-transcribe-03-2026 |
| transcribe | Echo | cavren:cohere:cohere-transcribe-03-2026 |

## Operações e preservação

A seleção automática de texto fica restrita à lista curta. Uma lista sem candidatos elegíveis não se expande silenciosamente para modelos não revisados. A seleção manual continua prioritária, com o controle de possível custo. Pausas por erro, anexos, limite de contexto, perfis por tarefa e respostas parciais foram preservados.

Gemini 3.6 Flash permanece como alternativa já validada somente quando o pedido requer entrada nativa de PDF, áudio ou vídeo e passa os filtros. Textos extraídos de documentos podem usar Kimi/Qwen/GPT-OSS; um PDF digitalizado não é enviado como texto a um modelo sem suporte.

Escuta usa Mistral com detecção automática. Lusofonia e Echo priorizam Cohere com idioma explícito, com Mistral como alternativa. [Cohere Transcribe](https://docs.cohere.com/docs/transcribe) não oferece detecção automática de idioma. Vox mantém a voz Magpie em pt-BR documentada e validada. Não há comparação padronizada suficiente para afirmar que essa voz seja a melhor do mercado.

Os perfis de imagens e as rotas existentes foram preservados. [Nano Banana 2.1](https://deepmind.google/models/model-cards/nano-banana-2-1/) tem avaliações publicadas promissoras, mas a operação correspondente não tem prova de geração elegível para automático nesta conta. Não se habilitou geração paga pelo nome ou pelo benchmark. Vídeo e música não foram adicionados como tarefas novas.

## Verificações e limites

78 testes locais passaram; após a última ordem de prioridades, 19 testes relevantes foram repetidos e passaram (não somar como testes distintos). Foram feitas sondagens curtas apenas nas quatro rotas principais e verificações do worker existente. Sete dos oito casos iniciais do worker passaram. O caso de pesquisa inicial permaneceu como falha no histórico; após revisar o critério para citações numéricas, uma nova checagem da mesma operação concluiu com URL oficial e ID correto. Uma tentativa com outra formulação da consulta não retornou fontes; pesquisa continua sujeita à busca real. Kimi passou o documento adicional em 34,341 s. Nenhuma dessas provas reproduz os benchmarks completos.

O serviço local foi reiniciado para carregar a seleção. Nenhuma dependência de produção ou alteração de frontend foi necessária. O checkout já tinha mudanças locais; elas foram preservadas. As mudanças desta etapa ficaram na integração de seleção, contrato Groq, recomendação por idioma, testes e relatórios. Credenciais e conversas não foram alteradas.

Custos ausentes nas respostas foram registrados como desconhecidos, sem serem tratados como zero. A etapa não comprou créditos, adicionou cartão nem ativou faturamento. Os tetos autorizados para sondagens de imagem/vídeo não foram transformados em autorização de consumo automático.

## Evidências reproduzíveis

- `auren-curated-2026-10-14.json`: tentativas iniciais por contrato.
- `auren-curated-flow-2026-10-14.json`: preparação do job, seleção e worker em streaming.
- `auren-curated-research-followup-2026-10-14.json` e `auren-curated-research-recheck-2026-10-14.json`: impedimento de busca e checagem final de fontes.
- `auren-curated-kimi-documents-2026-10-14.json`: documento sintético com preço ausente e instrução embutida.
- `auren-curated-selection-2026-10-14.json`: seleção declarada, principais efetivos e referências.
