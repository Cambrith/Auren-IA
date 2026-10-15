# Auren — atualização para o GitHub em 15/10/2026

Publicação autorizada pelo usuário para consolidar as alterações locais pendentes da Auren no repositório `Cambrith/Auren-IA`, branch `main`. Base conferida no remoto: `1be1210b524855229bdf87b0c36dd81f3a2a7656`.

## Conteúdo da atualização

- Um único indicador animado acompanha as etapas da pesquisa e da geração de imagens. Consultas e fontes continuam acessíveis; a resposta concluída mantém sua apresentação normal.
- A janela nativa, a página e o HTML de espera usam o mesmo azul `#080D17` que o splash da interface já utilizava.
- Documentação, verificações retomáveis e evidências visuais acompanham as duas correções.

As mudanças anteriores de modelos, anexos, tarefas e menus já estavam presentes no remoto e continuam no histórico. Nenhuma nova sondagem de modelos foi feita nesta publicação.

## Validação da publicação

- 60 testes do frontend passaram em nove arquivos. Cópias de referência em `.cavren/` foram excluídas dessa contagem.
- Compilação de produção concluída com sucesso. O compilador apresentou avisos em componentes do projeto; a conclusão do build não significa ausência desses avisos.
- Sintaxe Python aprovada nos dois scripts alterados e nos dois verificadores de interface.
- Verificação nativa do progresso: todas as nove condições passaram, incluindo indicador único, animação, acesso aos resultados, apresentação estreita e resposta final.
- Verificação nativa da primeira abertura: todas as condições passaram, incluindo 66 capturas e 264 conferências da cor nos cantos, com perfil temporário sem cache.
- Revisão visual das capturas e verificação de espaços do diff realizadas.
- Varredura dos arquivos preparados não encontrou os padrões pesquisados de chaves de provedores, tokens de acesso ou chaves privadas; nenhum arquivo de banco de dados ou de `.cavren/` integra a atualização.

Os testes de interface usam eventos sintéticos e espera controlada. Não chamam provedores para gerar conteúdo, não gravam conversas e não representam uma reinicialização física do computador. As quantidades de fila e estimativas nas capturas de geração são dados sintéticos do teste.

## Dados locais e dependências

Conversas, anexos pessoais, cofre, credenciais, perfil de navegação, caches e ambientes de execução permanecem locais e fora do versionamento. O motor instalado no checkout irmão `cavren-nextchat` continua sendo uma dependência externa, conforme `AUREN.md`; este envio não muda o repositório Cavren separado.

Os relatórios das correções foram atualizados para registrar a autorização posterior de publicação, preservando as datas e os limites das verificações.
