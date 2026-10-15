# Auren — fundo azul na primeira abertura

Correção de 15/10/2026, inicialmente mantida apenas no computador. Incluída na atualização para o GitHub autorizada pelo usuário em 15/10/2026. As alterações anteriores de progresso único foram preservadas.

## Causa confirmada

O atalho instalado `cavren.desktop`, exibido como Auren, executa `scripts/run_lunvri.sh`, que abre `scripts/lunvri_desktop.py`. Quando o serviço ainda está iniciando, esse script apresenta um HTML local com logo incorporado, antes de acessar a interface HTTP. Esse HTML definia explicitamente o fundo `#111214`. O splash posterior, em `src/app.html`, já usava `#080d17`.

Por isso a diferença ficava mais evidente após ligar o computador: o serviço é iniciado sob demanda e a primeira tela permanece visível durante essa espera. Reabrir com o serviço já disponível reduz a exposição dessa etapa.

## Alterações

- O HTML real de espera agora pinta tanto `html` quanto `body` com `#080d17` desde sua criação.
- A janela nativa, a base do WebEngineView e a página recebem o mesmo azul antes do HTML, cobrindo também a superfície inicial em branco.
- A cor nativa é compartilhada entre a janela e o HTML pelo valor `AUREN_BACKGROUND`.
- Logo, filtro, tamanho de 104 px, pulso, sincronização de fase e preferência por movimento reduzido foram preservados.
- Perfil persistente, caches pessoais, cofre, conversas, atalho e política de serviço sob demanda foram preservados.

Os registros locais de 15/10 mostram início do serviço às 07:57:58 e a mensagem de prévia pronta às 07:58:17, cerca de 19 segundos depois. A API já respondeu às 07:58:16. Esse intervalo é evidência desta abertura; não mede todo o tempo até a conversa estar pronta e não estabelece uma duração fixa para futuras inicializações. Esta alteração corrige a apresentação da espera, sem mudar a estratégia de inicialização do backend.

## Verificação

`tests/check_auren_cold_start_ui.py` usa a função de HTML da implementação e uma janela Qt/WebEngine real, em perfil temporário sem cache. Não chama o aplicativo principal com seu perfil persistente, não reinicia o computador e não para o serviço em uso.

Passaram:

- Paletas da janela, da base do WebEngineView e da página em azul.
- Cinco capturas antes do HTML com quatro pontos de fundo por captura em `#080d17`.
- Trinta capturas da tela de espera local, mantida durante alguns segundos, com o mesmo fundo nos quatro pontos.
- Trinta e uma capturas na verificação de publicação durante um atraso artificial de três segundos da requisição `/api/config`, em perfil vazio, com o mesmo fundo nos quatro pontos.
- Fundo do splash da interface em azul e chegada ao campo da conversa.
- Ausência de gravações de conversa e de chamadas de geração nos testes.
- Compilação sintática dos scripts alterados e `git diff --check`.

Na verificação de publicação foram 66 capturas amostradas, com 264 verificações de cor nos cantos do conteúdo. Isso verifica o caminho de renderização com espera controlada; não representa uma reinicialização completa do computador. O serviço local permaneceu disponível.

Evidências:

- `auren-primeira-abertura-ui-2026-10-15.json`
- `auren-primeira-abertura-espera-2026-10-15.png`
- `auren-primeira-abertura-interface-2026-10-15.png`

O launcher lê o código novo quando uma nova janela/processo da Auren é iniciado. Não foi necessário recompilar o frontend ou alterar a instalação do menu do usuário.
