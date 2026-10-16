# Marcas na Auren

SVGs selecionados de `@lobehub/icons-static-svg` versão 1.95.1, do projeto [Lobe Icons](https://github.com/lobehub/lobe-icons), sob licença MIT. A licença completa está em LICENSE-LobeHub.txt. O arquivo sources.json registra a origem e o SHA-256 de cada SVG. A integridade do pacote foi conferida com o SHA-512 publicado no registro npm; scripts, imagens externas e referências remotas não são aceitos nos SVGs importados.

`aihorde.png` é o favicon de 32 pixels servido pelo site oficial https://aihorde.net/favicon-32x32.png. Os nomes e marcas pertencem aos respectivos titulares. Os ícones indicam o modelo ou o provedor utilizado, sem afirmar afiliação comercial. Os arquivos são servidos localmente; nenhum CDN é consultado durante o uso da interface.

Quando uma família não tem uma marca local identificada, a interface usa a marca do provedor. Modelos personalizados mantêm suas imagens próprias quando configuradas.

## Revisão dos 30 provedores — 15/10/2026

`provider-sources.json` registra a página oficial, o arquivo declarado por ela,
o SHA-256 local e a origem de cada marca. Os novos recursos ficam em `providers/`.
Foram obtidos 28 recursos diretamente de sites oficiais; AI Horde mantém seu
favicon oficial já existente e OpenAI mantém o SVG atribuído ao Lobe Icons como
fallback. Esses dois arquivos não foram substituídos por recursos sem procedência.

SVGs com scripts, entidades, handlers de eventos, conteúdo HTML ou dependências
externas são recusados pelo importador. Imagens rasterizadas são normalizadas
para PNG sem modificar a identidade. Os arquivos são servidos localmente e
preservam cores e proporções; a interface preserva as cores das marcas coloridas. Marcas monocromáticas
usam sua variante branca no tema escuro para manter o contraste sem fundo.
Os contêineres dos ícones são transparentes e sem borda, inclusive nos seletores.
Na revisão de transparência, os SVGs locais atribuídos substituem tiles opacos
quando disponíveis; o manifesto registra esses fallbacks e mantém a referência
ao recurso oficial anterior. No SVG Voyage foi retirado apenas o retângulo de
fundo branco, preservando os caminhos e as máscaras da marca.

Os tiles rasterizados remanescentes usam máscaras SVG locais no componente: a
superfície uniforme é separada por diferença de cor; Canva e Replicate preservam
o símbolo branco e descartam o tile em gradiente. Os arquivos originais continuam
intactos, sem redesenho, dependência externa ou alteração de credenciais.
