"""Run against the actual Qt/Wayland compositor; operates only this test window."""
import json
import sys
import os
import subprocess
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from auren_window import AurenWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QObject, Slot, ClassInfo
from PySide6.QtDBus import QDBusConnection
from PySide6.QtTest import QTest
app=QApplication([])
window=AurenWindow()
window.setHtml('<html><body style="background:#080d17;color:white">Verificação da janela Auren</body></html>')
window.showMaximized()
QTest.qWait(700)
checks={}
@ClassInfo(**{'D-Bus Interface':'org.cambrith.AurenWindowTest'})
class Probe(QObject):
    result=None
    @Slot(str)
    def report(self,value):self.result=json.loads(value)
probe=Probe()
bus=QDBusConnection.sessionBus()
service='org.cambrith.AurenWindowTest.p'+str(os.getpid())
assert bus.registerService(service)
assert bus.registerObject('/Probe',probe,QDBusConnection.ExportAllSlots)
def compositor_state():
    # Read only this test process's windows; do not alter compositor settings/windows.
    script=f"callDBus('{service}','/Probe','org.cambrith.AurenWindowTest','report',JSON.stringify(workspace.windowList().filter(w=>w.pid=={os.getpid()}).map(w=>({{minimized:w.minimized,fullscreen:w.fullScreen,geometry:w.frameGeometry,area:workspace.clientArea(KWin.MaximizeArea,w)}}))));"
    name='auren-window-test-'+str(os.getpid())
    probe.result=None
    with tempfile.NamedTemporaryFile(mode='w',suffix='.js') as f:
        f.write(script);f.flush()
        loaded=subprocess.check_output(['qdbus6','org.kde.KWin','/Scripting','org.kde.kwin.Scripting.loadScript',f.name,name],text=True).strip()
        try:
            subprocess.run(['qdbus6','org.kde.KWin','/Scripting/Script'+loaded,'org.kde.kwin.Script.run'],check=True,capture_output=True)
            QTest.qWait(400)
            return probe.result
        finally:subprocess.run(['qdbus6','org.kde.KWin','/Scripting','org.kde.kwin.Scripting.unloadScript',name],capture_output=True)

def restored_geometry_matches():
    state=compositor_state()[0]
    area,geometry=state['area'],state['geometry']
    width,height=min(910,area['width']),min(600,area['height'])
    expected=(area['x']+(area['width']-width)//2,area['y']+(area['height']-height)//2,width,height)
    actual=tuple(geometry[key] for key in ('x','y','width','height'))
    print('restored geometry',actual,'expected',expected,flush=True)
    return actual==expected

checks['starts_maximized']=window.isMaximized()
QTest.mouseClick(window.maximize,Qt.LeftButton);QTest.qWait(700)
checks['startup_restore_centered_910x600']=restored_geometry_matches()
window.minimize.clicked.connect(lambda: print('minimize clicked',flush=True))
window.maximize.clicked.connect(lambda: print('maximize clicked',flush=True))
window.fullscreen_shortcut.activated.connect(lambda: print('shortcut',window.windowState(),window.previous_state,flush=True))
checks['platform']=app.platformName()
checks['three_window_buttons']=window.controls.layout().count()==3
checks['frameless']=bool(window.windowFlags()&Qt.FramelessWindowHint)
normal=window.geometry()
window.activateWindow();window.setFocus();QTest.qWait(300)
QTest.keyClick(window,Qt.Key_F11);QTest.qWait(700)
print('state',window.windowState(),window.previous_state,flush=True)
checks['F11_enters_fullscreen']=window.isFullScreen() and not window.controls.isVisible()
window.activateWindow();window.setFocus();QTest.qWait(300)
QTest.keyClick(window,Qt.Key_F11);QTest.qWait(700)
print('state',window.windowState(),window.previous_state,flush=True)
checks['F11_restores_normal']=not window.isFullScreen() and not window.isMaximized() and window.size()==normal.size()
QTest.mouseClick(window.maximize,Qt.LeftButton);QTest.qWait(500)
checks['maximize']=window.isMaximized()
checks['restore_icon_state']=window.maximize.accessibleName()=='Restaurar'
window.activateWindow();window.setFocus();QTest.qWait(300)
QTest.keyClick(window,Qt.Key_F11);QTest.qWait(700)
print('state',window.windowState(),window.previous_state,flush=True)
checks['maximized_to_fullscreen']=window.isFullScreen()
window.activateWindow();window.setFocus();QTest.qWait(300)
QTest.keyClick(window,Qt.Key_F11);QTest.qWait(700)
print('state',window.windowState(),window.previous_state,flush=True)
checks['fullscreen_restores_maximized']=window.isMaximized() and not window.isFullScreen()
QTest.mouseClick(window.maximize,Qt.LeftButton);QTest.qWait(500)
checks['restore_button']=not window.isMaximized()
checks['repeated_restore_centered_910x600']=restored_geometry_matches()
checks['maximize_icon_state']=window.maximize.accessibleName()=='Maximizar'
window.resize(520,440);QTest.qWait(300)
checks['resize_and_controls_contained']=window.width()==520 and window.header.rect().contains(window.controls.geometry())
checks['resize_handles']=all(edge.isVisible() for edge in window.edges)
QTest.mouseClick(window.minimize,Qt.LeftButton)
print('minimize immediate',window.windowState(),window.isActiveWindow(),flush=True)
QTest.qWait(1000)
print('minimize compositor',window.windowState(),window.isActiveWindow(),window.windowHandle().visibility(),flush=True)
native=compositor_state();print('native minimize',native,flush=True)
checks['minimize']=bool(native and native[0]['minimized'])
window.showNormal();window.raise_();window.activateWindow();QTest.qWait(700)
native=compositor_state()
checks['restore_minimized']=bool(native and not native[0]['minimized'])
QTest.mouseClick(window.close_button,Qt.LeftButton);QTest.qWait(300)
checks['close']=not window.isVisible()
print(json.dumps(checks,ensure_ascii=False))
assert all(v for k,v in checks.items() if k!='platform'),checks
