"""Native composer admission on a text-only model; uploads and writes are mocked."""
import base64
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from auren_window import AurenWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineScript
from PySide6.QtTest import QTest

app=QApplication([]);window=AurenWindow();profile=QWebEngineProfile(window)
window.setPage(QWebEnginePage(profile,window.web));window.resize(1200,760)
guard=QWebEngineScript();guard.setInjectionPoint(QWebEngineScript.DocumentCreation);guard.setWorldId(QWebEngineScript.MainWorld)
guard.setSourceCode(r"""
const originalFetch=window.fetch;
window.__testUploads=[];window.__blockedWrites=0;
window.fetch=async (...args)=>{
  const url=String(args[0]),init=args[1]??{},method=(init.method??'GET').toUpperCase();
  if(url.includes('/api/v1/files')&&method==='POST'){
    const file=init.body.get('file');const id='synthetic-upload-'+window.__testUploads.length;
    window.__testUploads.push({name:file.name,type:file.type});
    return new Response(JSON.stringify({id,filename:file.name,meta:{content_type:file.type},status:'uploaded'}),{status:200,headers:{'Content-Type':'application/json'}});
  }
  if(method!=='GET'&&(/chat\/completions|\/api\/v1\/chats/.test(url))){window.__blockedWrites++;throw new Error('No production writes in UI check');}
  return originalFetch(...args);
};
""");window.page().scripts().insert(guard);window.show()

def js(code):
    out=[];window.page().runJavaScript('JSON.stringify('+code+')',out.append)
    deadline=time.monotonic()+10
    while not out and time.monotonic()<deadline:QTest.qWait(20)
    assert out,'JavaScript timeout'
    return json.loads(out[0]) if out[0] else None

def until(code):
    deadline=time.monotonic()+50
    while time.monotonic()<deadline:
        if js(code):return
        QTest.qWait(150)
    raise AssertionError({'condition':code,'page':js("({url:location.href,ready:window.__aurenInterfaceReady,fonts:document.fonts.status,body:document.body.innerText.slice(0,1200)})")})

def click(selector):
    assert js(f"(()=>{{const e=document.querySelector({json.dumps(selector)});if(!e)return false;e.click();return true}})()")
    QTest.qWait(250)

window.setUrl(QUrl('http://127.0.0.1:8175/'))
until("!!window.__aurenInterfaceReady&&!!document.querySelector('.lunvri-controls')")
click('.task-trigger')
assert js("(()=>{const e=[...document.querySelectorAll('[aria-label=\"Tarefas da Auren\"] [data-choice]')].find(e=>e.querySelector('strong')?.textContent==='Conversar');if(!e)return false;e.click();return true})()")
QTest.qWait(250);click('.model-trigger')
assert js("(()=>{const e=document.querySelector('[aria-label=\"Filtrar modelos\"]');e.value='gpt oss 120b groq';e.dispatchEvent(new Event('input',{bubbles:true}));return true})()")
QTest.qWait(300);click('.models-panel .model-choice')
chosen=js("document.querySelector('.model-trigger strong').textContent")
assert '120' in chosen
for name,mime in [('vision.png','image/png'),('document.pdf','application/pdf'),('pt.wav','audio/wav'),('video.mp4','video/mp4')]:
    encoded=base64.b64encode((ROOT/'reports/auren-gemini-groq-2026-10-14-r2/fixtures'/name).read_bytes()).decode()
    assert js(f"(()=>{{const input=document.querySelector('#auren-chat-file-input');const bytes=Uint8Array.from(atob({json.dumps(encoded)}),c=>c.charCodeAt(0));const dt=new DataTransfer();dt.items.add(new File([bytes],{json.dumps(name)},{{type:{json.dumps(mime)}}}));input.files=dt.files;input.dispatchEvent(new Event('change',{{bubbles:true}}));return true}})()")
    until(f"window.__testUploads.some(f=>f.name==={json.dumps(name)})")
    assert js("document.querySelector('.model-trigger strong').textContent")==chosen
result={'selected_model_kept':chosen,'accepted_uploads':js('window.__testUploads'),
        'all_uploads_mocked':True,'generation_not_called':js('window.__blockedWrites===0')}
assert len(result['accepted_uploads'])==4 and result['generation_not_called']
window.resize(520,720);QTest.qWait(400)
result['narrow_no_overflow']=js('document.documentElement.scrollWidth<=innerWidth')
assert result['narrow_no_overflow']
(ROOT/'reports/auren-attachment-ui-2026-10-14.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
window.close();window.web.setPage(QWebEnginePage(window.web));print(json.dumps(result),flush=True)
