# Auren — refinamento e verificação

Atualizado em 12/10/2026. Trabalho aplicado ao projeto existente, sem substituir o motor, apagar conversas, cadastrar chaves novas ou instalar dependências de produção. Os ajustes posteriores de janela prevalecem sobre a proposta inicial de remover a barra.

## Resultado implementado

- Barra superior nativa com Voltar, Avançar, alternância da barra lateral e menus Arquivo, Editar, Exibir e Ajuda. Os menus executam ações reais da aplicação: novo chat, anexar, exportar JSON, edição, configurações, zoom, atalhos e Sobre.
- Três controles à direita: minimizar, maximizar/restaurar e fechar. O mesmo botão central troca o desenho e o nome acessível conforme o estado. Em janelas estreitas, os menus se agrupam.
- Restaurar aplica 910×600 e centraliza na área útil do monitor pelo KWin, respeitando a barra de tarefas. Removida a sobrescrita de 1200×820 no inicializador. O caminho completo foi verificado após a abertura maximizada e após mover/redimensionar a janela: ambos retornaram a 910×600 em x=228/y=61 na área útil local de 1366×722.
- F11 alterna tela cheia real e recupera o estado normal ou maximizado. Qt/KWin distingue os dois estados; a restauração maximizada espera a confirmação da saída de tela cheia.
- Movimento pelo espaço livre da barra e redimensionamento pelas bordas usam as funções nativas do Qt. Não foi alterada a decoração global do KDE.
- Seletor de modelos com pesquisa, agrupamento, filtro de provedor e tipos de uso, dimensões limitadas à janela, rolagem interna e navegação por teclado.
- Nome real e provedor nos modelos externos. Ausência de permissões deixou de significar “privado” para modelos do catálogo. Configurações e imagens de modelos personalizados permanecem preservadas.
- Logotipos locais das famílias identificadas; o provedor aparece separadamente e fornece o ícone quando a marca específica não está identificada. SVGs do Lobe Icons e favicon oficial do AI Horde, com origem/licença em `static/brand-icons/`.
- Conta: foto original aceita, salvamento sem erro falso de autenticação, validação de datas e apresentação DD/MM/AAAA. O banco e a API continuam usando ISO.
- Conexões mostra os provedores do motor, distingue acesso ao catálogo de permissão/cota de geração, permite configurar chaves no cofre e nunca devolve seus valores na consulta de estado.
- Texto de Conexões simplificado, sem referência ao documento local, com aviso reformulado sobre chave, saldo e uso pago. A contagem distingue “1 modelo” de “0 modelos” e “2 modelos”.
- OpenAI e Anthropic preparados sem chaves cadastradas e sem ativação a partir de credenciais incidentais do ambiente/documento. A futura configuração explícita habilita o catálogo; gerar exige confirmação de possível custo. Não entram nas alternativas gratuitas automáticas.
- Imagens: gerador padrão persistido, parâmetros válidos do AI Horde, pedido de teste, resultados exibidos e opção de salvar. Parâmetros Horde não são enviados a Gemini/OpenRouter.
- Sobre identifica Auren, o fork real, a base Open WebUI 0.12.0, créditos e licença existentes.
- Preferências administrativas persistidas, preservando endereço e token temporários da ponte como dados específicos de cada execução.
- Anexos multimodais e documentos mantidos. A interface avisa para trocar de modelo ao tentar enviar imagem a um modelo sem visão. A animação original de atividade permanece discreta e com deslocamento reduzido; não há avatar repetido nas respostas.

## Causas confirmadas

| Problema | Causa observada | Correção |
|---|---|---|
| Salvar conta retornava “Invalid authentication request.” | A validação rejeitava `/cambrith-avatar.png`; o tratamento comum das rotas de autenticação ocultava a causa da resposta 422. | Caminho estático exato permitido, preservação do endereço original quando usado seu alias de perfil e mensagem de validação específica. |
| Perfil não mantinha edições | Login local voltava a impor nome/foto iniciais. | Valores iniciais somente na criação; login preserva o perfil existente. |
| Todos os modelos se chamavam Auren | O catálogo enviava um nome único para todas as rotas. | Nome do modelo separado do provedor e do protocolo da ponte. |
| Catálogo externo aparecia como privado | A interface aplicava a regra de ACL de modelos personalizados a itens externos sem registro de permissões. | Identificação “Externo”; permissões reais de modelos personalizados preservadas. |
| Conteúdo escapava do seletor | Altura externa limitada sem contenção flexível adequada da lista interna. | Limites de viewport, `min-height: 0`, rolagem própria e tratamento de nomes longos. |
| Configurações administrativas desapareciam | Persistência global desabilitada. | Persistência normal habilitada, com exceção dos dados efêmeros da ponte. |
| Saída de tela cheia perdia maximização no Wayland | Solicitação de maximizar concorria com a confirmação da saída de tela cheia. | Transição em duas etapas, verificada no compositor real. |

Não foi necessário alterar senha, criar uma senha temporária ou substituir a autenticação para corrigir o salvamento do perfil.

## Configurações: alcance da auditoria

As categorias e seus componentes/rotas foram inspecionados. Leituras autenticadas de 15 endpoints de configurações/dados retornaram JSON com HTTP 200. Isso verifica acesso e esquema, não prova cada controle individual.

| Categorias | Situação |
|---|---|
| Geral, Interface, Notificações, Teclado, Personalização | Fluxos existentes de preferências preservados; persistência de usuário e configuração administrativa inspecionada. |
| Conta | Salvamento real pela interface e API verificado; foto, formato de data, rejeição de data inválida e persistência testados. |
| Controle de Dados, Uso, Chats Arquivados | Funcionalidades existentes preservadas. Não foram executadas exclusões/importações sobre dados pessoais para testar controles destrutivos. |
| Sobre | Identidade, versão base, repositório, créditos e licença conferidos na interface. |
| Administração: Geral e Autenticação | Sessão local identificada. Senha/MFA de acesso remoto não são necessários para salvar o perfil e não são apresentados como requisitos desta instalação. |
| Administração: Interface e Modelos | Configurações existentes mantidas; nomes, origem, pesquisa, ícones e classificação dos modelos corrigidos. |
| Conexões | Estado do motor real; 12 provedores apresentados. OpenAI/Anthropic sem chave e sem chamada de geração real. |
| Imagens | Preferências e geração real pelo AI Horde verificadas. Gemini/OpenRouter têm adaptadores e proteção de custo; geração paga não testada. |
| Pesquisa na Web | Controle da Auren usa SearXNG local. A configuração adicional do Open WebUI foi preservada e identificada como mecanismo distinto. |
| Documentos | Extração local de anexos mantida. Indexação de uma base RAG depende de embeddings e serviço próprio ainda não configurados. |
| Áudio | Recursos existentes mantidos. APIs de transcrição/síntese não foram configuradas ou declaradas funcionando sem teste. |
| Subagentes, Integrações, Execução de Código, Pipelines | Recursos avançados existentes preservados; a ponte da Auren não é apresentada como servidor de ferramentas, áudio ou execução de código. Serviços externos adicionais não foram provisionados. |
| Análises, Avaliações, Banco de Dados | Seções existentes mantidas; sem experimentos destrutivos ou alteração da base pessoal. |

## Verificação executada

### Testes automatizados e de contrato

- Ponte: autenticação, origem/host, modo/modelo, eventos, streaming, fontes, arquivos e interrupção do processo na desconexão.
- Mídia: classificação conservadora, proteção de custo, formatos e transporte de geração de imagens.
- Alternativas: erros/cotas, seleção de alternativas gratuitas compatíveis, preservação de texto parcial e fila de imagens com transportes simulados.
- Preferências/cofre: validação, persistência, arquivo com acesso restrito, rollback em falha de confirmação e consulta de estado sem credenciais.
- Perfil/configuração: foto local, rejeição de caminhos perigosos/datas inválidas/futuras e configuração persistente sem substituir dados efêmeros da ponte.
- Novos provedores: ausência de chaves por padrão, filtro de catálogo, cabeçalhos Anthropic, metadados de visão e `max_completion_tokens` OpenAI — APIs simuladas.
- Datas pt-BR e escolha das marcas dos modelos: testes de interface/utilitários.
- Janela Qt/Wayland: minimizar, maximizar/restaurar no mesmo botão, fechar, F11 normal e maximizado, restauração, controles contidos e redimensionamento. A minimização foi confirmada no KWin, porque o Qt não refletia corretamente esse estado no Wayland.
- Integração nativa com a interface real: menus Sobre/Configurações, barra separada do conteúdo, agrupamento em janela estreita e F11 com foco dentro da página.
- Build de produção, compilação Python e verificação de whitespace do diff.

### Testes reais

- Perfil salvo pela interface com HTTP 200; a falha 422 da foto não se repetiu. Perfil e preferências de imagem permaneceram após reiniciar o serviço.
- Catálogos dos provedores já configurados consultados. “Catálogo acessível” não é tratado como confirmação de cota de geração.
- Imagem anexada pelo navegador e interpretada por Qwen/Cloudflare: a resposta descreveu a forma de três arcos e o gradiente azul/ciano do símbolo enviado. Anexo e resposta permaneceram ao recarregar a conversa.
- Tentativa de anexar imagem ao Cohere Command R7b mostrou aviso para selecionar um modelo com visão, sem enviar uma solicitação incompatível.
- AI Horde aceitou pedidos reais gratuitos e retornou imagens. Resultado 512×512 foi exibido na tela Imagens. Bytes da imagem foram decodificados e validados; download Qt WebEngine concluiu com conteúdo idêntico.
- O seletor permaneceu contido em 1366×722 e 420×430, com rolagem interna. Pesquisa de nomes extensos e filtro de provedor foram conferidos.

## Limitações e pendências explícitas

- OpenAI/Anthropic não receberam chaves nesta entrega. Geração real nesses dois serviços depende da futura chave/saldo; somente contratos foram testados. A Anthropic usa a camada Chat Completions compatível, sem prometer os recursos nativos completos de Claude.
- Gemini/OpenRouter: geração de imagens paga não foi executada. A disponibilidade de um modelo no catálogo não implica gratuidade ou permissão de gerar.
- AI Horde usa fila comunitária e kudos; tempo e disponibilidade variam. Não há compra automática de créditos.
- O download da imagem pela automação do navegador integrado não produziu um evento de download. O mesmo fluxo foi verificado com sucesso no Qt WebEngine utilizado pelo aplicativo desktop.
- Vídeos/áudio e recursos avançados não foram testados em todas as APIs. Contratos e classificação não equivalem a teste real de cada modelo.
- Arrastar/redimensionar com o mouse físico não foi automatizado: foram implementados os mecanismos nativos e conferidos geometria/bordas. Não foram alteradas regras globais do sistema para contornar isso.
- A checagem global de tipos do projeto continua apresentando erros herdados. Foi comparada com uma cópia da revisão original, e as alterações desta entrega não adicionaram diagnósticos novos após os ajustes específicos. O build de produção é uma verificação distinta.
- Não foi alegado que centenas de modelos externos ou cada configuração avançada foram testados individualmente.

## Principais componentes

- `scripts/auren_window.py`, `scripts/lunvri_desktop.py`: barra nativa, menus, estados e carregamento da janela.
- `src/routes/(app)/+layout.svelte`: ações da barra nativa integradas às funções existentes da interface.
- `src/lib/components/chat/LunvriControls.svelte`: seletor responsivo e escolha de modo/modelo.
- `src/lib/components/admin/Settings/Models.svelte`, `AurenProviderBadge.svelte`, `src/lib/utils/modelBrand.ts`: nomes, proveniência e logotipos.
- `integration/lunvri_connections.py`, `integration/auren_settings.py`, `backend/open_webui/routers/auren.py`: catálogo, conexões, cofre e preferências.
- `integration/lunvri_manual.py`, `lunvri_bridge.py`: conversa, arquivos e geração de imagens.
- `backend/open_webui/models/config.py`: persistência com exceções de execução.
- `backend/open_webui/utils/validate.py`, `routers/auths.py`, `routers/mfa.py`, `models/users.py`, `Settings/Account.svelte`, `birthDate.ts`: correção do perfil e validação/apresentação de data.
- `Settings/AurenConnections.svelte`, `Settings/AurenImages.svelte`, `Settings/About.svelte`, `src/lunvri.css`: configurações e identidade visual.
- `tests/`: verificações específicas. Evidências locais e logs ficam em `.cavren/`, fora do versionamento.

## Recomendações

Priorizar a redução dos erros de tipos herdados em uma tarefa separada, validar cada novo provedor com sua futura credencial e manter a distinção entre catálogo, cota e geração real. Não habilitar uso automático sujeito a cobrança para contornar falta de modelos gratuitos.

## Ajuste de Conexões e escolha de imagens — 12/10/2026

- Conexões mostra somente a quantidade de modelos, sem contagem de geradores nem o aviso de acesso ao catálogo. Os cartões estão em ordem alfabética pelo nome exibido.
- A área local de Conexões/Imagens tem altura limitada ao modal e rolagem própria; o conteúdo inferior e a configuração de chave continuam acessíveis.
- O botão de imagens funciona também quando o modelo de conversa não gera imagens. Mantém uma escolha manual compatível; caso contrário, seleciona o padrão gratuito disponível ou um gerador gratuito compatível. Sem opção gratuita, abre a seleção sem escolher automaticamente uma rota paga.
- A interface identifica o gerador ativo, permite trocá-lo e voltar à conversa. O modo e o modelo anteriores são preservados durante a alternância; pesquisa e escolha de modo ficam desativadas enquanto se descreve uma imagem. Os modos continuam determinando o trabalho de conversa, sem fingir alterar parâmetros de um gerador de imagens.
- Escolhas pagas manuais continuam exigindo a confirmação de custo. A seleção do botão não inicia uma chamada: o pedido só é enviado ao enviar a mensagem.
- Oito testes adicionais verificam compatibilidade, disponibilidade, escolha do padrão, exclusão de seleção paga automática e ordenação.

Verificação desta etapa: 26 testes de interface/lógica passaram; build de produção concluído e nenhuma nova ocorrência de tipos em comparação com a base. Na prévia real, a roda do mouse levou Conexões do topo ao fim em 520×573 e 1366×722. O botão selecionou Stable Diffusion/AI Horde partindo de Arquiteto/Automático; a lista de troca continha 231 opções com suporte a geração, e a volta recuperou Arquiteto/Automático. Não foi enviado um novo pedido de geração nem feita uma chamada paga nesta etapa.
