"""Observe only a disposable Auren window and its KDE association."""
import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from auren_identity import ensure_icons,DESKTOP_ID
from PySide6.QtWidgets import QApplication,QWidget,QHBoxLayout,QVBoxLayout,QLabel
from PySide6.QtCore import Qt,QObject,Slot,ClassInfo
from PySide6.QtGui import QIcon
from PySide6.QtDBus import QDBusConnection
from PySide6.QtTest import QTest
app=QApplication([]);app.setApplicationName('Auren');app.setDesktopFileName(DESKTOP_ID)
icon_path,_=ensure_icons();app.setWindowIcon(QIcon(str(icon_path)))
QIcon.setThemeSearchPaths([str(Path.home()/'.local/share/icons'),'/usr/share/icons',*QIcon.themeSearchPaths()]);QIcon.setFallbackThemeName('hicolor')
icon=QIcon.fromTheme('auren')
w=QWidget();w.setWindowTitle('Auren — verificação de ícones');w.setStyleSheet('background:#101720;color:#d7e4ef');layout=QVBoxLayout(w);layout.addWidget(QLabel('Auren · ícones recuperados'))
row=QHBoxLayout();layout.addLayout(row)
for size in (16,24,32,48,64,128):
 cell=QVBoxLayout();image=QLabel();image.setPixmap(icon.pixmap(size,size));cell.addWidget(image,alignment=Qt.AlignCenter);cell.addWidget(QLabel(str(size)+' px'),alignment=Qt.AlignCenter);row.addLayout(cell)
w.show();QTest.qWait(500)
@ClassInfo(**{'D-Bus Interface':'org.cambrith.AurenIconTest'})
class Probe(QObject):
 result=None
 @Slot(str)
 def report(self,value):self.result=json.loads(value)
probe=Probe();bus=QDBusConnection.sessionBus();service='org.cambrith.AurenIconTest.p'+str(os.getpid());assert bus.registerService(service);assert bus.registerObject('/Probe',probe,QDBusConnection.ExportAllSlots)
script=f"callDBus('{service}','/Probe','org.cambrith.AurenIconTest','report',JSON.stringify(workspace.windowList().filter(w=>w.pid=={os.getpid()}).map(w=>({{desktopFileName:w.desktopFileName,resourceClass:w.resourceClass}}))));"
name='auren-icon-test-'+str(os.getpid())
with tempfile.NamedTemporaryFile(mode='w',suffix='.js') as f:
 f.write(script);f.flush();loaded=subprocess.check_output(['qdbus6','org.kde.KWin','/Scripting','org.kde.kwin.Scripting.loadScript',f.name,name],text=True).strip()
 try:
  subprocess.run(['qdbus6','org.kde.KWin','/Scripting/Script'+loaded,'org.kde.kwin.Script.run'],check=True,capture_output=True);QTest.qWait(400)
 finally:subprocess.run(['qdbus6','org.kde.KWin','/Scripting','org.kde.kwin.Scripting.unloadScript',name],capture_output=True)
result={'theme_icon_found':QIcon.hasThemeIcon('auren'),'native_window_icon_valid':not w.windowIcon().pixmap(32,32).isNull(),'desktop_id':app.desktopFileName(),'compositor':probe.result}
result['window_associated']=bool(probe.result and any(str(x.get('desktopFileName','')).removesuffix('.desktop').endswith('cavren') for x in probe.result))
output=Path(__file__).resolve().parents[1]/'reports/auren-icones-verificados-2026-10-13.png';w.grab().save(str(output));result['preview']=str(output)
w.close();print(json.dumps(result),flush=True)
assert result['theme_icon_found'] and result['native_window_icon_valid'] and result['window_associated']
