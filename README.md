# Auren — assistente de IA do Cambrith OS

Auren é uma interface pessoal de inteligência artificial baseada no **Open WebUI 0.12.0**, integrada ao motor Python do Cambrith OS. Reúne conversa, pesquisa na web, anexos e geração de imagens em uma interface com identidade própria.

## Recursos

- Modos **Éter, Ímpeto, Insight e Arquiteto**, com seleção automática ou manual do modelo.
- Modelos organizados por provedor e família, com pesquisa, filtros, logotipos e indicação de capacidades.
- Conexões com Google Gemini, Groq, Mistral AI, OpenRouter, Cloudflare, Cohere, NVIDIA NIM, Ollama Cloud, Z.ai e AI Horde. OpenAI e Anthropic estão preparados para configuração explícita.
- Credenciais salvas no **cofre do sistema (Secret Service/KWallet)**. O funcionamento não depende do nome, localização ou existência do documento de chaves.
- Alternativas gratuitas compatíveis após erros ou limites, com preservação de respostas parciais e confirmação quando houver possível custo.
- Anexos de documentos e mídias conforme o suporte do modelo, pesquisa pelo SearXNG local e geração de imagens pelos provedores compatíveis.
- Aplicativo KDE/Wayland com menus, três controles de janela, restauração centralizada em 910×600 e histórico persistente.

## Execução local

O projeto depende de um motor separado, instalado em `../cavren-nextchat` ou indicado por `--engine`. Este repositório não inclui suas chaves nem o ambiente pessoal do motor.

No ambiente já preparado, abra o aplicativo:

```bash
bash scripts/run_lunvri.sh
```

Para iniciar a interface no navegador:

```bash
python scripts/lunvri_preview.py
```

Acesse **http://127.0.0.1:8175**. Preparação do ambiente, desenvolvimento e requisitos estão em [AUREN.md](AUREN.md#execução-local).

## Componentes do projeto

| Componente | Localização | Responsabilidade |
|---|---|---|
| Interface | [`src/`](src/) | Conversas, seletores, configurações, perfil e identidade visual. |
| API da Auren | [`backend/open_webui/routers/auren.py`](backend/open_webui/routers/auren.py) | Acesso autenticado às conexões, preferências e geração de imagens. |
| Ponte com o motor | [`integration/lunvri_bridge.py`](integration/lunvri_bridge.py) | Comunicação local e transmissão das respostas do motor Python. |
| Provedores e catálogo | [`integration/lunvri_connections.py`](integration/lunvri_connections.py) | Credenciais do cofre, descoberta dos modelos e suas capacidades. |
| Alternativas de modelos | [`integration/auren_fallback.py`](integration/auren_fallback.py) | Tratamento de falhas, limites e seleção de alternativas compatíveis. |
| Preferências e credenciais | [`integration/auren_settings.py`](integration/auren_settings.py) | Configurações persistentes e armazenamento seguro de chaves. |
| Janela desktop | [`scripts/auren_window.py`](scripts/auren_window.py) | Barra superior, menus e controles nativos de janela. |
| Identidade visual | [`static/brand-icons/`](static/brand-icons/) | Logotipos locais, fontes e licenças dos ícones. |
| Verificações | [`tests/`](tests/) | Testes de integração, credenciais, modelos e janela. |

Os nomes internos `cavren` e `lunvri` permanecem nos pontos necessários à compatibilidade com o motor e a instalação existente. O nome público do aplicativo é **Auren**.

## Documentação e limites

- [AUREN.md](AUREN.md): arquitetura, execução, provedores e integração desktop.
- [AUREN-REFINEMENT.md](AUREN-REFINEMENT.md): alterações implementadas, verificações realizadas e limitações conhecidas.
- [README.upstream.md](README.upstream.md): documentação original do Open WebUI.

A disponibilidade no catálogo não garante saldo, cota ou acesso à geração. Voz, RAG e ferramentas avançadas dependem de configuração própria; não estão apresentados como recursos verificados em todos os provedores. O histórico antigo permanece preservado, sem migração automática.

## Créditos e licença

Este é um fork pessoal do [Open WebUI](https://github.com/open-webui/open-webui). Os créditos e a licença originais estão preservados em [LICENSE](LICENSE); as condições de identidade visual estão descritas em [AUREN.md](AUREN.md#licença-e-identidade-visual).

Credenciais, conversas, anexos pessoais e arquivos de execução em `.cavren/` não fazem parte do repositório.
