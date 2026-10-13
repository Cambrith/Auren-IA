"""Install existing Auren artwork and preserve its desktop application identity."""
import os
import base64
import struct
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICON_NAME = 'auren'
DESKTOP_ID = 'cavren'
SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)


def replace_file(path, content, mode=0o644):
    if path.is_file() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
            os.fchmod(output.fileno(), mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return True


def ensure_icons(home=None, root=ROOT):
    home = Path(home) if home else Path.home()
    target_root = home / '.local/share/icons/hicolor'
    source_root = root.parent / 'cavren-nextchat/src/cavren/assets/hicolor'
    assets = {}
    for size in SIZES:
        source = source_root / f'{size}x{size}/apps/cavren.png'
        content = source.read_bytes()
        if content[:8] != b'\x89PNG\r\n\x1a\n' or int.from_bytes(content[16:20], 'big') != size or int.from_bytes(content[20:24], 'big') != size:
            raise OSError('O ícone original da Auren é inválido.')
        assets[size] = content
    changed = False
    # hicolor is the standard fallback, even when the user changes icon themes.
    index = target_root / 'index.theme'
    if not index.exists():
        default_index = Path('/usr/share/icons/hicolor/index.theme')
        if default_index.exists(): changed |= replace_file(index, default_index.read_bytes())
    for size, content in assets.items():
        # Retain aliases for older shortcuts without changing their launch command.
        for name in (ICON_NAME, 'lunvri', 'cavren'):
            changed |= replace_file(target_root / f'{size}x{size}/apps/{name}.png', content)
    return target_root / f'512x512/apps/{ICON_NAME}.png', changed


def update_launcher(path, icon, template=None):
    content = path.read_text() if path.exists() else template
    if content is None: raise OSError('O atalho original da Auren não foi encontrado.')
    lines = content.splitlines()
    in_entry = False
    found = False
    for index, line in enumerate(lines):
        if line.startswith('['): in_entry = line == '[Desktop Entry]'
        if in_entry and line.startswith('Icon='):
            lines[index] = 'Icon=' + str(icon)
            found = True
    if not found:
        lines.insert(lines.index('[Desktop Entry]') + 1, 'Icon=' + str(icon))
    return replace_file(path, ('\n'.join(lines) + '\n').encode(), 0o755 if path.parent.name != 'applications' else 0o644)


def refresh_desktop_cache():
    commands = [('gtk-update-icon-cache', '-f', '-t', str(Path.home() / '.local/share/icons/hicolor')),
                ('update-desktop-database', str(Path.home() / '.local/share/applications')),
                ('kbuildsycoca6', '--noincremental')]
    for command in commands:
        if shutil.which(command[0]): subprocess.run(command, check=True, capture_output=True, timeout=30)


def repair_web_icons(root=ROOT):
    """Reuse existing PNG pixels in browser containers, without redrawing the logo."""
    source = root / 'static/lunvri-icon.png'
    artwork = source.read_bytes()
    assets = root.parent / 'cavren-nextchat/src/cavren/assets/hicolor'
    sizes = (16, 32, 48, 64, 128, 256)
    payloads = [(size, (assets / f'{size}x{size}/apps/cavren.png').read_bytes()) for size in sizes]
    offset = 6 + 16 * len(payloads)
    entries = []
    for size, content in payloads:
        entries.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(content), offset))
        offset += len(content)
    ico = struct.pack('<HHH', 0, 1, len(payloads)) + b''.join(entries) + b''.join(content for _, content in payloads)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">'
           '<image width="512" height="512" href="data:image/png;base64,' + base64.b64encode(artwork).decode() + '"/></svg>\n').encode()
    changed = False
    for directory in (root / 'static/static', root / 'backend/open_webui/static', root / 'build/static', root / '.cavren/static'):
        if directory.exists():
            changed |= replace_file(directory / 'favicon.ico', ico)
            changed |= replace_file(directory / 'favicon.svg', svg)
            changed |= replace_file(directory / 'swagger-ui/favicon.png', payloads[1][1])
    for directory in (root / 'static', root / 'build'):
        if directory.exists():
            changed |= replace_file(directory / 'favicon.ico', ico)
            changed |= replace_file(directory / 'favicon.svg', svg)
    return changed
