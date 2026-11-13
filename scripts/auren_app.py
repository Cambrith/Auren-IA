"""Auren como app: janela limpa sem barra de título nativa, com controles mínimos e abertura imediata."""

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

from PySide6.QtCore import QEvent, QRect, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPainter, QPalette, QPen, QPixmap, QShortcut
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QHBoxLayout, QToolButton, QVBoxLayout, QWidget

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get('AUREN_PORT', '8080'))
URL = f'http://127.0.0.1:{PORT}'
STATE = Path.home() / '.local/share/auren'
AUREN_BG = '#080d17'
EDGE_SIZE = 6


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
    background: {AUREN_BG};
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


def control_icon(kind: str) -> QIcon:
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor('#9aa8b8'), 1.35))
    if kind == 'minimize':
        painter.drawLine(3, 10, 13, 10)
    elif kind == 'maximize':
        painter.drawRect(3, 3, 10, 10)
    elif kind == 'restore':
        painter.drawRect(5, 2, 8, 8)
        painter.fillRect(2, 5, 8, 8, QColor(AUREN_BG))
        painter.drawRect(2, 5, 8, 8)
    elif kind == 'close':
        painter.drawLine(4, 4, 12, 12)
        painter.drawLine(12, 4, 4, 12)
    painter.end()
    return QIcon(pixmap)


class DragStrip(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.window().toggle_maximized()


class ResizeEdge(QWidget):
    def __init__(self, window: QWidget, edges, cursor):
        super().__init__(window)
        self.edges = edges
        self.setCursor(cursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemResize(self.edges)
            event.accept()


class AurenMainWindow(QWidget):
    def __init__(self, profile: QWebEngineProfile):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowTitle('Auren')
        self.setMinimumSize(520, 420)
        self.resize(1280, 860)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(AUREN_BG))
        palette.setColor(QPalette.ColorRole.Base, QColor(AUREN_BG))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = DragStrip(self)
        self.header.setObjectName('aurenCleanBar')
        self.header.setFixedHeight(28)
        row = QHBoxLayout(self.header)
        row.setContentsMargins(0, 0, 4, 0)
        row.setSpacing(2)
        row.addStretch(1)

        self.btn_min = self._make_btn('minimize', 'Minimizar', self.showMinimized)
        self.btn_max = self._make_btn('maximize', 'Maximizar', self.toggle_maximized)
        self.btn_close = self._make_btn('close', 'Fechar', self.close)
        self.btn_close.setObjectName('aurenCloseBtn')
        for btn in (self.btn_min, self.btn_max, self.btn_close):
            row.addWidget(btn)

        self.web = QWebEngineView(self)
        self.web.setPalette(palette)
        self.web.setAutoFillBackground(True)
        page = QWebEnginePage(profile, self.web)
        page.setBackgroundColor(QColor(AUREN_BG))
        self.web.setPage(page)

        root.addWidget(self.header)
        root.addWidget(self.web, 1)

        self.setStyleSheet(f'''
            QWidget#aurenCleanBar {{
                background: {AUREN_BG};
            }}
            QWidget#aurenCleanBar QToolButton {{
                background: transparent;
                border: 0;
                border-radius: 6px;
                padding: 0;
            }}
            QWidget#aurenCleanBar QToolButton:hover {{
                background: rgba(255, 255, 255, 0.08);
            }}
            QWidget#aurenCleanBar QToolButton#aurenCloseBtn:hover {{
                background: #9f2938;
            }}
        ''')

        self.fullscreen_shortcut = QShortcut(QKeySequence('F11'), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)

        edge_defs = (
            (Qt.Edge.TopEdge, Qt.CursorShape.SizeVerCursor),
            (Qt.Edge.BottomEdge, Qt.CursorShape.SizeVerCursor),
            (Qt.Edge.LeftEdge, Qt.CursorShape.SizeHorCursor),
            (Qt.Edge.RightEdge, Qt.CursorShape.SizeHorCursor),
            (Qt.Edge.TopEdge | Qt.Edge.LeftEdge, Qt.CursorShape.SizeFDiagCursor),
            (Qt.Edge.TopEdge | Qt.Edge.RightEdge, Qt.CursorShape.SizeBDiagCursor),
            (Qt.Edge.BottomEdge | Qt.Edge.LeftEdge, Qt.CursorShape.SizeBDiagCursor),
            (Qt.Edge.BottomEdge | Qt.Edge.RightEdge, Qt.CursorShape.SizeFDiagCursor),
        )
        self.edges = [ResizeEdge(self, e, c) for e, c in edge_defs]
        self._layout_edges()

    def _make_btn(self, kind: str, tip: str, slot) -> QToolButton:
        btn = QToolButton(self.header)
        btn.setIcon(control_icon(kind))
        btn.setToolTip(tip)
        btn.setFixedSize(28, 24)
        btn.clicked.connect(slot)
        return btn

    def toggle_maximized(self):
        if self.isMaximized() or self.isFullScreen():
            self.showNormal()
        else:
            self.showMaximized()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.header.show()
        else:
            self.header.hide()
            self.showFullScreen()

    def _update_max_icon(self):
        if self.isMaximized():
            self.btn_max.setIcon(control_icon('restore'))
            self.btn_max.setToolTip('Restaurar')
        else:
            self.btn_max.setIcon(control_icon('maximize'))
            self.btn_max.setToolTip('Maximizar')

    def _layout_edges(self):
        w, h, s = self.width(), self.height(), EDGE_SIZE
        geometries = (
            QRect(s, 0, max(0, w - 2 * s), s),
            QRect(s, h - s, max(0, w - 2 * s), s),
            QRect(0, s, s, max(0, h - 2 * s)),
            QRect(w - s, s, s, max(0, h - 2 * s)),
            QRect(0, 0, s, s),
            QRect(w - s, 0, s, s),
            QRect(0, h - s, s, s),
            QRect(w - s, h - s, s, s),
        )
        hide = self.isMaximized() or self.isFullScreen()
        for edge, rect in zip(self.edges, geometries):
            edge.setVisible(not hide)
            edge.setGeometry(rect)
            edge.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_edges()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._update_max_icon()
            self._layout_edges()


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

    win = AurenMainWindow(profile)

    if already_up:
        win.web.load(QUrl(URL))
        win.show()
        sys.exit(app.exec())

    win.web.setHtml(splash_html(), QUrl('about:blank'))
    win.show()

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
            win.web.load(QUrl(URL))
        elif state['failed']:
            timer.stop()
            sys.exit(f'Servidor não iniciou; veja {STATE / "server.log"}')

    timer.timeout.connect(check_ready)
    timer.start(100)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
