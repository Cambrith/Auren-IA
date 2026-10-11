"""Replace the personal Cavren shortcut with Lunvri, keeping a recovery copy."""

from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    applications = Path.home() / '.local/share/applications'
    units = Path.home() / '.config/systemd/user'
    applications.mkdir(parents=True, exist_ok=True)
    units.mkdir(parents=True, exist_ok=True)
    desktop = applications / 'cavren.desktop'
    backup = ROOT / '.cavren/desktop-backup/cavren.desktop'
    backup.parent.mkdir(parents=True, exist_ok=True)
    if desktop.exists() and not backup.exists():
        shutil.copy2(desktop, backup)
    icons = Path.home() / '.local/share/icons/hicolor'
    source_icons = ROOT.parent / 'cavren-nextchat/src/cavren/assets/hicolor'
    for source in source_icons.glob('*/apps/cavren.png'):
        target = icons / source.relative_to(source_icons).parent / 'lunvri.png'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    desktop.write_text(f'''[Desktop Entry]
Type=Application
Version=1.0
Name=Lunvri
GenericName=Assistente de inteligência artificial
Comment=Espaço de trabalho Lunvri
Exec="{ROOT}/scripts/run_lunvri.sh"
Icon=lunvri
Terminal=false
Categories=Utility;
StartupNotify=true
StartupWMClass=cavren
''')
    (units / 'lunvri.service').write_text(f'''[Unit]
Description=Lunvri - interface local e ponte de IA
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
    for command in ('update-desktop-database', 'kbuildsycoca6'):
        if shutil.which(command):
            subprocess.run(
                [command, str(applications)] if command == 'update-desktop-database' else [command], check=True
            )
    print('Atalho Lunvri instalado. O original está em .cavren/desktop-backup/.')


if __name__ == '__main__':
    main()
