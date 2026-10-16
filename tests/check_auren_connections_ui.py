"""Native card UI, real Sortable drag and disk order persistence in an isolated test backend.
No production preference, vault, chat or provider writes. Uses synthetic credentials only.
"""
import json
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from integration import auren_settings as settings,auren_credentials as credentials
from integration.auren_connection_registry import CONNECTIONS,fields
from auren_window import AurenWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl,QRect,QPoint,QPointF,QEvent,Qt
from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineScript
from PySide6.QtTest import QTest
from PySide6.QtGui import QMouseEvent

class Vault:
    def __init__(self):self.data={}
    def get(self,k):return self.data.get(k,'')
    def set(self,k,v):self.data[k]=v
    def delete(self,k):self.data.pop(k,None)
vault=Vault();checks={};calls=[];connection_checks={}
temporary=tempfile.TemporaryDirectory(prefix='auren-connections-ui-')
for obj in (settings,credentials):obj.STATE=Path(temporary.name)
settings.catalog=lambda **kw:[]

def state():
    return {'connections':[{'id':id,'name':spec.name,'state':'catalog_available' if id=='bedrock' else 'configured' if spec.key in vault.data else 'unconfigured',
            'count':0,'image_count':0,'auth_kind':spec.kind,'fields':fields(id),'check':connection_checks.get(id)} for id,spec in CONNECTIONS.items()],
            'preferences':settings.preferences(),'tasks':[],'models':[],'version':'0.12.0','local':True}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,data):
        body=json.dumps(data).encode();self.send_response(200)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
        self.send_header('Access-Control-Allow-Origin','http://127.0.0.1:8175')
        self.send_header('Access-Control-Allow-Headers','Content-Type');self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS')
        self.end_headers();self.wfile.write(body)
    def do_OPTIONS(self):self.respond({})
    def do_GET(self):self.respond(state())
    def do_POST(self):
        payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path.endswith('preferences'):
            result=settings.save_preferences(payload);calls.append('order')
        elif self.path.endswith('provider'):
            result=settings.save_connection(payload['provider'],payload['fields'],vault);calls.append('vault')
        elif self.path.endswith('validate'):
            result={'status':'success','reason':'ok','message':'Consulta autenticada concluída (simulação local).','checked_at':'2026-10-15T00:00:00Z'}
            if payload['provider']=='bedrock':result={'status':'failed','reason':'auth_error','message':'Credencial recusada (teste local).','checked_at':'2026-10-15T00:00:00Z'}
            connection_checks[payload['provider']]=result;calls.append('validate')
        elif self.path.endswith('oauth/canva/start'):
            result={'url':'https://www.canva.com/api/oauth/authorize?client_id=synthetic-client'};calls.append('oauth')
        else:result={}
        self.respond(result)
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
class Page(QWebEnginePage):
    def acceptNavigationRequest(self,url,kind,main_frame):
        if main_frame and url.host()=='www.canva.com' and url.path()=='/api/oauth/authorize':
            checks['oauth_native_navigation']=True
            return False  # Test handoff without opening an external website or granting permissions.
        return super().acceptNavigationRequest(url,kind,main_frame)

app=QApplication([]);window=AurenWindow();profile=QWebEngineProfile(window)
window.setPage(Page(profile,window.web));window.web.setZoomFactor(1);window.resize(1440,950)
guard=QWebEngineScript();guard.setInjectionPoint(QWebEngineScript.DocumentCreation);guard.setWorldId(QWebEngineScript.MainWorld)
guard.setSourceCode(r'''
const nativeFetch=window.fetch;window.__aurenOriginalFetch=nativeFetch;window.__blockedWrites=0;
window.fetch=async (url,options={})=>{
 const path=String(url);
 if(path.startsWith('/api/v1/auren/'))return nativeFetch('http://127.0.0.1:PORT/'+path.slice('/api/v1/auren/'.length),{method:options.method??'GET',headers:options.body?{'Content-Type':'application/json'}:{},...(options.body?{body:options.body}:{})});
 if((options.method??'GET').toUpperCase()!=='GET' && /chat\/completions|images\/generations|\/api\/v1\/chats/.test(path)) {window.__blockedWrites++;throw Error('Production writes blocked');}
 return nativeFetch(url,options);
};
'''.replace('PORT',str(server.server_port)))
window.page().scripts().insert(guard);window.show()

def js(code):
    values=[];window.page().runJavaScript('JSON.stringify('+code+')',values.append)
    deadline=time.monotonic()+10
    while not values and time.monotonic()<deadline:QTest.qWait(20)
    assert values,'JavaScript timeout'
    return json.loads(values[0]) if values[0] else None

def until(code,seconds=45):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if js(code):return
        QTest.qWait(100)
    raise AssertionError({'condition':code,'completed_calls':calls,'status':js("document.querySelector('.auren-settings [role=status]')?.textContent"),'error':js("document.querySelector('.auren-settings [role=alert]')?.textContent")})

def click(selector):
    assert js(f"(()=>{{const e=document.querySelector({json.dumps(selector)});if(!e)return false;e.click();return true}})()")
    QTest.qWait(200)

def ids():return js("[...document.querySelectorAll('[data-connection-id]')].map(e=>e.dataset.connectionId)")

def capture(name):
    js("(()=>{document.querySelector('.auren-settings-page').scrollTop=0;return true})()")
    QTest.qWait(200)
    box=js("(()=>{const b=document.querySelector('.auren-settings').getBoundingClientRect();return [b.x,b.y,b.width,b.height]})()")
    window.web.grab(QRect(*(int(n) for n in box))).save(str(ROOT/'reports'/name))

def open_connections():
    window.native_action('settings');until("!!document.querySelector('[aria-controls=\"tab-admin-connections\"]')")
    click('[aria-controls="tab-admin-connections"]');until("document.querySelectorAll('[data-connection-id]').length===30")

try:
    window.setUrl(QUrl('http://127.0.0.1:8175/'))
    until("!!window.__aurenInterfaceReady && !!document.querySelector('.lunvri-controls')")
    open_connections();initial=ids()
    checks['exact_30_alphabetical']=initial==sorted(CONNECTIONS,key=lambda id:CONNECTIONS[id].name.casefold())
    checks['wide_three_columns']=js("getComputedStyle(document.querySelector('.connection-grid')).gridTemplateColumns.split(' ').length===3")
    checks['validation_buttons_30']=js("[...document.querySelectorAll('[data-connection-id] button')].filter(e=>e.textContent==='Validar conexão'&&e.getBoundingClientRect().width>0&&getComputedStyle(e).visibility==='visible').length===30")
    checks['canva_oauth_label']=js("document.querySelector('[data-connection-id=canva]').textContent.includes('Integração OAuth 2.0')")
    js("(()=>{document.querySelectorAll('[data-connection-id] .provider-badge img').forEach(i=>i.loading='eager');return true})()")
    until("document.querySelectorAll('[data-connection-id] .provider-badge img').length===30 && [...document.querySelectorAll('[data-connection-id] .provider-badge img')].every(i=>i.complete&&i.naturalWidth>0)")
    checks['all_30_provider_icons_loaded']=True
    checks['opaque_assets_have_render_masks']=js("['bedrock','cerebras','deepgram','fal','hyperbolic','canva','replicate'].every(id=>document.querySelector('[data-connection-id='+id+'] img').dataset.transparentSurface===id)")
    checks['transparent_edges_keep_no_white_matte']=js("!!document.querySelector('#provider-cutout-cerebras feColorMatrix[result=opaqueColors]')")
    checks['provider_badges_have_no_background']=js("[...document.querySelectorAll('[data-connection-id] .provider-badge')].every(e=>getComputedStyle(e).backgroundColor==='rgba(0, 0, 0, 0)'&&getComputedStyle(e).borderTopWidth==='0px')")
    checks['logos_keep_original_colors']=js("[...document.querySelectorAll('[data-connection-id] .provider-badge img')].every(i=>(i.classList.contains('monochrome')||i.dataset.transparentSurface||getComputedStyle(i).filter==='none')&&getComputedStyle(i).objectFit==='contain')")
    js("(()=>{document.documentElement.classList.remove('dark');document.documentElement.classList.add('light');return true})()")
    checks['logos_in_light_theme']=js("[...document.querySelectorAll('[data-connection-id] .provider-badge img')].every(i=>i.naturalWidth>0&&getComputedStyle(i).width==='20px')")
    js("(()=>{document.documentElement.classList.remove('light');document.documentElement.classList.add('dark');return true})()")
    checks['logos_in_dark_theme']=js("[...document.querySelectorAll('[data-connection-id] .provider-badge img')].every(i=>i.naturalWidth>0&&getComputedStyle(i).width==='20px')")
    checks['existing_surface_preserved']=js("(()=>{const s=getComputedStyle(document.querySelector('[data-connection-id]'));return s.borderRadius==='12px'&&s.padding==='14px'&&s.backgroundColor==='rgb(13, 23, 39)'})()")
    # Render the actual badges together for transparency QA, with synthetic account state only.
    js("""(()=>{const gallery=document.createElement('div');gallery.id='provider-transparency-preview';gallery.style.cssText='position:fixed;inset:0;z-index:2147483647;background:#080d17;display:grid;grid-template-columns:repeat(6,1fr);gap:12px;padding:24px;';document.querySelectorAll('[data-connection-id] .provider-badge').forEach(b=>{const cell=document.createElement('div');cell.style.cssText='display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:#dbe5ef;font:13px sans-serif;text-align:center;';const copy=b.cloneNode(true);copy.style.width='64px';copy.style.height='64px';copy.querySelector('img').style.width='48px';copy.querySelector('img').style.height='48px';cell.append(copy,document.createTextNode(b.title));gallery.append(cell)});document.body.append(gallery);return true})()""")
    QTest.qWait(300)
    window.web.grab().save(str(ROOT/'reports/auren-connections-30-transparent-icons-2026-10-15.png'))
    js("(()=>{document.querySelector('#provider-transparency-preview').remove();return true})()")
    capture('auren-connections-30-wide-2026-10-15.png')
    # Open a configuration and type a synthetic value before reordering another card.
    click('[data-connection-id=assemblyai] button:not(.connection-drag-handle)')
    until("document.activeElement===document.querySelector('.auren-settings form h3')")
    checks['configuration_form_receives_focus']=True
    js("(()=>{const e=document.querySelector('.auren-settings form input');e.value='synthetic-ui-only';e.dispatchEvent(new Event('input',{bubbles:true}));return true})()")
    js("(()=>{document.querySelector('[data-connection-id=aihorde]').scrollIntoView({block:'center'});return true})()")
    QTest.qWait(200)
    # Native mouse events exercise Sortable itself, including its DOM restoration callback.
    start=js("(()=>{const b=document.querySelector('[data-connection-id=aihorde] .connection-drag-handle').getBoundingClientRect();return [b.x+b.width/2,b.y+b.height/2]})()")
    end=js("(()=>{const b=document.querySelector('[data-connection-id=assemblyai]').getBoundingClientRect();return [b.x+b.width/2,b.bottom-10]})()")
    a,b=QPoint(*(int(n) for n in start)),QPoint(*(int(n) for n in end))
    js("(()=>{window.__dragCounts={};for(const type of ['pointerdown','pointermove','pointerup','dragstart','dragend'])document.addEventListener(type,e=>{window.__dragCounts[type]=(window.__dragCounts[type]??0)+1},true);return true})()")
    target=window.web.focusProxy() or window.web
    QTest.mouseMove(target,a);QTest.mousePress(target,Qt.LeftButton,Qt.NoModifier,a);QTest.qWait(150)
    for step in range(1,21):
        point=QPoint(a.x()+(b.x()-a.x())*step//20,a.y()+(b.y()-a.y())*step//20)
        event=QMouseEvent(QEvent.MouseMove,QPointF(point),QPointF(target.mapToGlobal(point)),Qt.NoButton,Qt.LeftButton,Qt.NoModifier)
        QApplication.sendEvent(target,event);QTest.qWait(30)
    QTest.mouseRelease(target,Qt.LeftButton,Qt.NoModifier,b);QTest.qWait(500)
    checks['native_mouse_drag']=ids()!=initial
    print(json.dumps({'native_mouse_drag':checks['native_mouse_drag'],'order_saved':bool(settings.preferences()['connection_order']),'pointer_events':js('window.__dragCounts')}),flush=True)
    # Keyboard ordering works independently and must hit the real isolated persistence endpoint.
    until("!document.querySelector('[data-connection-id=bedrock] .connection-drag-handle').disabled")
    previous=ids()
    js("(()=>{const e=document.querySelector('[data-connection-id=bedrock] .connection-drag-handle');e.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));return true})()")
    until("document.querySelector('.auren-settings [role=status]')?.textContent==='Ordem das conexões salva.'")
    checks['keyboard_order']=ids()!=previous
    checks['fields_survive_reordering']=js("document.querySelector('.auren-settings form h3').textContent.includes('AssemblyAI API')&&document.querySelector('.auren-settings form input').value==='synthetic-ui-only'")
    click('.auren-settings form button[type=submit]');until("!document.querySelector('.auren-settings form') && !document.querySelector('[data-connection-id=assemblyai] button:last-child').disabled")
    checks['credential_stays_with_card']=vault.get('ASSEMBLYAI_API_KEY')=='synthetic-ui-only' and not vault.get('AWS_BEARER_TOKEN_BEDROCK')
    click('[data-connection-id=assemblyai] button:last-child')
    until("document.querySelector('[data-connection-id=assemblyai] > div > span')?.title.includes('simulação local')")
    checks['validation_stays_with_card']=not js("Boolean(document.querySelector('[data-connection-id=bedrock] > div > span')?.title.includes('simulação local'))")
    until("!document.querySelector('[data-connection-id=bedrock] button:last-child').disabled")
    click('[data-connection-id=bedrock] button:last-child')
    until("document.querySelector('[data-connection-id=bedrock] > div > span')?.title.includes('Credencial recusada')")
    checks['failed_check_overrides_old_healthy_state']=js("!document.querySelector('[data-connection-id=bedrock] > div > span').classList.contains('healthy')")
    saved=ids();checks['persisted_to_disk']=settings.preferences()['connection_order']==saved and 'order' in calls
    js("(()=>{window.__aurenInterfaceReady=false;return true})()");window.web.reload();until("!!window.__aurenInterfaceReady && !!document.querySelector('.lunvri-controls')")
    open_connections();checks['order_after_reload']=ids()==saved
    for width,columns in ((800,2),(520,1)):
        window.resize(width,850);QTest.qWait(500)
        checks[f'columns_{width}']=js("getComputedStyle(document.querySelector('.connection-grid')).gridTemplateColumns.split(' ').length")==columns
        checks[f'no_overflow_{width}']=js("document.documentElement.scrollWidth<=innerWidth && document.querySelector('.connection-grid').scrollWidth<=document.querySelector('.connection-grid').clientWidth")
    capture('auren-connections-30-narrow-2026-10-15.png')
    click('[data-connection-id=canva] button:not(.connection-drag-handle)')
    checks['canva_three_distinct_fields']=js("document.querySelectorAll('.auren-settings form input[type=password]').length===3")
    until("!document.querySelector('.auren-settings form button[type=button]').disabled")
    click('.auren-settings form button[type=button]')
    until("document.querySelector('.auren-settings form [role=status]')?.textContent.includes('Conclua a autorização')")
    checks['oauth_request_sent']='oauth' in calls
    checks['oauth_native_navigation']=checks.get('oauth_native_navigation',False)
    checks['no_production_writes']=js('window.__blockedWrites===0')
    js("(()=>{window.__aurenOriginalFetch('/api/v1/auren/state',{headers:{Authorization:'Bearer '+localStorage.token}}).then(async r=>{const state=await r.json();window.__liveCheck={status:r.status,count:state.connections?.length,oauth:state.connections?.find(c=>c.id==='canva')?.auth_kind};}).catch(()=>window.__liveCheck={status:0});return true})()")
    until("!!window.__liveCheck")
    checks['authenticated_production_api_30']=js("window.__liveCheck.status===200 && window.__liveCheck.count===30 && window.__liveCheck.oauth==='oauth'")
    (ROOT/'reports/auren-connections-30-ui-2026-10-15.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(checks,ensure_ascii=False),flush=True)
    assert all(checks.values()),'UI checks failed; see sanitized report.'
finally:
    window.close();window.web.setPage(QWebEnginePage(window.web));server.shutdown();temporary.cleanup()
