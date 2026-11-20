#!/usr/bin/env python3
"""Coleta um inventário técnico enxuto e seguro do sistema do Mestre para a Minerva (Chat e Dev)."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

PROFILE_PATH = Path.home() / ".local" / "share" / "auren" / "minerva_system_profile.md"


def _run(cmd: list[str], timeout: float = 3.0) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "").strip()
        if not out and r.returncode == 0:
            out = (r.stderr or "").strip()
        return out
    except Exception:
        return ""


def _read_os_release() -> str:
    p = Path("/etc/os-release")
    if not p.is_file():
        return platform.system()
    pretty = ""
    version = ""
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("PRETTY_NAME="):
            pretty = line.split("=", 1)[1].strip().strip("'\"")
        elif line.startswith("VERSION="):
            version = line.split("=", 1)[1].strip().strip("'\"")
    return f"{pretty} {version}".strip() or platform.system()


def _read_cpu() -> str:
    p = Path("/proc/cpuinfo")
    model = ""
    if p.is_file():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.lower().startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
    threads = os.cpu_count() or 0
    return f"{model} ({threads} threads)" if model else f"{threads} threads"


def _read_ram_disk() -> tuple[str, str]:
    ram = ""
    for ln in _run(["free", "-h"]).splitlines():
        if ln.lower().startswith("mem"):
            parts = ln.split()
            if len(parts) >= 2:
                ram = parts[1]
            break
    swap = ""
    for ln in _run(["free", "-h"]).splitlines():
        if ln.lower().startswith("swap"):
            parts = ln.split()
            if len(parts) >= 2:
                swap = parts[1]
            break
    ram_str = f"{ram} RAM" + (f" + {swap} Swap" if swap else "")

    disk_str = ""
    for ln in _run(["df", "-h", "/"]).splitlines()[1:2]:
        parts = ln.split()
        if len(parts) >= 5:
            disk_str = f"{parts[0]} ({parts[1]} total, {parts[3]} livres)"
    return ram_str, disk_str


def _read_gpu() -> str:
    out = _run(["bash", "-c", "lspci | grep -iE 'vga|3d|display'"])
    lines = [ln.split(": ", 1)[-1].strip() for ln in out.splitlines() if ln.strip()]
    return "; ".join(lines) or "não detectada"


def _read_portage_summary() -> str:
    emerge = _run(["emerge", "--version"])
    first = emerge.splitlines()[0] if emerge else ""
    make_conf = Path("/etc/portage/make.conf")
    flags: list[str] = []
    if make_conf.is_file():
        for ln in make_conf.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = ln.strip()
            if s.startswith(("COMMON_FLAGS=", "MAKEOPTS=", "VIDEO_CARDS=", "USE=")):
                flags.append(s)
    parts = [p for p in [first, " | ".join(flags)] if p]
    return " — ".join(parts)


def _read_runtimes() -> list[str]:
    checks = [
        ("Python", ["python3", "--version"]),
        ("uv", ["uv", "--version"]),
        ("Node", ["node", "--version"]),
        ("npm", ["npm", "--version"]),
        ("Rust", ["rustc", "--version"]),
        ("Go", ["go", "version"]),
        ("Java", ["java", "-version"]),
        ("Git", ["git", "--version"]),
        ("Ollama", ["ollama", "--version"]),
        ("Claude Code CLI", ["/opt/bin/claude", "--version"]),
    ]
    found: list[str] = []
    for label, cmd in checks:
        exe = cmd[0]
        if not (os.path.exists(exe) or shutil.which(exe)):
            continue
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            raw = (r.stdout or r.stderr or "").strip()
            ver = raw.splitlines()[0] if raw else "instalado"
            found.append(f"{label}: {ver}")
        except Exception:
            continue
    return found


def _read_ollama_models() -> list[str]:
    out = _run(["ollama", "list"])
    models: list[str] = []
    for ln in out.splitlines()[1:]:
        parts = ln.split()
        if parts:
            models.append(parts[0])
    return models


def _read_user_services() -> list[str]:
    out = _run(["systemctl", "--user", "list-unit-files", "--state=enabled", "--no-legend"])
    return sorted({ln.split()[0] for ln in out.splitlines() if ln.strip()})


def _read_desktop_apps() -> list[str]:
    ignore_prefixes = (
        "Avahi ",
        "Qt ",
        "About ",
        "Sobre ",
        "Browse C:",
        "Uninstall Wine",
        "Preferências",
        "Configuração do Wine",
        "Configure Wine",
    )
    apps: set[str] = set()
    for d in (Path("/usr/share/applications"), Path.home() / ".local" / "share" / "applications"):
        if not d.is_dir():
            continue
        for f in d.glob("*.desktop"):
            try:
                txt = f.read_text(encoding="utf-8", errors="ignore")
                if "NoDisplay=true" in txt or "Hidden=true" in txt:
                    continue
                name = ""
                for ln in txt.splitlines():
                    if ln.startswith("Name="):
                        name = ln.split("=", 1)[1].strip()
                        break
                if name and not name.startswith(ignore_prefixes):
                    apps.add(name)
            except Exception:
                continue
    return sorted(apps)


def _list_subdirs(path: Path) -> list[str]:
    if not path.is_dir():
        return []
    return sorted(p.name for p in path.iterdir() if p.is_dir() and not p.name.startswith("."))


def generate_system_profile() -> str:
    home = Path.home()
    os_name = _read_os_release()
    kernel = f"{platform.release()} ({platform.machine()})"
    hostname = platform.node()
    desktop = f"{os.environ.get('XDG_CURRENT_DESKTOP', 'KDE')} / {os.environ.get('XDG_SESSION_TYPE', 'wayland')}"
    plasma = _run(["plasmashell", "--version"])
    cpu = _read_cpu()
    ram_str, disk_str = _read_ram_disk()
    gpu = _read_gpu()
    portage = _read_portage_summary()
    runtimes = _read_runtimes()
    ollama_models = _read_ollama_models()
    services = _read_user_services()
    opt_apps = _list_subdirs(Path("/opt"))
    desktop_apps = _read_desktop_apps()
    home_dirs = _list_subdirs(home)
    projetos = _list_subdirs(home / "Projetos")
    documentos = _list_subdirs(home / "Documentos")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# Perfil Técnico do Sistema do Mestre (atualizado em {stamp})",
        "",
        "## Identidade da Máquina & Sistema Operacional",
        f"- **Mestre / Usuário Linux**: `cambrith` (Cambrith) · **Hostname**: `{hostname}` · **Home**: `{home}`",
        f"- **SO**: {os_name} · **Kernel**: `{kernel}` · **Shell**: `{os.environ.get('SHELL', '/bin/bash')}`",
        f"- **Ambiente Gráfico**: {desktop}" + (f" ({plasma})" if plasma else ""),
        f"- **Hardware**: CPU {cpu} | GPU {gpu} | {ram_str} | Disco {disk_str}",
    ]
    if portage:
        lines.append(f"- **Portage / Gentoo**: {portage}")

    lines.extend(
        [
            "",
            "## Ecossistema Minerva & Serviços do Usuário Ativos (`systemctl --user`)",
            "- **Minerva App Desktop**: lançador `~/.local/share/applications/auren.desktop` (`Documentos/Auren IA - Desenvolvimento/scripts/auren_app.py`, PySide6/QtWebEngine) apontando para `http://127.0.0.1:8080` (`auren-backend.service`).",
            "- **Free Claude Code (FCC)**: `http://127.0.0.1:8082` (`fcc-server.service`), proxy multi-provedor para Minerva Dev (UI + CLI `minerva`).",
            "- **Workspace de desenvolvimento**: `~/Projetos/Auren IA - Desenvolvimento` e instalação do lançador em `~/Documentos/Auren IA - Desenvolvimento`.",
            f"- **Serviços habilitados**: {', '.join(services) if services else 'nenhum listado'}",
        ]
    )
    if ollama_models:
        lines.append(f"- **Modelos Ollama locais**: {', '.join(ollama_models)}")

    lines.extend(
        [
            "",
            "## Stack de Desenvolvimento & Ferramentas",
            f"- **Runtimes & CLIs**: {' | '.join(runtimes)}",
            f"- **Softwares em `/opt`**: {', '.join(opt_apps)}",
            "",
            "## Estrutura de Pastas & Projetos",
            f"- **Pastas em `~/`**: {', '.join(home_dirs)}",
            f"- **Projetos (`~/Projetos`)**: {', '.join(projetos)}",
            f"- **Documentos (`~/Documentos`)**: {', '.join(documentos)}",
            "",
            "## Aplicativos Instalados (Desktop)",
            ", ".join(desktop_apps),
            "",
            "## Ferramentas Personalizadas do Mestre",
            "- `Modo Administrador` (`sudo-temp`), `Modo Cambrith`, `Modo Windows`, `Cambrith Boot Settings` (`/opt/cambrith-boot-settings`), `Cambrith Plymouth`, `cambrith-grub`, `kde-snap-assist`, `rclone-gdrive` (`~/GoogleDrive`), `Waydroid`, `Antigravity`.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def sync_profile(path: Path = PROFILE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = generate_system_profile()
    path.write_text(content, encoding="utf-8")
    return path


if __name__ == "__main__":
    out = sync_profile()
    print(f"Perfil do sistema salvo em: {out} ({out.stat().st_size} bytes)")
