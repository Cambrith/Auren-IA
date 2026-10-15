"""Synthetic Socket.IO progress in a temporary chat; no provider call or chat write."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from auren_window import AurenWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl, QRect
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript
from PySide6.QtTest import QTest

app = QApplication([])
window = AurenWindow()
profile = QWebEngineProfile(window)
window.setPage(QWebEnginePage(profile, window.web))
window.web.setZoomFactor(1)
window.resize(1200, 760)
guard = QWebEngineScript()
guard.setInjectionPoint(QWebEngineScript.DocumentCreation)
guard.setWorldId(QWebEngineScript.MainWorld)
guard.setSourceCode(r"""
const originalFetch = window.fetch, OriginalSocket = window.WebSocket;
window.__progressSockets = []; window.__testRequest = null; window.__blockedWrites = 0;
window.WebSocket = class extends OriginalSocket {
  constructor(...args) { super(...args); window.__progressSockets.push(this); }
};
window.fetch = async (...args) => {
  const url = String(args[0]), init = args[1] ?? {}, method = (init.method ?? 'GET').toUpperCase();
  if (url.includes('/chat/completions') && method === 'POST') {
    const body = JSON.parse(init.body);
    window.__testRequest = { chat_id:body.chat_id, message_id:body.id };
    return new Response(JSON.stringify({task_id:'synthetic-progress-task'}),
      {status:200,headers:{'Content-Type':'application/json'}});
  }
  if (method !== 'GET' && /images\/generations|\/api\/v1\/chats/.test(url)) {
    window.__blockedWrites++; throw new Error('No production writes in progress check');
  }
  return originalFetch(...args);
};
window.__emitProgress = (type,data) => {
  const body = {...window.__testRequest,data:{type,data}};
  const sockets = window.__progressSockets.filter(s=>s.readyState===1);
  for (const socket of sockets) socket.dispatchEvent(new MessageEvent('message',
    {data:'42'+JSON.stringify(['events',body])}));
  return sockets.length > 0;
};
""")
window.page().scripts().insert(guard)
window.show()


def js(code):
    out = []
    window.page().runJavaScript('JSON.stringify(' + code + ')', out.append)
    deadline = time.monotonic() + 10
    while not out and time.monotonic() < deadline:
        QTest.qWait(20)
    assert out, 'JavaScript timeout'
    return json.loads(out[0]) if out[0] else None


def until(code):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if js(code):
            return
        QTest.qWait(100)
    raise AssertionError({'condition':code,'visible':js("document.body.innerText.slice(-1600)")})


def emit(kind, data):
    assert js(f'window.__emitProgress({json.dumps(kind)},{json.dumps(data)})')
    QTest.qWait(200)


def capture(name):
    box = js("(()=>{const b=document.querySelector('.auren-activity').getBoundingClientRect();return [b.x,b.y,b.width,b.height]})()")
    window.web.grab(QRect(*(int(n) for n in box))).save(str(ROOT / 'reports' / name))


window.setUrl(QUrl('http://127.0.0.1:8175/?temporary-chat=true'))
until("!!window.__aurenInterfaceReady&&!!document.querySelector('.lunvri-controls')")
assert js("(()=>{window.postMessage({type:'input:prompt:submit',text:'Teste sintetico de progresso.'},location.origin);return true})()")
until('!!window.__testRequest')
until('window.__progressSockets.some(s=>s.readyState===1)')
emit('status', {'action':'web_search','description':'Pesquisando na web','done':False})
until("document.querySelector('.auren-activity')?.textContent.includes('Pesquisando na web')")
checks = {'single_search_status':js("document.querySelectorAll('.lunvri-response .status-description').length===1&&document.querySelectorAll('.auren-activity').length===1"),
          'animated_mark':js("!!document.querySelector('.auren-activity .lunvri-mark.active')")}
capture('auren-progresso-unico-pesquisa-2026-10-14.png')
emit('status', {'action':'web_search','description':'Consultando fontes públicas','done':False})
until("document.querySelector('.auren-activity')?.textContent.includes('Consultando fontes públicas')")
checks['current_step_replaces_previous'] = js("!document.querySelector('.lunvri-response').textContent.includes('Pesquisando na web')")
emit('status', {'action':'web_search','description':'Pesquisa concluída','urls':['https://example.org'],'done':True})
until("document.querySelector('.auren-activity')?.textContent.includes('Organizando')")
assert js("(()=>{document.querySelector('.auren-activity .cursor-pointer').click();return true})()")
until("!!document.querySelector('.auren-activity a[href=\"https://example.org\"]')")
checks['search_results_preserved'] = True
emit('status', {'action':'image_generation','state':'queued','queue_position':2,'wait_time':10,'done':False})
until("document.querySelector('.auren-activity')?.textContent.includes('Posição na fila: 2')")
checks['single_image_status'] = js("document.querySelectorAll('.auren-activity').length===1&&document.querySelectorAll('.lunvri-response .status-description').length===0")
capture('auren-progresso-unico-imagem-2026-10-14.png')
window.resize(520, 720)
QTest.qWait(300)
checks['narrow_no_overflow'] = js('document.documentElement.scrollWidth<=innerWidth')
emit('chat:completion', {'content':'Resposta sintetica normal.','done':True})
until("!document.querySelector('.auren-activity')&&document.querySelector('.lunvri-response')?.textContent.includes('Resposta sintetica normal.')")
checks['ordinary_response_after_completion'] = js("!document.querySelector('.lunvri-response .status-description')")
checks['no_chat_writes'] = js('window.__blockedWrites===0')
checks['provider_calls_mocked'] = True
assert all(checks.values()), checks
(ROOT / 'reports/auren-progresso-unico-ui-2026-10-14.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(checks,ensure_ascii=False),flush=True)
window.close()
window.web.setPage(QWebEnginePage(window.web))
