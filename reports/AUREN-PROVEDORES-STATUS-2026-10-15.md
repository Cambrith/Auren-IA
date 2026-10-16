# Auren — estado atualizado das 30 conexões

Atualização de 15/10/2026, após autorização para testes mínimos reais e publicação no GitHub.

**27 consultas autenticadas bem-sucedidas; 3 provedores reservados para ativação futura; nenhuma falha ou pendência de autenticação registrada.**

Sucesso de autenticação não comprova saldo nem disponibilidade de todos os modelos, modalidades, regiões ou tarefas. NVIDIA e Ollama também concluíram uma inferência mínima nesta rodada.

## Verificação real autorizada

- NVIDIA NIM: uma chamada de embeddings, com um único texto sintético curto; vetor numérico válido recebido.
- Ollama Cloud: uma chamada de chat ao modelo `gemma4:31b`, com mensagem sintética curta e saída limitada a um token; resposta de texto recebida.
- Voyage AI: `GET /v1/files?limit=1` autenticado aceito; controle com credencial inválida recusado. Sem geração de embeddings.
- Canva Connect: OAuth autorizado pelo titular; consulta autenticada ao perfil concluída. Tokens permanecem no cofre.
- Anthropic, Fireworks e xAI: reservados para ativação futura. As credenciais existentes são preservadas; não houve tentativa de contornar limites da conta.
- Nenhum faturamento ou compra de créditos foi habilitado. Os dois testes de inferência foram expressamente autorizados; eventual débito depende da cota e da contabilização do provedor.

## Conexões

| Conexão | Estado registrado | Comprovação |
|---|---|---|
| AI Horde | Sucesso | Consulta autenticada |
| Amazon Bedrock | Sucesso | Consulta autenticada |
| Anthropic API (Claude) | Ativação futura | Reservado pelo titular |
| AssemblyAI API | Sucesso | Consulta autenticada |
| Canva Connect | Sucesso | Consulta autenticada |
| Cartesia API | Sucesso | Consulta autenticada |
| Cerebras Inference API | Sucesso | Consulta autenticada |
| Cloudflare Workers AI | Sucesso | Consulta autenticada |
| Cohere API | Sucesso | Consulta autenticada |
| Deepgram API | Sucesso | Consulta autenticada |
| DeepInfra API | Sucesso | Consulta autenticada |
| DeepSeek API | Sucesso | Consulta autenticada |
| ElevenLabs API | Sucesso | Consulta autenticada |
| fal API (fal.ai) | Sucesso | Consulta autenticada |
| Fireworks AI API | Ativação futura | Reservado pelo titular |
| Google Gemini API | Sucesso | Consulta autenticada |
| GroqCloud API | Sucesso | Consulta autenticada |
| Hugging Face Inference Providers | Sucesso | Consulta autenticada |
| Hyperbolic API | Sucesso | Consulta autenticada |
| Mistral AI API | Sucesso | Consulta autenticada |
| Novita AI API | Sucesso | Consulta autenticada |
| NVIDIA NIM API | Sucesso | Inferência mínima autenticada |
| Ollama Cloud API | Sucesso | Inferência mínima autenticada |
| OpenAI API | Sucesso | Consulta autenticada |
| OpenRouter API | Sucesso | Consulta autenticada |
| Replicate API | Sucesso | Consulta autenticada |
| Stability AI API | Sucesso | Consulta autenticada |
| Voyage AI API | Sucesso | Consulta autenticada |
| xAI API | Ativação futura | Reservado pelo titular |
| Z.ai API | Sucesso | Consulta autenticada |

## Segurança e configuração local

As chaves, tokens OAuth, inventário privado e estado da conta são locais e não integram o Git. O runtime `.cavren/` continua ignorado. O documento privado usa referências ao cofre Auren/KWallet. Nenhuma credencial precisa ser colada no chat.

Os relatórios anteriores são registros históricos com seus respectivos resultados e horários. Este documento e `auren-provider-current-status-2026-10-15.json` representam o estado mais recente.

## Verificações para publicação

- 259 testes Python aprovados, separados entre os ambientes existentes do backend e da interface Qt. Bancos e credenciais dos testes são isolados e sintéticos.
- 50 testes Vitest aprovados em 6 arquivos.
- 30 verificações da interface nativa aprovadas: ícones, transparência, temas, campos, botões, OAuth, três colunas, responsividade, arraste, teclado e persistência da ordem após recarregar.
- Build de produção concluído.
- ESLint dos módulos novos e dos componentes de conexões aprovado. Nos dois componentes legados mais amplos, restam 38 diagnósticos (13 em `Models.svelte`, 25 em `LunvriControls.svelte`), contra 39 na versão anterior. Nenhum diagnóstico adicional foi introduzido.
- `git diff --check` aprovado.
- Os arquivos destinados ao GitHub foram comparados com os segredos atuais do cofre e examinados por padrões de chaves, tokens, chaves privadas e URLs autenticadas. Nenhum segredo encontrado.
- Nenhum envio ao Google Drive foi realizado.
