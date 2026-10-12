"""Native Auren toolbar and window controls, with real Qt/Wayland window states."""
import os
import shutil

from PySide6.QtCore import QEvent, QProcess, QRect, Qt, QTimer, QSettings
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMenu, QToolButton, QVBoxLayout, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineScript


def toolbar_icon(kind):
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor('#a9bdd0'), 1.4))
    if kind in ('back', 'forward'):
        direction = 1 if kind == 'back' else -1
        painter.drawLine(4, 9, 14, 9)
        x = 4 if direction == 1 else 14
        painter.drawLine(x, 9, x + 4*direction, 5)
        painter.drawLine(x, 9, x + 4*direction, 13)
    elif kind == 'sidebar':
        painter.drawRoundedRect(2, 3, 14, 12, 2, 2)
        painter.drawLine(7, 3, 7, 15)
    elif kind == 'minimize':
        painter.drawLine(4, 12, 14, 12)
    elif kind == 'maximize':
        painter.drawRect(4, 4, 10, 10)
    elif kind == 'restore':
        painter.drawRect(7, 3, 8, 8)
        painter.fillRect(3, 7, 8, 8, QColor('#101720'))
        painter.drawRect(3, 7, 8, 8)
    elif kind == 'close':
        painter.drawLine(5, 5, 13, 13)
        painter.drawLine(13, 5, 5, 13)
    else:
        for y in (5, 9, 13):
            painter.drawLine(3, y, 15, y)
    painter.end()
    return QIcon(pixmap)


class TitleBar(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.window().toggle_maximized()


class ResizeEdge(QWidget):
    def __init__(self, window, edges, cursor):
        super().__init__(window)
        self.edges = edges
        self.setCursor(cursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            handle = self.window().windowHandle()
            if handle:
                handle.startSystemResize(self.edges)
            event.accept()


class AurenWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint
                            | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle('Auren')
        self.setMinimumSize(420, 360)
        # Keep a centered normal geometry underneath the maximized state. This
        # makes the single maximize/restore control shrink symmetrically, like
        # the user's ChatGPT desktop reference (910x600 at 1x scale).
        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            width = min(910, area.width())
            height = min(600, area.height())
            self.setGeometry(
                area.x() + (area.width() - width) // 2,
                area.y() + (area.height() - height) // 2,
                width,
                height,
            )
        self.previous_state = Qt.WindowNoState
        self.previous_geometry = QRect()
        self.restore_timer = QTimer(self)
        self.restore_timer.setSingleShot(True)
        self.restore_timer.timeout.connect(self.showMaximized)
        self.normal_geometry_timer = QTimer(self)
        self.normal_geometry_timer.setSingleShot(True)
        self.normal_geometry_timer.timeout.connect(self.apply_restore_geometry)
        self.kwin_geometry_process = QProcess(self)
        self.web = QWebEngineView(self)
        self.loadFinished = self.web.loadFinished
        self.preferences = QSettings('Cambrith', 'Auren')
        try:
            zoom = float(self.preferences.value('interface/zoom', 1))
        except (TypeError, ValueError):
            zoom = 1
        self.web.setZoomFactor(max(.75, min(1.75, zoom)))
        self.fullscreen_shortcut = QShortcut(QKeySequence('F11'), self)
        self.fullscreen_shortcut.setContext(Qt.WindowShortcut)
        self.fullscreen_shortcut.setAutoRepeat(False)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.header = TitleBar(self)
        self.header.setObjectName('aurenTitleBar')
        self.header.setFixedHeight(40)
        self.header.setAccessibleName('Barra superior da Auren')
        row = QHBoxLayout(self.header)
        row.setContentsMargins(7, 3, 5, 3)
        row.setSpacing(2)
        self.back = self.button('back', 'Voltar', self.web.back)
        self.forward = self.button('forward', 'Avançar', self.web.forward)
        self.sidebar = self.button('sidebar', 'Alternar barra lateral', lambda: self.native_action('sidebar'))
        for button in (self.back, self.forward, self.sidebar):
            row.addWidget(button)
        self.menu_buttons = []
        self.menus = {}
        for name in ('Arquivo', 'Editar', 'Exibir', 'Ajuda'):
            menu = QMenu(name, self.header)
            button = QToolButton(self.header)
            button.setText(name)
            button.setAccessibleName('Menu '+name)
            button.setPopupMode(QToolButton.InstantPopup)
            button.setMenu(menu)
            button.setFixedHeight(32)
            row.addWidget(button)
            self.menu_buttons.append(button)
            self.menus[name] = menu
        self.compact_menu = QMenu(self.header)
        for menu in self.menus.values():
            self.compact_menu.addMenu(menu)
        self.menu_toggle = self.button('menu', 'Menus da aplicação', lambda: None)
        self.menu_toggle.setMenu(self.compact_menu)
        self.menu_toggle.setPopupMode(QToolButton.InstantPopup)
        row.addWidget(self.menu_toggle)
        row.addStretch(1)  # This empty area supports native dragging.

        self.controls = QWidget(self.header)
        controls = QHBoxLayout(self.controls)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(0)
        self.minimize = self.button('minimize', 'Minimizar', self.showMinimized, self.controls)
        self.maximize = self.button('maximize', 'Maximizar', self.toggle_maximized, self.controls)
        self.close_button = self.button('close', 'Fechar', self.close, self.controls)
        self.close_button.setObjectName('aurenCloseButton')
        for button in (self.minimize, self.maximize, self.close_button):
            controls.addWidget(button)
        row.addWidget(self.controls)
        root.addWidget(self.header)
        root.addWidget(self.web, 1)
        self.setStyleSheet('''
            QWidget#aurenTitleBar {background:#101720; border-bottom:1px solid #1a2b3d;}
            QWidget#aurenTitleBar QToolButton {color:#a9bdd0; background:transparent;
                border:0; border-radius:5px; padding:0 7px; font-size:13px;}
            QWidget#aurenTitleBar QToolButton:hover {background:#1a2b3d; color:#f4faff;}
            QWidget#aurenTitleBar QToolButton:focus {border:1px solid #59e0f3;}
            QWidget#aurenTitleBar QToolButton:disabled {color:#50667e;}
            QWidget#aurenTitleBar QToolButton::menu-indicator {image:none;}
            QWidget#aurenTitleBar QToolButton#aurenCloseButton:hover {background:#8f2634;}
            QMenu {background:#0d1727; color:#d7e4ef; border:1px solid #2a3b50; padding:5px;}
            QMenu::item {padding:7px 24px 7px 12px; border-radius:4px;}
            QMenu::item:selected {background:#1a2b3d; color:#f4faff;}
            QMenu::item:disabled {color:#50667e;}
            QMenu::separator {height:1px; background:#2a3b50; margin:5px;}
        ''')
        self.setup_menus()
        self.web.urlChanged.connect(self.update_navigation)
        self.web.loadFinished.connect(lambda _ok: self.update_navigation())
        self.web.loadProgress.connect(lambda _value: self.update_navigation())
        edge_cursors = (
            (Qt.TopEdge, Qt.SizeVerCursor), (Qt.BottomEdge, Qt.SizeVerCursor),
            (Qt.LeftEdge, Qt.SizeHorCursor), (Qt.RightEdge, Qt.SizeHorCursor),
            (Qt.TopEdge | Qt.LeftEdge, Qt.SizeFDiagCursor), (Qt.TopEdge | Qt.RightEdge, Qt.SizeBDiagCursor),
            (Qt.BottomEdge | Qt.LeftEdge, Qt.SizeBDiagCursor), (Qt.BottomEdge | Qt.RightEdge, Qt.SizeFDiagCursor),
        )
        self.edges = [ResizeEdge(self, edge, cursor) for edge, cursor in edge_cursors]
        self.layout_controls()
        self.update_navigation()

    def button(self, icon, label, action, parent=None):
        button = QToolButton(parent or self.header)
        button.setIcon(toolbar_icon(icon))
        button.setToolTip(label)
        button.setAccessibleName(label)
        button.setFixedSize(32, 32)
        button.clicked.connect(action)
        return button

    def menu_action(self, menu, label, action, shortcut=None):
        item = self.menus[menu].addAction(label)
        item.triggered.connect(action)
        self.addAction(item)
        if shortcut:
            item.setShortcut(QKeySequence(shortcut))
        return item

    def setup_menus(self):
        self.menu_action('Arquivo', 'Novo chat', lambda: self.native_action('new-chat'), 'Ctrl+N')
        self.menu_action('Arquivo', 'Anexar arquivo…', lambda: self.native_action('attach'), 'Ctrl+O')
        self.menu_action('Arquivo', 'Exportar conversa (.json)', lambda: self.native_action('export'), 'Ctrl+Shift+S')
        self.menus['Arquivo'].addSeparator()
        self.menu_action('Arquivo', 'Fechar janela', self.close)
        self.update_edit_actions()
        self.menu_action('Exibir', 'Alternar barra lateral', lambda: self.native_action('sidebar'))
        self.menu_action('Exibir', 'Controles da conversa', lambda: self.native_action('controls'))
        self.menu_action('Exibir', 'Configurações', lambda: self.native_action('settings'))
        self.menus['Exibir'].addSeparator()
        self.menu_action('Exibir', 'Aumentar interface', lambda: self.set_zoom(self.web.zoomFactor()+.1), 'Ctrl++')
        self.menu_action('Exibir', 'Diminuir interface', lambda: self.set_zoom(self.web.zoomFactor()-.1), 'Ctrl+-')
        self.menu_action('Exibir', 'Tamanho original', lambda: self.set_zoom(1), 'Ctrl+0')
        self.menu_action('Exibir', 'Tela cheia (F11)', self.toggle_fullscreen)
        self.menu_action('Ajuda', 'Atalhos do teclado', lambda: self.native_action('shortcuts'), 'F1')
        self.menu_action('Ajuda', 'Sobre a Auren', lambda: self.native_action('about'))

    def update_edit_actions(self):
        menu = self.menus['Editar']
        menu.clear()
        for kind, label in ((QWebEnginePage.Undo, 'Desfazer'), (QWebEnginePage.Redo, 'Refazer'),
                            (QWebEnginePage.Cut, 'Recortar'), (QWebEnginePage.Copy, 'Copiar'),
                            (QWebEnginePage.Paste, 'Colar'), (QWebEnginePage.SelectAll, 'Selecionar tudo')):
            action = self.page().action(kind)
            action.setText(label)
            menu.addAction(action)

    def native_action(self, action):
        import json
        self.page().runJavaScript("window.dispatchEvent(new CustomEvent('auren-native-action',{detail:"+json.dumps(action)+'}));')

    def set_zoom(self, value):
        value = round(max(.75, min(1.75, value)), 2)
        self.web.setZoomFactor(value)
        self.preferences.setValue('interface/zoom', value)

    def update_navigation(self, *_args):
        self.back.setEnabled(self.web.history().canGoBack())
        self.forward.setEnabled(self.web.history().canGoForward())

    def page(self):
        return self.web.page()

    def setPage(self, page):
        self.web.setPage(page)
        script = QWebEngineScript()
        script.setName('auren-native-layout')
        script.setInjectionPoint(QWebEngineScript.DocumentReady)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setSourceCode("document.body.classList.add('auren-desktop');")
        page.scripts().insert(script)
        page.loadFinished.connect(lambda ok: self.sync_fullscreen_css() if ok else None)
        self.update_edit_actions()

    def setUrl(self, url):
        self.web.setUrl(url)

    def setHtml(self, html):
        self.web.setHtml(html)

    def layout_controls(self):
        self.header.setVisible(not self.isFullScreen())
        compact = self.width() < 650
        for button in self.menu_buttons:
            button.setVisible(not compact)
        self.menu_toggle.setVisible(compact)
        maximized = self.isMaximized()
        self.maximize.setIcon(toolbar_icon('restore' if maximized else 'maximize'))
        self.maximize.setToolTip('Restaurar' if maximized else 'Maximizar')
        self.maximize.setAccessibleName('Restaurar' if maximized else 'Maximizar')
        w, h = self.width(), self.height()
        rects = [(6,0,w-12,5),(6,h-5,w-12,5),(0,6,5,h-12),(w-5,6,5,h-12),
                 (0,0,6,6),(w-6,0,6,6),(0,h-6,6,6),(w-6,h-6,6,6)]
        for edge, rect in zip(self.edges, rects):
            edge.setGeometry(*rect)
            edge.setVisible(not self.isMaximized() and not self.isFullScreen())
            edge.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'edges'):
            self.layout_controls()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange and hasattr(self, 'edges'):
            self.layout_controls()
            self.sync_fullscreen_css()

    def sync_fullscreen_css(self):
        value = 'true' if self.isFullScreen() else 'false'
        self.page().runJavaScript("document.body?.classList.toggle('auren-fullscreen',"+value+');')

    def maximize_window(self):
        self.restore_timer.stop()
        self.normal_geometry_timer.stop()
        self.showMaximized()

    def restore_window(self):
        self.restore_timer.stop()
        self.showNormal()
        # Qt cannot position a Wayland top-level window. Apply its geometry
        # through KWin after the compositor has completed the state change.
        self.normal_geometry_timer.start(150)
        self.raise_()
        self.activateWindow()

    def apply_restore_geometry(self):
        if self.isMaximized() or self.isFullScreen() or self.isMinimized() or not self.isVisible():
            return
        area = self.screen().availableGeometry()
        width, height = min(910, area.width()), min(600, area.height())
        self.setGeometry(area.x() + (area.width() - width) // 2,
                         area.y() + (area.height() - height) // 2, width, height)
        kdotool = shutil.which('kdotool')
        if QApplication.platformName() != 'wayland' or not kdotool:
            return
        # Target this process's main window only. KWin's work area accounts
        # for panels and the monitor containing the window; Qt's may not.
        script = f'''
            const w = workspace.windowList().find(w =>
                w.pid === {os.getpid()} && w.normalWindow && w.caption === 'Auren');
            if (w && !w.fullScreen && !w.minimized && w.maximizeMode === 0) {{
                const area = workspace.clientArea(KWin.MaximizeArea, w);
                const width = Math.min(910, area.width);
                const height = Math.min(600, area.height);
                w.frameGeometry = {{
                    x: area.x + Math.floor((area.width - width) / 2),
                    y: area.y + Math.floor((area.height - height) / 2),
                    width: width, height: height
                }};
            }}
        '''
        if self.kwin_geometry_process.state() == QProcess.NotRunning:
            self.kwin_geometry_process.start(kdotool, ['kwinscript', '--inline', script])

    def toggle_maximized(self):
        if self.isMaximized():
            self.restore_window()
        else:
            self.maximize_window()

    def toggle_fullscreen(self):
        self.restore_timer.stop()
        self.normal_geometry_timer.stop()
        if self.isFullScreen():
            self.showNormal()
            if self.previous_state & Qt.WindowMaximized:
                self.restore_timer.start(150)
            elif not self.previous_geometry.isNull():
                self.setGeometry(self.previous_geometry)
        else:
            self.previous_state = self.windowState()
            self.previous_geometry = QRect(self.geometry())
            self.showFullScreen()
        self.layout_controls()
        self.sync_fullscreen_css()
