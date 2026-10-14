"""Native selector regression checks in an isolated profile; no generation or saves."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from auren_window import AurenWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl, QRect, Qt
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript
from PySide6.QtTest import QTest

app = QApplication([])
window = AurenWindow()
profile = QWebEngineProfile(window)  # Off the record; no personal browser storage.
window.setPage(QWebEnginePage(profile, window.web))
window.web.setZoomFactor(1)
guard = QWebEngineScript()
guard.setInjectionPoint(QWebEngineScript.DocumentCreation)
guard.setWorldId(QWebEngineScript.MainWorld)
guard.setSourceCode(r"""
const originalFetch = window.fetch;
window.__blockedGenerations = 0;
window.fetch = async (...args) => {
  if (/images\/generations|chat\/completions/.test(String(args[0]))) {
    window.__blockedGenerations++;
    throw new Error('Generation disabled by UI test');
  }
  return originalFetch(...args);
};
""")
window.page().scripts().insert(guard)
window.resize(1200, 760)
window.show()
checks = {}


def js(code):
    values = []
    window.page().runJavaScript('JSON.stringify(' + code + ')', lambda value: values.append(value))
    deadline = time.monotonic() + 10
    while not values and time.monotonic() < deadline:
        QTest.qWait(10)
    assert values, 'JavaScript did not respond'
    return json.loads(values[0]) if values[0] else None


def until(code, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if js(code):
            return
        QTest.qWait(100)
    raise AssertionError(code)


def click(selector):
    assert js(f"(()=>{{const e=document.querySelector({json.dumps(selector)});if(!e)return false;e.click();return true}})()")
    QTest.qWait(300)


def task(name):
    click('.task-trigger')
    assert js(f"(()=>{{const e=[...document.querySelectorAll('[aria-label=\"Tarefas da Auren\"] [data-choice]')].find(e=>e.querySelector('strong')?.textContent==={json.dumps(name)});if(!e)return false;e.click();return true}})()")
    QTest.qWait(300)


def search(value):
    assert js(f"(()=>{{const e=document.querySelector('[aria-label=\"Filtrar modelos\"]');e.value={json.dumps(value)};e.dispatchEvent(new Event('input',{{bubbles:true}}));return true}})()")
    QTest.qWait(200)


def capture(name, selector):
    box = js(f"(()=>{{const b=document.querySelector({json.dumps(selector)}).getBoundingClientRect();return [b.x,b.y,b.width,b.height]}})()")
    window.web.grab(QRect(*(int(n) for n in box))).save(str(ROOT / 'reports' / name))


window.setUrl(QUrl('http://127.0.0.1:8175/'))
until("!!window.__aurenInterfaceReady && !!document.querySelector('.lunvri-controls')")
task('Gerar imagens')
click('.model-trigger')
checks['single_search'] = js("document.querySelectorAll('.models-panel input').length===1 && !document.querySelector('.models-panel select')")
checks['only_horde_group'] = js("[...document.querySelectorAll('.models-panel .provider-heading')].map(e=>e.textContent.trim())")
assert checks['single_search'] and checks['only_horde_group'] == ['AI Horde']
checks['footer_spacing'] = js("(()=>{const s=getComputedStyle(document.querySelector('.panel-footer'));return s.display==='flex' && parseFloat(s.columnGap)>=12})()")
assert checks['footer_spacing']
checks['image_models_shown'] = js("document.querySelectorAll('.models-panel .model-choice').length")
assert checks['image_models_shown'] > 0
capture('auren-imagens-seletor-amplo-2026-10-14.png', '.lunvri-selector-popover')
search(' HOrde deliberate ')
checks['combined_search'] = js("[...document.querySelectorAll('.models-panel .model-choice strong')].map(e=>e.textContent.trim())")
assert checks['combined_search'] and all('deliberate' in n.lower() for n in checks['combined_search'])
search('Gemini')
checks['paid_search_empty'] = js("!document.querySelector('.models-panel .model-choice') && !!document.querySelector('.empty-results')")
assert checks['paid_search_empty']
click('[aria-label="Limpar busca"]')
js("(()=>{document.querySelector('[aria-label=\"Filtrar modelos\"]').focus();return true})()")
js("(()=>{document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));return true})()")
QTest.qWait(150)
checks['keyboard_search_to_auto'] = js("document.activeElement.classList.contains('automatic-choice')")
js("(()=>{document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));return true})()")
QTest.qWait(150)
checks['keyboard_auto_to_model'] = js("document.activeElement.classList.contains('model-choice')")
assert checks['keyboard_search_to_auto'] and checks['keyboard_auto_to_model']
js("(()=>{document.activeElement.click();return true})()")
QTest.qWait(300)
checks['minimal_image_actions'] = js("(()=>{const e=document.querySelector('.image-actions');return !!e?.querySelector('input[type=checkbox]') && e.querySelectorAll('button').length===1 && e.querySelector('button').textContent==='Voltar à conversa' && !document.querySelector('.image-context') && getComputedStyle(e.querySelector('label')).color==='rgb(231, 182, 111)'})()")
assert checks['minimal_image_actions']
capture('auren-imagens-controles-2026-10-14.png', '.image-actions')
checkbox = js("document.querySelector('.image-actions input').checked")
click('.image-actions input')
checks['fallback_toggle'] = js("document.querySelector('.image-actions input').checked") != checkbox
assert checks['fallback_toggle']
window.resize(520, 720)
QTest.qWait(500)
click('.model-trigger')
checks['narrow_layout'] = js("(()=>{const p=document.querySelector('.models-panel').getBoundingClientRect(),l=document.querySelector('.models-panel .auren-choice-list');return p.left>=0 && p.right<=innerWidth && l.clientHeight>50 && l.scrollHeight>l.clientHeight && document.documentElement.scrollWidth<=innerWidth})()")
assert checks['narrow_layout']
capture('auren-imagens-seletor-estreito-2026-10-14.png', '.lunvri-selector-popover')
click('.models-panel .automatic-choice')
click('.image-actions button')
checks['returns_to_conversation'] = js("document.querySelector('.task-trigger strong').textContent==='Conversar' && !document.querySelector('.image-actions')")
assert checks['returns_to_conversation']
click('.model-trigger')
search('gemini')
checks['gemini_conversation_preserved'] = js("document.querySelectorAll('.models-panel .model-choice').length>0")
assert checks['gemini_conversation_preserved']
click('.models-panel .automatic-choice')
window.resize(1200, 760)
window.native_action('settings')
until("!!document.querySelector('[aria-controls=\"tab-admin-images\"]')", 10)
click('[aria-controls="tab-admin-images"]')
until("!!document.querySelector('.auren-settings select option[value*=\"gemini\"]')", 15)
checks['paid_image_config_preserved'] = js("!!document.querySelector('.auren-settings select option[value*=\"gemini\"]') && !!document.querySelector('.auren-settings select option[value*=\"openrouter\"]')")
assert checks['paid_image_config_preserved']
checks['no_generations'] = js('window.__blockedGenerations===0')
assert checks['no_generations']
(ROOT / 'reports' / 'auren-imagens-seletor-ui-2026-10-14.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(checks, ensure_ascii=False), flush=True)
window.close()
window.web.setPage(QWebEnginePage(window.web))
