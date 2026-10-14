"""Native Auren UI checks with synthetic delay/resume; no generation requests."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from auren_window import AurenWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl,QRect,Qt
from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineScript
from PySide6.QtTest import QTest
app=QApplication([]);window=AurenWindow();profile=QWebEngineProfile(window)
window.setPage(QWebEnginePage(profile,window.web));window.web.setZoomFactor(1)
script=QWebEngineScript();script.setInjectionPoint(QWebEngineScript.DocumentCreation);script.setWorldId(QWebEngineScript.MainWorld)
script.setSourceCode("const realFetch=window.fetch;let delayed=false;window.fetch=async(...args)=>{if(!delayed&&String(args[0]).endsWith('/api/config')){delayed=true;await new Promise(r=>setTimeout(r,2000));}return realFetch(...args)};")
window.page().scripts().insert(script)
window.resize(1200,720);window.show();result={}
def js(code):
 out=[];window.page().runJavaScript('JSON.stringify('+code+')',lambda v:out.append(v))
 deadline=time.monotonic()+10
 while not out and time.monotonic()<deadline:QTest.qWait(10)
 if not out:raise AssertionError('JavaScript não respondeu.')
 return json.loads(out[0]) if out[0] else None
def ready():
 deadline=time.monotonic()+30
 while time.monotonic()<deadline:
  if js("!!window.__aurenInterfaceReady && !!document.querySelector('.lunvri-controls')"):return
  QTest.qWait(50)
 raise AssertionError('Interface não revelou o chat.')
def click(selector):
 assert js(f"(()=>{{const el=document.querySelector({json.dumps(selector)});if(!el)return false;el.click();return true}})()")
 QTest.qWait(400)
def layout():
 return js("(()=>{const r=s=>{const e=document.querySelector(s);if(!e)return null;const b=e.getBoundingClientRect();return [Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)]};return [r('#sidebar'),r('.lunvri-controls'),r('#chat-input')]})()")
def capture(name,menu=None):
 selector='.lunvri-controls' if not menu else menu
 box=js(f"(()=>{{const boxes=[...document.querySelectorAll({json.dumps(selector if menu else '.lunvri-controls .selector')})].map(e=>e.getBoundingClientRect());const x=Math.min(...boxes.map(b=>b.x)),y=Math.min(...boxes.map(b=>b.y)),right=Math.max(...boxes.map(b=>b.right)),bottom=Math.max(...boxes.map(b=>b.bottom));return {{x,y,w:right-x,h:bottom-y}}}})()")
 path=Path(__file__).resolve().parents[1]/'reports'/name
 window.web.grab(QRect(int(box['x']),int(box['y']),int(box['w'])+2,int(box['h'])+2)).save(str(path))
def menu_metrics(selector):
 return js(f"(()=>{{const panel=document.querySelector({json.dumps(selector)}),list=panel.querySelector('.auren-choice-list'),chosen=list.querySelector('[aria-checked=true]');const b=panel.getBoundingClientRect(),v=list.getBoundingClientRect(),c=chosen?.getBoundingClientRect();return {{panelHeight:b.height,listHeight:v.height,scrollHeight:list.scrollHeight,scrollTop:list.scrollTop,chosenVisible:!c||(c.top>=v.top-1&&c.bottom<=v.bottom+1),rowHeights:[...list.querySelectorAll('[data-choice]')].slice(0,8).map(x=>x.getBoundingClientRect().height),overflowX:document.documentElement.scrollWidth>innerWidth}}}})()")
window.setUrl(QUrl('http://127.0.0.1:8175/'))
QTest.qWait(600)
pulse1=js("(()=>{const e=document.querySelector('#splash-screen img');if(!e)return null;const s=getComputedStyle(e);return {transform:s.transform,width:s.width,height:s.height,animation:s.animationName}})()")
QTest.qWait(500)
pulse2=js("(()=>{const e=document.querySelector('#splash-screen img');if(!e)return null;const s=getComputedStyle(e);return {transform:s.transform,width:s.width,height:s.height,animation:s.animationName}})()")
result['pulse_changes_transform_only']=bool(pulse1 and pulse2 and pulse1['animation']=='auren-loading' and pulse1['width']==pulse2['width']=='104px' and pulse1['transform']!=pulse2['transform'])
ready();QTest.qWait(500)
result['default_labels']=js("[...document.querySelectorAll('.lunvri-controls .selector')].map(e=>e.textContent.trim())")
assert 'Automática' in result['default_labels'][0]
assert 'Automático' in result['default_labels'][1]
assert 'Automático' in result['default_labels'][2]
result['matching_trigger_text']=js("(()=>{const font=s=>{const c=getComputedStyle(document.querySelector(s));return [c.fontFamily,c.fontSize,c.fontWeight,c.lineHeight,c.color]};return {task:font('.task-trigger strong'),mode:font('.mode-trigger strong'),automatic:font('.automatic-label'),heights:[...document.querySelectorAll('.lunvri-controls .selector')].map(x=>x.getBoundingClientRect().height)}})()")
assert result['matching_trigger_text']['task']==result['matching_trigger_text']['mode']==result['matching_trigger_text']['automatic']
capture('auren-perfis-cartoes-iniciais-2026-10-13.png')
if '--capture-only' in sys.argv:
 window.close();print(json.dumps(result),flush=True);raise SystemExit(0)

result['equal_automatic_widths']=js("[...document.querySelectorAll('.lunvri-controls .selector')].map(e=>Math.round(e.getBoundingClientRect().width))")
assert result['equal_automatic_widths']==[176,176,176]
click('.mode-trigger')
result['automatic_profiles']=js("[...document.querySelectorAll('.modes-panel [data-choice] strong')].map(e=>e.textContent)")
assert result['automatic_profiles']==['Automático']
click('.modes-panel [data-choice]')
expected={
 'Conversar':['Éter','Ímpeto','Insight','Arquiteto'],
 'Gerar imagens':['Centelha','Aurora','Prisma'],
 'Analisar documentos':['Prisma','Lente','Atlas','Cartógrafo'],
 'Gerar código':['Oficina','Faísca','Nexo','Forja'],
 'Pesquisa aprofundada':['Trama','Radar','Horizonte','Observatório'],
 'Gerar voz':['Vox'],
 'Transcrever áudio':['Escuta','Lusofonia','Echo']}
result['task_profiles']={}
for task,names in expected.items():
 click('[aria-label="Tarefa da Auren"]')
 assert js(f"(()=>{{const e=[...document.querySelectorAll('[aria-label=\"Tarefas da Auren\"] [data-choice]')].find(e=>e.querySelector('strong')?.textContent==={json.dumps(task)});if(!e)return false;e.click();return true}})()")
 QTest.qWait(300);click('.mode-trigger')
 found=js("[...document.querySelectorAll('.modes-panel [data-choice] strong')].map(e=>e.textContent)")
 assert found==names,(task,found)
 assert js("(()=>{document.querySelectorAll('.modes-panel [data-choice]').item(document.querySelectorAll('.modes-panel [data-choice]').length-1).click();return true})()")
 QTest.qWait(200);selected=js("document.querySelector('.mode-trigger strong').textContent")
 assert selected==names[-1];result['task_profiles'][task]=found
 # A fresh empty conversation intentionally resets on reload. Check per-task
 # restoration by switching away and back, without creating a user conversation.
 click('[aria-label="Tarefa da Auren"]')
 assert js("(()=>{[...document.querySelectorAll('[aria-label=\"Tarefas da Auren\"] [data-choice]')].find(e=>e.querySelector('strong')?.textContent==='Automática').click();return true})()")
 QTest.qWait(250);click('[aria-label="Tarefa da Auren"]')
 assert js(f"(()=>{{[...document.querySelectorAll('[aria-label=\"Tarefas da Auren\"] [data-choice]')].find(e=>e.querySelector('strong')?.textContent==={json.dumps(task)}).click();return true}})()")
 QTest.qWait(250);assert js("document.querySelector('.mode-trigger strong').textContent")==selected
# The preceding task is transcription. Inspect compatibility per language profile.
for name,cohere_expected in [('Escuta',False),('Echo',True)]:
 click('.mode-trigger')
 assert js(f"(()=>{{[...document.querySelectorAll('.modes-panel [data-choice]')].find(e=>e.querySelector('strong')?.textContent==={json.dumps(name)}).click();return true}})()")
 QTest.qWait(250);click('[aria-label="Modelo da Auren"]')
 cohere=js("[...document.querySelectorAll('.models-panel .provider-heading')].some(e=>e.textContent.includes('Cohere'))")
 assert cohere==cohere_expected
 result['transcribe_'+name+'_cohere_visible']=cohere
 click('.models-panel button[data-choice]')
click('[aria-label="Tarefa da Auren"]')
assert js("(()=>{[...document.querySelectorAll('[aria-label=\"Tarefas da Auren\"] [data-choice]')].find(e=>e.querySelector('strong')?.textContent==='Automática').click();return true})()")
QTest.qWait(300);click('.mode-trigger')
assert js("[...document.querySelectorAll('.modes-panel [data-choice] strong')].map(e=>e.textContent)")==['Automático']
click('.modes-panel [data-choice]')
click('[aria-label="Modelo da Auren"]')
assert js("(()=>{const input=document.querySelector('[aria-label=\"Filtrar modelos\"]');input.value='Tiny Aya Water';input.dispatchEvent(new Event('input',{bubbles:true}));return true})()")
QTest.qWait(400)
assert js("(()=>{const e=[...document.querySelectorAll('.model-choice')].find(e=>!e.disabled&&e.querySelector('strong')?.textContent==='Tiny Aya Water');if(!e)return false;e.click();return true})()")
QTest.qWait(300)
result['manual_model']=js("(()=>{const e=document.querySelector('.model-trigger');return {caption:e.querySelector('small').textContent,name:e.querySelector('strong').textContent,width:e.getBoundingClientRect().width,align:getComputedStyle(e.querySelector('strong')).textAlign,textX:e.querySelector('strong').getBoundingClientRect().x}})()")
assert result['manual_model']['caption']=='Modelo' and 176<=result['manual_model']['width']<=224 and result['manual_model']['align']=='left'
capture('auren-perfis-cartoes-manual-2026-10-13.png')
click('[aria-label="Modelo da Auren"]');click('.models-panel button[data-choice]')
capture('auren-perfis-cartoes-automaticos-2026-10-13.png')
result['matching_model_alignment']=abs(result['manual_model']['textX']-js("document.querySelector('.model-trigger strong').getBoundingClientRect().x"))<1
assert result['matching_model_alignment']
window.resize(520,720);QTest.qWait(500)
result['narrow_widths']=js("[...document.querySelectorAll('.lunvri-controls .selector')].map(e=>e.getBoundingClientRect().width)")
assert max(result['narrow_widths'])-min(result['narrow_widths'])<1
result['no_horizontal_overflow']=js('document.documentElement.scrollWidth<=innerWidth');assert result['no_horizontal_overflow']
result['page_background']=window.page().backgroundColor().name();assert result['page_background']=='#080d17'
window.close();print(json.dumps(result),flush=True)
window.web.setPage(QWebEnginePage(window.web))
