# Auren — cartões, perfis por tarefa e acesso ampliado

Implementação e testes: **13/10/2026**, referência America/Sao_Paulo. Complementa o relatório de benchmarks do mesmo dia; não altera seus resultados históricos. Preserva a interface `cavren-openwebui`, o motor `cavren-nextchat`, o cofre e os controles de confirmação de custo.

## Cartões e formatação

- Na janela ampla, Tarefa, Perfil e Modelo automático têm **176 px de largura** e 54 px de altura.
- O cartão de modelo manual cresce apenas conforme o nome, entre 176 e **224 px**. Nomes maiores recebem reticências e continuam disponíveis por inteiro na lista e na dica do cartão.
- “Modelo” permanece como título tanto em automático quanto em manual. O valor usa a mesma fonte e alinhamento à esquerda; foi removida a centralização especial do automático.
- Em janela estreita, os três cartões recebem a mesma largura proporcional. Os títulos longos podem usar reticências; nenhum nome longo expande a página horizontalmente.

## Perfis próprios de cada tarefa

A definição compartilhada de nomes, IDs e descrições está em `src/lib/utils/aurenProfiles.json`, utilizada pela interface e pela integração. Os IDs existentes dos adaptadores foram preservados.

| Tarefa | Perfis disponíveis | Comportamento |
|---|---|---|
| Automática | **Automático** | Única escolha; selecione uma tarefa para liberar perfis manuais |
| Conversar | **Éter · Ímpeto · Insight · Arquiteto** | Contextos de conversa existentes |
| Gerar imagens | **Centelha · Aurora · Prisma** | Rapidez priorizada, equilíbrio e detalhamento; mantêm os parâmetros dos perfis existentes |
| Gerar código | **Oficina · Faísca · Nexo · Forja** | Uso geral, correção pontual, revisão e arquitetura |
| Analisar documentos | **Prisma · Lente · Atlas · Cartógrafo** | Comparação, extração objetiva, análise e organização estrutural |
| Pesquisa aprofundada | **Trama · Radar · Horizonte · Observatório** | Síntese, pergunta delimitada, análise de evidências e organização da investigação |
| Gerar voz | **Vox** | A voz Magpie já validada, em português do Brasil; não foram inventadas outras vozes |
| Transcrever áudio | **Escuta · Lusofonia · Echo** | Detecção de idioma, português explícito e inglês explícito |

As tarefas de texto recebem instruções específicas por perfil. Cartógrafo e Observatório não herdam um papel de engenharia de software apenas porque reutilizam um ID de roteamento do motor. Forja mantém o contexto de arquitetura sem duplicar nomes públicos.

### Regra de automático e memória

Tarefa Automática implica perfil Automático. A regra vale na interface, na normalização do estado restaurado e na preparação do pedido no servidor. Um modo manual antigo não força Éter, Ímpeto, Insight ou Arquiteto sobre uma tarefa detectada de imagem/áudio. O perfil de imagem e o idioma são detectados/selecionados pelo fluxo automático compatível.

Ao escolher uma tarefa específica, os perfis correspondentes ficam disponíveis. Alternar entre tarefas preserva a escolha manual de cada uma. A escolha de modelo manual permanece independente, sujeita à compatibilidade da tarefa e à confirmação de possível custo. Conversas salvas continuam usando seus parâmetros; uma conversa nova e vazia recarregada segue a regra anterior de iniciar em automático.

## Correção de compatibilidade na transcrição

O teste real de Escuta na Cohere retornou erro de parâmetro. A [referência oficial da API Cohere](https://docs.cohere.com/reference/create-audio-transcription) exige `language` em formato ISO-639-1; o [model card oficial](https://docs.cohere.com/v2/docs/transcribe) informa que não há detecção automática explícita.

- Escuta utiliza a rota Mistral validada para detecção; Cohere é excluída desse perfil antes da chamada.
- Lusofonia e Echo aceitam Cohere com `pt`/`en`, ou Mistral.
- Escolher manualmente Cohere com detecção automática recebe uma orientação para escolher um idioma explícito. Nenhum idioma é inventado.
- A defesa existe na lista da interface, no planejamento de alternativas, na preparação do pedido e no adaptador.

## Testes reais dos perfis

Foram registrados **26 testes de perfil/rota**, abrangendo os **23 perfis operacionais** das sete tarefas. Automático é um seletor local e foi verificado com testes de estado/classificação. Transcrição foi sondada em dois provedores por idioma.

- 19 testes passaram diretamente.
- Seis testes de texto tiveram falha ou prazo excedido no principal; os mesmos contextos passaram em alternativas gratuitas, com o resultado original preservado.
- O teste restante foi a combinação incompatível Escuta/Cohere, corrigida para ser rejeitada localmente e usar Mistral no planejamento automático.
- Cada perfil operacional tem pelo menos um resultado real positivo, considerando as alternativas. Isso não é garantia de disponibilidade permanente nem avaliação ampla de qualidade.

### Imagens e áudio

| Perfil | Rota efetiva | Resultado | Duração |
|---|---|---|---:|
| Centelha | Horde / Deliberate | Imagem real válida | 23,055 s |
| Aurora | Horde / stable_diffusion | Imagem real válida | 11,094 s |
| Prisma | Horde / stable_diffusion | Imagem real válida | 17,063 s |
| Vox | NVIDIA / Magpie | Áudio real válido | 1,381 s |
| Escuta | Mistral / Voxtral | Marcador da transcrição conferido | 0,917 s |
| Lusofonia | Cohere / Transcribe | Transporte com `pt` respondeu | 0,859 s |
| Lusofonia | Mistral / Voxtral | Transporte com `pt` respondeu | 2,443 s |
| Echo | Cohere / Transcribe | Marcador da transcrição conferido | 0,768 s |
| Echo | Mistral / Voxtral | Marcador da transcrição conferido | 0,967 s |

A amostra de transcrição é um WAV público em inglês. Os testes de Lusofonia confirmam o transporte do parâmetro português, **não a precisão da transcrição de português**. Nenhum áudio pessoal foi enviado. Imagens, voz e corpos das respostas não são armazenados nos relatórios.

A fila explica a variabilidade de duração: Centelha foi mais lenta que Aurora nesta rodada. Seu nome não representa uma garantia de tempo. Mais passos tampouco provam qualidade superior em cada imagem.

[Resultados por perfil e alternativas](AUREN-TESTES-PERFIS-2026-10-13.json).

## Sondagens ampliadas de modelos

A autorização explícita deste pedido permitiu chamadas curtas a rotas anunciadas como pagas, sem o teto zero usado na etapa anterior. O ensaio está separado do uso normal da Auren: não alterou o plano da conta, não adicionou créditos, não ativou faturamento e **não promoveu os aprovados a alternativas gratuitas**.

Foram concluídas **471 sondagens OpenRouter** de rotas anteriormente bloqueadas pelo critério de preço, incluindo 49 operações de imagem. As demais rotas já tinham registros reais na etapa anterior; esses resultados foram reaproveitados. O catálogo foi atualizado, e a evidência disponível foi conferida para os modelos que voltaram a aparecer.

| Resultado HTTP | Chamadas | Interpretação |
|---|---:|---|
| 200 | 268 | API respondeu; 253 passaram na checagem da operação e 15 não |
| 402 | 108 | Falta de crédito/cota de pagamento na solicitação |
| 404 | 81 | Rota não encontrada/disponível; inclui aliases e variantes batch |
| 400 | 9 | Pedido/operação rejeitado |
| 429 | 5 | Limitação de taxa observada |

A checagem textual usa uma conta aritmética pequena. Imagens requerem um arquivo de imagem válido retornado pelo adaptador. Nenhuma prova de acesso transforma um modelo em gerador de vídeo, agente irrestrito ou executor de código.

### Custo observado

**215 respostas informaram custo positivo**, somando **US$ 0,07574093** no campo retornado pela API. Outras respostas não forneceram esse campo ou foram anteriores à captura dele. A soma é **parcial**, não o custo total de uma fatura nem uma confirmação de cobrança em cartão. Não foi possível confirmar a origem do saldo/crédito que permitiu as respostas.

Um rótulo de catálogo não foi usado como prova de custo. As rotas que responderam nesse ensaio continuam com gratuidade não comprovada e confirmação de possível custo no uso manual. A autorização foi para testes; o automático continua utilizando somente evidência gratuita e compatibilidade validadas.

[CSV das 471 sondagens](AUREN-ACESSO-AMPLIADO-2026-10-13.csv). Os cabeçalhos de cota retornados pela API estão no campo `limits` do CSV; um campo vazio significa que não foram informados/capturados, nunca que não há limite. Nenhum modelo foi declarado “sem limite”: sucesso pontual não mede a cota máxima. Cotas são específicas da conta, rota e momento; por exemplo, a [documentação oficial de limites Groq](https://console.groq.com/docs/rate-limits) descreve limites próprios por modelo e cabeçalhos de acompanhamento.

## Verificação

- **104 testes de integração** aprovados, incluindo a regra de automático, memória por tarefa, contextos, alternativas e rejeição local da combinação Cohere/detecção.
- **48 testes de interface** aprovados, incluindo perfis e largura limitada dos cartões.
- Build de produção concluído. Os avisos da base não impediram a compilação.
- A conferência nativa e suas capturas são registradas após a execução final abaixo.

Não houve instalação de dependências de produção, troca de arquitetura ou publicação automática no GitHub. As referências e os resultados anteriores permanecem no [relatório de benchmarks](AUREN-BENCHMARKS-2026-10-13.md).

### Conferência nativa final

- Janela ampla: **176 / 176 / 176 px**, com tipografia e altura iguais.
- Modelo manual Tiny Aya Water: **196 px**, título Modelo e alinhamento à esquerda. O texto manteve a mesma posição horizontal ao alternar automático/manual.
- Janela de 520 × 720: três cartões de **153,33 px**, sem overflow horizontal.
- Conferidos os nomes e escolhas de perfil de todas as sete tarefas, incluindo restauração ao alternar para Automática e retornar à tarefa.
- Tarefa Automática mostrou exatamente uma opção de perfil: Automático.
- Cohere ausente no seletor do perfil Escuta e presente no perfil Echo.
- Fundo de abertura #080d17 e pulso do ícone preservados.
- `git diff --check` aprovado. Relatórios exportam somente metadados permitidos, sem corpos de resposta ou credenciais.

[Registro estruturado da interface](AUREN-VERIFICACAO-PERFIS-2026-10-13.json), [cartões automáticos](auren-perfis-cartoes-automaticos-2026-10-13.png) e [modelo manual](auren-perfis-cartoes-manual-2026-10-13.png).
