# Lunvri — prévia da interface baseada no Open WebUI

Adaptação pessoal do Open WebUI **v0.12.0**, commit `15818d88fd7bde1b73de33590f50d15d21e8d7c1`.
O fork é `Cambrith/Lunvri-IA`; o código original permanece como remote `upstream`.

## O que esta prévia implementa

- Identidade Lunvri, logo existente, português e tema escuro inicial.
- Seletor de modo no topo: Éter, Ímpeto, Insight e Arquiteto.
- Seletor de modelo independente: Automático ou uma rota integrada do motor.
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
O motor continua responsável por planejamento de rotas, limites, fallback, contexto,
saúde dos provedores e pesquisa. As chaves ficam apenas no ambiente desse processo.
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
A base da prévia é separada. O catálogo de modelos é o conjunto integrado do motor,
incluindo suas verificações de credenciais e custo; o catálogo remoto não autoriza
automaticamente novos modelos.

Arquivos para RAG, voz, memória automática, execução de ferramentas e controle do
computador não fazem parte da validação desta primeira prévia. Upload de documentos
para RAG está desabilitado nas capacidades dos modelos, pois a ponte não oferece
embeddings. A opção de pesquisa no topo usa o SearXNG do motor.

## Verificação

Foram verificados 12 testes de contrato, autorização, origem, modo, modelo, streaming, contexto e cancelamento, sem chamadas a provedores nos testes automatizados.

A compilação de produção passou. A checagem de tipos da versão original apresenta 6.040 erros; esta adaptação apresenta 6.022, sem diagnósticos novos na comparação por arquivo e mensagem. A checagem global continua falhando por problemas anteriores do projeto base.

Na validação pela interface, Éter, Ímpeto, Insight e Arquiteto responderam a mensagens reais, a identidade retornada foi Lunvri, o bloqueio de custo foi observado e modo/modelo foram preservados após recarregar a conversa. A pesquisa real recuperou cinco fontes e gerou uma resposta com citação após a normalização final das mensagens de sistema.

Comandos dos testes:

```bash
PYTHONPATH=../cavren-nextchat/src ../cavren-nextchat/.venv/bin/python -m unittest discover -s tests -p test_lunvri_bridge.py -v
PYTHONPATH=backend .cavren/venv/bin/python -m unittest discover -s tests -p test_lunvri_local.py -v
```

Compilação:

```bash
PATH="$PWD/.cavren/runtime/node/bin:$PATH" npm run build
```

## Licença e identidade visual

Os avisos de copyright e o arquivo LICENSE do Open WebUI permanecem no projeto.
Esta adaptação pessoal de marca se enquadra na exceção de até 50 usuários finais
em um período móvel de 30 dias descrita na licença. Uma distribuição acima desse
limite precisa respeitar as condições de branding ou obter a permissão aplicável.
