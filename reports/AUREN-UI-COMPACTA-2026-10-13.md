# Auren — seletores compactos e abertura estável

Data da verificação: 2026-10-13. Alterações localizadas, sem novas dependências de produção, sem chamadas de geração e sem executar o lote de modelos anteriormente pausado.

## Diagnóstico baseado no código

1. Tarefas eram colocadas diretamente no painel, cujo teto era 38 rem, sem uma lista interna com rolagem própria. O painel podia ocupar quase a altura da janela. Modelos tinham uma implementação separada de rolagem e vários controles fixos.
2. O posicionamento responsivo podia retirar o limite de altura após o conteúdo flexível encolher; o próximo cálculo voltava a encontrar conteúdo maior. O limite da área disponível passou a permanecer aplicado.
3. Automático definia peso mas herdava o tamanho de texto do botão, enquanto os nomes dos outros campos tinham regra explícita de 13 px. A altura mínima também estava definida apenas no estado automático.
4. Layout e chat podiam iniciar a retirada da tela de carregamento simultaneamente. loading=false acontecia antes de terminar a restauração de rascunho/defaults, e a classe inicial desativava também a transição da própria tela de carregamento. A reativação nativa de uma janela minimizada solicitava sempre maximização, mudando a geometria de janelas normais. O fundo padrão da página Qt, não definido pelo aplicativo, também podia aparecer branco durante a navegação. Essas condições são demonstráveis no código; não se atribui toda ocorrência relatada a uma única delas sem reprodução.

## Alterações

- AurenChoiceList.svelte: lista compartilhada por tarefas, modelos e perfis, teto de 18 rem/45dvh, rolagem fina e espaço estável para a barra. O item escolhido é revelado por rolagem local ao abrir ou atualizar a lista; o documento não é deslocado. Navegação por teclado preservada.
- LunvriControls.svelte: painéis limitados a 26 rem e à janela disponível, itens com menor espaçamento, textos compactos e descrições limitadas a duas linhas. Controles de busca/provedor/Automático permanecem disponíveis. Eliminada duplicação de Automático entre a opção principal e as linhas manuais. Automático e demais nomes compartilham fonte, peso, linha e cor; os três campos compartilham altura mínima de 54 px, borda e padding.
- Dropdown.svelte: limite responsivo permanece ativo depois do encolhimento dos filhos, evitando realimentação entre alturas.
- aurenStartup.ts: retirada única compartilhada, espera pelas fontes e por quatro quadros iguais de geometria; finaliza efeitos de entrada finitos sob a tela opaca, preservando atividades infinitas da resposta e do pulso. Proteção de transições de layout nos eventos de visibilidade, pageshow e reativação nativa.
- Chat.svelte e layouts: prontidão depois da restauração inicial do chat e rascunho; início local sem autenticação não expõe a interface antes do login automático terminar.
- app.html: pulso suave apenas por transform/opacity, imagem de 104 px em camada fixa, fase compartilhada com a tela nativa, pausa na posição atual durante fade e respeito a movimento reduzido. Fade da tela de carregamento é excluído da desativação de transições estruturais.
- auren_window.py/lunvri_desktop.py: fundo da página definido em grafite; fase do pulso mantida durante a troca de documento. Reativar mantém normal/maximizada/tela cheia e apenas remove o estado minimizado.

## Resultados observados

- Tarefas: painel 345 px, área de rolagem 288 px, oito tarefas preservadas. Em janela estreita o painel manteve 345 px, sem rolagem horizontal.
- Modelos: painel 402 px, lista interna 169,5 px no cenário com busca, filtro e opção automática fixos. A mesma lista compartilhada aplica o teto e encolhe conforme o espaço restante.
- Última tarefa e último modelo selecionados ficaram visíveis ao reabrir os menus.
- Fonte calculada de tarefa, modo e Automático: mesma família, 13 px, peso 600, linha de 18 px e rgb(244,250,255). Três campos com 54 px de altura.
- Oito amostras após abrir o menu estreito mantiveram sua altura estável.
- Pulso observado sob atraso sintético de dois segundos na primeira consulta de configuração: transform mudou, dimensões CSS permaneceram 104×104.
- Três recarregamentos completos da interface mantiveram o layout estável após revelar o chat.
- Janela normal minimizada e reativada manteve tamanho e layout, sem virar maximizada.
- Página Qt com fundo #111214.
- 82 testes Python de integração, tarefas, cofre, referências, alternativas e mídia aprovados; testes adicionais de API/eventos/anexos/origem rodados isoladamente. 40 testes frontend aprovados, incluindo prontidão compartilhada, layout variável, movimento reduzido e preservação de animações infinitas. Build de produção e diff aprovados.

## Limites honestos

A permanência de 12 horas em segundo plano foi simulada com relógio de testes e eventos de visibilidade. Não houve suspensão real prolongada do PC, reinício do PC nem teste de todos os drivers/compositores possíveis. Os mecanismos corrigidos não têm expiração por tempo e foram verificados em aberturas/reativação reais; isso não certifica toda condição externa de hardware.

A checagem ampla de tipos anteriormente apresentava milhares de diagnósticos também presentes no HEAD de referência. Ela não é declarada aprovada. Nenhuma geração de modelo foi repetida para esta mudança visual; as medições reais de tarefas anteriores continuam datadas e separadas dos testes simulados.

## Capturas

- auren-seletores-compactos-2026-10-13.png
- auren-tarefas-compactas-2026-10-13.png
- auren-modelos-compactos-2026-10-13.png

## Código e controle de versão

As mudanças anteriores desta conversa também integram a entrega: tarefas/Plugins, roteamento e cancelamento, cofre persistente e ícones. Logs, banco, histórico de chats, perfis de navegador e credenciais em .cavren permanecem privados e não integram a publicação. Os relatórios públicos usam caminhos relativos ao repositório.

O estado inicial era main=a587c851d, alinhado a origin/main, sem commits locais novos. O envio usa a conexão GitHub autenticada do aplicativo, com permissão admin, pois a credencial da ferramenta Git local estava inválida. O resultado do envio e os SHAs exatos serão informados após conferir a referência remota.

## Referência primária

[Qt: backgroundColor e prevenção de flashes brancos](https://doc.qt.io/qtforpython-6.11/PySide6/QtWebEngineCore/QWebEnginePage.html).
