# Auren — prévia da interface baseada no Open WebUI

Adaptação pessoal do Open WebUI **v0.12.0**, commit `15818d88fd7bde1b73de33590f50d15d21e8d7c1`.
O fork é `Cambrith/Auren-IA`; o código original permanece como remote `upstream`.

## O que esta prévia implementa

- Identidade Auren, português e paleta original da Cavren: fundo `#080D17`, superfícies `#0D1727`/`#121E2D`, azul `#0162F8` e ciano `#21D4FB`.
- Logo somente na barra lateral, animada durante a geração, com deslocamento máximo de 4 px e respeito à preferência de movimento reduzido. Respostas sem avatar ou cabeçalho da IA.
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
