"""Inspect only a disposable native Auren window; no provider generation calls."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from auren_window import AurenWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,QUrl
from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile
app=QApplication([])
window=AurenWindow()
profile=QWebEngineProfile(window)
window.setPage(QWebEnginePage(profile,window.web))
window.showMaximized();window.web.setFocus()
start=time.monotonic();ready_at=None;pending=False;measurements=[]
result={'file_menu_initial_focus':window.menu_buttons[0].hasFocus(),'focus_is_content':window.web.hasFocus()}
timer=QTimer(window)
def complete(value):
 global ready_at,pending
 pending=False
 if isinstance(value,str):
  try:value=json.loads(value)
  except ValueError:return
 if not isinstance(value,dict):return
 result['last_state']=value
 if not value.get('starting') and not value.get('splash') and value.get('composer'):
  if ready_at is None:ready_at=time.monotonic();result['interface_ready_s']=round(ready_at-start,3)
  measurements.append(value)
  if time.monotonic()-ready_at>=2:
   result['layout_after_reveal_stable']=all(m['sidebar']==measurements[0]['sidebar'] and m['composer']==measurements[0]['composer'] for m in measurements)
   result['file_menu_final_focus']=window.menu_buttons[0].hasFocus()
   result['native_marker_present']=value.get('native')
   result['samples_after_reveal']=len(measurements)
   output=Path(__file__).resolve().parents[1]/'reports/auren-barra-inicial-2026-10-13.png'
   window.header.grab().save(str(output))
   result['screenshot']=str(output)
   print(json.dumps(result),flush=True);timer.stop();window.close();app.quit()
def poll():
 global pending
 if time.monotonic()-start>60:
  result['timeout']=True;print(json.dumps(result),flush=True);timer.stop();window.close();app.quit();return
 if pending:return
 pending=True
 window.page().runJavaScript("""(()=>{const r=s=>{const e=document.querySelector(s);if(!e)return null;const b=e.getBoundingClientRect();return [Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)]};return JSON.stringify({starting:document.documentElement.classList.contains('auren-starting'),splash:!!document.getElementById('splash-screen'),native:document.documentElement.classList.contains('auren-desktop'),sidebar:r('#sidebar'),composer:r('#chat-input')})})()""",complete)
timer.timeout.connect(poll);timer.start(100)
window.setUrl(QUrl('http://127.0.0.1:8175/'))
app.exec()
window.web.setPage(QWebEnginePage(window.web))
