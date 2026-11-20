"""Router da Minerva Dev UI: integra Claude Code CLI + Free Claude Code na interface web."""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from open_webui.utils.auth import get_verified_user

# Garante acesso ao pacote compartilhado minerva_dev na raiz do repositório
_REPO_ROOT = str(Path(__file__).resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from minerva_dev.claude_harness import (  # noqa: E402
    build_claude_command,
    filter_claude_stderr,
    list_recent_sessions,
    parse_stream_event,
    quick_side_question,
)
from minerva_dev.fcc_bridge import (  # noqa: E402
    DEFAULT_FCC_TOKEN,
    DEFAULT_FCC_URL,
    MINERVA_DEV_MODES,
    apply_fcc_config,
    apply_minerva_mode,
    build_claude_env,
    detect_minerva_mode,
    ensure_fcc_running,
    fetch_fcc_models,
    fetch_fcc_status,
    format_model_name,
    format_provider_name,
    is_dev_chat_model,
    is_free_model,
)
from minerva_dev.theme import format_tool_summary, translate_tool_name  # noqa: E402

router = APIRouter()

_ACTIVE_RUNS: dict[str, asyncio.subprocess.Process] = {}


class DevModePayload(BaseModel):
    mode: str | None = None
    model: str | None = None


class DevChatPayload(BaseModel):
    prompt: str = Field(min_length=1, max_length=200_000)
    cwd: str | None = None
    session_id: str | None = None
    permission_mode: str = "bypassPermissions"
    model: str | None = None
    effort: str | None = None
    extra_dirs: list[str] = Field(default_factory=list)
    run_id: str | None = None


class DevSideQuestionPayload(BaseModel):
    question: str = Field(min_length=1, max_length=20_000)
    model: str | None = None


class DevStopPayload(BaseModel):
    run_id: str


class DevHistorySavePayload(BaseModel):
    id: str | None = None
    title: str = Field(min_length=1, max_length=200)
    cwd: str = ""
    session_id: str | None = None
    model: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)


def _dev_history_dir(user_id: str) -> Path:
    safe_uid = re.sub(r"[^a-zA-Z0-9_-]", "_", str(user_id or "default"))
    d = Path.home() / ".local" / "share" / "auren" / "dev_sessions" / safe_uid
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_conv_path(user_id: str, conv_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", conv_id)
    if not safe_id:
        raise HTTPException(status_code=400, detail="ID de conversa inválido.")
    return _dev_history_dir(user_id) / f"{safe_id}.json"


def _default_cwd() -> str:
    home = Path.home()
    proj = home / "Projetos"
    if proj.is_dir():
        return str(proj)
    return str(home)


@router.get("/status")
async def dev_status(
    ensure_default: bool = Query(default=False),
    user=Depends(get_verified_user),
) -> dict[str, Any]:
    """Retorna o estado do Free Claude Code, modos Minerva Dev e modelos disponíveis."""
    ensure_fcc_running(DEFAULT_FCC_URL)
    st = fetch_fcc_status(DEFAULT_FCC_URL)
    active_model = st.active_model
    active_mode = detect_minerva_mode(active_model)
    if ensure_default and st.online and active_mode != "harmonia":
        ok, primary, _msg = apply_minerva_mode("harmonia", base_url=DEFAULT_FCC_URL)
        if ok and primary:
            active_model = primary
            active_mode = "harmonia"
    raw_models = fetch_fcc_models(DEFAULT_FCC_URL)

    formatted_models: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw_models:
        mid = str(item.get("id") or "")
        if not mid or mid in seen:
            continue
        prov_id = str(item.get("provider") or (mid.split("/")[0] if "/" in mid else ""))
        if not is_free_model(mid, prov_id) or not is_dev_chat_model(mid):
            continue
        seen.add(mid)
        formatted_models.append(
            {
                "id": mid,
                "name": format_model_name(mid),
                "provider_id": prov_id,
                "provider_name": format_provider_name(prov_id),
            }
        )

    modes = [
        {
            "id": mid,
            "label": cfg["label"],
            "description": cfg["description"],
            "model": cfg["model"],
            "model_name": format_model_name(cfg["model"]),
            "fallbacks": cfg["fallbacks"],
        }
        for mid, cfg in MINERVA_DEV_MODES.items()
    ]

    return {
        "fcc_online": st.online,
        "fcc_url": st.url,
        "claude_installed": st.claude_installed,
        "active_model": active_model,
        "active_model_name": format_model_name(active_model),
        "active_mode": active_mode,
        "providers": [
            {"id": p, "name": format_provider_name(p)}
            for p in st.configured_providers
        ],
        "modes": modes,
        "models": formatted_models,
        "default_cwd": _default_cwd(),
    }


@router.post("/mode")
async def dev_set_mode(
    payload: DevModePayload, user=Depends(get_verified_user)
) -> dict[str, Any]:
    """Alterna o modo (harmonia/sabia/impeto) ou define um modelo manual no FCC."""
    if payload.mode:
        ok, primary, msg = apply_minerva_mode(payload.mode, base_url=DEFAULT_FCC_URL)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {
            "ok": True,
            "mode": payload.mode,
            "model": primary,
            "model_name": format_model_name(primary),
            "message": msg,
        }

    if payload.model:
        ok, msg = apply_fcc_config({"MODEL": payload.model}, base_url=DEFAULT_FCC_URL)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {
            "ok": True,
            "mode": detect_minerva_mode(payload.model),
            "model": payload.model,
            "model_name": format_model_name(payload.model),
            "message": f"Modelo alterado para {format_model_name(payload.model)}.",
        }

    raise HTTPException(status_code=400, detail="Informe 'mode' ou 'model'.")


@router.get("/dirs")
async def dev_list_dirs(
    path: str | None = Query(default=None), user=Depends(get_verified_user)
) -> dict[str, Any]:
    """Lista subpastas para o seletor de diretório do projeto."""
    target = Path(path).expanduser() if path else Path(_default_cwd())
    if not target.exists() or not target.is_dir():
        target = Path.home()

    dirs: list[dict[str, str]] = []
    try:
        for entry in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_dir() and not entry.name.startswith("."):
                dirs.append({"name": entry.name, "path": str(entry)})
    except PermissionError:
        pass

    parent = str(target.parent) if target.parent != target else ""
    return {
        "current": str(target),
        "parent": parent,
        "directories": dirs[:80],
    }


@router.get("/sessions")
async def dev_sessions(
    cwd: str | None = Query(default=None), user=Depends(get_verified_user)
) -> dict[str, Any]:
    """Lista sessões recentes do Claude Code para a pasta informada (ou $HOME no modo sem pasta)."""
    folder = cwd.strip() if cwd and cwd.strip() else str(Path.home())
    return {"cwd": folder, "sessions": list_recent_sessions(folder, limit=12)}


@router.get("/history")
async def dev_list_history(user=Depends(get_verified_user)) -> dict[str, Any]:
    """Lista exclusivamente as conversas criadas na Minerva Dev."""
    hdir = _dev_history_dir(getattr(user, "id", "default"))
    items: list[dict[str, Any]] = []
    for p in hdir.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            items.append(
                {
                    "id": data.get("id") or p.stem,
                    "title": data.get("title") or "Sessão Minerva Dev",
                    "cwd": data.get("cwd") or "",
                    "session_id": data.get("session_id"),
                    "model": data.get("model"),
                    "updated_at": float(data.get("updated_at") or p.stat().st_mtime),
                }
            )
        except Exception:
            continue
    items.sort(key=lambda x: x["updated_at"], reverse=True)
    return {"items": items[:100]}


@router.get("/history/{conv_id}")
async def dev_get_history(conv_id: str, user=Depends(get_verified_user)) -> dict[str, Any]:
    """Carrega uma conversa exclusiva da Minerva Dev."""
    path = _safe_conv_path(getattr(user, "id", "default"), conv_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Conversa Dev não encontrada.")
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/history")
async def dev_save_history(
    payload: DevHistorySavePayload, user=Depends(get_verified_user)
) -> dict[str, Any]:
    """Salva ou atualiza uma conversa exclusiva da Minerva Dev."""
    uid = getattr(user, "id", "default")
    conv_id = re.sub(r"[^a-zA-Z0-9_-]", "", payload.id or "") or uuid.uuid4().hex[:12]
    path = _safe_conv_path(uid, conv_id)
    record = {
        "id": conv_id,
        "title": payload.title.strip()[:200],
        "cwd": payload.cwd,
        "session_id": payload.session_id,
        "model": payload.model,
        "updated_at": time.time(),
        "messages": payload.messages,
    }
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return {
        "id": conv_id,
        "title": record["title"],
        "cwd": record["cwd"],
        "session_id": record["session_id"],
        "model": record["model"],
        "updated_at": record["updated_at"],
    }


@router.delete("/history/{conv_id}")
async def dev_delete_history(conv_id: str, user=Depends(get_verified_user)) -> dict[str, Any]:
    """Remove uma conversa exclusiva da Minerva Dev."""
    path = _safe_conv_path(getattr(user, "id", "default"), conv_id)
    if path.is_file():
        path.unlink()
    return {"ok": True}


_IGNORE_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".svelte-kit",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "target",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "coverage",
        ".cache",
    }
)


def _sanitize_tool_input(tool_name: str, tool_input: dict[str, Any] | None) -> dict[str, Any]:
    """Extrai os campos úteis de entrada da ferramenta para renderização rica na UI."""
    if not isinstance(tool_input, dict):
        return {}
    out: dict[str, Any] = {}
    if tool_name == "TodoWrite":
        todos = tool_input.get("todos")
        if isinstance(todos, list):
            clean_todos = []
            for item in todos[:40]:
                if isinstance(item, dict):
                    clean_todos.append(
                        {
                            "content": str(item.get("content") or item.get("activeForm") or "")[:200],
                            "status": str(item.get("status") or "pending"),
                            "priority": str(item.get("priority") or ""),
                        }
                    )
            out["todos"] = clean_todos
        return out

    if tool_name in {"Edit", "MultiEdit"}:
        if tool_input.get("file_path"):
            out["file_path"] = str(tool_input["file_path"])
        if isinstance(tool_input.get("old_string"), str):
            out["old_string"] = tool_input["old_string"][:2400]
        if isinstance(tool_input.get("new_string"), str):
            out["new_string"] = tool_input["new_string"][:2400]
        if isinstance(tool_input.get("edits"), list):
            out["edits_count"] = len(tool_input["edits"])
            first = tool_input["edits"][0] if tool_input["edits"] else None
            if isinstance(first, dict):
                out["old_string"] = str(first.get("old_string") or "")[:1600]
                out["new_string"] = str(first.get("new_string") or "")[:1600]
        return out

    if tool_name == "Write":
        if tool_input.get("file_path"):
            out["file_path"] = str(tool_input["file_path"])
        content = tool_input.get("content")
        if isinstance(content, str):
            out["lines"] = content.count("\n") + 1
            out["preview"] = content[:1600]
        return out

    if tool_name == "Bash":
        if tool_input.get("command"):
            out["command"] = str(tool_input["command"])[:1600]
        if tool_input.get("description"):
            out["description"] = str(tool_input["description"])[:240]
        return out

    if tool_name == "Read":
        for k in ("file_path", "offset", "limit"):
            if k in tool_input and tool_input[k] is not None:
                out[k] = tool_input[k]
        return out

    if tool_name in {"Glob", "Grep"}:
        for k in ("pattern", "path", "glob"):
            if tool_input.get(k):
                out[k] = str(tool_input[k])[:300]
        return out

    for k, v in list(tool_input.items())[:6]:
        if isinstance(v, (str, int, float, bool)):
            out[k] = v if not isinstance(v, str) else v[:400]
    return out


@router.get("/git")
async def dev_git_status(
    cwd: str | None = Query(default=None), user=Depends(get_verified_user)
) -> dict[str, Any]:
    """Retorna branch atual e arquivos modificados (git status + numstat) para o painel lateral."""
    if not cwd or not cwd.strip():
        return {"is_git": False, "branch": "", "files": []}
    folder = cwd.strip()
    if not os.path.isdir(folder):
        return {"is_git": False, "branch": "", "files": []}
    try:
        br = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=folder,
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        if br.returncode != 0:
            return {"is_git": False, "branch": "", "files": []}
        branch = br.stdout.strip()

        st = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=folder,
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        stats: dict[str, tuple[int, int]] = {}
        for diff_args in (["git", "diff", "--numstat"], ["git", "diff", "--cached", "--numstat"]):
            ns = subprocess.run(
                diff_args,
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            for line in ns.stdout.splitlines():
                parts = line.split("\t", 2)
                if len(parts) == 3:
                    a = int(parts[0]) if parts[0].isdigit() else 0
                    d = int(parts[1]) if parts[1].isdigit() else 0
                    prev_a, prev_d = stats.get(parts[2], (0, 0))
                    stats[parts[2]] = (prev_a + a, prev_d + d)

        files: list[dict[str, Any]] = []
        for line in st.stdout.splitlines():
            if len(line) < 4:
                continue
            code = line[:2].strip() or "M"
            fpath = line[3:].strip().strip('"')
            if " -> " in fpath:
                fpath = fpath.split(" -> ", 1)[1].strip('"')
            added, removed = stats.get(fpath, (0, 0))
            if code == "??" and added == 0:
                full = Path(folder) / fpath
                if full.is_file() and full.stat().st_size <= 256_000:
                    try:
                        added = full.read_text(encoding="utf-8", errors="ignore").count("\n") + 1
                    except OSError:
                        pass
            files.append(
                {
                    "path": fpath,
                    "status": code,
                    "added": added,
                    "removed": removed,
                }
            )
        return {"is_git": True, "branch": branch, "files": files[:100]}
    except Exception:
        return {"is_git": False, "branch": "", "files": []}


@router.get("/git/diff")
async def dev_git_diff(
    cwd: str | None = Query(default=None),
    file: str = Query(...),
    user=Depends(get_verified_user),
) -> dict[str, Any]:
    """Retorna o diff unificado (unstaged, staged ou arquivo novo) de um arquivo no repositório."""
    folder = cwd or _default_cwd()
    if not os.path.isdir(folder):
        raise HTTPException(status_code=400, detail="Pasta inválida.")
    try:
        res = subprocess.run(
            ["git", "diff", "--", file],
            cwd=folder,
            capture_output=True,
            text=True,
            timeout=4.0,
        )
        diff_txt = res.stdout
        if not diff_txt.strip():
            cached = subprocess.run(
                ["git", "diff", "--cached", "--", file],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=4.0,
            )
            diff_txt = cached.stdout
        if not diff_txt.strip():
            # Arquivo novo (untracked): gera diff sintético com todas as linhas como adição
            root = Path(folder).resolve()
            target = (root / file).resolve()
            if str(target).startswith(str(root)) and target.is_file() and target.stat().st_size <= 128_000:
                raw_bytes = target.read_bytes()
                if b"\x00" not in raw_bytes[:1024]:
                    lines = raw_bytes.decode("utf-8", errors="replace").splitlines()
                    header = f"--- /dev/null\n+++ b/{file}\n@@ -0,0 +1,{len(lines)} @@\n"
                    diff_txt = header + "\n".join(f"+{ln}" for ln in lines[:600])
                    if len(lines) > 600:
                        diff_txt += f"\n... (+{len(lines) - 600} linhas omitidas)"
        if len(diff_txt) > 40000:
            diff_txt = diff_txt[:40000] + "\n... (diff truncado)"
        return {"file": file, "diff": diff_txt or "(sem diff unificado — arquivo binário ou sem mudanças)"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from None


@router.get("/files")
async def dev_list_files(
    cwd: str | None = Query(default=None),
    q: str = Query(default=""),
    limit: int = Query(default=120, ge=1, le=500),
    user=Depends(get_verified_user),
) -> dict[str, Any]:
    """Lista arquivos do projeto ou do PC (modo sem pasta ou caminhos absolutos / e ~) para @arquivo."""
    raw_query = q.strip()
    folderless = not bool(cwd and cwd.strip())

    # Suporte direto a caminhos absolutos (ex.: @/etc/portage ou @~/Documentos/)
    if raw_query.startswith("/") or raw_query.startswith("~"):
        expanded = os.path.expanduser(raw_query)
        target_p = Path(expanded)
        if raw_query.endswith("/") and target_p.is_dir():
            search_dir = target_p
            name_prefix = ""
        else:
            search_dir = target_p.parent
            name_prefix = target_p.name.lower()
        results: list[dict[str, Any]] = []
        if search_dir.is_dir():
            try:
                entries = sorted(
                    search_dir.iterdir(),
                    key=lambda p: (0 if p.is_dir() else 1, p.name.lower()),
                )
                for entry in entries:
                    if name_prefix and name_prefix not in entry.name.lower():
                        continue
                    full_str = str(entry) + ("/" if entry.is_dir() else "")
                    ext = "dir" if entry.is_dir() else entry.suffix.lstrip(".").lower()
                    results.append({"path": full_str, "name": entry.name, "ext": ext})
                    if len(results) >= limit:
                        break
            except PermissionError:
                pass
        return {"cwd": str(search_dir), "files": results, "total": len(results)}

    root = Path.home() if folderless else Path(cwd.strip()).expanduser()
    if not root.is_dir():
        return {"cwd": str(root), "files": [], "total": 0}

    query = raw_query.lower()
    results = []
    scanned = 0
    max_scan = 2500 if folderless else 4000
    max_depth = 2 if folderless else 12

    # Busca em largura (BFS) no modo PC inteiro para priorizar pastas principais do usuário
    from collections import deque

    queue: deque[tuple[Path, int]] = deque([(root, 0)])
    while queue and scanned <= max_scan:
        cur_dir, depth = queue.popleft()
        try:
            entries = sorted(cur_dir.iterdir(), key=lambda p: (0 if p.is_file() else 1, p.name.lower()))
        except (PermissionError, OSError):
            continue

        rel_dir = os.path.relpath(str(cur_dir), str(root))
        for entry in entries:
            name = entry.name
            if entry.is_dir():
                if name in _IGNORE_DIRS or name.startswith("."):
                    continue
                if depth < max_depth:
                    queue.append((entry, depth + 1))
                continue
            if name.startswith(".") and name not in {".env.example", ".gitignore", ".eslintrc.cjs", ".bashrc", ".zshrc"}:
                continue
            rel_path = name if rel_dir == "." else os.path.join(rel_dir, name)
            display_path = str(entry) if folderless else rel_path
            scanned += 1
            if scanned > max_scan:
                break
            if query and query not in display_path.lower():
                continue
            ext = entry.suffix.lstrip(".").lower()
            results.append({"path": display_path, "name": name, "ext": ext})
            if len(results) >= limit and not query:
                break
        if len(results) >= limit and not query:
            break

    if query:
        results.sort(
            key=lambda it: (
                0 if it["name"].lower().startswith(query) else 1 if query in it["name"].lower() else 2,
                len(it["path"]),
            )
        )
        results = results[:limit]

    return {"cwd": str(root), "files": results, "total": len(results)}


@router.get("/file")
async def dev_read_file(
    cwd: str | None = Query(default=None),
    path: str = Query(...),
    user=Depends(get_verified_user),
) -> dict[str, Any]:
    """Lê um arquivo acessível pelo usuário (relativo ao workspace ou caminho absoluto)."""
    folder = cwd.strip() if cwd and cwd.strip() else str(Path.home())
    raw_path = Path(path).expanduser()
    if raw_path.is_absolute():
        target = raw_path.resolve()
    else:
        target = (Path(folder).expanduser().resolve() / raw_path).resolve()
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    size = target.stat().st_size
    if size > 1_048_576:
        raise HTTPException(status_code=413, detail="Arquivo muito grande para pré-visualização (>1 MB).")
    raw = target.read_bytes()
    if b"\x00" in raw[:2048]:
        return {"path": str(path), "binary": True, "size": size, "content": "", "lines": 0}
    text = raw.decode("utf-8", errors="replace")
    truncated = len(text) > 96_000
    if truncated:
        text = text[:96_000]
    return {
        "path": str(path),
        "binary": False,
        "size": size,
        "lines": text.count("\n") + 1,
        "truncated": truncated,
        "content": text,
    }


@router.get("/project-info")
async def dev_project_info(
    cwd: str | None = Query(default=None), user=Depends(get_verified_user)
) -> dict[str, Any]:
    """Detecta stack, arquivos de memória/contexto e commits recentes do projeto ativo (ou perfil do PC)."""
    folderless = not bool(cwd and cwd.strip())
    if folderless:
        memory_files: list[dict[str, Any]] = []
        sys_profile = Path.home() / ".local" / "share" / "auren" / "minerva_system_profile.md"
        if sys_profile.is_file():
            try:
                content = sys_profile.read_text(encoding="utf-8", errors="replace")
                memory_files.append(
                    {
                        "name": "minerva_system_profile.md",
                        "size": sys_profile.stat().st_size,
                        "lines": content.count("\n") + 1,
                        "preview": content[:800],
                    }
                )
            except OSError:
                pass
        return {
            "stack": ["PC inteiro", "Gentoo Linux"],
            "memory_files": memory_files,
            "recent_commits": [],
        }

    folder = cwd.strip()
    root = Path(folder).expanduser()
    if not root.is_dir():
        return {"stack": [], "memory_files": [], "recent_commits": []}

    stack: list[str] = []
    markers = [
        ("package.json", "Node.js"),
        ("svelte.config.js", "SvelteKit"),
        ("next.config.js", "Next.js"),
        ("next.config.mjs", "Next.js"),
        ("next.config.ts", "Next.js"),
        ("tsconfig.json", "TypeScript"),
        ("tailwind.config.js", "Tailwind"),
        ("tailwind.config.ts", "Tailwind"),
        ("pyproject.toml", "Python"),
        ("requirements.txt", "Python"),
        ("Cargo.toml", "Rust"),
        ("go.mod", "Go"),
        ("Dockerfile", "Docker"),
        ("docker-compose.yaml", "Compose"),
        ("docker-compose.yml", "Compose"),
    ]
    seen_stack: set[str] = set()
    for fname, label in markers:
        if (root / fname).exists() and label not in seen_stack:
            seen_stack.add(label)
            stack.append(label)

    memory_files: list[dict[str, Any]] = []
    for mname in ("MINERVA.md", "CLAUDE.md", "AGENTS.md", "AUREN.md", "README.md"):
        mp = root / mname
        if mp.is_file():
            try:
                content = mp.read_text(encoding="utf-8", errors="replace")
                memory_files.append(
                    {
                        "name": mname,
                        "size": mp.stat().st_size,
                        "lines": content.count("\n") + 1,
                        "preview": content[:800],
                    }
                )
            except OSError:
                pass

    recent_commits: list[dict[str, str]] = []
    try:
        log = subprocess.run(
            ["git", "log", "-n", "5", "--pretty=format:%h|%s|%cr"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=2.5,
        )
        if log.returncode == 0:
            for ln in log.stdout.splitlines():
                parts = ln.split("|", 2)
                if len(parts) == 3:
                    recent_commits.append({"hash": parts[0], "subject": parts[1], "when": parts[2]})
    except Exception:
        pass

    return {
        "stack": stack[:8],
        "memory_files": memory_files,
        "recent_commits": recent_commits,
    }


@router.post("/side-question")
async def dev_side_question(
    payload: DevSideQuestionPayload, user=Depends(get_verified_user)
) -> dict[str, Any]:
    """Responde uma pergunta paralela (/paralela) sem alterar o contexto da sessão principal."""
    ensure_fcc_running(DEFAULT_FCC_URL)
    st = fetch_fcc_status(DEFAULT_FCC_URL)
    model = payload.model or st.active_model
    if not model:
        raise HTTPException(status_code=400, detail="Nenhum modelo ativo configurado no FCC.")
    ok, answer = await asyncio.to_thread(
        quick_side_question,
        payload.question,
        model=model,
        fcc_url=DEFAULT_FCC_URL,
        fcc_token=DEFAULT_FCC_TOKEN,
    )
    if not ok:
        raise HTTPException(status_code=502, detail=answer)
    return {
        "ok": True,
        "model": model,
        "model_name": format_model_name(model),
        "answer": answer,
    }


@router.post("/stop")
async def dev_stop(payload: DevStopPayload, user=Depends(get_verified_user)) -> dict[str, Any]:
    """Interrompe uma execução ativa da Minerva Dev."""
    proc = _ACTIVE_RUNS.get(payload.run_id)
    if proc is None:
        return {"ok": False, "message": "Execução não encontrada ou já finalizada."}
    try:
        proc.terminate()
    except ProcessLookupError:
        pass
    return {"ok": True}


@router.post("/chat")
async def dev_chat_stream(payload: DevChatPayload, user=Depends(get_verified_user)):
    """Executa o harness Claude Code via FCC e transmite eventos SSE em tempo real."""
    ensure_fcc_running(DEFAULT_FCC_URL)
    folderless = not bool(payload.cwd and payload.cwd.strip())
    exec_cwd = str(Path.home()) if folderless else payload.cwd.strip()
    if not os.path.isdir(exec_cwd):
        raise HTTPException(status_code=400, detail=f"Diretório inválido: {exec_cwd}")

    effective_perm = payload.permission_mode or "bypassPermissions"
    valid_extra_dirs = [d for d in (payload.extra_dirs or []) if d and os.path.isdir(d)]
    if effective_perm == "bypassPermissions":
        for sys_dir in (str(Path.home()), "/"):
            if os.path.isdir(sys_dir) and sys_dir not in valid_extra_dirs:
                valid_extra_dirs.append(sys_dir)

    run_id = payload.run_id or uuid.uuid4().hex[:12]
    cmd = build_claude_command(
        payload.prompt,
        session_id=payload.session_id,
        permission_mode=effective_perm,
        model=payload.model,
        extra_dirs=valid_extra_dirs or None,
        effort=payload.effort,
        folderless=folderless,
    )
    env = build_claude_env(proxy_url=DEFAULT_FCC_URL, auth_token=DEFAULT_FCC_TOKEN)

    def _sse(event_type: str, data: dict[str, Any]) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def event_generator():
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=exec_cwd,
            env=env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024 * 1024,
        )
        _ACTIVE_RUNS[run_id] = proc
        stderr_lines: list[str] = []

        async def _drain_stderr():
            assert proc.stderr is not None
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                stderr_lines.append(line.decode("utf-8", errors="replace"))

        stderr_task = asyncio.create_task(_drain_stderr())
        yield _sse("run", {"run_id": run_id, "cwd": "" if folderless else exec_cwd, "folderless": folderless})

        try:
            assert proc.stdout is not None
            while True:
                raw = await proc.stdout.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace")
                for ev in parse_stream_event(line):
                    if ev.kind == "init":
                        yield _sse("init", {"session_id": ev.session_id})
                    elif ev.kind == "thinking_delta":
                        yield _sse("thinking", {"text": ev.text})
                    elif ev.kind == "text_delta":
                        yield _sse("text", {"text": ev.text})
                    elif ev.kind == "tool_use":
                        label, icon = translate_tool_name(ev.tool_name)
                        summary = format_tool_summary(ev.tool_name, ev.tool_input)
                        yield _sse(
                            "tool_use",
                            {
                                "name": ev.tool_name,
                                "label": label,
                                "icon": icon,
                                "summary": summary,
                                "input": _sanitize_tool_input(ev.tool_name, ev.tool_input),
                            },
                        )
                    elif ev.kind == "tool_result":
                        snippet = ev.text.strip()
                        if len(snippet) > 1200:
                            snippet = snippet[:1200] + "…"
                        yield _sse(
                            "tool_result",
                            {"text": snippet, "is_error": ev.is_error},
                        )
                    elif ev.kind == "result":
                        yield _sse(
                            "result",
                            {
                                "session_id": ev.session_id,
                                "text": ev.text,
                                "is_error": ev.is_error,
                                "duration_ms": ev.duration_ms,
                            },
                        )

            await stderr_task
            rc = await proc.wait()
            if rc != 0:
                err = filter_claude_stderr("".join(stderr_lines))
                if err:
                    yield _sse("error", {"message": err})
            yield _sse("done", {"run_id": run_id, "returncode": rc})
        finally:
            _ACTIVE_RUNS.pop(run_id, None)
            if proc.returncode is None:
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
