# Auren — correção de ícones em 2026-10-13

## Causa confirmada

O atalho do aplicativo usava Icon=lunvri, mas não havia ícones lunvri instalados na árvore de ícones local. O arquivo original static/lunvri-icon.png estava íntegro e era idêntico ao ícone 512 px do motor ativo. O favicon ICO legado continha imagem monocromática diferente da logo atual. Havia também metadados de instalação declarando 500×500 para uma imagem de 512×512.

## Correção aplicada

- Reinstalados os nove tamanhos existentes (16, 22, 24, 32, 48, 64, 128, 256 e 512 px), sob o nome auren e aliases lunvri/cavren. Os pixels vieram dos ativos existentes, sem redesenho.
- Atalho canônico cavren.desktop preservado, incluindo nome, traduções, comando, identidade e associação da barra de tarefas. Icon passou a apontar diretamente ao PNG instalado.
- Atalho Auren.desktop criado na pasta configurada da área de trabalho; não havia atalho Auren/Cavren nessa pasta no momento da inspeção.
- A janela usa o ícone por caminho direto. A abertura verifica e restaura os arquivos de ícone ausentes ou corrompidos a partir dos ativos do projeto.
- ICO recriado como contêiner dos PNGs existentes, em seis tamanhos; SVG usa a imagem PNG atual embutida. Corrigidas referências da documentação local e dimensões do manifesto local. Os arquivos de origem, os arquivos já compilados e os servidos foram sincronizados.
- Cache de ícones e catálogo de aplicativos KDE atualizados. A identidade cavren permaneceu para preservar os itens já fixados. Não foi reiniciado Plasma nem o PC.
- Logo lateral estática e animação junto à mensagem preservadas. A tela de carregamento continua monocromática conforme o pedido anterior.

## Verificação

- Cinco testes automatizados de instalação, recuperação, idempotência, proteção contra ativo inválido e preservação dos atalhos aprovados.
- Atalhos validados com desktop-file-validate; compilação Python e diff aprovados.
- Qt encontrou auren no tema e os nove tamanhos; ICO decodificado com seis imagens; SVG renderizado com conteúdo visível.
- Janela real de teste: ícone válido e KWin informou desktopFileName=cavren e resourceClass=cavren, confirmando a associação com o atalho canônico. Apenas essa janela de teste foi observada e encerrada.
- Oito URLs de logo/favicons responderam HTTP 200 após reiniciar o serviço Auren. Manifesto informou Auren e tamanho 512×512. Nenhuma geração de IA ou chamada paga foi realizada.
- Captura: auren-icones-verificados-2026-10-13.png. A captura mostra a resolução real dos ícones em uma janela própria de verificação; não representa uma inspeção visual de todas as posições do painel KDE.

## Arquivos

scripts/auren_identity.py, scripts/install_lunvri_desktop.py, scripts/lunvri_desktop.py, backend/open_webui/main.py e arquivos favicon.ico/favicon.svg no frontend/backend. Testes: tests/test_auren_identity.py e tests/check_auren_identity_window.py.

Instalação local: ~/.local/share/icons/hicolor, ~/.local/share/applications/cavren.desktop e a pasta da área de trabalho. Credenciais e serviço de conexão preservados. A tarefa de reorganização/testes de modelos anterior continua pausada.

## Fontes oficiais

- [Ícones em temas e fallback hicolor](https://specifications.freedesktop.org/icon-theme/0.11/).
- [Caminhos e nomes de ícones em atalhos](https://specifications.freedesktop.org/desktop-entry/latest/value-types.html).
- [Qt: identidade desktopFileName](https://doc.qt.io/qt-6/qguiapplication.html).
