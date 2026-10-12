# Auren

Interface de IA integrada ao Cambrith OS, baseada no Open WebUI v0.12.0 e conectada ao motor Python da assistente.

A primeira prévia tem identidade Auren, modos Éter, Ímpeto, Insight e Arquiteto no topo, seleção independente de modelo, respostas em streaming e pesquisa opcional na web.

Leia [LUNVRI.md](LUNVRI.md) para execução, arquitetura, testes e limites da prévia.

No ambiente preparado:

```bash
python scripts/lunvri_preview.py
```

Abra `http://127.0.0.1:8175`. O motor existente é localizado em `../cavren-nextchat` ou pode ser informado com `--engine`.

Esta prévia usa uma base de conversas separada e reutiliza o cofre e as regras de roteamento do motor. A migração do histórico antigo e a integração de voz, RAG e ferramentas estão fora desta primeira entrega.

A documentação original está preservada em [README.upstream.md](README.upstream.md). Consulte também [LICENSE](LICENSE) e [LUNVRI.md](LUNVRI.md#licença-e-identidade-visual) para as condições de uso e branding do Open WebUI.
