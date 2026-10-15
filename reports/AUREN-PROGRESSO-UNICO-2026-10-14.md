# Auren — progresso único na resposta

Ajuste de 14/10/2026, inicialmente mantido apenas no computador, conforme solicitado na ocasião. Incluído na atualização para o GitHub autorizada pelo usuário em 15/10/2026.

A duplicação vinha do histórico de status do Open WebUI e do indicador animado da Auren renderizados simultaneamente. Durante a geração, a etapa atual passa a ser apresentada pelo próprio indicador animado. O histórico continua armazenado, sem alterar os eventos dos provedores, e pode ser inspecionado após a conclusão quando a opção de detalhes técnicos estiver ativada. A apresentação dos modelos externos à integração Auren foi preservada.

O indicador acompanha a descrição atual da pesquisa, mantém consultas e resultados acessíveis pelo componente existente e passa para organização das informações e redação conforme o progresso. Uma nova etapa substitui a anterior no mesmo indicador. Ao concluir ou receber erro, o indicador de geração deixa de ser exibido; resposta, fontes, arquivos e erros mantêm seus componentes existentes.

Na geração de imagens, o mesmo indicador reúne a etapa, o tempo decorrido e os dados efetivamente informados de fila e estimativa. A ausência de uma estimativa continua sem número inventado. O resultado visual é um único indicador, que pode quebrar o texto em linhas para caber em uma janela estreita.

Verificações desta alteração:

- Seis testes de apresentação passaram: filtro de detalhes, métricas, entrega de arquivos, transições de pesquisa, progresso unificado de imagem e espera sem status visível.
- Compilação dos dois componentes alterados e build de produção passaram.
- Verificação nativa em perfil isolado e conversa temporária: um único status de pesquisa, logo ativo, substituição da etapa, resultados de busca acessíveis, um único indicador de imagem, janela estreita sem transbordamento e resposta normal sem progresso após a conclusão.
- `git diff --check` passou. O serviço local confirmou estado ativo.

O teste nativo usou uma resposta de requisição simulada e eventos Socket.IO sintéticos pelo receptor da interface. Não realizou pesquisa ou geração real em um provedor nem gravou conversa. Os números de fila das capturas são fixtures de teste, não medições reais. Esta verificação confirma a apresentação, sem revalidar a qualidade dos modelos ou das fontes.

Evidência: `auren-progresso-unico-ui-2026-10-14.json`.

Capturas: `auren-progresso-unico-pesquisa-2026-10-14.png` e `auren-progresso-unico-imagem-2026-10-14.png`.

Verificação retomável da interface: `tests/check_auren_progress_ui.py`. O teste intercepta requisições de geração e bloqueia gravações de conversa; depende do serviço local e de uma conexão de eventos disponível.
