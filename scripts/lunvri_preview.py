"""Start the local Open WebUI fork and its Cavren-engine bridge.

Only the bridge process loads provider credentials. Open WebUI gets a random,
ephemeral bridge token; histories are stored in a separate preview database.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.cavren'


def wait_ready(url: str, process, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Um serviço da prévia encerrou. Consulte os logs em .cavren/.')
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    raise RuntimeError('A prévia não iniciou no tempo esperado. Consulte os logs em .cavren/.')


def main():
    parser = argparse.ArgumentParser(description='Prévia local da Lunvri')
    parser.add_argument('--port', type=int, default=8175)
    parser.add_argument('--dev', action='store_true', help='Use o frontend de desenvolvimento.')
    parser.add_argument('--dev-port', type=int, default=5179)
    parser.add_argument('--engine', type=Path, default=ROOT.parent / 'cavren-nextchat')
    args = parser.parse_args()
    engine = args.engine.resolve()
    engine_python = engine / '.venv/bin/python'
    backend_python = RUNTIME / 'venv/bin/python'
    node = RUNTIME / 'runtime/node/bin/node'
    for required in (engine_python, backend_python, node):
        if not required.exists():
            parser.error(f'Runtime ausente: {required}')
    if not args.dev and not (ROOT / 'build/index.html').exists():
        parser.error('Compile a interface antes de iniciar: npm run build.')
    if not 1024 <= args.port <= 65535:
        parser.error('Use uma porta entre 1024 e 65535.')
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    data = RUNTIME / 'data'
    data.mkdir(mode=0o700, exist_ok=True)
    secret_path = RUNTIME / 'webui-secret'
    if not secret_path.exists():
        descriptor = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as file:
            file.write(secrets.token_urlsafe(48))
    token = secrets.token_urlsafe(48)
    for port in [args.port, *([args.dev_port] if args.dev else [])]:
        with socket.socket() as check:
            check.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                check.bind(('127.0.0.1', port))
            except OSError:
                parser.error(f'A porta {port} já está em uso. Escolha outra porta.')
    public_url = f'http://127.0.0.1:{args.dev_port if args.dev else args.port}'
    origins = [f'http://127.0.0.1:{args.port}']
    if args.dev:
        origins.append(public_url)
    processes = []
    logs = []
    try:
        bridge_env = os.environ.copy()
        bridge_env.update(CAVREN_BRIDGE_TOKEN=token, PYTHONPATH=str(engine / 'src'))
        bridge = subprocess.Popen(
            [str(engine_python), str(ROOT / 'integration/lunvri_bridge.py')],
            cwd=engine,
            env=bridge_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            start_new_session=True,
        )
        processes.append(bridge)
        port = json.loads(bridge.stdout.readline())['port']
        # No provider credential is copied to this environment or the WebUI DB.
        backend_env = os.environ.copy()
        for key in list(backend_env):
            if key.endswith(('_API_KEY', '_API_TOKEN')) or key in ('OPENAI_API_KEYS', 'CLOUDFLARE_ACCOUNT_ID'):
                backend_env.pop(key)
        backend_env.update(
            {
                'DATA_DIR': str(data),
                'STATIC_DIR': str(RUNTIME / 'static'),
                'WEBUI_NAME': 'Lunvri',
                'WEBUI_AUTH': 'False',
                'WEBUI_SECRET_KEY': secret_path.read_text(),
                'LUNVRI_LOCAL_PREVIEW': '1',
                'LUNVRI_LOCAL_ORIGINS': ';'.join(origins),
                'CORS_ALLOW_ORIGIN': ';'.join(origins),
                'ENABLE_PERSISTENT_CONFIG': 'False',
                'ENABLE_OLLAMA_API': 'False',
                'ENABLE_OPENAI_API': 'True',
                'OPENAI_API_BASE_URLS': f'http://127.0.0.1:{port}/v1',
                'OPENAI_API_KEYS': token,
                'DEFAULT_MODELS': 'cavren:auto',
                'DEFAULT_LOCALE': 'pt-BR',
                'RAG_FILE_MAX_SIZE': '20',
                'RAG_FILE_MAX_COUNT': '5',
                'DEFAULT_INTERFACE_SETTINGS': json.dumps(
                    {'theme': 'dark', 'landingPageMode': 'default', 'showChangelog': False}
                ),
                'DEFAULT_MODEL_METADATA': json.dumps(
                    {
                        'capabilities': {
                            'file_upload': False,
                            'web_search': False,
                            'image_generation': False,
                            'code_interpreter': False,
                            'terminal': False,
                        }
                    }
                ),
                'ENABLE_VERSION_UPDATE_CHECK': 'False',
                'OFFLINE_MODE': 'True',
                'RAG_EMBEDDING_ENGINE': 'openai',
                'ENABLE_TITLE_GENERATION': 'False',
                'ENABLE_TAGS_GENERATION': 'False',
                'ENABLE_FOLLOW_UP_GENERATION': 'False',
                'ENABLE_AUTOCOMPLETE_GENERATION': 'False',
                'ENABLE_PROMPT_GENERATION': 'False',
                'DEFAULT_PROMPT_SUGGESTIONS': json.dumps(
                    [
                        {
                            'title': ['Explore uma ideia', 'Transforme uma ideia em um plano.'],
                            'content': 'Me ajude a transformar uma ideia em um plano. Comece perguntando o que quero fazer.',
                        },
                        {
                            'title': ['Entenda um assunto', 'Aprenda com exemplos claros.'],
                            'content': 'Quero entender um assunto com exemplos claros. Pergunte qual é o tema e o que já sei sobre ele.',
                        },
                        {
                            'title': ['Construa um projeto', 'Organize os próximos passos.'],
                            'content': 'Me ajude a organizar um projeto. Pergunte o objetivo, os recursos disponíveis e o prazo.',
                        },
                    ]
                ),
            }
        )
        log = open(RUNTIME / 'backend.log', 'w')
        logs.append(log)
        backend = subprocess.Popen(
            [
                str(backend_python),
                '-m',
                'uvicorn',
                'open_webui.main:app',
                '--app-dir',
                str(ROOT / 'backend'),
                '--host',
                '127.0.0.1',
                '--port',
                str(args.port),
                '--no-access-log',
            ],
            cwd=ROOT,
            env=backend_env,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
        processes.append(backend)
        wait_ready(f'http://127.0.0.1:{args.port}/api/config', backend)
        if args.dev:
            log = open(RUNTIME / 'frontend.log', 'w')
            logs.append(log)
            frontend_env = os.environ.copy()
            frontend_env['PATH'] = str(node.parent) + os.pathsep + frontend_env['PATH']
            frontend_env['WEBUI_BACKEND_URL'] = f'http://127.0.0.1:{args.port}'
            frontend = subprocess.Popen(
                [
                    str(node),
                    str(ROOT / 'node_modules/vite/bin/vite.js'),
                    '--host',
                    '127.0.0.1',
                    '--port',
                    str(args.dev_port),
                    '--strictPort',
                ],
                cwd=ROOT,
                env=frontend_env,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
            processes.append(frontend)
            wait_ready(public_url, frontend)
        (RUNTIME / 'preview.json').write_text(json.dumps({'url': public_url, 'pid': os.getpid()}))
        print(f'Prévia Lunvri pronta: {public_url}', flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(1)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        for log in logs:
            log.close()


if __name__ == '__main__':

    def stop(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        main()
    except KeyboardInterrupt:
        pass
