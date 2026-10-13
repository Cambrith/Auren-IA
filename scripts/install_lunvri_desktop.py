"""Replace the personal Cavren shortcut with Auren, keeping a recovery copy."""

from pathlib import Path
import argparse
import shutil
import subprocess
from auren_identity import ensure_icons, update_launcher, refresh_desktop_cache, repair_web_icons

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--icons-only', action='store_true', help='Corrigir ícones e atalhos sem alterar o serviço.')
    args = parser.parse_args()
    applications = Path.home() / '.local/share/applications'
    units = Path.home() / '.config/systemd/user'
    applications.mkdir(parents=True, exist_ok=True)
    units.mkdir(parents=True, exist_ok=True)
    desktop = applications / 'cavren.desktop'
    backup = ROOT / '.cavren/desktop-backup/cavren.desktop'
    backup.parent.mkdir(parents=True, exist_ok=True)
    if desktop.exists() and not backup.exists():
        shutil.copy2(desktop, backup)
    icon, _changed = ensure_icons()
    repair_web_icons()
    template = f'''[Desktop Entry]
Type=Application
Version=1.0
Name=Auren
GenericName=Assistente de inteligência artificial
Comment=Espaço de trabalho Auren
Exec="{ROOT}/scripts/run_lunvri.sh"
Icon=lunvri
Terminal=false
Categories=Utility;
StartupNotify=true
StartupWMClass=cavren
'''
    update_launcher(desktop, icon, template)
    desktop_dir = Path(subprocess.check_output(['xdg-user-dir', 'DESKTOP'], text=True).strip())
    if desktop_dir != Path.home() and desktop_dir.is_dir():
        # Repair existing copies and offer the named desktop shortcut when absent.
        copies = [p for p in desktop_dir.glob('*.desktop') if p.name.casefold() in ('auren.desktop', 'cavren.desktop', 'lunvri.desktop')]
        for copy in copies or [desktop_dir / 'Auren.desktop']:
            update_launcher(copy, icon, desktop.read_text())
    if args.icons_only:
        refresh_desktop_cache()
        print('Ícones e atalhos da Auren corrigidos; serviço preservado.')
        return
    (units / 'lunvri.service').write_text(f'''[Unit]
Description=Auren - interface local e ponte de IA
After=cavren-search.service
Wants=cavren-search.service

[Service]
Type=simple
WorkingDirectory={ROOT}
ExecStart="{ROOT}/../cavren-nextchat/.venv/bin/python" "{ROOT}/scripts/lunvri_preview.py"
Restart=on-failure
RestartSec=3
KillMode=control-group
TimeoutStopSec=30
''')
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    refresh_desktop_cache()
    print('Atalho Auren instalado. O original está em .cavren/desktop-backup/.')


if __name__ == '__main__':
    main()
