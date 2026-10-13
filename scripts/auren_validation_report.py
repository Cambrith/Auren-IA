"""Export dated real observations without credentials or personal input."""
from pathlib import Path
import json
import csv
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]

def main():
    state=ROOT/'.cavren'
    data=json.loads((state/'validation_results.json').read_text())
    text_data=json.loads((state/'validation_text_results.json').read_text())
    data['records'].update({k:v for k,v in text_data['records'].items() if k.startswith('text:')})
    task_data=json.loads((state/'validation_tasks.json').read_text())['tasks']
    records=list(data['records'].values())
    out=ROOT/'reports';out.mkdir(exist_ok=True)
    stamp=datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
    def clean(value): return str(value).replace('|','/').replace('\n',' ')
    def observation(r):
        notes=[r.get('reason','')]
        if r.get('interruptions'):notes.append(str(len(r['interruptions']))+' interrupções locais adicionais, sem conclusão; excluídas da média')
        for sample in r.get('samples',[]):
            progress=sample.get('progress',{})
            detail=sample.get('code','')
            if sample.get('semantic_check') is False:detail+='; sanidade aritmética falhou'
            if sample.get('error'):detail+=': '+sample['error']
            if progress:detail+='; último estado '+str(progress)
            notes.append(detail)
        return clean('; '.join(n for n in notes if n))
    rows=[]
    for r in sorted(records,key=lambda r:(r['kind'],r['provider'],r['model'].casefold())):
        samples=r.get('samples',[]);success=sum(s.get('ok') is True for s in samples)
        required=2 if r['kind'] in ('image','profile') else 1
        function=('sim' if success==len(samples) else f'sim, intermitente ({success}/{len(samples)})') if success>=required else f'parcial ({success}/{len(samples)})' if success else 'não concluiu no teste' if samples else 'não testado'
        if r['kind']=='text' and success and not any(s.get('ok') and s.get('semantic_check') is not False for s in samples):function='respondeu; sanidade falhou'
        cost='gratuito com limites (rota confirmada + chamada real)' if success else 'não confirmado por geração'
        mean=r.get('mean_seconds') if success>=required else ''
        rows.append([r['model']+(' ['+r['profile']+']' if r['kind']=='profile' else ''),r['provider'],r['kind'],function,cost,mean,len(samples),observation(r),r.get('verified_at','')])
    for key in ('speech','transcribe_cohere','transcribe_mistral'):
        r=task_data.get(key,{})
        if not r:continue
        provider,model=r.get('model','cavren:unknown:unknown').removeprefix('cavren:').split(':',1)
        rows.append([model,provider,'audio','sim' if r.get('ok') else 'não testado','gratuito com limites (trial/plano configurado + chamada real)' if r.get('ok') else 'não confirmado',r.get('seconds',''),len(r.get('samples',[])) or 1,clean(r.get('check','Transcrição verificada com amostra pública')),r.get('date','')])
    header=['modelo','provedor','tipo','funciona','custo','tempo_medio_s','amostras','observacoes','data']
    with (out/'auren-modelos-2026-10-12.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator="\n");writer.writerow(header);writer.writerows(rows)
    image_records=[r for r in records if r['kind']=='image']
    texts=[r for r in records if r['kind']=='text']
    def passed(r,required=1):return sum(s.get('ok') is True and s.get('semantic_check') is not False for s in r.get('samples',[]))>=required
    text=f'''# Auren — implementação e validação de tarefas

Atualizado: {stamp} (America/Sao_Paulo). Entradas sintéticas e amostra pública de áudio. Nenhuma chave, saldo ou dado pessoal é incluído neste relatório.

## Método e alcance

As chamadas marcadas como reais foram efetuadas com as conexões existentes no cofre. Não foi ativado plano, comprado crédito ou autorizado fallback pago. Uma resposta bem-sucedida sozinha não comprova custo zero: a condição de gratuidade também exige rota comunitária, plano Free/trial já configurado ou preço zero consultado no catálogo oficial do provedor. Não houve auditoria de fatura. Cotas e latência podem mudar.

Imagens: duas tentativas sequenciais por modelo elegível sem cobrança, prazo de 75 segundos por tentativa, 512×512, 20 etapas e uma imagem no AI Horde. Depois de observar congestionamento, o lote passou a cancelar pedidos quando consultas repetidas, separadas por pelo menos cinco segundos, informavam espera estimada acima de duas vezes o orçamento do teste. Esses casos têm código benchmark_queue_budget e não são classificados como incompatibilidade ou tempo médio de geração. A calibração de perfis usa os parâmetros efetivos, incluindo 30 etapas em stable_diffusion/Detalhado; a rodada posterior de calibração teve prazo de 180 segundos por tentativa. Tempo inclui fila, geração e transporte. O pedido pendente recebe tentativa de cancelamento remoto no encerramento; isso não garante que cada trabalhador interrompa imediatamente sua execução. Timeout informa que não houve conclusão dentro do prazo, não que o modelo seja incapaz. A média de imagens só é publicada com duas gerações concluídas; uma conclusão isolada aparece como parcial.

Texto: uma chamada sintética por rota elegível, até 256 tokens, verificação de resposta não vazia e sanidade aritmética 17×23=391. Essa prova confirma o transporte e um teste básico, sem certificar toda a qualidade do modelo. Rotas sem prova prévia de cobrança zero não foram chamadas. Catálogo é anúncio de capacidade, não prova de integração ou de funcionamento.

Inventário: {len(image_records)} rotas de imagem, {len(texts)} de texto; {sum(bool(r.get('samples')) for r in image_records)} imagens já chamadas, {sum(bool(r.get('samples')) for r in texts)} rotas de texto chamadas. {sum(passed(r,2) for r in image_records)} geradores têm duas conclusões; {sum(passed(r) for r in texts)} rotas de texto passaram na sanidade. Lote de imagens: {'concluído' if data.get('image_completed_at') else 'pausado por pedido do usuário em '+data['image_paused_at'] if data.get('image_paused_at') else 'em andamento'}. Lote de texto: {'concluído' if text_data.get('text_completed_at') else 'em andamento'}.

## 1. Tela de carregamento

Ícone existente centralizado, escala de cinza sobre grafite, pulso suave e respeito a movimento reduzido. Saída em fade após a montagem. A janela nativa passa a aparecer durante a inicialização do serviço. A tela de carregamento foi observada na prévia web.

## 2. Tarefa, modo/perfil e modelo

O seletor de tarefas reutiliza o menu e o acabamento dos demais controles. Cada tarefa recupera suas escolhas persistidas. Código recomenda Arquiteto; documentos e pesquisa recomendam Insight. A escolha explícita de modo ou modelo é preservada. Imagens têm Rápido, Equilibrado e Detalhado com ícones próprios. Transcrição tem seleção de idioma; voz tem o perfil português validado. Modelo padrão: uma única palavra Automático, centralizada, sem seleção em massa.

Pesquisa e geração de imagem ficam em + → Plugins com ícones. As opções de upload, captura, páginas, notas, conhecimento e chats foram preservadas. Foi corrigido também o encaminhamento das propriedades na tela inicial vazia: Plugins e seletor agora leem a mesma fonte de estado.

## 3. Barra de título

Retirado o botão de alternar a barra lateral da barra nativa, com ajuste de margens e espaçamento. O controle da interface permanece. A alteração da barra nativa exige abrir uma nova janela da Auren para carregar o código atualizado.

## 4. Imagens: causa e correção

A escolha anterior dependia da ordem de disponibilidade anunciada, sem medições comparáveis dos perfis. A fila compartilhada e variável do Horde pode dominar o tempo. Além disso, filtros de famílias dos modos Insight/Arquiteto excluíam geradores válidos: o planejamento de imagem foi separado desses filtros de conversa.

Rápido prioriza geradores com duas conclusões reais e menor média observada, penalizando falhas de calibração mais recentes que essa média. Detalhado usa a rota stable_diffusion validada, com 30 etapas; a escolha manual é encaminhada exatamente ao adaptador e à operação selecionados. Equilibrado preserva a preferência configurada quando compatível. Mais etapas não certificam qualidade visual, e perfis não garantem uma ordem de latência sob filas futuras. A tabela de calibração abaixo registra o comportamento atual, incluindo novas filas.

Progresso contém pedido, tentativa, provedor e modelo efetivos; posição, espera estimada e trabalhadores elegíveis vêm da resposta real do Horde. Ausência é exibida como indisponível. Trocar modelo não implica mudar de posição. Pedidos antigos são isolados; parar ou substituir encerra o trabalhador e solicita o cancelamento remoto disponível. O prazo global de 480 segundos é compartilhado entre tentativas, com limite efetivo no trabalhador.

Referências, anexos, máscaras e parâmetros são validados antes da chamada. Horde não tem transporte de referência integrado nesta versão; Gemini/OpenRouter exigem rota compatível. Máscaras e parâmetros sem transporte integrado geram erro explícito. Referências não são descartadas para conseguir uma alternativa. Conclusão sem imagem utilizável é erro explícito; resposta marcada como retida pelo filtro de conteúdo não é tratada como geração concluída nem aciona alternativa para contornar o filtro.

## 5. Texto e escolha de modelos

As rotas chamadas e as excluídas estão integralmente nas tabelas. Automático só usa evidência gratuita real válida. A lista manual pode manter modelos anunciados sem validação; possível cobrança exige confirmação explícita para aquela rota e não é transferida à alternativa. As credenciais permanecem no cofre. Listas de modelos em massa de conversas antigas são retomadas em Automático para novos pedidos, preservando o histórico das respostas; uma escolha manual única válida permanece. Conversas antigas com modelo exclusivo de imagem recuperam a tarefa de imagem quando ainda não tinham uma tarefa explícita.

## 6. Tarefas pesquisadas, testadas e implementadas

| Tarefa | Modelos testados | Gratuidade/limites | Implementada? | Decisão | Data |
|---|---|---|---|---|---|
'''
    definitions=[('chat','Conversar','Integrada: inclui redação, tradução e perguntas'),('image','Gerar imagens','Independente: saída e parâmetros próprios'),('documents','Analisar documentos','Independente: extração local + contexto do documento'),('code','Gerar código','Independente: contexto Arquiteto; execução não incluída'),('research','Pesquisa aprofundada','Independente: pesquisa restrita em etapas + síntese'),('speech','Gerar voz','Independente: transporte TTS e saída de áudio'),('transcribe','Transcrever áudio','Independente: transporte ASR e seleção de idioma')]
    for key,label,decision in definitions:
        r=task_data.get(key,{})
        if key=='image':models=', '.join(x['model'] for x in image_records if passed(x,2));ok=bool(models);date=max((x.get('verified_at','') for x in image_records if passed(x,2)),default='')
        elif key=='chat':models=str(sum(passed(x) for x in texts))+' rotas na tabela de texto';ok=any(passed(x) for x in texts);date=r.get('date','')
        elif key=='transcribe':models=', '.join(x.get('model','').removeprefix('cavren:') for name,x in task_data.items() if name.startswith('transcribe_') and x.get('ok'));ok=bool(models);date=r.get('date','')
        else:models=r.get('model','').removeprefix('cavren:');ok=r.get('ok');date=r.get('date','')
        seconds=r.get('seconds');limits='Gratuito com limites; '+(str(seconds)+' s no teste' if seconds is not None else 'tempos por modelo abaixo') if ok else 'Não testado/confirmado'
        text+='| '+' | '.join(map(clean,[label,models or '—',limits,'Sim' if ok else 'Não',decision,date or 'não testado']))+' |\n'
    text+='''| Agente restrito de pesquisa | Command A 03-2025: chamada real de função search_docs | Trial; planejamento real em 1,567 s; mesma cota da conversa | Integrado | Pesquisa aprofundada: somente até três buscas e síntese; sem executor de código ou ações externas | 2026-10-12 |
| Geração de vídeo | Veo, Cosmos-Predict2.5 e Wan2.1/Hugging Face pesquisados; nenhuma geração chamada | Veo sem faixa gratuita de API; Hugging Face anuncia crédito mensal pequeno, sem chave configurada nesta integração; contrato hospedado Cosmos não confirmado | Não | Inventário futuro; gratuidade geral de vídeo não foi descartada, mas não foi validada com estas conexões | Não testado |
| Agente irrestrito/ações externas | Nenhum executor de ações externas validado | Não confirmado | Não | Pesquisa em etapas é a automação restrita disponível; agente irrestrito não foi habilitado | Não testado |
| Execução de código | Nenhum executor integrado nesta mudança | Não confirmado | Não | Gerar/revisar código não executa o resultado | Não testado |
| Música/efeitos de áudio | Nenhuma rota testada | Não confirmado | Não | Voz TTS não certifica geração de música | Não testado |
| RAG/embeddings | Nenhuma indexação nova testada | Não confirmado | Não | Leitura de documento não certifica busca vetorial | Não testado |
| Deep Research nativo Gemini | API pesquisada, nenhuma chamada | Conta/custo não confirmados | Não | Auren usa seu próprio fluxo restrito de pesquisa; não anuncia o agente externo como integrado | Não testado |
| Tradução/redação | Transporte de Conversar validado; qualidade específica não testada | Mesmas cotas de Conversar | Integrada | Não exige seletor ou transporte separado | Não testado especificamente |

Limites da integração: até cinco anexos por mensagem; arquivos até 20 MB e total de 24 MB por conversa; extração de documentos até 180 mil caracteres, primeiras 80 páginas de PDF ou 2 mil linhas por aba. Leitura parcial é informada; PDF digitalizado sem texto não recebe promessa de OCR. Voz: português, uma voz validada, até 2 mil caracteres. Transcrição: um áudio WAV/MP3/MPEG/OGG/FLAC, português, inglês ou detecção automática; até 20 MB. O provedor pode aplicar limites menores e cotas próprias. Cohere trial tem cotas mensais/RPM; Cloudflare Free tem cota diária de neurônios; Horde depende de kudos e trabalhadores; planos trial não equivalem a acesso irrestrito permanente.

## 7. Tarefa Automática

Classificador local sem chamada adicional: verbo explícito e objeto identificam imagem, código, documento, pesquisa, narração ou transcrição. Trechos entre aspas/crases e o bloco de dados do documento não comandam a escolha. Pedidos de explicação e intenções ambíguas retornam a Conversar. Sem escolha manual, código recomenda Arquiteto e pesquisa/documentos recomendam Insight; conversa com pedido explícito de rapidez usa Ímpeto e aprofundamento usa Insight, ficando em Éter nos demais casos. Imagem com rapidez explícita usa Rápido e detalhe explícito usa Detalhado; sinais conflitantes usam Equilibrado. Um perfil de imagem escolhido explicitamente fica preservado ao mudar para Automática. Só tarefas com teste real e modelos compatíveis verificados participam. Tarefa escolhida manualmente não passa pelo classificador; modo manual é preservado; modelo manual tem prioridade e incompatibilidade produz erro explícito. Não há troca silenciosa de modalidade nem fallback pago.

## 8. Contextos dos modos

Éter: assistência geral, crítica de premissas e pedidos adversariais. Ímpeto: ação direta e resposta concisa. Insight: investigação, evidências, incerteza e fontes. Arquiteto: engenharia de software, requisitos, contratos, compatibilidade, preservação do projeto, impacto de dependências e honestidade sobre testes. Cada modo recebe seu system prompt mesmo com modelo manual.

Nesta primeira versão, a recomendação de conversa e dos contextos especializados utiliza command-a-03-2025, que passou nos testes reais de conversa, código, documentos e pesquisa. Isso é uma escolha conservadora de transporte validado, não prova comparativa de superioridade. A escolha manual permanece soberana; o contexto do modo continua aplicado.

## Verificações e limitações práticas

Verificações simuladas: contratos de referência/parâmetros, planejamento em quatro modos, alternativas gratuitas, eventos antigos, prazo compartilhado, isolamento após cancelamento, conversão de arquivos e persistência dos seletores. Esses testes não comprovam geração real.

Verificações reais: catálogo oficial de preço zero, chamadas de texto, imagens concluídas registradas abaixo, pesquisa local com síntese do modelo, síntese de voz em português e transcrição de amostras públicas/sintéticas. Na interface estreita (520×720), foram observados seletores, Plugins com seleção sincronizada, anexos preservados, ausência de rolagem horizontal, narração automática real com áudio e persistência após recarregar, transcrição real de arquivo anexado, extração de documento sintético com identificador/projetos corretos e geração de código com escolha manual. Cancelamento real de texto e de imagem liberou os controles. A imagem mostrava AbsoluteReality, posição 181, espera estimada 407 s e 4 trabalhadores, conforme o provedor; após Parar, uma nova conversa respondeu 391 sem ser substituída pela imagem antiga. Continuar resposta preservou o texto parcial e concluiu a lista; o erro antigo foi removido também após recarregar. Pesquisa pela tarefa Automática concluiu com duas fontes do domínio oficial Cohere e manteve o modo Arquiteto escolhido manualmente. Esses testes usam somente conversas sintéticas criadas para esta validação.

O build de produção concluiu. O teste da barra nativa foi feito em uma janela Qt fora da tela: botão lateral ausente, três controles da janela e espaçamento ajustado; isso não equivale a reiniciar e inspecionar a janela nativa já aberta. A checagem ampla de tipos tem milhares de diagnósticos preexistentes também presentes no HEAD de referência; não está sendo apresentada como aprovada. Não foram instaladas dependências de produção nem alterado o motor irmão. As mudanças locais prévias na logo lateral estática e animação junto à resposta foram preservadas. O botão de executar código herdado do renderizador fica oculto na Auren, pois nenhum executor novo foi validado nesta entrega.

A evidência real permanece datada; as tarefas não desaparecem simplesmente no dia seguinte. A seleção automática exige também a declaração atual de plano Free/trial nas rotas que dependem desse plano. Preços anunciados e compatibilidade continuam sujeitos aos controles do catálogo e da operação. Trocar a chave no cofre pela interface da Auren ou a opção de trial invalida a autorização baseada em medições anteriores, sem registrar a chave. Uma mudança de plano fora da Auren exige nova validação: as medições atuais não certificam outra conta. Nem duas imagens nem um teste de texto garantem disponibilidade futura, qualidade, ausência de toda cobrança ou duração fixa. Não foram feitas chamadas de risco pago para preencher lacunas.

## Documentação oficial consultada

- [Progresso do AI Horde](https://horde-sdk.readthedocs.io/en/latest/reference/api/horde_sdk/ai_horde_api/apimodels/generate/progress/) e [parâmetros](https://aihorde.net/docs/image/settings/).
- [Imagens Gemini](https://ai.google.dev/gemini-api/docs/image-generation), [preços Gemini/Veo](https://ai.google.dev/gemini-api/docs/pricing) e [Deep Research](https://ai.google.dev/gemini-api/docs/deep-research).
- [Imagens OpenRouter](https://openrouter.ai/docs/guides/overview/multimodal/image-generation) e [limites](https://openrouter.ai/docs/api_reference/limits).
- [Cohere: cotas](https://docs.cohere.com/docs/rate-limits) e [transcrição](https://docs.cohere.com/docs/audio-transcription-quickstart).
- [Mistral: transcrição](https://docs.mistral.ai/studio/audio/speech_to_text).
- [NVIDIA Magpie: contrato HTTP](https://build.nvidia.com/nvidia/magpie-tts-multilingual/api) e [matriz de suporte](https://docs.nvidia.com/nim/speech/26.10.0/reference/support-matrix/tts.html).
- [Cloudflare Workers AI: preço/cota Free](https://developers.cloudflare.com/workers-ai/platform/pricing/) e [Z.AI: preços](https://docs.z.ai/guides/overview/pricing).
- [Cohere: uso de ferramentas e agentes](https://docs.cohere.com/docs/tool-use-quickstart), [Hugging Face: créditos](https://huggingface.co/docs/inference-providers/en/pricing), [vídeo via API](https://huggingface.co/docs/inference-providers/tasks/text-to-video) e [Cosmos-Predict2.5](https://docs.nvidia.com/cosmos/latest/predict2.5/reference.html).
- [Amostra pública de áudio do Google](https://docs.cloud.google.com/speech-to-text/docs/samples/speech-quickstart?hl=en).

## Tabelas completas dos modelos

'''
    for kind,label in [('profile','Calibração dos perfis de imagem'),('image','Modelos de imagem'),('text','Modelos de texto'),('audio','Modelos de áudio')]:
        text+=f'### {label}\n\n| Modelo | Provedor | Funciona? | Gratuito/pago | Tempo médio | Amostras | Observações | Data |\n|---|---|---|---|---:|---:|---|---|\n'
        for row in rows:
            if row[2]!=kind:continue
            text+='| '+' | '.join(clean(v) for v in [row[0],row[1],row[3],row[4],str(row[5])+' s' if row[5] not in ('',None) else '—',row[6],row[7],row[8] or 'não testado'])+' |\n'
        text+='\n'
    (out/'AUREN-VALIDACAO-2026-10-12.md').write_text(text.rstrip()+'\n')
    print('Report rows:',len(rows))

if __name__=='__main__':main()
