# Auren — anexos automáticos e perfis de imagem

Implementado e verificado em 14/10/2026 no checkout `cavren-openwebui`. O motor do checkout irmão foi preservado. Alterações locais anteriores, conversas, cofre, credenciais, nomes dos perfis e configurações foram preservados. O serviço local `lunvri.service` foi reiniciado após a compilação e confirmou estado ativo.

## Comportamento dos anexos

O arquivo é preparado independentemente das capacidades do modelo selecionado. Depois, a ponte verifica as modalidades de toda a conversa e seleciona uma rota compatível. Se o modelo manual aceitar todos os anexos, ele mantém a prioridade. Se não aceitar, apenas a requisição usa o roteamento automático; a escolha da interface e o modo de conversa são preservados. A resposta registra o modelo solicitado, o modelo efetivo, as modalidades e a troca. O fluxo exibe “Usando um modelo compatível com os anexos nesta mensagem”.

Os fallbacks recebem os mesmos anexos e o mesmo contexto. Limites de quantidade de imagens, credenciais, custo, cota/cooldown, contexto e evidência continuam sendo verificados. Consentimento de custo não é transferido ao fallback. Uma resposta já iniciada não é substituída silenciosamente.

Anexo sem instrução também entra na classificação: PDF e texto extraído de documento sugerem Analisar documentos; imagem, áudio e vídeo sem outro pedido entram em Conversar. Pedidos explícitos de transcrição continuam utilizando o roteador especializado de transcrição. A presença de um anexo não decide sozinha que o usuário quer gerar outra imagem.

### Rotas para analisar imagens

A ordem abaixo é a política anterior às verificações de credenciais, preço, evidência, limites e disponibilidade. Uma rota bloqueada não é chamada só por estar nesta tabela.

| Tarefa/perfil | Prioridade e alternativas |
| --- | --- |
| Conversar — Éter | Groq Qwen 3.8 27B → Gemini 3.5 Flash Lite → Cohere Command A Vision → Cohere Command A+ → NVIDIA Llama 3.2 11B Vision → Cloudflare Qwen 3.8 27B |
| Conversar — Ímpeto | Groq Qwen → NVIDIA Llama Vision → Gemini Lite → Cohere Vision → Cohere A+ → Cloudflare Qwen |
| Conversar — Insight/Arquiteto | Groq Qwen → Cohere A+ → Gemini Lite → Cohere Vision → NVIDIA Llama Vision → Cloudflare Qwen |
| Analisar documentos com imagens | Cohere Vision → Cohere A+ → Gemini Lite → Groq Qwen → NVIDIA Llama Vision → Cloudflare Qwen |
| PDF nativo, áudio, vídeo ou combinação destas modalidades | Gemini 3.5 Flash Lite; sem segundo provedor com transporte nativo comprovado nesta configuração |

IDs completos:

- `groq:qwen/qwen3.8-27b`
- `gemini:gemini-3.5-flash-lite`
- `cohere:command-a-vision-07-2025`
- `cohere:command-a-plus-05-2026`
- `nvidia:meta/llama-3.2-11b-vision-instruct`
- `cloudflare:@cf/qwen/qwen3.8-27b`

Éter preserva o esforço `high` do Qwen; Ímpeto usa `none`. O limite integrado do Qwen Groq é três imagens, e o do NVIDIA é uma. Se o histórico exceder isso, ele é preservado e outra rota é escolhida. Sem rota compatível disponível, o fluxo apresenta impedimento explícito; não descarta a mídia nem simula leitura.

### Formatos

| Arquivo | Tratamento |
| --- | --- |
| PNG, JPEG, WebP | Imagem enviada ao modelo de visão |
| PDF | Leitura nativa, preservando páginas digitalizadas, figuras e layout |
| WAV, MP3, OGG, FLAC, AAC | Áudio nativo para conversa; a tarefa Transcrever áudio mantém seu contrato próprio |
| MP4, MPEG, MOV, WebM | Vídeo nativo |
| DOCX, PPTX, ODT | Texto extraído localmente; imagens e layout não são analisados |
| XLSX | Valores em cache, até 2.000 linhas por planilha; fórmulas não são executadas |
| TXT, Markdown, CSV/TSV, JSON/XML, texto e código | Texto local; sem execução de código |

O limite é cinco anexos por mensagem, 20 MB por arquivo e 24 MB somados no histórico preparado. Extração de texto: até 180 mil caracteres; PPTX: até 80 slides. Limitações são informadas no conteúdo extraído. Formatos fora do contrato, como M4A, GIF e SVG, recebem mensagem explícita; isso não é suporte universal a arquivos. HEIC mantém o caminho de conversão já existente na interface. Arquivos de outras contas continuam rejeitados.

## Geração de imagens

Os três perfis compartilham a política de candidatos, preservam as dimensões salvas e aplicam os parâmetros também aos modelos alternativos. Parâmetros explícitos válidos têm prioridade sobre o preset.

| Perfil | Modelo/prioridade | Parâmetros e fallbacks |
| --- | --- | --- |
| Centelha | Ordem dinâmica por tempos medidos, falhas recentes e trabalhadores no snapshot. Recomendação observada nesta entrega: Deliberate | Até 12 passos. Rotas comprovadas: Stable Diffusion, Deliberate, AbsoluteReality, Abyss OrangeMix; ordem ajustada pela evidência |
| Aurora | Gerador padrão salvo; na ausência de preferência, Stable Diffusion | Passos e dimensões salvos; padrão de passos: 20. Ordem base: Stable Diffusion → Deliberate → AbsoluteReality → Abyss OrangeMix |
| Prisma | Deliberate | Pelo menos 30 passos. Ordem base: Deliberate → Stable Diffusion → AbsoluteReality → Abyss OrangeMix |

“Detalhado” descreve os parâmetros do perfil; não é uma certificação comparativa de qualidade. Mais passos podem consumir mais kudos e aumentar a espera. A fila comunitária continua variável. Tempos antigos e quantidade de trabalhadores não são promessa de tempo futuro.

Geração automática continua restrita ao AI Horde com evidência da operação, sem promover Gemini/OpenRouter ou outras rotas pagas. A lista manual da interface mostra 165 modelos anunciados pelo AI Horde no snapshot atual; isso não significa que todos foram testados. Os modelos pagos continuam nas configurações para eventual uso futuro. O controle de alternativas do modelo manual foi preservado.

Edição, máscara e geração com imagem de referência não foram habilitadas no AI Horde: seu adaptador não transporta a referência. O usuário recebe impedimento explícito, com alternativa de analisar o anexo em Conversar/Automática. Nenhuma referência é descartada para produzir uma imagem sem ela.

## Evidência desta entrega

Testes reais com arquivos sintéticos e modelo solicitado GPT OSS 120B, sem confirmação de faturamento, usando `prepare_job → auren_fallback.run → adaptador do provedor`:

| Entrada | Resultado observável | Rota efetiva | Tempo desta chamada |
| --- | --- | --- | --- |
| Imagem | Leu `PIXEL-739` e contou `2|1` formas | Gemini 3.5 Flash Lite, após uma tentativa na primeira rota | 7,506 s |
| PDF | Leu `PDF-628` | Gemini 3.5 Flash Lite; tarefa automática Analisar documentos/Atlas | 6,654 s |
| Áudio | Transcreveu “Auren está pronta. Bom dia.” | Gemini 3.5 Flash Lite | 5,356 s |
| Vídeo | Leu `PIXEL-739` e contou `2|1` formas | Gemini 3.5 Flash Lite | 2,568 s |

A primeira chamada de imagem registrou fallback, mas o código específico da falha inicial não foi gravado por essa versão do probe. Não se atribui a causa a saldo ou cota. O fluxo agora publica `failure_code` nos eventos de fallback para futuras verificações.

Uma chamada adicional pela compatibilidade de chat da Auren confirmou a visão do Cohere Command A+ (`PIXEL-739|2|1`, 1,666 s). Seu sinalizador de visão foi corrigido no catálogo validado. As demais evidências de leitura de imagem vêm da rodada real anterior de 14/10, em `auren-vision-candidates-2026-10-14`.

O custo financeiro efetivo destas cinco sondagens permanece **desconhecido**, separado de custo zero: as respostas não forneceram um total financeiro verificável. Não houve compra de créditos, cartão adicionado ou ativação de faturamento. Sucesso da chamada não determina gratuidade nem cota ilimitada.

Verificações locais:

- 179 testes do motor: passaram.
- 20 testes do backend: passaram, em banco temporário.
- 25 testes de frontend: passaram, em quatro arquivos de teste do código atual.
- Compilação de produção: passou com heap de 6 GB, após a tentativa padrão atingir o limite de memória.
- `git diff --check`: passou.
- Interface nativa em perfil temporário: aceitou PNG/PDF/WAV/MP4 com GPT OSS 120B selecionado; os uploads foram simulados e não houve geração nem gravação de conversa.
- Regressão nativa do seletor: uma busca, somente AI Horde na geração, pagos preservados nas configurações, navegação por teclado, retorno à conversa, aviso amarelo e janela estreita sem transbordamento.
- Contrato dos presets Horde verificado com transporte HTTP simulado nos modelos principal e alternativo. **Nenhuma nova geração real do AI Horde foi solicitada nesta entrega**; a evidência de funcionamento dos quatro geradores vem da rodada anterior.

Artefatos rastreáveis:

- `auren-media-routing-live-2026-10-14.json`: quatro chamadas reais e rotas efetivas.
- `auren-media-compatibility-2026-10-14.json`: chamada real de visão Cohere A+.
- `auren-attachment-ui-2026-10-14.json`: admissão da interface com uploads simulados.
- `auren-media-imagens-seletor-ui-2026-10-14.json`: regressão do seletor.
- `auren-media-imagens-seletor-amplo-2026-10-14.png`, `auren-media-imagens-seletor-estreito-2026-10-14.png`, `auren-media-imagens-controles-2026-10-14.png`: capturas sintéticas da interface.
- `scripts/auren_media_routing_probe.py`: sondagem retomável que não repete casos já registrados nem repete automaticamente uma chamada interrompida.

Esta entrega valida o roteamento implementado e as sondagens descritas. Não representa novo teste exaustivo de todo o catálogo, de todos os formatos aceitos ou de todos os modelos Gemini/Groq. Cotas, filas, disponibilidade e qualidade em documentos longos continuam sujeitos aos limites dos provedores e dos arquivos.
