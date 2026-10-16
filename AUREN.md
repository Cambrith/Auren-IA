# Auren — prévia da interface baseada no Open WebUI

## Atualização para o GitHub — 15/10/2026

As correções locais de progresso único e do fundo da primeira abertura foram
reunidas com seus testes e evidências. O registro da atualização está em
`reports/AUREN-PUBLICACAO-2026-10-15.md`. Dados pessoais e credenciais continuam
fora do versionamento.

## Fundo da primeira abertura — 15/10/2026

A tela nativa que aguarda o serviço usa `#080D17`, assim como o splash da
interface. A janela, o WebEngineView e a página também recebem esse azul antes
do HTML. O logo, seu pulso e a continuidade da animação foram preservados.
`tests/check_auren_cold_start_ui.py` verifica o HTML real de espera, uma página
com cache vazio e espera artificial da API, sem reiniciar o computador ou
interromper o serviço existente. Evidências em
`reports/AUREN-PRIMEIRA-ABERTURA-2026-10-15.md`.

## Progresso único na resposta — 14/10/2026

Durante uma resposta da Auren, somente o indicador animado apresenta a etapa
atual da pesquisa ou geração. O histórico de status continua nos dados da
conversa, e os resultados de pesquisa podem ser abertos pelo próprio indicador.
Ao concluir, o progresso desaparece e a resposta mantém a apresentação normal;
o histórico técnico fica disponível depois da conclusão se a opção de detalhes
estiver ativada. Na geração de imagens, etapa, tempo decorrido, fila e estimativa
recebida do provedor compartilham o mesmo indicador.

Verificação e limites em `reports/AUREN-PROGRESSO-UNICO-2026-10-14.md`.

## Menu + e ícones dos seletores — 14/10/2026

“Pesquisar na web” é um item direto do menu +, com a mesma altura, tipografia,
espaçamento e interação dos outros itens. A indicação de ativação e as restrições
de tarefa foram preservadas. O submenu Plugins e seu atalho Gerar imagens foram
removidos; geração continua pelo seletor de tarefa.

A busca usa um ícone vetorial próprio de lupa com globo, distinguindo-a de
Anexar Página Web. O rótulo usa a mesma estrutura `line-clamp-1` dos demais itens;
a verificação compara também fonte, tamanho, peso, altura da linha e espaçamento
dos textos efetivamente renderizados.

Perfis de código, documentos, pesquisa e transcrição têm ícones próprios para
seus objetivos. A seleção manual de modelo mostra o ícone local da família ou
provedor, mantendo o indicador de custo. Os campos preservam as dimensões e os
rótulos acessíveis. A verificação nativa sem gravações de conversa está em
`tests/check_auren_menu_ui.py`.

## Anexos automáticos e perfis de geração — 14/10/2026

Anexos são preparados antes da escolha da rota. Um modelo manual incompatível
aciona uma rota compatível apenas para aquela requisição, preservando a escolha
da conversa. Imagens têm alternativas comprovadas por modo; PDF, áudio e vídeo
nativos usam Gemini 3.5 Flash Lite na configuração validada. Falta de uma rota
disponível é informada sem remover o anexo. DOCX/PPTX/ODT, planilhas e arquivos
de texto/código usam extração local dentro dos limites documentados.

Centelha aplica até 12 passos e ordena por evidência de velocidade; Aurora mantém
os parâmetros salvos; Prisma prioriza Deliberate com pelo menos 30 passos. Os
fallbacks preservam os parâmetros e a política automática de geração AI Horde.
Referências/edição continuam exigindo um contrato específico compatível.

Contratos, ordens, limitações e evidências reais/simuladas estão em
`reports/AUREN-ANEXOS-E-PERFIS-2026-10-14.md`.

## Seletor de imagens sem pagamento — 14/10/2026

O seletor da conversa oferece apenas a rota nativa comunitária AI Horde, com
preço gratuito em dinheiro. Kudos, fila e disponibilidade dos trabalhadores
continuam sendo requisitos do provedor. Gemini, OpenRouter e os demais geradores
permanecem no catálogo e nas configurações para uso futuro; suas credenciais,
preferências e adaptadores não foram removidos. Uma seleção paga antiga é trocada
por Automático ao entrar na tarefa de imagem, sem apagar o catálogo.

O menu tem uma única busca por nome, provedor ou ID, com termos combinados e
normalização de acentos. A lista usa grupos por provedor, ordem alfabética,
ícones locais, indicação do modelo padrão e foco de teclado. O filtro separado
por provedor e o botão duplicado do gerador padrão foram retirados. Abaixo dos
seletores ficam o controle amarelo de alternativas para o modelo manual e
“Voltar à conversa”, sem o bloco descritivo anterior.

A verificação nativa em perfil isolado está em
`tests/check_auren_image_selector_ui.py`: lista sem pagos, configurações completas,
busca, navegação, alternativas, retorno à conversa e janela estreita. Não solicita
gerações nem salva preferências. Evidências em
`reports/auren-imagens-seletor-ui-2026-10-14.json` e nas capturas correspondentes.

## Seleção por tarefa e rodada Gemini/Groq — 14/10/2026

Éter prioriza Qwen 3.8 27B na Groq com esforço `high`; Ímpeto usa `none`.
Kimi K3 mantém a prioridade efetiva de profundidade nos perfis de qualidade.
Gemini 3.8 Flash é condicional à validação e disponibilidade; as chamadas atuais
receberam indisponibilidade/limite. Gemini 3.5 Flash-Lite passou no adaptador para
conversa, código, documentos e pesquisa com fontes, e no worker com PDF nativo.
Ele substitui a antiga alternativa 3.6 para entrada multimodal compatível.

O Automático mantém as regras locais e usa classificação JSON limitada com Qwen
para pedidos de ação não reconhecidos. Falha retorna à regra local, sem ferramentas,
liberação de cobrança ou envio de bytes de anexos ao classificador. A transcrição
com idioma explícito prioriza Cohere; detecção automática usa Mistral. Whisper v3
e Turbo da Groq foram integrados e verificados como alternativas de transcrição.
Os 23 perfis, a escolha manual, os controles de custo e as tarefas existentes
foram preservados. A primeira linha do progresso de imagem mostra tempo, fila e
estimativa do provedor quando disponíveis; a segunda mantém a atividade animada.

A rodada delimitada reúne 77 IDs e 492 operações: 71 IDs e 284 operações tiveram
chamadas reais. Todas as linhas têm resultado ou impedimento. Não foram todos
testados. A auditoria exaustiva geral continua pausada. Nenhum novo gerador de
imagens foi aprovado: os testes práticos desta rodada tiveram baixa aderência,
retenção pelo provedor ou prazo inconclusivo. O histórico de transporte continua
separado da qualidade atual, sem habilitar consumo automático pago.

Resultados, lacunas, benchmarks e seleção:

- [Rodada Gemini/Groq](reports/auren-gemini-groq-2026-10-14-r2/REPORT.md)
- [Fontes e benchmarks](reports/AUREN-BENCHMARKS-GEMINI-GROQ-2026-10-14.md)
- [Ordem atual dos perfis](reports/auren-scoped-selection-2026-10-14.json)
- [Testes práticos de imagem](reports/auren-image-practical-2026-10-14/results.json)

As seções abaixo registram a implementação e as verificações anteriores.

Adaptação pessoal do Open WebUI **v0.12.0**, commit `15818d88fd7bde1b73de33590f50d15d21e8d7c1`.
O fork é `Cambrith/Auren-IA`; o código original permanece como remote `upstream`.

## O que esta prévia implementa

- Identidade Auren, português e paleta original da Cavren: fundo `#080D17`, superfícies `#0D1727`/`#121E2D`, azul `#0162F8` e ciano `#21D4FB`.
- Logo estática na barra lateral. Indicador de atividade animado somente junto à mensagem durante a geração, com deslocamento máximo de 4 px e respeito à preferência de movimento reduzido. Respostas sem avatar ou cabeçalho da IA.
- Seletor de modo no topo: Éter, Ímpeto, Insight e Arquiteto.
- Seletor de modelo independente, com busca: Automático, rotas integradas e modelos de conversa/imagem descobertos nas APIs configuradas.
- Conexões Gemini, Groq, Mistral, OpenRouter, Cloudflare, NVIDIA NIM, Cohere, Ollama Cloud, Z.ai e AI Horde, usando as credenciais salvas no cofre do sistema, sem depender de documentos locais.
- Anexos de imagens e vídeos conforme a capacidade declarada pelo modelo; documentos extraídos localmente.
- Geração de imagens nativa de Gemini, OpenRouter e AI Horde (fila assíncrona), retornada como anexo da resposta.
- Preservação da escolha de modo e modelo por conversa; cada mensagem registra seu modo.
- Geração real em streaming, interrupção de geração e conversa persistida pelo Open WebUI.
- Pesquisa opcional pelo SearXNG do motor, com status e fontes na conversa.
- Reutilização do motor Python existente, do cofre de credenciais e das regras de custo e fallback.
- Confirmação de possível custo para modelos manuais quando exigida pelo motor.

O nome público é **Auren**. O pacote `cavren` e os campos de integração `cavren_*`
continuam com o nome antigo para compatibilidade com o motor atual. O adaptador
normaliza a identidade nas mensagens de sistema para Auren.

## Execução local

Este checkout usa um ambiente próprio em `.cavren/`, ignorado pelo Git. Esse diretório
contém os runtimes, a base da prévia e os logs. Não contém uma cópia das chaves dos provedores.

Na máquina preparada, execute:

```bash
python scripts/lunvri_preview.py
```

A interface fica em `http://127.0.0.1:8175`. O endereço aceita acesso somente local.
Para desenvolvimento:

```bash
python scripts/lunvri_preview.py --dev
```

O frontend de desenvolvimento fica em `http://127.0.0.1:5179`.
As opções `--port` e `--dev-port` permitem mudar as portas sem encerrar outros serviços.

O motor é buscado no checkout irmão `../cavren-nextchat`. Ele precisa ter seu ambiente
`.venv` e as configurações já usadas pelo aplicativo anterior. Para outro local:

```bash
python scripts/lunvri_preview.py --engine /caminho/para/cavren-nextchat
```

Em outra máquina Linux x86-64, `bash scripts/setup_lunvri.sh` prepara apenas o runtime
do Open WebUI, com Node 22, Python 3.12 e as dependências originais. O motor continua
sendo uma instalação separada. A instalação inicial baixa alguns gigabytes.

## Como a integração funciona

O frontend envia o modo da mensagem e a escolha do modelo ao backend do Open WebUI.
O backend chama um adaptador OpenAI local, autenticado por um token aleatório válido
somente nessa execução. Esse token é diferente das credenciais dos provedores.

O adaptador lê o cofre através do motor e inicia um processo de geração cancelável.
O adaptador `integration/auren_fallback.py` mantém o perfil de cada modo e a seleção manual inicial,
com alternativas gratuitas compatíveis. Aplica pausas compartilhadas por rota/provedor após erros,
limite de dez candidatos e prazo total. A troca acontece apenas antes de texto visível; uma
resposta parcial nunca é seguida de outra resposta concatenada. Pesquisa e contexto são
reutilizados entre tentativas. Modelos sem preço gratuito confirmado não entram nas alternativas.
Os eventos do motor são convertidos em streaming compatível com o Open WebUI.

Para compatibilidade com provedores que exigem uma única mensagem de sistema,
`integration/lunvri_worker.py` reúne as instruções em uma mensagem inicial e normaliza novamente o payload final,
incluindo os metadados de rota acrescentados pelo motor. Esse ajuste
fica na nova integração e não modifica o checkout anterior.

A prévia usa o modo local sem criação de conta. Além do vínculo a `127.0.0.1`, há
validação de Host, Origin e requisições entre sites, incluindo WebSocket. Esta
configuração é destinada ao aplicativo pessoal local; exposição na rede requer
uma configuração própria de autenticação e implantação.

## Limites da entrega

As conversas antigas não foram importadas; ficam preservadas no aplicativo anterior.
A base da prévia é separada. A descoberta remota confirma acesso ao catálogo, mas não garante saldo, quota ou permissão de geração para todos os modelos. O catálogo é renovado a cada cinco minutos quando consultado. Modelos com preço não confirmado exigem confirmação de possível custo por seleção. AI Horde usa a fila comunitária gratuita; Gemini e OpenRouter podem cobrar pela geração de imagens.

Os documentos aceitos incluem PDF com texto, DOCX, XLSX, CSV, TXT, Markdown e arquivos de código. A leitura local não usa embeddings: envia o texto extraído no contexto da conversa. O Gemini recebe PDF nativamente quando o modelo permite. PDFs digitalizados sem texto exigem um modelo com leitura nativa; não há OCR local. Limites: cinco anexos por mensagem, 20 MB por arquivo e 24 MB de anexos na conversa; texto limitado a 180 mil caracteres, PDFs a 80 páginas e planilhas a 2.000 linhas por aba. A interface avisa quando limita a extração. O limite de contexto do provedor ainda pode ser menor.

Vídeos são enviados como dados locais às rotas que declaram suporte (Gemini e modelos compatíveis no OpenRouter). A pesquisa usa o SearXNG existente. A geração de imagens usa os endpoints nativos dos provedores; as chaves permanecem na ponte. Voz, memória automática, outros plugins e controle do computador não fazem parte desta entrega.

As credenciais cadastradas são carregadas do cofre do sistema (Secret Service/KWallet). Documentos com chaves servem apenas como fonte para importação autorizada; a aplicação não os consulta durante o uso e não utiliza `LUNVRI_CREDENTIALS_FILE`. Renomear, mover ou remover o documento não afeta as conexões já salvas no cofre. OpenAI e Anthropic exigem configuração explícita pela Auren. Cloudflare também precisa do identificador da conta, armazenado no cofre nesta máquina. Não inclua documentos de chaves no repositório.

## Verificação

Os testes automatizados verificam contrato, autorização, origem, modo, modelo, streaming, contexto, cancelamento, leitura de anexos, propriedade de arquivos, capacidades e os formatos nativos de geração de imagens e vídeo. Esses testes usam transporte simulado, sem consumir APIs pagas.

Nesta atualização, 24 testes automatizados passaram. As cinco APIs configuradas aceitaram a consulta de catálogo. O catálogo é atualizado com as opções de conversa e imagem disponíveis nos provedores. Documentos e imagens foram anexados e interpretados por um modelo real na interface; as conversas e os anexos persistiram após recarregar. A animação lateral foi observada durante a geração e a resposta foi conferida sem avatar. O modo Insight também respondeu corretamente 391 ao teste 17 × 23 nesta versão final. Vídeos e geração de imagens têm testes de transporte/contrato; não houve chamada paga para gerar imagem nesta validação.

A compilação de produção passou. A checagem de tipos da versão original apresenta 6.040 erros; esta adaptação apresenta 6.022, sem diagnósticos novos na comparação por arquivo e mensagem. A checagem global continua falhando por problemas anteriores do projeto base.

Na validação anterior à mudança de nome, Éter, Ímpeto, Insight e Arquiteto responderam a mensagens reais, a identidade retornada foi Lunvri, o bloqueio de custo foi observado e modo/modelo foram preservados após recarregar a conversa. A pesquisa real recuperou cinco fontes e gerou uma resposta com citação após a normalização final das mensagens de sistema.

Comandos dos testes:

```bash
PYTHONPATH=../cavren-nextchat/src ../cavren-nextchat/.venv/bin/python -m unittest discover -s tests -p test_lunvri_bridge.py -v
PYTHONPATH=backend .cavren/venv/bin/python -m unittest discover -s tests -p test_lunvri_local.py -v
PYTHONPATH=../cavren-nextchat/src ../cavren-nextchat/.venv/bin/python -m unittest discover -s tests -p test_lunvri_media.py -v
PYTHONPATH=backend .cavren/venv/bin/python -m unittest discover -s tests -p test_lunvri_attachments.py -v
```

Compilação:

```bash
NODE_OPTIONS=--max-old-space-size=8192 PATH="$PWD/.cavren/runtime/node/bin:$PATH" npm run build
```

## Licença e identidade visual

Os avisos de copyright e o arquivo LICENSE do Open WebUI permanecem no projeto.
Esta adaptação pessoal de marca se enquadra na exceção de até 50 usuários finais
em um período móvel de 30 dias descrita na licença. Uma distribuição acima desse
limite precisa respeitar as condições de branding ou obter a permissão aplicável.

DeepSeek: a API direta permanece desativada. No OpenRouter, apenas variantes `:free` com preços zero são aceitas. No Cloudflare, somente `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b` é permitido quando `.cavren/provider_policy.json` registra `cloudflare_workers_free: true`, conforme o plano informado pelo usuário. Se o plano mudar para Paid, retire essa confirmação antes de usar o modelo. Variantes pagas ou sem confirmação ficam bloqueadas.

## Aplicativo do KDE

Execute `python scripts/install_lunvri_desktop.py` para substituir o atalho pessoal Cavren pela Auren. O identificador `cavren.desktop` é mantido para preservar favoritos; o atalho anterior fica em `.cavren/desktop-backup/cavren.desktop`. O instalador atualiza somente o menu do usuário e cria `lunvri.service`, iniciado sob demanda pelo app, sem habilitar execução no login.

`scripts/run_lunvri.sh` abre uma janela Qt maximizada com perfil persistente próprio. Abrir novamente ativa a janela existente. O serviço mantém interface e ponte disponíveis em `127.0.0.1:8175`, mesmo depois de fechar a janela. Para encerrá-lo, use `systemctl --user stop lunvri.service`. Conversas e anexos da Auren permanecem em `.cavren/data`; o histórico anterior da Cavren é preservado, sem migração automática. O app ainda usa o ambiente e motor de `../cavren-nextchat`, que precisa permanecer instalado.

Os seletores usam menus com descrições de modo, busca de modelos, filtros por provedor, indicação de custo e navegação por teclado. A animação da resposta afeta somente fragmentos novos de prosa, preservando espaços e o conteúdo já exibido, sem translação; código permanece no renderizador próprio. Movimento reduzido desativa o efeito. O ícone KDE usa variantes transparentes por resolução instaladas no tema hicolor, com fallback dedicado de 512 px.

## Atualização Auren — 11/10/2026

- Nome público Auren; IDs, caminhos e serviço `lunvri.service` preservados por compatibilidade.
- Seletor agrupado por provedor, nomes legíveis e busca por modelo/provedor/identificador.
- Perfil local Cambrith com a foto original, sem alterar a imagem.
- Janela abre depois do carregamento, sem a tela de inicialização.
- Atividade recuperada da interface anterior, com frases a cada oito segundos e alcance máximo de 4 px (antes 11 px).
- Anexos incompatíveis são bloqueados antes do envio e mantidos para trocar o modelo.
- NVIDIA e Cohere usam as credenciais pessoais de desenvolvimento/teste confirmadas em `.cavren/provider_policy.json`; não pressupõe plano de produção gratuito.
- Ollama permanece com custo a confirmar: o catálogo não informa se há créditos pagos na conta. Z.ai automático usa somente GLM-4.5-Flash.
- AI Horde utiliza geração de imagens na fila comunitária; cancelar o processo tenta cancelar o pedido pendente.

Validação específica: testes de ponte (9), mídia (10), alternativas e fila de imagens (8), anexos (3) e isolamento local (3). Respostas reais confirmadas para Cohere, Z.ai e NVIDIA (Nemotron 3.5 Lightning). O catálogo NVIDIA ainda pode listar modelos retirados; erros recebem pausa e acionam alternativa.

Verificação real da atualização: os quatro modos responderam pela API local com identidade Auren e resultado 391 para 17 × 23. Pelo navegador, Cohere leu o identificador AUREN-TESTE-471 de um TXT anexado; Qwen/Cloudflare analisou a imagem enviada; um modelo sem visão mostrou o aviso para trocar de modelo. O endpoint da foto devolveu bytes idênticos ao arquivo original. Layout conferido em 520 px e 1366 × 722. A geração real de imagens da fila Horde não foi executada nesta validação; a credencial foi reconhecida e conclusão/cancelamento da fila foram testados com respostas simuladas.


## Refinamento de 12/10/2026

A barra nativa inclui navegação, menus Arquivo/Editar/Exibir/Ajuda e três controles à direita: minimizar, maximizar/restaurar com ícone conforme o estado, e fechar. F11 restaura o estado anterior. Em janelas estreitas, os menus se agrupam; mover e redimensionar usam os mecanismos nativos do Qt/Wayland.

Conexões agora descreve o motor real. OpenAI e Anthropic foram preparados sem cadastrar chaves ou habilitar uso pago automático. A futura configuração usa o cofre e requer confirmação de custo para gerar. Anthropic usa catálogo nativo e a camada Chat Completions compatível para conversas; os recursos nativos completos de Claude (como ferramentas, PDFs e pensamento) não são oferecidos por essa camada. OpenAI usa o limite atual `max_completion_tokens`.

A lista de modelos usa logotipos locais por família, com a marca do provedor como alternativa. A origem e licença dos SVGs estão em `static/brand-icons/`. Sem CDN no uso da aplicação.

O erro de salvar o perfil era validação da foto local mascarada pelo tratamento de autenticação. Datas usam DD/MM/AAAA na interface e ISO no banco. Perfil e preferências de imagem foram conferidos após reiniciar o serviço. Configurações administrativas persistem; endereço/token temporários da ponte permanecem específicos de cada execução.

Geração real gratuita pelo AI Horde foi conferida pela API e pela interface; uma imagem 512×512 foi recebida, exibida e validada. O download dos bytes da imagem foi verificado no Qt WebEngine. Catálogo acessível não implica saldo/cota/permissão de geração. O relatório de verificação detalha a cobertura e as limitações em `AUREN-REFINEMENT.md`.


## Conexões de provedores — 15/10/2026

A lista contém 30 conexões, com credenciais no cofre Auren/KWallet, três colunas
em telas largas e reordenação persistente por arraste ou teclado. Canva Connect
é uma integração OAuth 2.0 com PKCE; seu callback local padrão é
`http://127.0.0.1:8176/oauth/canva/callback`.

O estado verificado mais recente é **27 conexões com autenticação comprovada e
3 reservadas para ativação futura** (Anthropic, Fireworks e xAI). NVIDIA e Ollama
também passaram em uma inferência mínima autorizada. Isso não garante saldo,
acesso a todos os modelos ou suporte a todas as tarefas.

Consulte o [registro atualizado de validação](reports/AUREN-PROVEDORES-STATUS-2026-10-15.md).
O botão de validação usa consultas sem inferência por padrão. NVIDIA e Ollama
têm catálogos públicos: uma consulta de catálogo isolada pode voltar a registrar
pendência, pois ela não substitui a comprovação de inferência. O teste mínimo
explícito fica separado por `allow_inference=True`; não é executado por padrão.

Segredos, banco, preferências e resultados locais em `.cavren/` ficam fora do
Git. Nunca versione o documento privado de credenciais nem o conteúdo do cofre.
