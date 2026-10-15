"""Persistent KDE window for the local Auren interface."""

from pathlib import Path
import os
import subprocess
import sys

from PySide6.QtCore import QLockFile, QUrl, QTimer
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket, QNetworkAccessManager, QNetworkRequest
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from auren_window import AurenWindow, AUREN_BACKGROUND
from auren_identity import DESKTOP_ID, ensure_icons, update_launcher

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8175'


def startup_html():
    """The service-wait screen paints the same blue before any HTTP request."""
    import base64
    icon = base64.b64encode((ROOT / 'static/lunvri-logo.png').read_bytes()).decode()
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
    <meta name="color-scheme" content="dark">
    <style>
    html,body{{margin:0;width:100%;height:100%;background:{AUREN_BACKGROUND};overflow:hidden}}
    body{{display:grid;place-items:center}}
    @keyframes pulse{{0%,100%{{opacity:.58;transform:scale(.985)}}50%{{opacity:.92;transform:scale(1.015)}}}}
    @media(prefers-reduced-motion:reduce){{img{{animation:none!important}}}}
    </style></head><body>
    <script>document.documentElement.style.setProperty('--auren-pulse-delay', -((Date.now()-window.__aurenLoadStarted)%2600)+'ms');</script>
    <img alt="Carregando Auren" src="data:image/png;base64,{icon}" style="width:104px;height:104px;object-fit:contain;filter:grayscale(1) brightness(.74);animation:pulse 2.6s ease-in-out infinite;animation-delay:var(--auren-pulse-delay,0ms);will-change:transform,opacity"/></body></html>"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Auren')
    app.setOrganizationName('Cambrith')
    app.setDesktopFileName(DESKTOP_ID)
    # Recover deleted local icon files without relying on the theme cache.
    icon_path, repaired = ensure_icons()
    launcher = Path.home() / '.local/share/applications' / (DESKTOP_ID + '.desktop')
    if launcher.exists(): update_launcher(launcher, icon_path)
    QIcon.setThemeSearchPaths([str(Path.home() / '.local/share/icons'), '/usr/share/icons', *QIcon.themeSearchPaths()])
    QIcon.setFallbackThemeName('hicolor')
    # A direct file keeps the window icon usable even with a stale theme cache.
    app.setWindowIcon(QIcon(str(icon_path)))
    instance = f'lunvri-desktop-{os.getuid()}'
    lock = QLockFile(str(Path(os.environ['XDG_RUNTIME_DIR']) / (instance + '.lock')))
    if not lock.tryLock(0):
        client = QLocalSocket()
        client.connectToServer(instance)
        if client.waitForConnected(2000):
            client.write(b'activate')
            client.waitForBytesWritten(1000)
        return 0
    profile = QWebEngineProfile('Auren', app)
    profile.setPersistentStoragePath(str(ROOT / '.cavren/desktop-profile'))
    profile.setCachePath(str(ROOT / '.cavren/desktop-cache'))
    profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)

    class Page(QWebEnginePage):
        def acceptNavigationRequest(self, url, kind, main_frame):
            if main_frame and url.scheme() in ('http', 'https') and (url.host() != '127.0.0.1' or url.port() != 8175):
                QDesktopServices.openUrl(url)
                return False
            return super().acceptNavigationRequest(url, kind, main_frame)

    view = AurenWindow()
    view.setPage(Page(profile, view))
    view.setWindowTitle('Auren')
    # The window is visible during service startup and frontend hydration.
    view.setHtml(startup_html())
    view.showMaximized()
    view.web.setFocus()
    server = QLocalServer(app)
    QLocalServer.removeServer(instance)
    server.listen(instance)

    def activate():
        client = server.nextPendingConnection()
        if client:
            client.close()
            client.deleteLater()
        view.activate_restored()
        try:
            result = subprocess.run(
                ['kdotool', 'search', '--class', 'cavren'], capture_output=True, text=True, timeout=2
            )
            if result.stdout.splitlines():
                subprocess.run(
                    ['kdotool', 'windowactivate', result.stdout.splitlines()[-1]], timeout=2, capture_output=True
                )
        except (OSError, subprocess.TimeoutExpired):
            pass

    server.newConnection.connect(activate)

    def download(request):
        filename, _ = QFileDialog.getSaveFileName(
            view, 'Salvar arquivo', str(Path.home() / 'Downloads' / request.downloadFileName())
        )
        if filename:
            request.setDownloadDirectory(str(Path(filename).parent))
            request.setDownloadFileName(Path(filename).name)
            request.accept()
        else:
            request.cancel()

    profile.downloadRequested.connect(download)
    process = subprocess.Popen(['systemctl', '--user', 'start', 'lunvri.service'])
    import time
    deadline = time.monotonic() + 180
    timer = QTimer(view)
    network = QNetworkAccessManager(view)
    pending = None

    def ready():
        nonlocal pending
        if time.monotonic() >= deadline or process.poll() not in (None, 0):
            timer.stop()
            if pending is not None: pending.abort()
            QMessageBox.critical(
                view, 'Auren', 'Não foi possível iniciar a Auren. Consulte o serviço lunvri.service.'
            )
            return
        if pending is not None: return
        request = QNetworkRequest(QUrl(URL + '/api/config'))
        request.setTransferTimeout(1000)
        reply = network.get(request)
        pending = reply

        def checked():
            nonlocal pending
            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            pending = None
            reply.deleteLater()
            if status == 200 and timer.isActive():
                timer.stop()
                view.setUrl(QUrl(URL))
                view.loadFinished.connect(
                    lambda ok: print('Auren: interface carregada.' if ok else 'Auren: falha ao carregar.', flush=True)
                )
        reply.finished.connect(checked)

    timer.timeout.connect(ready)
    timer.start(250)
    status = app.exec()
    view.page().deleteLater()
    return status


if __name__ == '__main__':
    raise SystemExit(main())
