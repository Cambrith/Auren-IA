"""Actual Qt WebEngine download, using a real generated Horde image as the fixture."""
import base64
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from auren_window import AurenWindow
app=QApplication([])
window=AurenWindow()
profile=QWebEngineProfile('AurenDownloadTest',window)
window.setPage(QWebEnginePage(profile,window.web))
original=Path('.cavren/auren-real-horde.webp').read_bytes()
result=[]
with tempfile.TemporaryDirectory() as target:
    def download(item):
        item.setDownloadDirectory(target);item.setDownloadFileName('Auren.webp')
        item.isFinishedChanged.connect(lambda:result.append(item.state().name) if item.isFinished() else None)
        item.accept()
    profile.downloadRequested.connect(download)
    data=base64.b64encode(original).decode()
    window.setHtml('<a id="download" download="Auren.webp" href="data:image/webp;base64,'+data+'">Salvar imagem gerada</a>')
    window.show();QTest.qWait(800)
    window.page().runJavaScript("document.getElementById('download').click()")
    for _ in range(30):
        if result:break
        QTest.qWait(100)
    path=Path(target)/'Auren.webp'
    assert path.exists() and path.read_bytes()==original,(result,path.exists())
    print('Native WebEngine download verified:',result,len(original),'bytes')
window.close()
