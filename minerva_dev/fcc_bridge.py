"""Integração com o servidor Free Claude Code (fcc-server) e ambiente do Claude Code."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Mapping

import httpx

DEFAULT_FCC_URL = "http://127.0.0.1:8082"
DEFAULT_FCC_TOKEN = "fcc-proxy"

PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "alibaba_cloud": "Alibaba Cloud",
    "anthropic": "Anthropic",
    "atlascloud": "AtlasCloud",
    "azure_openai": "Azure OpenAI",
    "bedrock": "Amazon Bedrock",
    "cerebras": "Cerebras",
    "chutes": "Chutes",
    "cloudflare": "Cloudflare",
    "cohere": "Cohere",
    "deepinfra": "DeepInfra",
    "deepseek": "DeepSeek",
    "fireworks": "Fireworks",
    "gemini": "Google Gemini",
    "github_copilot": "GitHub Copilot",
    "groq": "Groq",
    "huggingface": "Hugging Face",
    "kimi": "Kimi",
    "kimi_code": "Kimi Code",
    "llamacpp": "llama.cpp",
    "lmstudio": "LM Studio",
    "minimax": "MiniMax",
    "mistral": "Mistral",
    "mistral_codestral": "Mistral Codestral",
    "nebius": "Nebius",
    "novita": "Novita",
    "nvidia_nim": "NVIDIA",
    "ollama": "Ollama",
    "ollama_cloud": "Ollama Cloud",
    "open_router": "OpenRouter",
    "openai": "OpenAI",
    "openai_api": "OpenAI",
    "sambanova": "SambaNova",
    "siliconflow": "SiliconFlow",
    "together": "Together AI",
    "vercel": "Vercel",
    "vertex": "Google Vertex",
    "xai": "xAI",
    "zai": "Z.ai",
}

_UPPER_TOKENS = {
    "gpt",
    "oss",
    "ai",
    "vl",
    "it",
    "fp8",
    "bf16",
    "r1",
    "v1",
    "v2",
    "v3",
    "v4",
    "e4b",
    "llm",
    "tts",
    "ocr",
    "xs",
    "glm",
    "lfm",
    "ernie",
    "sea",
    "lion",
}

_BRAND_TOKEN_CASING: dict[str, str] = {
    "minimax": "MiniMax",
    "deepseek": "DeepSeek",
    "qwq": "QwQ",
    "qwen2.5": "Qwen 2.5",
    "qwen3": "Qwen 3",
    "qwen3.8": "Qwen 3.8",
    "c4ai": "Aya",
    "openrouter": "OpenRouter",
}


def format_provider_name(provider_id: str) -> str:
    """Retorna o nome limpo e capitalizado de um provedor (sem sublinhados)."""
    raw = (provider_id or "").strip()
    if not raw:
        return "Não definido"
    key = raw.lower()
    if key in PROVIDER_DISPLAY_NAMES:
        return PROVIDER_DISPLAY_NAMES[key]
    return raw.replace("_", " ").replace("-", " ").title()


def _format_model_token(tok: str) -> str:
    low = tok.lower()
    if low in _BRAND_TOKEN_CASING:
        return _BRAND_TOKEN_CASING[low]
    if low in _UPPER_TOKENS:
        return low.upper()
    if len(low) >= 2 and low[-1] in {"b", "t"} and low[:-1].replace(".", "").isdigit():
        return low[:-1] + low[-1].upper()
    if low.startswith("a") and len(low) >= 3 and low[1:-1].isdigit() and low[-1] == "b":
        return "A" + low[1:-1] + "B"
    if len(low) >= 3 and low[-1] == "e" and low[:-1].isdigit():
        return low[:-1] + "E"
    if any(ch.isdigit() for ch in low) and low[0] in {"v", "q", "m", "r", "l"}:
        return tok[0].upper() + tok[1:]
    return tok.capitalize()


def format_model_name(model_id: str) -> str:
    """Formata um ID de modelo em nome legível, capitalizado e limpo."""
    raw = (model_id or "").strip()
    if not raw:
        return "Não definido"

    clean = raw[:-5] if raw.endswith(":free") else raw
    if clean.endswith(":latest"):
        clean = clean[:-7]

    parts = [p for p in clean.split("/") if p and p not in {"models", "@cf"}]
    if len(parts) > 1 and parts[0].lower() in PROVIDER_DISPLAY_NAMES:
        parts = parts[1:]
    if len(parts) > 1:
        leaf = parts[-1]
    else:
        leaf = parts[0] if parts else clean

    # Separa tags de tamanho de modelos Ollama (ex.: qwen2.5-abliterate:3b -> qwen2.5 abliterate 3b)
    leaf = leaf.replace(":", " ").replace("_", " ").replace("-", " ")
    tokens = [t for t in leaf.split() if t]
    pretty = " ".join(_format_model_token(t) for t in tokens)
    return pretty

# Modos inteligentes da Minerva Dev auditados por benchmarks oficiais (AA Index v5, SWE-bench,
# DeepSWE, LiveCodeBench, Terminal-Bench) e estresse ao vivo de estabilidade, latência e tool calling.
MINERVA_DEV_MODES: dict[str, dict[str, Any]] = {
    "harmonia": {
        "label": "Harmonia",
        "description": "Equilíbrio entre código agêntico (SWE 70,9%), estabilidade 100% e resposta rápida",
        "model": "nvidia_nim/poolside/laguna-xs-2.1",
        "fallbacks": [
            "nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b",
            "cerebras/qwen-3.8-27b",
            "groq/qwen/qwen3.8-27b",
            "nvidia_nim/nvidia/nemotron-3.5-super-vl-120b-a12b",
        ],
    },
    "sabia": {
        "label": "Sábia",
        "description": "Máxima profundidade agêntica (550B MoE, 1M ctx, SWE 71,9%) com alta estabilidade",
        "model": "nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b",
        "fallbacks": [
            "nvidia_nim/minimaxai/minimax-m3.1-flash",
            "nvidia_nim/poolside/laguna-xs-2.1",
            "nvidia_nim/nvidia/nemotron-3.5-super-vl-120b-a12b",
            "open_router/particle-ai/particle-1:free",
            "cerebras/qwen-3.8-27b",
        ],
    },
    "impeto": {
        "label": "Ímpeto",
        "description": "Velocidade extrema (<1s) e alta disponibilidade de cota permanente no terminal",
        "model": "cerebras/qwen-3.8-27b",
        "fallbacks": [
            "groq/qwen/qwen3.8-27b",
            "cerebras/gpt-oss-120b",
            "groq/openai/gpt-oss-120b",
            "cloudflare/@cf/qwen/qwen3.8-27b",
        ],
    },
}

# Provedores gratuitos populares suportados pelo FCC e suas chaves de configuração no /admin/api/config/apply
FREE_PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "nvidia_nim": {
        "label": "NVIDIA NIM (Gratuito)",
        "env_key": "NVIDIA_NIM_API_KEY",
        "default_model": "nvidia_nim/poolside/laguna-xs-2.1",
    },
    "gemini": {
        "label": "Google Gemini (Gratuito)",
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini/models/gemini-3.6-flash",
    },
    "groq": {
        "label": "Groq (Gratuito / Ultra-rápido)",
        "env_key": "GROQ_API_KEY",
        "default_model": "groq/qwen/qwen3.8-27b",
    },
    "open_router": {
        "label": "OpenRouter (Modelos :free)",
        "env_key": "OPENROUTER_API_KEY",
        "default_model": "open_router/particle-ai/particle-1:free",
    },
}

# Provedores locais (sempre gratuitos e offline) e provedores com tier gratuito ativo (sem saldo pago obrigatório)
LOCAL_PROVIDERS: frozenset[str] = frozenset({"ollama", "llamacpp", "lmstudio"})
FREE_TIER_PROVIDERS: frozenset[str] = frozenset(
    {
        "nvidia_nim",
        "groq",
        "cerebras",
        "gemini",
        "cloudflare",
        "cohere",
    }
)

_NON_CHAT_MODEL_MARKERS: tuple[str, ...] = (
    "embed",
    "rerank",
    "-tts",
    "transcribe",
    "whisper",
    "guard",
    "safeguard",
    "parse",
    "safety",
    "detector",
    "lyria",
    "robotics",
    "gliner2",
    "native-audio",
    "-live",
    "orpheus",
    "clairic",
    "/clef",
    "deep-research",
    "antigravity-preview",
)

_DEPRECATED_DEV_MODEL_IDS: frozenset[str] = frozenset(
    {
        "cloudflare/@cf/nvidia/nemotron-3-120b-a12b",
        "cloudflare/@cf/qwen/qwen3-30b-a3b-fp8",
        "cloudflare/@cf/deepseek-ai/deepseek-v4.1-flash-1017",
        "cloudflare/@cf/deepseek-ai/deepseek-v4-pro-0813",
        "cloudflare/@cf/deepseek-ai/deepseek-v4-flash-0731",
        "open_router/cohere/north-mini-code:free",
    }
)


def is_dev_chat_model(model_id: str) -> bool:
    """Filtra utilitários não-chat (embed, rerank, tts, guard, audio) e modelos descontinuados."""
    low = (model_id or "").strip().lower()
    if not low or low in _DEPRECATED_DEV_MODEL_IDS:
        return False
    return not any(marker in low for marker in _NON_CHAT_MODEL_MARKERS)


def is_free_model(model_id: str, provider: str = "") -> bool:
    """Retorna True somente para modelos locais ou de tiers gratuitos (sem saldo/crédito pago)."""
    mid = (model_id or "").strip()
    if not mid:
        return False
    prov = (provider or (mid.split("/")[0] if "/" in mid else "")).strip().lower()
    if prov in LOCAL_PROVIDERS or prov in FREE_TIER_PROVIDERS:
        return True
    if prov == "open_router":
        return mid.lower().endswith(":free")
    return False


def detect_minerva_mode(model: str) -> str | None:
    """Retorna o ID do modo da Minerva correspondente ao modelo ativo, ou None se manual."""
    for mode_id, cfg in MINERVA_DEV_MODES.items():
        if cfg["model"] == model:
            return mode_id
    return None


def apply_minerva_mode(
    mode_id: str, base_url: str = DEFAULT_FCC_URL
) -> tuple[bool, str, str]:
    """Aplica um modo da Minerva (principal + fallbacks) no FCC. Retorna (ok, modelo, msg)."""
    key = mode_id.strip().lower().replace("í", "i").replace("á", "a")
    cfg = MINERVA_DEV_MODES.get(key)
    if not cfg:
        return False, "", "Modo inválido. Use: harmonia, sabia ou impeto."
    primary = str(cfg["model"])
    fallbacks = ",".join(cfg["fallbacks"])
    ok, msg = apply_fcc_config(
        {"MODEL": primary, "MODEL_FALLBACKS": fallbacks},
        base_url=base_url,
    )
    if not ok:
        return False, "", msg
    fb_count = len(cfg["fallbacks"])
    return True, primary, f"Modo {cfg['label']} ativado ({format_model_name(primary)} + {fb_count} fallbacks)."


@dataclass
class FccStatus:
    online: bool
    url: str
    active_model: str
    configured_providers: list[str]
    claude_installed: bool
    claude_version: str | None = None


def build_claude_env(
    base_env: Mapping[str, str] | None = None,
    *,
    proxy_url: str = DEFAULT_FCC_URL,
    auth_token: str = DEFAULT_FCC_TOKEN,
) -> dict[str, str]:
    """Constrói o dicionário de ambiente para o binário /opt/bin/claude via FCC."""
    env = dict(os.environ if base_env is None else base_env)
    for key in list(env):
        if key.startswith("ANTHROPIC_"):
            del env[key]
    env.pop("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", None)

    env.update(
        {
            "ANTHROPIC_BASE_URL": proxy_url.rstrip("/"),
            "ANTHROPIC_AUTH_TOKEN": auth_token,
            "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1",
            "CLAUDE_CODE_AUTO_MODE_SERVER": "0",
            "CLAUDE_CODE_DISABLE_ADVISOR_TOOL": "1",
            "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "190000",
            "CLAUDE_ENABLE_STREAM_WATCHDOG": "0",
            "CLAUDE_ENABLE_BYTE_WATCHDOG": "0",
            "API_FORCE_IDLE_TIMEOUT": "0",
            "API_TIMEOUT_MS": "2147483647",
            "DISABLE_FEEDBACK_COMMAND": "1",
            "DISABLE_ERROR_REPORTING": "1",
            "LANG": env.get("LANG") or "pt_BR.UTF-8",
        }
    )
    return env


def is_fcc_healthy(base_url: str = DEFAULT_FCC_URL, timeout: float = 1.5) -> bool:
    """Verifica se o fcc-server responde em /health."""
    try:
        resp = httpx.get(f"{base_url.rstrip('/')}/health", timeout=timeout)
        return resp.status_code == 200
    except httpx.HTTPError:
        return False


def ensure_fcc_running(base_url: str = DEFAULT_FCC_URL, wait_seconds: float = 10.0) -> bool:
    """Garante que o fcc-server esteja ativo via systemd --user ou processo em segundo plano."""
    if is_fcc_healthy(base_url):
        return True

    # Tenta via systemd --user primeiro
    systemctl = shutil.which("systemctl")
    if systemctl:
        subprocess.run(
            [systemctl, "--user", "start", "fcc-server.service"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        deadline = time.monotonic() + min(wait_seconds, 6.0)
        while time.monotonic() < deadline:
            if is_fcc_healthy(base_url):
                return True
            time.sleep(0.3)

    # Fallback: inicia fcc-server diretamente
    fcc_bin = shutil.which("fcc-server") or "/home/cambrith/.local/bin/fcc-server"
    if os.path.exists(fcc_bin):
        subprocess.Popen(
            [fcc_bin],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            if is_fcc_healthy(base_url):
                return True
            time.sleep(0.3)

    return is_fcc_healthy(base_url)


def fetch_fcc_status(base_url: str = DEFAULT_FCC_URL) -> FccStatus:
    """Consulta o status do fcc-server, provedores configurados e modelo ativo."""
    claude_bin = shutil.which("claude") or "/opt/bin/claude"
    claude_installed = os.path.exists(claude_bin)
    online = is_fcc_healthy(base_url)
    active_model = ""
    configured: list[str] = []

    if online:
        try:
            with httpx.Client(base_url=base_url.rstrip("/"), timeout=4.0) as client:
                cfg_resp = client.get("/admin/api/config")
                if cfg_resp.status_code == 200:
                    cfg = cfg_resp.json()
                    for field in cfg.get("fields") or []:
                        if isinstance(field, dict) and field.get("key") == "MODEL":
                            active_model = str(field.get("value") or "")
                            break
                    for prov in cfg.get("provider_status") or []:
                        if (
                            isinstance(prov, dict)
                            and prov.get("status") == "configured"
                            and prov.get("kind") == "remote"
                        ):
                            pid = prov.get("provider_id")
                            if pid:
                                configured.append(str(pid))
                if not active_model:
                    st_resp = client.get("/admin/api/status")
                    if st_resp.status_code == 200:
                        st = st_resp.json()
                        active_model = str(st.get("model") or "")
        except (httpx.HTTPError, ValueError):
            pass

    return FccStatus(
        online=online,
        url=base_url,
        active_model=active_model,
        configured_providers=sorted(configured),
        claude_installed=claude_installed,
    )


def fetch_fcc_models(
    base_url: str = DEFAULT_FCC_URL, *, free_only: bool = True
) -> list[dict[str, Any]]:
    """Lista os modelos expostos por /admin/api/models no fcc-server (normalizados em dict).

    Por padrão (`free_only=True`), retorna apenas modelos locais (ex.: Ollama) e
    provedores/modelos gratuitos, priorizando modelos locais no topo da lista.
    """
    try:
        resp = httpx.get(f"{base_url.rstrip('/')}/admin/api/models", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            raw_list: list[Any] = []
            if isinstance(data, dict) and isinstance(data.get("models"), list):
                raw_list = data["models"]
            elif isinstance(data, list):
                raw_list = data

            normalized: list[dict[str, Any]] = []
            for item in raw_list:
                if isinstance(item, str):
                    prov = item.split("/")[0] if "/" in item else ""
                    if not free_only or is_free_model(item, prov):
                        normalized.append({"id": item, "provider": prov})
                elif isinstance(item, dict):
                    mid = str(item.get("id") or item.get("model") or "")
                    if mid:
                        prov = str(item.get("provider") or (mid.split("/")[0] if "/" in mid else ""))
                        if not free_only or is_free_model(mid, prov):
                            normalized.append({**item, "id": mid, "provider": prov})
            normalized.sort(
                key=lambda it: (0 if str(it.get("provider") or "").lower() in LOCAL_PROVIDERS else 1)
            )
            return normalized
    except (httpx.HTTPError, ValueError):
        pass
    return []


def apply_fcc_config(
    values: dict[str, Any], base_url: str = DEFAULT_FCC_URL
) -> tuple[bool, str]:
    """Aplica configurações no fcc-server via /admin/api/config/apply."""
    try:
        base = base_url.rstrip("/")
        submit_values: dict[str, Any] = dict(values)
        model_val = str(submit_values.get("MODEL") or "").strip()
        if model_val:
            model_prov = model_val.split("/")[0].lower() if "/" in model_val else ""
            if model_prov in LOCAL_PROVIDERS:
                if "MODEL_FALLBACKS" not in submit_values:
                    submit_values["MODEL_FALLBACKS"] = ""
                if "REASONING_POLICY" not in submit_values:
                    submit_values["REASONING_POLICY"] = "off"
            elif "REASONING_POLICY" not in submit_values:
                submit_values["REASONING_POLICY"] = "client"
        cfg_resp = httpx.get(f"{base}/admin/api/config", timeout=6.0)
        if cfg_resp.status_code == 200:
            fields_by_key = {
                f["key"]: f
                for f in cfg_resp.json().get("fields") or []
                if isinstance(f, dict) and "key" in f
            }
            for key, val in list(submit_values.items()):
                fmeta = fields_by_key.get(key)
                if (
                    isinstance(fmeta, dict)
                    and fmeta.get("type") == "api_key_list"
                    and isinstance(val, str)
                ):
                    rev = (fmeta.get("value") or {}).get("revision")
                    submit_values[key] = {
                        "revision": rev,
                        "entries": [{"value": val.strip()}],
                    }

        resp = httpx.post(
            f"{base}/admin/api/config/apply",
            json={"values": submit_values},
            timeout=20.0,
        )
        if resp.status_code == 200:
            body = resp.json()
            if body.get("applied") is False or body.get("errors"):
                errs = "; ".join(str(e) for e in (body.get("errors") or []))
                return False, errs or "Falha ao validar configuração no FCC."
            return True, "Configuração salva no Free Claude Code com sucesso."
        detail = resp.text
        try:
            detail = str(resp.json().get("detail") or detail)
        except ValueError:
            pass
        return False, f"Erro HTTP {resp.status_code}: {detail}"
    except httpx.HTTPError as exc:
        return False, f"Falha de comunicação com o FCC: {exc}"


def test_fcc_provider(
    provider_id: str, base_url: str = DEFAULT_FCC_URL
) -> tuple[bool, str]:
    """Testa conectividade de um provedor configurado no fcc-server."""
    try:
        resp = httpx.post(
            f"{base_url.rstrip('/')}/admin/api/providers/{provider_id}/test",
            timeout=20.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            ok = bool(data.get("ok", True))
            msg = str(data.get("message") or data.get("detail") or "Conexão validada.")
            return ok, msg
        return False, f"Falha no teste ({resp.status_code}): {resp.text[:200]}"
    except httpx.HTTPError as exc:
        return False, f"Erro ao testar provedor: {exc}"
