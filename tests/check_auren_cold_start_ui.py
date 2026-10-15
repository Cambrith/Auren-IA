"""Check the real service-wait HTML and a fresh frontend profile without rebooting."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from auren_window import AurenWindow, AUREN_BACKGROUND
from lunvri_desktop import startup_html
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl
from PySide6.QtGui import QPalette
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript
from PySide6.QtTest import QTest

app = QApplication([])
window = AurenWindow()
profile = QWebEngineProfile(window)  # Empty cache and no personal browser storage.
window.setPage(QWebEnginePage(profile, window.web))
window.resize(1200, 760)
guard = QWebEngineScript()
guard.setInjectionPoint(QWebEngineScript.DocumentCreation)
guard.setWorldId(QWebEngineScript.MainWorld)
guard.setSourceCode(r"""
const originalFetch = window.fetch;
window.__coldApiWaiting = false; window.__coldDelayUsed = false; window.__blockedWrites = 0;
window.fetch = async (...args) => {
  const url = String(args[0]), method = (args[1]?.method ?? 'GET').toUpperCase();
  if (method !== 'GET' && /chat\/completions|\/api\/v1\/chats/.test(url)) {
    window.__blockedWrites++; throw new Error('No chat writes in startup verification');
  }
  if (url.endsWith('/api/config') && !window.__coldDelayUsed) {
    window.__coldDelayUsed = true; window.__coldApiWaiting = true;
    await new Promise(resolve => setTimeout(resolve, 3000));
    window.__coldApiWaiting = false;
  }
  return originalFetch(...args);
};
""")
window.page().scripts().insert(guard)
window.show()


def js(code):
    out = []
    window.page().runJavaScript('JSON.stringify(' + code + ')', out.append)
    deadline = time.monotonic() + 10
    while not out and time.monotonic() < deadline:
        QTest.qWait(10)
    assert out, 'JavaScript timeout'
    return json.loads(out[0]) if out[0] else None


def until(code):
    deadline = time.monotonic() + 50
    while time.monotonic() < deadline:
        if js(code):
            return
        QTest.qWait(50)
    raise AssertionError(code)


def sample():
    frame = window.web.grab().toImage()
    w, h = frame.width(), frame.height()
    return [frame.pixelColor(x, y).name() for x, y in
            ((8, 8), (w-9, 8), (8, h-9), (w-9, h-9))]


checks = {
    'native_window_blue': window.palette().color(QPalette.ColorRole.Window).name() == AUREN_BACKGROUND,
    'native_view_blue': window.web.palette().color(QPalette.ColorRole.Base).name() == AUREN_BACKGROUND,
    'native_page_blue': window.page().backgroundColor().name() == AUREN_BACKGROUND,
    'isolated_empty_cache': profile.isOffTheRecord(),
}
blank = []
for _ in range(5):
    QTest.qWait(40)
    blank.append(sample())
checks['before_html_blue'] = all(c == AUREN_BACKGROUND for row in blank for c in row)
window.setHtml(startup_html())
until("document.querySelector('img')?.complete && document.querySelector('img')?.naturalWidth>0")
styles = js("({html:getComputedStyle(document.documentElement).backgroundColor,body:getComputedStyle(document.body).backgroundColor})")
checks['service_wait_html_blue'] = styles == {'html':'rgb(8, 13, 23)', 'body':'rgb(8, 13, 23)'}
waiting = []
for _ in range(30):
    QTest.qWait(100)
    waiting.append(sample())
checks['service_wait_frames_blue'] = all(c == AUREN_BACKGROUND for row in waiting for c in row)
window.web.grab().save(str(ROOT / 'reports/auren-primeira-abertura-espera-2026-10-15.png'))

window.setUrl(QUrl('http://127.0.0.1:8175/?temporary-chat=true'))
until('window.__coldApiWaiting===true')
hydrating = []
while js('window.__coldApiWaiting===true'):
    hydrating.append(sample())
    QTest.qWait(70)
checks['fresh_frontend_wait_blue'] = len(hydrating)>5 and all(c == AUREN_BACKGROUND for row in hydrating for c in row)
until("document.getElementById('splash-screen') && !document.getElementById('splash-screen').classList.contains('leaving')")
checks['frontend_splash_blue'] = js("getComputedStyle(document.getElementById('splash-screen')).backgroundColor==='rgb(8, 13, 23)'")
window.web.grab().save(str(ROOT / 'reports/auren-primeira-abertura-interface-2026-10-15.png'))
until("window.__aurenInterfaceReady===true && !!document.querySelector('.lunvri-controls')")
checks['frontend_reaches_conversation'] = True
checks['no_chat_writes'] = js('window.__blockedWrites===0')
checks['sample_counts'] = {'before_html':len(blank),'service_wait':len(waiting),'frontend_wait':len(hydrating)}
assert all(v for k,v in checks.items() if k != 'sample_counts'), checks
(ROOT / 'reports/auren-primeira-abertura-ui-2026-10-15.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(checks,ensure_ascii=False),flush=True)
window.close()
window.web.setPage(QWebEnginePage(window.web))
