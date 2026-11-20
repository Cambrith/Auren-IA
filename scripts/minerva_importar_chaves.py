#!/usr/bin/env python3
"""Importa chaves de API do cofre criptografado (GPG) para as Conexões da Minerva.

Roda no SEU terminal: você digita a senha do cofre; o texto é descriptografado só na
memória. Nenhuma chave é impressa, escrita em disco ou enviada a outro lugar além do
próprio provedor (teste de validade) e da Minerva em 127.0.0.1.

    python3 scripts/minerva_importar_chaves.py            # mostra o plano e pergunta antes de salvar
    python3 scripts/minerva_importar_chaves.py --simular  # só valida, não salva nada
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

COFRE = Path.home() / 'Documentos/Cofre-API/Chaves-de-API.md.asc'
MINERVA = os.environ.get('MINERVA_URL', 'http://127.0.0.1:8080')

# id -> (nome, URL base compatível com OpenAI, variável de ambiente usual, apelidos no cofre)
PROVEDORES = {
    'openai': ('OpenAI', 'https://api.openai.com/v1', 'OPENAI_API_KEY', ('openai', 'chatgpt')),
    'anthropic': ('Anthropic (Claude)', 'https://api.anthropic.com/v1', 'ANTHROPIC_API_KEY', ('anthropic', 'claude')),
    'gemini': ('Google Gemini', 'https://generativelanguage.googleapis.com/v1beta/openai', 'GEMINI_API_KEY', ('gemini', 'google ai', 'aistudio')),
    'groq': ('Groq', 'https://api.groq.com/openai/v1', 'GROQ_API_KEY', ('groq',)),
    'deepseek': ('DeepSeek', 'https://api.deepseek.com/v1', 'DEEPSEEK_API_KEY', ('deepseek',)),
    'mistral': ('Mistral', 'https://api.mistral.ai/v1', 'MISTRAL_API_KEY', ('mistral',)),
    'openrouter': ('OpenRouter', 'https://openrouter.ai/api/v1', 'OPENROUTER_API_KEY', ('openrouter',)),
    'xai': ('xAI (Grok)', 'https://api.x.ai/v1', 'XAI_API_KEY', ('xai', 'x.ai')),
    'cerebras': ('Cerebras', 'https://api.cerebras.ai/v1', 'CEREBRAS_API_KEY', ('cerebras',)),
    'fireworks': ('Fireworks AI', 'https://api.fireworks.ai/inference/v1', 'FIREWORKS_API_KEY', ('fireworks',)),
    'deepinfra': ('DeepInfra', 'https://api.deepinfra.com/v1/openai', 'DEEPINFRA_API_KEY', ('deepinfra',)),
    'nvidia': ('NVIDIA NIM', 'https://integrate.api.nvidia.com/v1', 'NVIDIA_API_KEY', ('nvidia',)),
    'huggingface': ('Hugging Face', 'https://router.huggingface.co/v1', 'HUGGINGFACE_API_KEY', ('hugging face', 'huggingface')),
    'zai': ('Z.ai', 'https://api.z.ai/api/paas/v4', 'ZAI_API_KEY', ('z.ai', 'zai', 'zhipu')),
    'novita': ('Novita AI', 'https://api.novita.ai/v3/openai', 'NOVITA_API_KEY', ('novita',)),
    'hyperbolic': ('Hyperbolic', 'https://api.hyperbolic.xyz/v1', 'HYPERBOLIC_API_KEY', ('hyperbolic',)),
    'cohere': ('Cohere', 'https://api.cohere.ai/compatibility/v1', 'COHERE_API_KEY', ('cohere',)),
    'ollama': ('Ollama Cloud', 'https://ollama.com/v1', 'OLLAMA_API_KEY', ('ollama',)),
    # Precisa do Account ID; a URL real é montada em main() (veja CLOUDFLARE).
    'cloudflare': ('Cloudflare Workers AI', 'https://api.cloudflare.com/client/v4/accounts/{conta}/ai/v1', 'CLOUDFLARE_API_TOKEN', ('cloudflare',)),
}
HEX32 = re.compile(r'[0-9a-fA-F]{32}')
# Serviços que não são de chat (áudio, imagem, embeddings): ficam de fora das conexões nativas.
OUTROS = {
    'AI_HORDE_API_KEY': 'AI Horde (imagens)', 'ASSEMBLYAI_API_KEY': 'AssemblyAI (áudio)',
    'CARTESIA_API_KEY': 'Cartesia (voz)', 'DEEPGRAM_API_KEY': 'Deepgram (áudio)',
    'ELEVENLABS_API_KEY': 'ElevenLabs (voz)', 'FAL_KEY': 'fal (mídia)',
    'REPLICATE_API_TOKEN': 'Replicate', 'STABILITY_API_KEY': 'Stability (imagens)',
    'VOYAGE_API_KEY': 'Voyage (embeddings)',
    'AWS_BEARER_TOKEN_BEDROCK': 'Amazon Bedrock', 'CANVA_CLIENT_SECRET': 'Canva',
}
PREFIXOS = (('sk-ant-', 'anthropic'), ('sk-or-', 'openrouter'), ('gsk_', 'groq'), ('hf_', 'huggingface'),
            ('nvapi-', 'nvidia'), ('xai-', 'xai'), ('AIza', 'gemini'), ('csk-', 'cerebras'), ('fw_', 'fireworks'))
IGNORAR = {'cole_aqui', 'pendente', 'ativa'}
NOME_ENV = re.compile(r'\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b')
ENV_PARA_ID = {spec[2]: pid for pid, spec in PROVEDORES.items()} | {'GOOGLE_API_KEY': 'gemini', 'HF_TOKEN': 'huggingface'}


def descriptografar(senha: str) -> str:
    return descriptografar_arquivo(COFRE, senha)


def descriptografar_arquivo(arquivo: Path, senha: str) -> str:
    r, w = os.pipe()
    os.write(w, senha.encode()); os.close(w)
    try:
        p = subprocess.run(['gpg', '--batch', '--quiet', '--pinentry-mode', 'loopback', '--passphrase-fd', str(r),
                            '-d', str(arquivo)], capture_output=True, pass_fds=(r,), timeout=60)
    finally:
        os.close(r)
    if p.returncode:
        raise SystemExit('Senha incorreta ou arquivo inválido.')
    return p.stdout.decode('utf-8', 'replace')


def _provedor_do_texto(texto: str) -> str | None:
    t = texto.lower()
    for pid, (_, _, _, apelidos) in PROVEDORES.items():
        if any(re.search(rf'(?<![a-z]){re.escape(a)}(?![a-z])', t) for a in apelidos):
            return pid
    return None


def extrair(texto: str):
    """Devolve (chaves {provedor: chave}, ignoradas [(motivo, linha mascarada)], outros [nomes])."""
    chaves: dict[str, str] = {}
    avisos: list[tuple[str, str]] = []
    outros: set[str] = set()
    secao: str | None = None
    for linha in texto.splitlines():
        if linha.lstrip().startswith('#'):
            secao = _provedor_do_texto(linha)
            continue
        if secao == 'cloudflare':
            achado = HEX32.search(linha)
            if achado and 'conta' not in chaves:
                chaves['conta'] = achado.group(0)
        candidatos = {c for c in re.findall(r'`([!-~]{8,})`', linha) if not HEX32.fullmatch(c)}
        for m in re.finditer(r'\b[A-Z][A-Z0-9_]{3,}\s*[=:]\s*([!-~]{8,})', linha):
            candidatos.add(m.group(1).strip('`'))
        mascarada = linha
        for c in sorted(candidatos, key=len, reverse=True):
            mascarada = mascarada.replace(c, '•••')
        envs = NOME_ENV.findall(linha)
        de_outro_servico = False
        for env, rotulo in OUTROS.items():
            if env in envs:
                outros.add(rotulo)
                de_outro_servico = True
        for c in candidatos:
            if de_outro_servico:
                break
            if c.lower() in IGNORAR or NOME_ENV.fullmatch(c) or c.startswith(('http://', 'https://')):
                continue
            alvo = next((ENV_PARA_ID[e] for e in envs if e in ENV_PARA_ID), None)
            alvo = alvo or next((pid for pre, pid in PREFIXOS if c.startswith(pre)), None)
            alvo = alvo or _provedor_do_texto(linha) or secao
            if not alvo:
                avisos.append(('sem provedor identificado', mascarada.strip()[:110]))
            elif alvo in chaves and chaves[alvo] != c:
                avisos.append((f'mais de uma chave para {alvo}; mantida a primeira', mascarada.strip()[:110]))
            else:
                chaves.setdefault(alvo, c)
    return chaves, avisos, sorted(outros)


def testar(url: str, chave: str) -> str:
    req = urllib.request.Request(url.rstrip('/') + '/models', headers={'Authorization': 'Bearer ' + chave, 'User-Agent': 'minerva-importador'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 'ok' if 200 <= r.status < 300 else f'http {r.status}'
    except urllib.error.HTTPError as e:
        return 'recusada' if e.code in (401, 403) else f'http {e.code}'
    except (urllib.error.URLError, TimeoutError, OSError):
        return 'sem resposta'


def testar_cloudflare(conta: str, chave: str):
    """Valida o token da conta e lista os modelos de texto (a Cloudflare não lista em /v1/models)."""
    url = f'https://api.cloudflare.com/client/v4/accounts/{conta}/ai/models/search?per_page=100&task=Text%20Generation'
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + chave, 'User-Agent': 'minerva-importador'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            dados = json.load(r)
    except urllib.error.HTTPError as e:
        return ('recusada' if e.code in (401, 403) else f'http {e.code}'), []
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return 'sem resposta', []
    if dados.get('success') is not True:
        return 'resposta inesperada', []
    return 'ok', sorted(m['name'] for m in dados.get('result', []) if isinstance(m, dict) and str(m.get('name', '')).startswith('@cf/'))


def criptografar(texto: str, senha: str, destino: Path):
    r, w = os.pipe()
    os.write(w, senha.encode()); os.close(w)
    try:
        p = subprocess.run(['gpg', '--batch', '--quiet', '--yes', '--pinentry-mode', 'loopback', '--passphrase-fd', str(r),
                            '--symmetric', '--cipher-algo', 'AES256', '--armor', '-o', str(destino)],
                           input=texto.encode(), capture_output=True, pass_fds=(r,), timeout=60)
    finally:
        os.close(r)
    if p.returncode:
        raise SystemExit('Falha ao criptografar; o cofre original não foi alterado.')


def guardar_conta(texto: str, senha: str, conta: str) -> str:
    """Grava o Account ID na seção da Cloudflare do cofre, com cópia de segurança e conferência."""
    linhas = texto.split('\n')
    ini = next((i for i, l in enumerate(linhas) if l.lstrip().startswith('#') and 'cloudflare' in l.lower()), None)
    if ini is None:
        raise SystemExit('Seção da Cloudflare não encontrada no cofre; nada foi gravado.')
    fim = next((i for i in range(ini + 1, len(linhas)) if linhas[i].lstrip().startswith('#')), len(linhas))
    if any(conta.lower() in l.lower() for l in linhas[ini:fim]):
        return texto
    novo = '\n'.join(linhas[:ini + 1] + [f'- **Account ID:** `{conta}`'] + linhas[ini + 1:])
    tmp = COFRE.with_suffix('.asc.novo')
    criptografar(novo, senha, tmp)
    if descriptografar_arquivo(tmp, senha) != novo:
        tmp.unlink(missing_ok=True)
        raise SystemExit('A conferência do cofre novo falhou; o original não foi alterado.')
    import shutil, time
    backup = COFRE.with_name(COFRE.name + '.bak-' + time.strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(COFRE, backup); backup.chmod(0o600)
    tmp.chmod(0o600); tmp.replace(COFRE)
    print(f'Account ID gravado no cofre (cópia anterior: {backup.name}).')
    return novo


def chamar(caminho: str, corpo=None, token=None):
    req = urllib.request.Request(MINERVA + caminho, data=None if corpo is None else json.dumps(corpo).encode(),
                                 headers={'Content-Type': 'application/json', **({'Authorization': 'Bearer ' + token} if token else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def salvar(prontas: dict[str, str], conta: str | None = None, modelos: dict[str, list[str]] | None = None):
    try:
        token = chamar('/api/v1/auths/signin', {'email': 'admin@localhost', 'password': 'admin'})['token']
        cfg = chamar('/openai/config', token=token)
    except (urllib.error.URLError, KeyError, OSError):
        raise SystemExit('Não consegui falar com a Minerva em ' + MINERVA + '. Abra o app e tente de novo.')
    urls, keys, confs = list(cfg['OPENAI_API_BASE_URLS']), list(cfg['OPENAI_API_KEYS']), dict(cfg['OPENAI_API_CONFIGS'])
    keys += [''] * (len(urls) - len(keys))
    for pid, chave in prontas.items():
        base = PROVEDORES[pid][1].format(conta=conta).rstrip('/')
        idx = next((i for i, u in enumerate(urls) if u.rstrip('/') == base), None)
        if idx is None:
            urls.append(base); keys.append(chave); idx = len(urls) - 1
        else:
            keys[idx] = chave
        atual = confs.get(str(idx), {})
        confs[str(idx)] = {**atual, 'enable': True, 'prefix_id': atual.get('prefix_id') or pid, 'connection_type': 'external',
                           'auth_type': 'bearer', 'tags': atual.get('tags', []), 'model_ids': (modelos or {}).get(pid) or atual.get('model_ids', [])}
    chamar('/openai/config/update', {'ENABLE_OPENAI_API': True, 'OPENAI_API_BASE_URLS': urls,
                                     'OPENAI_API_KEYS': keys, 'OPENAI_API_CONFIGS': confs}, token)


def diagnostico(texto: str):
    """Mostra a estrutura (títulos e tamanhos), nunca o valor das chaves."""
    titulo = '(antes do primeiro título)'
    achados: dict[str, list[str]] = {}
    for linha in texto.splitlines():
        if linha.lstrip().startswith('#'):
            titulo = linha.strip()
            continue
        for c in re.findall(r'`([!-~]{8,})`', linha):
            if c.lower() not in IGNORAR and not NOME_ENV.fullmatch(c) and not c.startswith('http'):
                achados.setdefault(titulo, []).append(f'{len(c)} car.')
    for t, v in achados.items():
        print(f'  {t}  ->  {len(v)} chave(s): {", ".join(v)}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--simular', action='store_true', help='só valida as chaves; não salva na Minerva')
    ap.add_argument('--so', help='processa só estes provedores (ex.: cloudflare ou groq,gemini)')
    ap.add_argument('--cloudflare-conta', help='Account ID da Cloudflare (32 caracteres hexadecimais); também é gravado no cofre')
    ap.add_argument('--diagnostico', action='store_true', help='mostra títulos e tamanhos do cofre, sem as chaves')
    args = ap.parse_args()
    if not COFRE.exists():
        raise SystemExit(f'Cofre não encontrado: {COFRE}')
    senha = getpass.getpass('Senha do cofre: ')
    texto = descriptografar(senha)
    if args.diagnostico:
        print()
        diagnostico(texto)
        raise SystemExit(0)
    conta = args.cloudflare_conta
    if conta and not HEX32.fullmatch(conta):
        raise SystemExit('Account ID inválido: deve ter 32 caracteres hexadecimais.')
    if conta:
        texto = guardar_conta(texto, senha, conta.lower())
    chaves, avisos, outros = extrair(texto)
    del texto, senha
    conta = (conta or chaves.pop('conta', None) or '').lower() or None
    chaves.pop('conta', None)
    if args.so:
        chaves = {p: c for p, c in chaves.items() if p in {x.strip() for x in args.so.split(',')}}
    if 'cloudflare' in chaves and not conta:
        print('Cloudflare: falta o Account ID (use --cloudflare-conta).')
        del chaves['cloudflare']
    print(f'\nChaves reconhecidas: {len(chaves)}\n')
    prontas: dict[str, str] = {}
    modelos: dict[str, list[str]] = {}
    for pid, chave in chaves.items():
        nome, url = PROVEDORES[pid][0], PROVEDORES[pid][1]
        if pid == 'cloudflare':
            estado, modelos[pid] = testar_cloudflare(conta, chave)
            if estado == 'ok':
                estado = f'ok ({len(modelos[pid])} modelos de texto)'
        else:
            estado = testar(url, chave)
        print(f'  {nome:<22} {len(chave):>3} caracteres   {estado}')
        if estado != 'recusada' and (pid != 'cloudflare' or estado.startswith('ok')):
            prontas[pid] = chave
    if outros:
        print('\nEncontrados, mas não são de chat (ficam de fora): ' + ', '.join(outros))
    for motivo, linha in avisos:
        print(f'\n  ! {motivo}: {linha}')
    if not prontas:
        raise SystemExit('\nNada para salvar.')
    if args.simular:
        raise SystemExit('\nModo simulação: nada foi salvo.')
    if input(f'\nSalvar {len(prontas)} conexão(ões) na Minerva? [s/N] ').strip().lower() not in ('s', 'sim'):
        raise SystemExit('Cancelado; nada foi salvo.')
    salvar(prontas, conta, modelos)
    print('Pronto. Abra Configurações > Conexões (admin) ou o seletor de modelos para ver os modelos.')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit('\nCancelado.')
