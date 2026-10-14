"""Native menu/profile checks in an isolated profile, without production writes."""
import json
import sys
import time
from pathlib import Path
from urllib.request import urlopen

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
const originalFetch = window.fetch;
window.__blockedWrites = 0;
window.fetch = async (...args) => {
  const url = String(args[0]), method = (args[1]?.method ?? 'GET').toUpperCase();
  if (method !== 'GET' && /chat\/completions|images\/generations|\/api\/v1\/chats/.test(url)) {
    window.__blockedWrites++;
    throw new Error('Production writes disabled by UI verification');
  }
  return originalFetch(...args);
};
""")
window.page().scripts().insert(guard)
window.show()


def js(code):
    values = []
    window.page().runJavaScript('JSON.stringify(' + code + ')', values.append)
    deadline = time.monotonic() + 10
    while not values and time.monotonic() < deadline:
        QTest.qWait(20)
    assert values, 'JavaScript timeout'
    return json.loads(values[0]) if values[0] else None


def until(code):
    deadline = time.monotonic() + 50
    while time.monotonic() < deadline:
        if js(code):
            return
        QTest.qWait(100)
    raise AssertionError({'condition': code, 'page': js("({url:location.href,fonts:document.fonts.status,body:document.body.innerText.slice(0,800)})")})


def click(selector):
    assert js(f"(()=>{{const e=document.querySelector({json.dumps(selector)});if(!e)return false;e.click();return true}})()")
    QTest.qWait(250)


def task(name):
    click('.task-trigger')
    assert js(f"(()=>{{const e=[...document.querySelectorAll('[aria-label=\"Tarefas da Auren\"] [data-choice]')].find(e=>e.querySelector('strong')?.textContent==={json.dumps(name)});if(!e)return false;e.click();return true}})()")
    QTest.qWait(250)


def capture(name, expression):
    box = js(f"(()=>{{const b=({expression}).getBoundingClientRect();return [b.x,b.y,b.width,b.height]}})()")
    window.web.grab(QRect(*(int(n) for n in box))).save(str(ROOT / 'reports' / name))


# A systemd restart returns before the preview's HTTP server is ready.
deadline = time.monotonic() + 40
while True:
    try:
        with urlopen('http://127.0.0.1:8175/', timeout=2) as response:
            if response.status == 200:
                break
    except OSError:
        pass
    assert time.monotonic() < deadline, 'Preview HTTP server unavailable'
    QTest.qWait(200)
window.setUrl(QUrl('http://127.0.0.1:8175/'))
until("!!window.__aurenInterfaceReady && !!document.querySelector('.lunvri-controls')")
checks = {}
click('.task-trigger')
checks['task_icons'] = js("[...document.querySelectorAll('.modes-panel [data-choice]')].every(e=>!!e.querySelector('.choice-symbol svg'))")
click('.modes-panel [data-choice]')
checks['profile_icons'] = {}
for name in ('Conversar', 'Gerar imagens', 'Analisar documentos', 'Gerar código', 'Pesquisa aprofundada', 'Gerar voz', 'Transcrever áudio'):
    task(name)
    click('.mode-trigger')
    icons = js("[...document.querySelectorAll('.modes-panel [data-choice]')].map(e=>e.querySelector('.choice-symbol svg')?.innerHTML)")
    assert all(icons) and len(set(icons)) == len(icons), (name, icons)
    checks['profile_icons'][name] = len(icons)
    if name == 'Analisar documentos':
        capture('auren-menu-perfis-documentos-2026-10-14.png', "document.querySelector('.lunvri-selector-popover')")
    click('.modes-panel [data-choice]')

task('Conversar')
click('.model-trigger')
assert js("(()=>{const e=document.querySelector('[aria-label=\"Filtrar modelos\"]');e.value='gpt oss 120b groq';e.dispatchEvent(new Event('input',{bubbles:true}));return true})()")
QTest.qWait(250)
click('.models-panel .model-choice')
checks['selected_model_icon'] = js("!!document.querySelector('.model-trigger .provider-badge.compact img') && !!document.querySelector('.model-trigger .connection-dot')")
until("document.querySelector('.model-trigger img')?.complete")
assert js("document.querySelector('.model-trigger img').naturalWidth>0")
capture('auren-menu-seletores-2026-10-14.png', "document.querySelector('.lunvri-controls')")

click('#input-menu-button')
until("!!document.querySelector('[data-auren-web-search]')")
checks['direct_web_search'] = js("document.querySelector('[data-auren-web-search]').textContent.trim()==='Pesquisar na web'")
checks['no_plugins_or_image_shortcut'] = js("[...document.querySelector('[data-auren-web-search]').parentElement.querySelectorAll('button')].every(e=>!['Plugins','Gerar imagens'].includes(e.textContent.trim()))")
checks['matching_menu_style'] = js("(()=>{const web=document.querySelector('[data-auren-web-search]'),other=[...web.parentElement.querySelectorAll('button')].find(e=>e!==web);const style=e=>{const s=getComputedStyle(e);return [s.height,s.fontSize,s.fontWeight,s.paddingLeft,s.borderRadius]};return !!other&&JSON.stringify(style(web))===JSON.stringify(style(other))})()")
capture('auren-menu-mais-2026-10-14.png', "document.querySelector('[data-auren-web-search]').parentElement")
click('[data-auren-web-search]')
click('#input-menu-button')
checks['web_toggle_on'] = js("document.querySelector('[data-auren-web-search]').getAttribute('aria-pressed')==='true'")
click('[data-auren-web-search]')
click('#input-menu-button')
checks['web_toggle_off'] = js("document.querySelector('[data-auren-web-search]').getAttribute('aria-pressed')==='false'")
click('#input-menu-button')

task('Gerar imagens')
click('#input-menu-button')
checks['image_generation_preserved'] = js("!!document.querySelector('.image-actions') && document.querySelector('.task-trigger strong').textContent==='Gerar imagens'")
checks['web_disabled_in_images'] = js("document.querySelector('[data-auren-web-search]').disabled")
click('#input-menu-button')
task('Conversar')
window.resize(520, 720)
QTest.qWait(500)
click('#input-menu-button')
checks['narrow_menu'] = js("(()=>{const b=document.querySelector('[data-auren-web-search]').parentElement.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth&&document.documentElement.scrollWidth<=innerWidth})()")
capture('auren-menu-mais-estreito-2026-10-14.png', "document.querySelector('[data-auren-web-search]').parentElement")
checks['no_generation_or_chat_writes'] = js('window.__blockedWrites===0')
assert all(value for value in checks.values()), checks
(ROOT / 'reports/auren-menu-ui-2026-10-14.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(checks, ensure_ascii=False), flush=True)
window.close()
window.web.setPage(QWebEnginePage(window.web))
