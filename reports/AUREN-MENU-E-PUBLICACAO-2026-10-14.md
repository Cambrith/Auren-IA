# Auren — menu +, ícones e consolidação para GitHub

Alterações implementadas em 14/10/2026 no repositório `Cambrith/Auren-IA`, branch `main`.

## Interface

- “Pesquisar na web” é uma ação direta no menu +, com a mesma altura, tipografia, espaçamento e bordas dos outros itens.
- A ativação permanece visível por indicação e estado acessível `aria-pressed`; um segundo clique desativa a busca.
- O campo Plugins, seu submenu e o atalho Gerar imagens foram removidos do +.
- Geração de imagens continua pelo seletor de tarefa e mantém seus perfis, modelos e fallbacks.
- A busca continua no caminho SearXNG existente, com as restrições para imagem, voz, transcrição e a tarefa que já realiza pesquisa.
- Perfis de código, documentos, pesquisa e transcrição têm ícones próprios; tarefas e perfis de conversa/imagem preservam seus ícones.
- O campo do modelo selecionado mostra a marca local da família ou provedor, mantendo o indicador de custo. Nenhuma nova dependência de produção foi adicionada.

## Verificação

- Compilação de produção: passou, com heap de 6 GB.
- 179 testes do motor: passaram.
- 20 testes do backend: passaram em banco temporário.
- 57 testes de frontend, em nove arquivos: passaram.
- Verificação nativa dos 23 perfis, dos ícones e do menu: passou em perfil temporário, sem geração ou gravação de conversa.
- O item direto de busca foi ativado e desativado; ficou desabilitado durante geração de imagem, preservando a regra existente.
- Layout de janela estreita, 520 px: passou sem transbordamento.
- Código Python novo/modificado: compilação sintática passou.
- `git diff --cached --check`: passou. Exportações CSV e a captura da página oficial preservam seu whitespace; fixtures PDF são marcadas como binárias nos atributos Git.
- Serviço local reiniciado após a compilação, confirmado ativo. A primeira tentativa da verificação nativa antecedeu a disponibilidade do servidor; o teste agora espera HTTP 200 e a repetição passou.

Evidência nativa: `auren-menu-ui-2026-10-14.json`.

Capturas de uma conversa temporária, sem conteúdo pessoal:

- `auren-menu-mais-2026-10-14.png`
- `auren-menu-mais-estreito-2026-10-14.png`
- `auren-menu-seletores-2026-10-14.png`
- `auren-menu-perfis-documentos-2026-10-14.png`

## Escopo consolidado

O conjunto inclui as alterações locais pendentes da Auren: roteamento por tarefa, classificação automática, perfis e fallback, contratos multimodais, preparo de anexos, seletor de imagens comunitárias, progresso das respostas, interface, scripts de sondagem, testes, relatórios e fixtures sintéticas das rodadas anteriores. Não representa nova validação de todos os modelos anunciados: resultados, custos desconhecidos, operações não chamadas e impedimentos históricos permanecem nos relatórios.

O cofre, as chaves dos provedores, bancos de conversas, runtimes, caches locais e arquivos temporários de execução não integram o conjunto versionado. O cotejo dos arquivos com as credenciais configuradas não encontrou correspondências. Uma captura HTML de página oficial continha nove chaves de configuração públicas do próprio site; essas sequências foram ocultadas na cópia para publicação, preservando o original no diretório local ignorado `.cavren/publication-originals/2026-10-14/`.

Os checkouts separados `cavren` e `cavren-nextchat` não foram alterados ou publicados por esta entrega. O destino é o repositório da Auren; suas alterações anteriores no motor permanecem nos respectivos checkouts.
