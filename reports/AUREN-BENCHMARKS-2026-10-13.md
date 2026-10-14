# Auren — validação real, benchmarks e apresentação

> **Atualização posterior no mesmo dia:** os novos nomes de perfis, a regra tarefa/perfil automático e os testes de rotas anunciadas como pagas estão no [relatório de perfis e acesso ampliado](AUREN-PERFIS-E-ACESSO-2026-10-13.md). Os resultados abaixo pertencem à etapa anterior.

Data da consolidação: **13/10/2026**, fuso de referência America/Sao_Paulo. As linhas individuais preservam o horário e o fuso de cada teste. Checkout da interface `cavren-openwebui`; motor existente `cavren-nextchat`. Este relatório substitui a tabela de modelos da primeira etapa de roteamento do mesmo dia.

## 1. O que foi feito

- Inventário de **852 rotas de provedor**, incluindo versões, aliases e operações específicas. Um mesmo modelo em dois provedores representa duas rotas: acesso, fila, velocidade e cota não são transferíveis.
- Testes reais curtos, autorizados, com as credenciais existentes no cofre e conteúdo sintético. Nenhuma ativação de faturamento, compra de créditos ou recarga foi feita.
- Provas específicas de código, documentos e pesquisa, além da resposta curta. Os aprovados não são habilitados para uma categoria apenas por estarem no catálogo.
- Ordem centralizada de recomendação e alternativas, filtrada por evidência gratuita, categoria, credencial, contexto, compatibilidade e disponibilidade.
- Classificação automática local em português: instruções explícitas, negações, pedidos de explicação, pedidos mistos e continuidade. Documentos, citações e blocos de código são dados, não instruções de roteamento. Escolhas manuais têm prioridade.
- Nova conversa inicia com tarefa Automática, modo Automático e modelo Automático. Conversas existentes mantêm suas escolhas.
- Abertura usa o fundo **#080d17**, igual ao fundo principal da Auren. Logo, pulso e transição foram preservados.
- O cartão automático tem o título **Modelo** e o valor **Automático**, com a tipografia dos demais cartões. A palavra “Externo” foi retirada da identificação dos modelos nas configurações.
- Configurações de interface recebem **Mostrar detalhes da resposta**, desligado por padrão. Os dados do modelo, modo e tarefa continuam disponíveis para inspeção, mas ficam ocultos nas respostas comuns.
- Imagens são armazenadas temporariamente na ponte e publicadas uma vez, somente após a conclusão. Texto intermediário do gerador é suprimido. Um erro não publica o arquivo temporário. O componente também aguarda o estado concluído antes de exibir a imagem.

## 2. Resultados reais de texto

O teste básico pede o resultado de 17 × 23 e confere 391. Trata-se de prova de acesso, transporte e resposta mínima, não de qualidade geral ou resistência adversarial. Falhas na checagem estrita não provam que um modelo seja incapaz de outras tarefas.

| Provedor | Rotas de texto no inventário | Chamadas no teste básico | Aprovadas no teste básico | Resultado observado |
|---|---:|---:|---:|---|
| Cloudflare | 33 | 33 | 17 | Acesso, plano, parâmetros, tempo e resposta variaram |
| Cohere | 17 | 17 | 16 | R7B não passou na checagem atual; não é promovido pela medição anterior |
| Gemini | 37 | 37 | 6 | Cotas, versões indisponíveis/retiradas e erros de acesso |
| Groq | 4 | 4 | 3 | Qwen 3.8 encontrou limitação de taxa |
| Mistral | 27 | 27 | 10 | Limitações de taxa e acesso em parte das rotas |
| NVIDIA | 61 | 61 | 13 | Muitas versões anunciadas retornaram indisponibilidade |
| Ollama | 16 | 16 | 6 | Cota esgotada em parte dos modelos; não foi ativado plano pago |
| OpenRouter | 440 | 18 | 10 | Rotas gratuitas anunciadas testadas; demais tratadas separadamente com teto zero |
| Z.ai | 1 | 1 | 0 | GLM 4.5 Flash excedeu o prazo deste teste |

**OpenRouter:** houve ainda **437 chamadas com teto de preço zero**, das quais 7 passaram na prova aritmética; parte repete rotas do teste básico. Não somar esses aprovados aos 81 como se fossem modelos novos. Outras 52 rotas de imagem foram separadas do teste textual. O retorno `not_found` sob teto zero pode significar ausência de provedor compatível com preço zero, não inexistência do modelo. Nos primeiros testes, o teto cobria prompt e completion; a implementação final também cobre request e image. As contas não tinham créditos adicionados, conforme declaração do usuário. Nenhuma rota paga foi chamada com autorização de cobrança.

O contrato do teto foi conferido na [documentação oficial de seleção de provedores](https://github.com/OpenRouterTeam/docs/blob/main/guides/routing/provider-selection.mdx), e o contrato de imagens na [documentação oficial de geração de imagens](https://openrouter.ai/docs/guides/overview/multimodal/image-generation).

### Tabela completa por modelo

[AUREN-TESTES-MODELOS-2026-10-13.csv](AUREN-TESTES-MODELOS-2026-10-13.csv) contém **869 linhas de operação** para as 852 rotas: texto, imagem, voz e transcrição. Inclui sucesso/falha, custo comprovado ou não, duração, quantidade de amostras, datas, categoria aprovada e fonte de benchmark. Algumas rotas têm mais de uma operação. Tempos de falhas são duração até o erro, não tempo médio de geração bem-sucedida. Não há chaves, respostas do usuário, áudios pessoais ou conteúdo de conversas no relatório.

Todas as 852 rotas do inventário têm ao menos uma chamada real registrada em uma operação. Há três operações textuais não chamadas em rotas tratadas pelo fluxo de imagens; elas permanecem explicitamente identificadas no CSV. Isso não significa aprovação das 852 rotas nem validação de todas as modalidades de cada modelo.

**Nenhum modelo foi declarado ilimitado.** Uma chamada curta comprova acesso naquele momento; não mede o teto da cota, limites por minuto/dia, contexto máximo ou disponibilidade futura. `rate_limit` e `quota_exhausted` registram restrições observadas, sem concluir automaticamente que é necessário pagar. Planos de avaliação e redes comunitárias continuam sujeitos a limites.

## 3. Ordem atual dos modos

Esta é a política implementada da Auren, apoiada em documentação oficial, avaliações publicadas e testes locais. **Não existe um ranking oficial único entre fabricantes**, e testes com diferentes versões, ferramentas e esforço de raciocínio não podem ser combinados como um placar universal.

| Modo | Principal atual | Objetivo | Duas chamadas reais com contexto do modo |
|---|---|---|---|
| Éter | Gemini 3.6 Flash / Gemini | Conversa geral e instruções | 1,741 s e 1,468 s; média 1,605 s |
| Ímpeto | GPT OSS 20B / Groq | Respostas breves e baixa latência | 0,631 s e 0,774 s; média 0,703 s |
| Insight | Kimi K3 / NVIDIA | Análise e raciocínio | 7,507 s e 9,015 s; média 8,261 s |
| Arquiteto | GLM 5.3 / NVIDIA | Engenharia, planejamento e código | 13,762 s e 10,145 s; média 11,954 s |

Essas oito chamadas reais usaram transporte em fluxo e os contextos especializados, mas um pedido aritmético pequeno. Não reproduzem DeepSWE, GPQA ou um projeto longo. A ordem efetiva completa está no [resumo estruturado](AUREN-TESTES-RESUMO-2026-10-13.json). Os filtros são reaplicados por tarefa: Kimi K3 falhou no prazo do teste de documentos e GLM 5.3 falhou no prazo do teste de pesquisa; isso impede sua promoção nessas categorias, embora tenham passado em conversa/código.

### Fontes oficiais e critérios

- Éter: [model card Gemini 3.6 Flash](https://deepmind.google/models/model-cards/gemini-3-6-flash/), com avaliações de contexto e instruções. A adequação como principal é uma decisão de produto, não dedução de superioridade universal.
- Ímpeto: [documentação Groq](https://console.groq.com/docs/models) e [publicação GPT OSS](https://openai.com/index/introducing-gpt-oss/), juntamente com a latência real observada. A velocidade publicada pelo provedor não é garantida em cada pedido.
- Insight: [model card Kimi K3](https://huggingface.co/moonshotai/Kimi-K3), avaliações de raciocínio e análise. Esforço máximo e ferramentas dos benchmarks diferem da configuração da Auren.
- Arquiteto: [model card GLM 5.3](https://huggingface.co/zai-org/GLM-5.3), com avaliações de engenharia, e prova local específica de código. A Auren não executa os programas gerados.
- Alternativas: [Qwen 3.8 27B](https://huggingface.co/Qwen/Qwen3.8-27B), [relatório Nemotron 3 Ultra](https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf), [Command A+](https://docs.cohere.com/docs/command-a-plus), [Gemini 3.1 Flash Lite](https://deepmind.google/models/model-cards/gemini-3-1-flash-lite/) e [Codestral](https://legal.mistral.ai/ai-governance/models/codestral/).

[Referências revisadas](AUREN-BENCHMARKS-REFERENCIAS-2026-10-13.json) registra 16 entradas e seus limites metodológicos. [Inventário de fontes](AUREN-BENCHMARKS-INVENTARIO-2026-10-13.csv) cobre as 852 rotas, com **332 fontes públicas distintas consultadas** e **128 indicações de seções de avaliação**. Encontrar palavras de avaliação automaticamente é apenas uma pista: não significa que seus números foram revisados. Não foi possível confirmar um benchmark exato para todos os aliases e versões. Fontes de modelo base não provam desempenho de quantização, adaptação ou implantação de outro provedor.

## 4. Tarefas e evidência

| Tarefa | Rotas elegíveis | Teste real | Decisão e limites | Data |
|---|---:|---|---|---|
| Conversar | 81 | Acesso e aritmética; oito amostras adicionais dos principais | Independente; modelos gratuitos com limites | 13/10/2026 |
| Gerar código | 73 | Função simples; validação estrutural Python, sem execução | Independente; não é execução de código | 13/10/2026 |
| Analisar documentos | 69 | Documento sintético, fatos e resistência a instrução embutida | Independente; não comprova leitura de todo formato/tamanho | 13/10/2026 |
| Pesquisa aprofundada | 15 | Duas buscas reais locais e síntese com referências fornecidas | Independente; pesquisa limitada e planejada, sem agente irrestrito | 13/10/2026 |
| Gerar imagens | 4 | Duas imagens reais nos quatro geradores elegíveis; novas rotas e filas também sondadas | Independente; rede comunitária, fila e trabalhadores variáveis | Sucessos em 12/10; sondagens em 13/10/2026 |
| Gerar voz | 1 | Magpie, duas respostas de áudio reais | Independente; prova da operação, não de todas as vozes/parâmetros | 13/10/2026 |
| Transcrever áudio | 2 | Cohere e Mistral, duas amostras por rota | Independente; WAV público de teste, nenhum áudio pessoal | 13/10/2026 |
| Automática | Apenas elegíveis acima | Classificação e prioridades testadas localmente; execução reaproveita os fluxos | Seleção local explicável; ambiguidade retorna a conversa | 13/10/2026 |
| Vídeo, música e execução de código | 0 | Não integrados nem testados como operações completas | Inventário futuro; não ativados pelo nome de um modelo | Não testado |

A voz teve 37,755 s e 7,597 s. Transcrição Cohere: 1,149 s e 0,857 s; Mistral: 0,838 s e 1,022 s. Esses pedidos curtos não estabelecem tempo constante ou limite de tamanho.

### Imagens e Rápido/Detalhado

Mantida a separação entre modos de conversa e perfis de imagem. As evidências anteriores confirmam dois sucessos por gerador elegível: AbsoluteReality média 33,808 s; Abyss OrangeMix 10,587 s; Deliberate 22,436 s; stable_diffusion 43,873 s. Medições de perfil e parâmetros são distintas dessas médias gerais. O perfil Rápido usa menos passos e escolha compatível; Detalhado usa mais passos. Fila e número de trabalhadores tornam impossível garantir que Rápido sempre termine antes em pedidos independentes.

As novas sondagens de imagens tiveram limites de cota/acesso no Gemini e falta de crédito nas rotas OpenRouter com teto zero. A rede Horde também teve filas superiores ao orçamento de teste. Cancelamento por `benchmark_queue_budget` significa que o tempo de espera informado ultrapassou o orçamento; **não prova que o gerador não funciona**. Os sucessos de 12/10 não são apresentados como novas gerações de 13/10. A entrega única da imagem foi verificada com resultados simulados da ponte e testes de apresentação; não houve nova imagem bem-sucedida produzida pela interface nesta conferência final.

## 5. Verificação e pendências

Resultados finais de build, interface e testes locais estão no registro de verificação acrescentado ao final deste documento. Os testes de apresentação usam dados simulados, e os testes reais de API estão identificados nas tabelas e no CSV.

Limitações: cotas máximas não foram esgotadas deliberadamente; duração de um teste curto não mede qualidade ampla; aliases podem mudar; catálogo pode anunciar uma rota sem acesso; erros transitórios não são prova de incapacidade permanente; benchmarks de todas as versões não foram confirmados numericamente. Não foi instalado pacote de produção nem trocada a arquitetura. As alterações desta etapa estão no checkout local, sem publicação automática no GitHub.

### Registro final de verificação

- **102 testes de integração aprovados**: classificação, ordem e filtros, parâmetros, alternativas, cofre simulado, validação, compatibilidade, arquivos, mídia e ponte.
- **10 testes de backend aprovados** em banco temporário: eventos antigos/cancelamento, configurações persistentes e anexos.
- **44 testes de interface aprovados**: tarefa, inicialização, seleção de imagem, identidade dos modelos, datas e apresentação de respostas.
- Teste da ponte com arquivo simulado: nenhum arquivo antes da conclusão; uma publicação no sucesso; nenhuma publicação na falha; texto intermediário suprimido. Dez testes da ponte foram novamente aprovados após o ajuste dos detalhes de perfil.
- Build de produção concluído; há avisos do compilador em componentes da base. Não houve erro de build.
- Prévia local reiniciada e pronta em `http://127.0.0.1:8175/`.
- Janela própria e descartável, com 1200 × 720 e 520 × 720: tipografia igual, cartões de 54 px, menus roláveis com seleção visível, sem overflow horizontal. Três recarregamentos, minimizar/restaurar e geometria estáveis. O pulso continuou alterando apenas a transformação do ícone.
- A opção Mostrar detalhes da resposta foi alternada pela interface, persistiu após recarregar e terminou desligada. Esse teste utiliza a configuração real local, mas nenhuma conversa ou pedido de geração real.
- `git diff --check` aprovado. Verificação dos relatórios não encontrou padrões conhecidos de credencial; somente metadados permitidos foram exportados, sem cabeçalhos ou corpos de resposta.

[Registro visual estruturado](AUREN-VERIFICACAO-INTERFACE-2026-10-13.json) e [prévia dos cartões](auren-final-seletores-2026-10-13.png).
