"""Loopback OpenAI adapter. Provider keys remain in the Cavren worker environment."""

from __future__ import annotations

import hmac
import json
import os
import selectors
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cavren.errors import CavrenError
from cavren.models import Message
from cavren.modes import DEFAULT_MODE_ID, MODE_BY_ID
from cavren.nextchat_server import CavrenHandler, worker_env
from integration.lunvri_connections import catalog, credentials_env

MAX_BODY = 40 * 1024 * 1024
WORKER = Path(__file__).with_name("lunvri_worker.py")


def prepare_job(body: dict, generation_id: str) -> dict:
    mode = body.get("cavren_mode_id", DEFAULT_MODE_ID)
    if mode not in MODE_BY_ID:
        raise ValueError("Escolha um modo Lunvri válido.")
    model = body.get("model", "")
    allowed = {item["id"]: item for item in catalog()}
    if model not in allowed:
        raise ValueError("Escolha um modelo integrado à Lunvri.")
    info = allowed[model].get('cavren', {})
    if info.get('price_kind', 'free') != 'free' and body.get('cavren_billing_confirmed') is not True:
        raise ValueError('Confirme o possível custo deste modelo antes de usá-lo.')
    images = body.get('lunvri_image_generation') is True or info.get('image_only') is True
    if images and not info.get('capabilities', {}).get('image_generation'):
        raise ValueError('Escolha um modelo que tenha suporte a geração de imagens.')
    raw_messages = body.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        raise ValueError("A conversa precisa de uma mensagem.")
    messages = []
    for item in raw_messages:
        if not isinstance(item, dict):
            raise ValueError("Mensagem inválida.")
        # Tool execution stays with Open WebUI; Cavren accepts its public message contract.
        message = Message(item.get("role"), item.get("content"))
        messages.append({"role": message.role, "content": message.content})
    users = [m for m in messages if m["role"] == "user"]
    if not users:
        raise ValueError("A conversa precisa de uma mensagem do usuário.")
    prompt = users[-1]["content"]
    if isinstance(prompt, list):
        prompt = "\n".join(part["text"] for part in prompt if part.get("type") == "text")
    limit = body.get("max_tokens") or body.get("max_completion_tokens") or 4096
    if type(limit) is not int or not 256 <= limit <= 65536:
        raise ValueError("O limite de resposta deve estar entre 256 e 65536 tokens.")
    return {
        "kind": "chat",
        "generation_id": generation_id,
        "mode_id": mode,
        "mode_options": {
            "manual_route": "" if model == "cavren:auto" else model.removeprefix("cavren:"),
            "billing_confirmed": body.get("cavren_billing_confirmed") is True,
            "web_search": body.get("cavren_web_search") is True,
        },
        "messages": messages,
        "prompt": prompt or "Analise o conteúdo enviado.",
        "task_kind": "chat",
        "max_tokens": limit,
        "lunvri_direct": info.get('integrated') is False or images,
        "lunvri_image_generation": images,
    }


class BridgeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, token: str, port: int = 0):
        super().__init__(("127.0.0.1", port), BridgeHandler)
        self.token = token
        self.active: set[subprocess.Popen] = set()
        self.lock = threading.Lock()

    def close_workers(self):
        with self.lock:
            for process in self.active:
                if process.poll() is None:
                    process.terminate()


class BridgeHandler(BaseHTTPRequestHandler):
    server: BridgeServer
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass  # Never log authorization, URLs, messages or provider errors.

    def authorized(self) -> bool:
        return (
            self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"
            and hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + self.server.token)
            and not self.headers.get("Origin")
        )

    def respond(self, status: int, data: dict):
        content = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def error(self, status: int, message: str, code: str = "input"):
        self.respond(status, {"error": {"message": message, "code": code, "type": "cavren"}})

    def do_GET(self):
        if not self.authorized():
            self.error(401, "Ponte local não autorizada.", "auth")
            return
        if self.path.split('?', 1)[0] != "/v1/models":
            self.error(404, "Recurso não encontrado.")
            return
        try:
            self.respond(200, {"object": "list", "data": catalog(refresh='refresh=true' in self.path)})
        except (OSError, ValueError, CavrenError):
            self.error(503, "Não foi possível acessar o cofre ou catálogo da Lunvri.", "credentials")

    def do_POST(self):
        if not self.authorized():
            self.error(401, "Ponte local não autorizada.", "auth")
            return
        if self.path != "/v1/chat/completions":
            self.error(404, "Recurso não encontrado.")
            return
        process = None
        streaming = False
        try:
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise ValueError("Envie JSON.")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY:
                raise ValueError("Pedido vazio ou grande demais.")
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError("Pedido inválido.")
            generation_id = "chatcmpl-" + str(uuid4())
            job = prepare_job(body, generation_id)
            env = credentials_env()
            env["CAVREN_MAX_TOKENS"] = str(job.pop("max_tokens"))
            process = subprocess.Popen(
                [sys.executable, str(WORKER)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env,
                text=True,
                bufsize=1,
            )
            with self.server.lock:
                self.server.active.add(process)
            process.stdin.write(json.dumps(job, ensure_ascii=False))
            process.stdin.close()
            streaming = body.get("stream") is True
            if streaming:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                self.sse(self.chunk(generation_id, body["model"], {"role": "assistant"}))
            final = None
            terminal = False
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                deadline = time.monotonic() + 600
                while time.monotonic() < deadline:
                    if not selector.select(timeout=5):
                        if streaming:
                            self.wfile.write(b": keep-alive\n\n")
                            self.wfile.flush()
                        continue
                    line = process.stdout.readline()
                    if not line:
                        break
                    event = json.loads(line)
                    kind = event.get("type")
                    if kind == "generation.delta" and streaming:
                        self.sse(self.chunk(generation_id, body["model"], {"content": event["text"]}))
                    elif kind == "generation.searching" and streaming:
                        self.sse(
                            {
                                "event": {
                                    "type": "status",
                                    "data": {
                                        "action": "web_search",
                                        "description": "Pesquisando na web",
                                        "done": False,
                                    },
                                }
                            }
                        )
                    elif kind == "generation.sources" and streaming:
                        sources = event.get("sources") or []
                        self.sse(
                            {
                                "event": {
                                    "type": "status",
                                    "data": {
                                        "action": "web_search",
                                        "description": "Pesquisa concluída",
                                        "done": True,
                                        "urls": [source["url"] for source in sources],
                                    },
                                }
                            }
                        )
                        for source in sources:
                            self.sse(
                                {
                                    "event": {
                                        "type": "source",
                                        "data": {
                                            "source": {"name": source["title"], "url": source["url"]},
                                            "document": [source.get("snippet", "")],
                                            "metadata": [{"source": source["url"], "name": source["title"]}],
                                        },
                                    }
                                }
                            )
                    elif kind == "generation.completed":
                        final = event["response"]
                        terminal = True
                        break
                    elif kind == 'generation.files' and streaming:
                        self.sse({'event': {'type': 'files', 'data': {'files': event['files']}}})
                    elif kind == "generation.error":
                        terminal = True
                        if streaming:
                            self.sse(
                                {
                                    "error": {
                                        "message": event["message"].replace("Cavren", "Lunvri"),
                                        "code": event["code"],
                                    }
                                }
                            )
                        else:
                            self.error(503, event["message"].replace("Cavren", "Lunvri"), event["code"])
                        break
            if not terminal:
                if streaming:
                    self.sse({"error": {"message": "A geração foi interrompida ou excedeu o tempo limite."}})
                else:
                    self.error(504, "A geração foi interrompida ou excedeu o tempo limite.", "timeout")
            if final:
                usage = final.get("usage") or {}
                usage = {
                    "prompt_tokens": usage.get("input_tokens"),
                    "completion_tokens": usage.get("output_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                }
                route = {k: final.get(k) for k in ("provider", "model", "public_mode", "fallback_index")}
                if streaming:
                    result = self.chunk(generation_id, body["model"], {}, "stop")
                    result.update(usage=usage, cavren=route)
                    self.sse(result)
                else:
                    self.respond(
                        200,
                        {
                            "id": generation_id,
                            "object": "chat.completion",
                            "created": int(time.time()),
                            "model": body["model"],
                            "choices": [
                                {
                                    "index": 0,
                                    "message": {"role": "assistant", "content": final["text"]},
                                    "finish_reason": "stop",
                                }
                            ],
                            "usage": usage,
                            "cavren": route,
                        },
                    )
            if streaming:
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # Disconnect cancels this worker in finally.
        except (ValueError, TypeError, KeyError):
            if streaming:
                self.sse({"error": {"message": "O motor retornou um evento inválido."}})
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            else:
                self.error(400, "Pedido inválido. Verifique as mensagens, o modo e o modelo.")
        except (OSError, CavrenError):
            if streaming:
                self.sse({"error": {"message": "A conexão com o motor foi interrompida."}})
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            else:
                self.error(503, "Não foi possível iniciar o motor ou acessar as credenciais.", "credentials")
        finally:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                with self.server.lock:
                    self.server.active.discard(process)
                if process.stdout:
                    process.stdout.close()

    def sse(self, data: dict):
        self.wfile.write(("data: " + json.dumps(data, ensure_ascii=False) + "\n\n").encode())
        self.wfile.flush()

    @staticmethod
    def chunk(generation_id: str, model: str, delta: dict, finish_reason=None):
        return {
            "id": generation_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
        }


if __name__ == "__main__":
    server = BridgeServer(os.environ["CAVREN_BRIDGE_TOKEN"])
    print(json.dumps({"port": server.server_port}), flush=True)
    try:
        server.serve_forever()
    finally:
        server.close_workers()
        server.server_close()
