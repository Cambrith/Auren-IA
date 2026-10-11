# Lunvri — prévia da interface baseada no Open WebUI

Adaptação pessoal do Open WebUI **v0.12.0**, commit `15818d88fd7bde1b73de33590f50d15d21e8d7c1`.
O fork é `Cambrith/Lunvri-IA`; o código original permanece como remote `upstream`.

## O que esta prévia implementa

- Identidade Lunvri, português e paleta original da Cavren: fundo `#080D17`, superfícies `#0D1727`/`#121E2D`, azul `#0162F8` e ciano `#21D4FB`.
- Logo somente na barra lateral, animada durante a geração, com deslocamento máximo de 4 px e respeito à preferência de movimento reduzido. Respostas sem avatar ou cabeçalho da IA.
- Seletor de modo no topo: Éter, Ímpeto, Insight e Arquiteto.
- Seletor de modelo independente, com busca: Automático, rotas integradas e modelos de conversa/imagem descobertos nas APIs configuradas.
- Conexões Gemini, Groq, Mistral, OpenRouter e Cloudflare, usando o cofre existente e o arquivo local para conexões ausentes.
- Anexos de imagens e vídeos conforme a capacidade declarada pelo modelo; documentos extraídos localmente.
- Geração de imagens nativa de Gemini e OpenRouter, retornada como anexo da resposta.
- Preservação da escolha de modo e modelo por conversa; cada mensagem registra seu modo.
- Geração real em streaming, interrupção de geração e conversa persistida pelo Open WebUI.
- Pesquisa opcional pelo SearXNG do motor, com status e fontes na conversa.
- Reutilização do motor Python existente, do cofre de credenciais e das regras de custo e fallback.
- Confirmação de possível custo para modelos manuais quando exigida pelo motor.

O nome público é **Lunvri**. O pacote `cavren` e os campos de integração `cavren_*`
continuam com o nome antigo para compatibilidade com o motor atual. O adaptador
normaliza a identidade nas mensagens de sistema para Lunvri.

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
No modo Automático e nas rotas já integradas, o motor continua responsável por planejamento de rotas, limites, fallback, contexto,
saúde dos provedores e pesquisa. Os modelos adicionais usam a rota manual solicitada, as instruções do modo e a pesquisa do motor, sem entrar no fallback automático. As chaves ficam apenas nos processos da ponte e de geração; não são enviadas ao navegador nem gravadas no banco do Open WebUI.
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
A base da prévia é separada. A descoberta remota confirma acesso ao catálogo, mas não garante saldo, quota ou permissão de geração para todos os modelos. O catálogo é renovado a cada cinco minutos quando consultado. Modelos adicionais com preço não confirmado e todos os geradores de imagens exigem confirmação de possível custo por seleção.

Os documentos aceitos incluem PDF com texto, DOCX, XLSX, CSV, TXT, Markdown e arquivos de código. A leitura local não usa embeddings: envia o texto extraído no contexto da conversa. O Gemini recebe PDF nativamente quando o modelo permite. PDFs digitalizados sem texto exigem um modelo com leitura nativa; não há OCR local. Limites: cinco anexos por mensagem, 20 MB por arquivo e 24 MB de anexos na conversa; texto limitado a 180 mil caracteres, PDFs a 80 páginas e planilhas a 2.000 linhas por aba. A interface avisa quando limita a extração. O limite de contexto do provedor ainda pode ser menor.

Vídeos são enviados como dados locais às rotas que declaram suporte (Gemini e modelos compatíveis no OpenRouter). A pesquisa usa o SearXNG existente. A geração de imagens usa os endpoints nativos dos provedores; as chaves permanecem na ponte. Voz, memória automática, outros plugins e controle do computador não fazem parte desta entrega.

O arquivo de credenciais padrão é `~/Documentos/Chaves de API - Cavren` (o nome histórico do arquivo é preservado). A variável `LUNVRI_CREDENTIALS_FILE` permite indicar outro arquivo. O parser aceita somente os nomes dos cinco provedores, no formato `Provedor: chave` ou uma variável conhecida `NOME_API_KEY=chave`. Credenciais existentes no cofre têm prioridade. Cloudflare também precisa do identificador da conta, já presente na configuração do motor nesta máquina. Não inclua esse arquivo no repositório.

## Verificação

Os testes automatizados verificam contrato, autorização, origem, modo, modelo, streaming, contexto, cancelamento, leitura de anexos, propriedade de arquivos, capacidades e os formatos nativos de geração de imagens e vídeo. Esses testes usam transporte simulado, sem consumir APIs pagas.

Nesta atualização, 24 testes automatizados passaram. As cinco APIs configuradas aceitaram a consulta de catálogo. O catálogo é atualizado com as opções de conversa e imagem disponíveis nos provedores. Documentos e imagens foram anexados e interpretados por um modelo real na interface; as conversas e os anexos persistiram após recarregar. A animação lateral foi observada durante a geração e a resposta foi conferida sem avatar. O modo Insight também respondeu corretamente 391 ao teste 17 × 23 nesta versão final. Vídeos e geração de imagens têm testes de transporte/contrato; não houve chamada paga para gerar imagem nesta validação.

A compilação de produção passou. A checagem de tipos da versão original apresenta 6.040 erros; esta adaptação apresenta 6.022, sem diagnósticos novos na comparação por arquivo e mensagem. A checagem global continua falhando por problemas anteriores do projeto base.

Na validação pela interface, Éter, Ímpeto, Insight e Arquiteto responderam a mensagens reais, a identidade retornada foi Lunvri, o bloqueio de custo foi observado e modo/modelo foram preservados após recarregar a conversa. A pesquisa real recuperou cinco fontes e gerou uma resposta com citação após a normalização final das mensagens de sistema.

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

Execute `python scripts/install_lunvri_desktop.py` para substituir o atalho pessoal Cavren pela Lunvri. O identificador `cavren.desktop` é mantido para preservar favoritos; o atalho anterior fica em `.cavren/desktop-backup/cavren.desktop`. O instalador atualiza somente o menu do usuário e cria `lunvri.service`, iniciado sob demanda pelo app, sem habilitar execução no login.

`scripts/run_lunvri.sh` abre uma janela Qt maximizada com perfil persistente próprio. Abrir novamente ativa a janela existente. O serviço mantém interface e ponte disponíveis em `127.0.0.1:8175`, mesmo depois de fechar a janela. Para encerrá-lo, use `systemctl --user stop lunvri.service`. Conversas e anexos da Lunvri permanecem em `.cavren/data`; o histórico anterior da Cavren é preservado, sem migração automática. O app ainda usa o ambiente e motor de `../cavren-nextchat`, que precisa permanecer instalado.

Os seletores usam menus com descrições de modo, busca de modelos, filtros por provedor, indicação de custo e navegação por teclado. A animação da resposta afeta somente fragmentos novos de prosa, preservando espaços e o conteúdo já exibido, sem translação; código permanece no renderizador próprio. Movimento reduzido desativa o efeito. O ícone KDE usa variantes transparentes por resolução instaladas no tema hicolor, com fallback dedicado de 512 px.
