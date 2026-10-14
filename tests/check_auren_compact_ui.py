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
capture('auren-seletores-compactos-2026-10-13.png')
if '--capture-only' in sys.argv:
 window.close();print(json.dumps(result),flush=True);raise SystemExit(0)
click('[aria-label="Tarefa da Auren"]');result['task_menu_wide']=menu_metrics('[aria-label="Tarefas da Auren"]');capture('auren-tarefas-compactas-2026-10-13.png','[aria-label="Tarefas da Auren"]')
assert js("(()=>{const b=[...document.querySelector('[aria-label=\"Tarefas da Auren\"]').querySelectorAll('[data-choice]')];b.at(-1).click();return true})()")
QTest.qWait(300);click('[aria-label="Tarefa da Auren"]');result['last_task_visible']=menu_metrics('[aria-label="Tarefas da Auren"]')['chosenVisible'];assert result['last_task_visible']
assert js("(()=>{const b=[...document.querySelector('[aria-label=\"Tarefas da Auren\"]').querySelectorAll('[data-choice]')].find(x=>x.textContent.includes('Conversar'));b.click();return true})()")
QTest.qWait(300);click('[aria-label="Modelo da Auren"]');result['model_menu_wide']=menu_metrics('[aria-label="Modelos disponíveis"]');capture('auren-modelos-compactos-2026-10-13.png','[aria-label="Modelos disponíveis"]')
assert js("(()=>{const b=[...document.querySelector('[aria-label=\"Modelos disponíveis\"]').querySelectorAll('.model-choice:not(:disabled)')].at(-1);if(!b)return false;b.click();return true})()")
QTest.qWait(200);click('[aria-label="Modelo da Auren"]');result['last_model_visible']=menu_metrics('[aria-label="Modelos disponíveis"]')['chosenVisible'];assert result['last_model_visible']
assert js("(()=>{document.querySelector('[aria-label=\"Modelos disponíveis\"] button[data-choice]').click();return true})()")
QTest.qWait(300);window.resize(520,720);QTest.qWait(500)
click('[aria-label="Tarefa da Auren"]');result['task_menu_narrow']=menu_metrics('[aria-label="Tarefas da Auren"]')
geometry=[]
for _ in range(8):geometry.append(menu_metrics('[aria-label="Tarefas da Auren"]')['panelHeight']);QTest.qWait(100)
result['menu_height_stable']=max(geometry)-min(geometry)<1;assert result['menu_height_stable']
assert js("(()=>{document.querySelector('[aria-label=\"Tarefas da Auren\"] [aria-checked=true]').click();return true})()")
QTest.qWait(300)
for i in range(3):
 window.web.reload();ready();QTest.qWait(400);before=layout();QTest.qWait(1000);assert layout()==before
 result['repeated_open_'+str(i+1)+'_stable']=True
before=layout();size=window.size();window.showMinimized();QTest.qWait(400);window.activate_restored();QTest.qWait(700)
result['normal_resume_preserves_size']=window.size()==size and not window.isMaximized();assert result['normal_resume_preserves_size']
result['resume_layout_stable']=layout()==before;assert result['resume_layout_stable']
result['no_horizontal_overflow']=js('document.documentElement.scrollWidth<=innerWidth');assert result['no_horizontal_overflow']
result['page_background']=window.page().backgroundColor().name();assert result['page_background']=='#080d17'
window.close();print(json.dumps(result),flush=True)
window.web.setPage(QWebEnginePage(window.web))
