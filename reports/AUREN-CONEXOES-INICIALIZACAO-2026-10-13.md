# Auren — persistência das conexões e abertura

Data: 2026-10-13T07:52:49.514571-03:00.

## Escopo

Correção das conexões que desapareciam após desligar o PC, demora de abertura, foco azul em Arquivo e movimento inicial. A reorganização de tarefas e o lote de geração de imagens de 2026-10-12 continuam pausados. Não houve chamada de geração, gasto, instalação de dependências de produção, alteração de provedor do cofre do sistema ou modificação do motor irmão.

## Causa confirmada das conexões

Neste login, org.freedesktop.secrets pertence ao GNOME Keyring. A busca dos atributos application=cavren nesse serviço retornou zero itens. O serviço org.kde.secretservicecompat encontrou 12 itens existentes no cofre KDE; as conexões ativas de dez provedores, além dos campos auxiliares, puderam ser recuperadas sem redigitar chaves. Uma leitura real de Gemini pelo endereço genérico retornou ausência; pelo endereço KDE retornou presença. Nenhum valor foi exibido ou incluído neste relatório.

A seleção anterior dependia de quem assumia o endereço genérico no login. As credenciais existentes não haviam sido apagadas. Além disso, consultas remotas malsucedidas substituíam o catálogo local por uma lista incompleta, causando perda de opções e espera na abertura.

## Correções

1. Auren persiste a identidade do cofre em .cavren/credential_backend.json, arquivo privado contendo apenas versão e endereço D-Bus. Nesta instalação, está fixado org.kde.secretservicecompat. Uma mudança de ambiente ou da ordem de inicialização não troca o cofre. Erro ou configuração ilegível falham explicitamente, sem procurar silenciosamente outro cofre vazio.
2. Leitura e gravação existentes usam libsecret/secret-tool com esse endereço no ambiente do processo Auren e de seus filhos. Isso não muda GNOME Keyring, KWallet, o login nem as outras aplicações. Antes de salvar, a Auren exige uma coleção persistente e rejeita coleção de sessão.
3. A identidade de credenciais já salvas é registrada somente por nomes, sem valores, em .cavren/credential_inventory.json. Chave salva, cofre temporariamente inacessível e consulta recusada pelo provedor são estados separados. Não há expiração local por tempo decorrido. A chave é relida do cofre nas operações; indisponibilidade não autoriza exclusão nem substituição.
4. Catálogo salvo é servido imediatamente. Descoberta automática acontece em segundo plano, com controle de concorrência. Falha de rede, catálogo inválido, erro de autenticação ou chave temporariamente ilegível preservam modelos existentes e o estado de configuração. A atualização explícita continua disponível em Conexões.
5. Metadados são gravados de forma atômica, com sincronização do arquivo e diretório. Credenciais continuam exclusivamente no cofre; não foram duplicadas em JSON ou banco da interface.
6. A janela direciona o foco inicial ao conteúdo, mantendo os menus acessíveis por teclado. Arquivo não é marcado inicialmente. O marcador da janela nativa é preparado antes da montagem da página.
7. O ícone de abertura não aumenta/diminui. As transições de layout ficam desativadas durante restauração inicial; a tela só revela o chat após montagem, carregamento das fontes e dois quadros de layout. A animação junto à mensagem e a logo lateral estática preexistentes foram preservadas.
8. A verificação de prontidão do serviço usa a rede assíncrona do Qt, evitando bloquear a janela; intervalo de 250 ms e prazo total de 180 s.

## Verificação real em 2026-10-13

- Dez provedores recuperados do cofre existente. Nove catálogos consultados com sucesso; Z.ai permanece configurado pela rota estática, sem chamada de geração nesta execução. Catálogo acessível não comprova geração ou gratuidade.
- Consulta externa completa: aproximadamente 1,724 s na medição. Leitura local em processo novo: 0,0732 s. Consulta de estado público: 0,259 s. Essas medições não representam reinício completo do PC.
- Três processos novos, alternando ambiente GNOME/KDE/GNOME e forçando o endereço genérico no ambiente: mesmos dez provedores recuperados em todos, graças ao endereço persistido da Auren.
- Uma entrada sintética de teste foi salva no cofre KDE, relida e sua coleção persistente confirmada por metadados D-Bus. A entrada criada exclusivamente para esse teste foi removida e a ausência confirmada. Nenhuma chave existente foi substituída ou apagada.
- Serviço da Auren reiniciado: 18,916 s até /api/config estar pronto. Janela Qt real no compositor: interface pronta em 2,172 s com backend já disponível; Arquivo sem foco inicial/final; marcador nativo presente; 22 medições de barra lateral/compositor de mensagem estáveis durante dois segundos após exibição. A janela de teste foi fechada.
- Captura da barra nativa, sem dados pessoais: [barra inicial](auren-barra-inicial-2026-10-13.png).

## Investigação da demora restante

O primeiro início desta manhã demorou aproximadamente 18 segundos até a prontidão do backend; o reinício medido nesta execução levou 18,916 s. Não foi reproduzido um atraso específico causado apenas por desligamento prolongado.

Um perfil isolado, com banco temporário, sem credenciais e sem servidor público, concluiu a importação de open_webui.main em 15,264 s. O tempo acumulado de importação do módulo principal foi 13,459 s; a cadeia de eventos/extração de páginas carregou langchain_text_splitters (6,370 s acumulados), incluindo sentence_transformers (4,668 s). Esses tempos são aninhados e não devem ser somados. Isso identifica carregamento pesado do backend como uma parte importante do atraso restante. Bibliotecas já presentes não foram removidas, substituídas nem alteradas para reduzir artificialmente a medição.

A espera remota dos catálogos e o bloqueio da janela foram corrigidos. A redução dos cerca de 19 segundos do serviço exigiria um trabalho adicional de carregamento sob demanda desses recursos, com validação de documentos e recuperação; essa mudança mais ampla não foi introduzida nesta correção focada.

## Testes simulados e locais

- 58 testes Python de início/cofre, preferências, tarefas, validação, filtros de imagem, alternativas e pesquisa aprovados.
- 19 testes adicionais de ponte e mídia aprovados.
- 33 testes frontend aprovados.
- Build de produção aprovado; verificação de diff e compilação Python aprovadas.
- Casos simulados: reinício com outro ambiente, endereço persistido inválido, coleção de sessão recusada antes da escrita, metadados sem segredos, catálogo frio sem esperar rede, falha de provedor preservando modelos, cofre ilegível preservando configuração e falha de atualização preservando arquivo anterior.

## Limites da garantia

O tempo desligado não expira as credenciais locais e a escolha do cofre não depende mais da corrida entre os serviços desta instalação. Nenhum software pode garantir que uma chave continue válida após revogação pelo provedor, exclusão manual do cofre, perda do disco ou indisponibilidade do serviço de segredos. A Auren deve informar essas condições sem fingir que a chave foi apagada pelo aplicativo. Não houve desligamento/reinício real do PC durante a validação; foram usados novos processos, reinício do serviço, consultas reais e simulações de falha. As alterações da barra nativa carregam na próxima abertura da janela normal.

## Fontes primárias

- [Secret Service: coleções e itens](https://specifications.freedesktop.org/secret-service/latest/ch03.html).
- [Secret Service: bloqueio e desbloqueio](https://specifications.freedesktop.org/secret-service/latest/unlocking.html).
- [Implementação oficial libsecret](https://raw.githubusercontent.com/GNOME/libsecret/main/libsecret/secret-service.c), incluindo seleção do nome do serviço.
- [Qt: QWidget e política de foco](https://doc.qt.io/qt-6/qwidget.html).

## Arquivos principais

- integration/auren_credentials.py
- integration/lunvri_connections.py
- integration/auren_settings.py
- scripts/auren_window.py e scripts/lunvri_desktop.py
- src/app.html, src/lib/utils/aurenStartup.ts e pontos de montagem do chat/layout
- src/lib/components/chat/Settings/AurenConnections.svelte
- tests/test_auren_startup.py e tests/check_auren_startup_window.py
