"""Auren como app: abre a janela nativa AurenWindow imediatamente e inicia o servidor em segundo plano."""

import base64
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QTimer, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWidgets import QApplication, QFileDialog

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auren_window import AUREN_BACKGROUND, AurenWindow

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get('AUREN_PORT', '8080'))
URL = f'http://127.0.0.1:{PORT}'
STATE = Path.home() / '.local/share/auren'


def healthy(timeout: float = 0.25) -> bool:
    try:
        with urllib.request.urlopen(f'{URL}/api/config', timeout=timeout) as resp:
            if resp.status != 200:
                return False
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('features', {}).get('auth') is False
    except OSError:
        return False


def secret_key() -> str:
    key_file = STATE / 'secret_key'
    if not key_file.exists():
        STATE.mkdir(parents=True, exist_ok=True)
        key_file.write_text(secrets.token_hex(32))
        key_file.chmod(0o600)
    return key_file.read_text().strip()


def build_server_env() -> dict[str, str]:
    env = {
        **os.environ,
        'WEBUI_NAME': 'Auren',
        'WEBUI_AUTH': 'False',
        'WEBUI_SECRET_KEY': secret_key(),
        'DATA_DIR': str(STATE / 'data'),
        'ENABLE_VERSION_UPDATE_CHECK': 'False',
        'AUREN_LAZY_EMBEDDINGS': '1',
    }
    hf_cached = Path.home() / '.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2'
    if hf_cached.exists():
        env.setdefault('HF_HUB_OFFLINE', '1')
        env.setdefault('TRANSFORMERS_OFFLINE', '1')
    return env


def spawn_server() -> subprocess.Popen:
    subprocess.run(
        ['pkill', '-f', f'[u]vicorn open_webui.main:app.*--port {PORT}'],
        check=False,
    )
    time.sleep(0.2)
    (STATE / 'data').mkdir(parents=True, exist_ok=True)
    return subprocess.Popen(
        [
            str(ROOT / '.venv/bin/uvicorn'),
            'open_webui.main:app',
            '--host',
            '127.0.0.1',
            '--port',
            str(PORT),
        ],
        cwd=ROOT / 'backend',
        env=build_server_env(),
        stdout=(STATE / 'server.log').open('a'),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def splash_html() -> str:
    logo_path = ROOT / 'static/lunvri-logo.png'
    logo_tag = ''
    if logo_path.exists():
        b64 = base64.b64encode(logo_path.read_bytes()).decode('ascii')
        logo_tag = f'<img src="data:image/png;base64,{b64}" alt="Auren" />'
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<style>
  html, body {{
    margin: 0;
    width: 100%;
    height: 100%;
    background: {AUREN_BACKGROUND};
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }}
  img {{
    width: 112px;
    height: 112px;
    object-fit: contain;
    animation: aurenPulse 2.6s ease-in-out infinite;
  }}
  @keyframes aurenPulse {{
    0%, 100% {{ opacity: 0.72; transform: scale(0.98); }}
    50% {{ opacity: 1; transform: scale(1.03); }}
  }}
</style>
</head>
<body>{logo_tag}</body>
</html>"""


def main():
    already_up = healthy(timeout=0.2)

    app = QApplication(sys.argv)
    app.setApplicationName('Auren')
    app.setDesktopFileName('auren')
    app.setWindowIcon(QIcon(str(ROOT / 'static/favicon.png')))

    profile = QWebEngineProfile('auren', app)
    profile.setPersistentStoragePath(str(STATE / 'webengine'))
    profile.setCachePath(str(STATE / 'webengine/cache'))
    profile.setPersistentCookiesPolicy(
        QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
    )

    win = AurenWindow()
    win.set_header_unlocked(False)
    win.setPage(QWebEnginePage(profile, win.web))

    def reveal_header_when_loaded(ok: bool):
        if ok and win.web.url().toString().startswith(URL):
            QTimer.singleShot(250, lambda: win.set_header_unlocked(True))

    win.web.loadFinished.connect(reveal_header_when_loaded)

    def handle_download(download):
        downloads_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation) or str(Path.home() / 'Downloads')
        suggested = download.downloadFileName() or 'download'
        target, _ = QFileDialog.getSaveFileName(win, 'Salvar arquivo', str(Path(downloads_dir) / suggested))
        if target:
            download.setDownloadDirectory(str(Path(target).parent))
            download.setDownloadFileName(Path(target).name)
            download.accept()
        else:
            download.cancel()

    profile.downloadRequested.connect(handle_download)

    if already_up:
        win.setUrl(QUrl(URL))
        win.maximize_window()
        QTimer.singleShot(50, win.showMaximized)
        sys.exit(app.exec())

    win.setHtml(splash_html())
    win.maximize_window()
    QTimer.singleShot(50, win.showMaximized)

    state = {'proc': None, 'ready': False, 'failed': False}

    def boot_worker():
        state['proc'] = spawn_server()
        while not state['ready']:
            if state['proc'].poll() is not None:
                state['failed'] = True
                return
            if healthy(timeout=0.3):
                state['ready'] = True
                return
            time.sleep(0.12)

    threading.Thread(target=boot_worker, daemon=True).start()

    timer = QTimer(win)

    def check_ready():
        if state['ready']:
            timer.stop()
            win.setUrl(QUrl(URL))
        elif state['failed']:
            timer.stop()
            sys.exit(f'Servidor não iniciou; veja {STATE / "server.log"}')

    timer.timeout.connect(check_ready)
    timer.start(100)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
