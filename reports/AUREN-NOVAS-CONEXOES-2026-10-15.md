# Novas conexões da Auren — 15/10/2026

## Escopo

Adicionar as entradas presentes no documento privado `Novas Chaves de API`, preservando o cofre, os perfis, a interface e os testes anteriores. O documento principal `Chaves de API - Auren` foi atualizado com as quatro chaves fornecidas, sem remover entradas anteriores. As seções foram ordenadas alfabeticamente e uma cópia privada anterior foi preservada fora do repositório. Claude continua sem chave.

## Implementação

- Novos cards: DeepSeek, Hugging Face e xAI (Grok). Os cards existentes de OpenAI e Anthropic passaram a identificar também ChatGPT e Claude.
- Os 15 cards mantêm a ordenação alfabética pelo nome exibido e usam os logotipos locais já integrantes da Auren. A marca monocromática da xAI ganhou o tratamento de contraste do tema. Os cards não receberam avisos ou blocos extras; o aviso geral ao pé de Conexões foi retirado.
- As quatro novas chaves foram salvas e relidas no cofre persistente. Os documentos são fontes de importação, não dependências de execução da Auren. Nenhuma chave é devolvida no estado público.
- OpenAI, Anthropic, DeepSeek direto e xAI usam política paga explícita. Seleção manual continua exigindo confirmação; automático e fallback não recebem autorização de cobrança por herança.
- Hugging Face usa o roteador oficial de conversa e permanece com custo desconhecido, sem promoção automática a gratuito. Crédito promocional não foi presumido. Não foi acrescentado um bloco de aviso ao seu card.
- Modelos documentados de Claude e Grok permanecem visíveis como reservas desabilitadas quando não há catálogo acessível. Não são apresentados como modelos disponíveis ou validados. A descoberta real substitui essas reservas quando a conta passa a permitir a consulta.
- Na página de Modelos, o pequeno texto já existente ao lado de cada nome recebe “Pago”, “Reservado” ou “Custo a verificar”, conforme a rota. Nenhum card ou bloco adicional foi criado nessa página.
- O seletor da tarefa automática permite encontrar os modelos manuais desses provedores. Isso não altera a seleção automática do motor nem as prioridades dos perfis.

## Consultas reais de catálogo, sem geração

| Provedor | Resultado | Modelos de conversa obtidos da API | Geração nesta atualização |
|---|---|---:|---|
| OpenAI (ChatGPT) | Catálogo acessível | 56 | Não chamada |
| DeepSeek | Catálogo acessível | 2 | Não chamada |
| Hugging Face | Catálogo acessível | 128 | Não chamada |
| xAI (Grok) | HTTP 403; API informa créditos esgotados **ou** limite mensal atingido | 0 | Não chamada |
| Anthropic (Claude) | Sem chave; catálogo não consultado | 0 | Não chamada |

A API da xAI não distingue, nessa resposta, falta de créditos de limite mensal atingido. Não atribuir exclusivamente a um deles. Nenhum crédito foi comprado e nenhum limite de faturamento foi alterado.

Os números são entradas de conversa compatíveis com o seletor; não representam todo o catálogo de operações dos provedores. Embeddings, imagem, áudio e outras modalidades não foram tratados como chat.

## Fontes oficiais consultadas

- Hugging Face, catálogo do roteador: https://huggingface.co/docs/inference-providers/main/hub-api
- xAI, consulta autenticada de modelos: https://docs.x.ai/developers/rest-api-reference/inference/models
- xAI, modelo reservado documentado: https://docs.x.ai/developers/models
- Anthropic, modelos reservados documentados: https://platform.claude.com/docs/en/models/overview
- OpenAI, consulta de modelos: https://developers.openai.com/api/reference/resources/models/methods/list

## Continuação dos testes

A rodada anterior está preservada em `auren-restantes-2026-10-15-r3`. Sua última janela terminou com 263 operações do AI Horde ainda pendentes. A mudança de prioridade foi registrada em `PAUSA-NOVAS-CONEXOES.md`. Hugging Face é uma adição posterior, ainda sem testes reais de geração. Esta entrega não significa que todos os modelos foram testados.

## Verificação da entrega

- 88 testes de configuração, importação de credenciais, confirmação de cobrança, transporte manual, tarefas, anexos e roteamento passaram, com 34 subtestes adicionais.
- Os 4 testes da API local passaram no runtime do backend, com banco de dados temporário separado.
- 36 testes de utilitários da interface passaram.
- A compilação de produção terminou com sucesso usando o limite de memória já indicado pelo instalador do projeto. Permanecem os avisos de componentes já presentes no frontend; nenhum erro impediu a compilação.
- Na janela Qt/WebEngine isolada, os 15 cards apareceram em ordem alfabética e todos os 15 logotipos carregaram. Após o ajuste visual solicitado, os cards mantêm apenas o pequeno texto original de situação, sem blocos extras de aviso. O aviso geral ao pé da página de Conexões também foi retirado. O custo continua indicado no pequeno texto das linhas da página de Modelos e na descrição do seletor, com a proteção de execução preservada.
- Uma busca pelos valores exatos das quatro novas chaves não encontrou nenhuma ocorrência nos arquivos novos ou modificados do repositório.
- O serviço local foi atualizado e voltou a responder HTTP 200. As alterações desta etapa não foram enviadas ao GitHub.

A verificação visual final confirmou ausência de avisos extras em Conexões e as descrições discretas na página de Modelos: `DeepSeek · Pago`, `Hugging Face · Custo a verificar` e `Anthropic (Claude) · Reservado`. A busca do seletor encontrou os novos provedores; Grok e Claude permaneceram desabilitados como reservas. Evidências: `auren-novas-conexoes-ui-2026-10-15.json`, `auren-novas-conexoes-2026-10-15.png` e `auren-modelos-texto-discreto-2026-10-15.png`.
