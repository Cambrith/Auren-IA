"""Canva authorization code + PKCE, with a bounded loopback callback and vault-only tokens."""
import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit, parse_qs, urlencode
import httpx
from integration.auren_credentials import AurenVault, LOCK

DEFAULT_REDIRECT = 'http://127.0.0.1:8176/oauth/canva/callback'
_active = None


def redirect_address(uri):
    u = urlsplit(uri)
    if (u.scheme != 'http' or u.hostname not in ('127.0.0.1','localhost') or u.username or u.password
            or u.query or u.fragment or not u.port or not 1024 <= u.port <= 65535
            or u.path != '/oauth/canva/callback'):
        raise ValueError('Cadastre uma Redirect URL HTTP local com a rota /oauth/canva/callback.')
    return u


def store_tokens(vault, payload):
    if not all(isinstance(payload.get(k),str) and payload[k] for k in ('access_token','refresh_token')):
        raise ValueError('Resposta OAuth inválida.')
    expires = int(payload.get('expires_in',0))
    if expires <= 0: raise ValueError('Expiração OAuth inválida.')
    values = {'CANVA_ACCESS_TOKEN':payload['access_token'],'CANVA_REFRESH_TOKEN':payload['refresh_token'],
              'CANVA_TOKEN_EXPIRES_AT':str(int(time.time())+expires)}
    with LOCK:
        before = {k:vault.get(k) for k in values}
        try:
            for k,v in values.items():
                vault.set(k,v)
                if vault.get(k) != v: raise OSError('Não foi possível salvar o token OAuth.')
        except OSError:
            for k,v in before.items():
                if v: vault.set(k,v)
                else: vault.delete(k)
            raise


def access_token(vault):
    with LOCK:
        token = vault.get('CANVA_ACCESS_TOKEN')
        if not token: return ''
        try: valid = float(vault.get('CANVA_TOKEN_EXPIRES_AT')) > time.time()+30
        except ValueError: valid = False
        if valid: return token
        refresh = vault.get('CANVA_REFRESH_TOKEN')
        if not refresh: return ''
        try:
            with httpx.Client(trust_env=False,timeout=15) as client:
                response = client.post('https://api.canva.com/rest/v1/oauth/token',
                    auth=(vault.get('CANVA_CLIENT_ID'),vault.get('CANVA_CLIENT_SECRET')),
                    data={'grant_type':'refresh_token','refresh_token':refresh})
            if response.status_code != 200: return ''
            payload = response.json(); store_tokens(vault,payload)
            return payload['access_token']
        except (httpx.HTTPError,ValueError,KeyError): return ''


def start(backend=None):
    global _active
    vault = backend or AurenVault()
    client_id, secret, uri = [vault.get(n) for n in ('CANVA_CLIENT_ID','CANVA_CLIENT_SECRET','CANVA_REDIRECT_URI')]
    if not all((client_id,secret,uri)): raise ValueError('Configure Client ID, client secret e Redirect URL no Canva.')
    address = redirect_address(uri)
    verifier, state = secrets.token_urlsafe(64), secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    completed = threading.Event()

    class Callback(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            parsed = urlsplit(self.path); params = parse_qs(parsed.query)
            valid = (self.headers.get('Host') == address.netloc and parsed.path == address.path
                     and hmac.compare_digest(params.get('state',[''])[0],state))
            ok = False
            if valid and not completed.is_set():
                completed.set()
                try:
                    if params.get('code') and not params.get('error'):
                        with httpx.Client(trust_env=False,timeout=15) as client:
                            response = client.post('https://api.canva.com/rest/v1/oauth/token',auth=(client_id,secret),
                                data={'grant_type':'authorization_code','code':params['code'][0],
                                      'code_verifier':verifier,'redirect_uri':uri})
                        if response.status_code == 200:
                            store_tokens(vault,response.json()); ok = True
                except (httpx.HTTPError,OSError,ValueError,KeyError,TypeError): pass
            message = 'Canva autorizado. Volte à Auren e valide a conexão.' if ok else 'Autorização não concluída. Volte à Auren.'
            body = ('<!doctype html><meta charset="utf-8"><script>history.replaceState(null,"","/oauth/canva/callback")</script><p>'+message+'</p>').encode()
            self.send_response(200 if ok else 400)
            self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store'); self.send_header('Referrer-Policy','no-referrer')
            self.end_headers(); self.wfile.write(body)

    with LOCK:
        if _active and _active.is_alive(): raise ValueError('Uma autorização Canva já está em andamento.')
        server = HTTPServer(('127.0.0.1',address.port),Callback); server.timeout=1
        def listen():
            deadline = time.monotonic()+600
            try:
                while time.monotonic() < deadline and not completed.is_set(): server.handle_request()
            finally: server.server_close()
        _active = threading.Thread(target=listen,daemon=True,name='canva-oauth'); _active.start()
    return {'url':'https://www.canva.com/api/oauth/authorize?'+urlencode({'response_type':'code','client_id':client_id,
            'redirect_uri':uri,'scope':'profile:read','code_challenge':challenge,'code_challenge_method':'S256','state':state})}
