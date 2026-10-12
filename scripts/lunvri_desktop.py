"""Persistent KDE window for the local Auren interface."""

from pathlib import Path
import os
import subprocess
import sys

from PySide6.QtCore import QLockFile, QUrl, QTimer
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from auren_window import AurenWindow

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8175'


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Auren')
    app.setOrganizationName('Cambrith')
    app.setDesktopFileName('cavren')
    QIcon.setThemeSearchPaths([str(Path.home() / '.local/share/icons'), '/usr/share/icons', *QIcon.themeSearchPaths()])
    QIcon.setFallbackThemeName('hicolor')
    app.setWindowIcon(QIcon.fromTheme('lunvri', QIcon(str(ROOT / 'static/lunvri-icon.png'))))
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
    shown = False
    def show_ready(ok):
        nonlocal shown
        if ok and not shown:
            view.showMaximized(); shown = True
    view.loadFinished.connect(show_ready)
    server = QLocalServer(app)
    QLocalServer.removeServer(instance)
    server.listen(instance)

    def activate():
        client = server.nextPendingConnection()
        if client:
            client.close()
            client.deleteLater()
        if view.isMinimized():
            view.showMaximized()
        view.raise_()
        view.activateWindow()
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
    attempts = 0
    timer = QTimer(view)

    def ready():
        nonlocal attempts
        import urllib.request
        import urllib.error

        attempts += 1
        try:
            with urllib.request.urlopen(URL + '/api/config', timeout=0.5) as response:
                if response.status == 200:
                    timer.stop()
                    view.setUrl(QUrl(URL))
                    view.loadFinished.connect(
                        lambda ok: print(
                            'Auren: interface carregada.' if ok else 'Auren: falha ao carregar.', flush=True
                        )
                    )
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        if attempts >= 180 or process.poll() not in (None, 0):
            timer.stop()
            QMessageBox.critical(
                view, 'Auren', 'Não foi possível iniciar a Auren. Consulte o serviço lunvri.service.'
            )

    timer.timeout.connect(ready)
    timer.start(1000)
    status = app.exec()
    view.page().deleteLater()
    return status


if __name__ == '__main__':
    raise SystemExit(main())
