"""Pin Auren to its persistent Secret Service; never copy secrets to disk."""
import json
import os
import subprocess
import tempfile
import threading
from pathlib import Path

from cavren.credentials import SecretServiceBackend

STATE = Path(os.environ.get('LUNVRI_RUNTIME_DIR', Path(__file__).resolve().parents[1] / '.cavren'))
SERVICES = ('org.kde.secretservicecompat', 'org.freedesktop.secrets')
LOCK = threading.RLock()


def configure_vault():
    """A persisted address wins over changing login order and desktop variables."""
    with LOCK:
        path = STATE / 'credential_backend.json'
        if not path.exists():
            kde = 'kde' in os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
            service = SERVICES[0] if kde and Path('/usr/share/dbus-1/services/org.kde.secretservicecompat.service').exists() else SERVICES[1]
            STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
            fd, temporary = tempfile.mkstemp(dir=STATE, prefix='.credential-backend-')
            try:
                with os.fdopen(fd, 'w') as output:
                    json.dump({'version': 1, 'service': service}, output)
                    output.flush()
                    os.fsync(output.fileno())
                # Do not replace a choice made by another process concurrently.
                try: os.link(temporary, path)
                except FileExistsError: pass
                directory = os.open(STATE, os.O_RDONLY | os.O_DIRECTORY)
                try: os.fsync(directory)
                finally: os.close(directory)
            finally:
                os.unlink(temporary)
        try:
            data = json.loads(path.read_text())
            service = data['service']
            if data.get('version') != 1 or service not in SERVICES: raise ValueError()
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise OSError('Não foi possível identificar o cofre configurado da Auren.') from error
        # libsecret supports this override. It affects Auren and its children only.
        # Never fall back to another wallet when the chosen wallet is unavailable.
        os.environ['SECRET_SERVICE_BUS_NAME'] = service
        return service


def persistent_collection(service):
    try:
        result = subprocess.run(
            ['busctl', '--user', '--json=short', 'call', service,
             '/org/freedesktop/secrets', 'org.freedesktop.Secret.Service',
             'ReadAlias', 's', 'default'], capture_output=True, text=True, timeout=5,
        )
        collection = json.loads(result.stdout)['data'][0]
        if result.returncode or collection == '/' or collection.endswith('/session'):
            raise ValueError()
        return collection
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, IndexError, TypeError) as error:
        raise OSError('O cofre persistente não está disponível; a chave não foi alterada.') from error


class AurenVault(SecretServiceBackend):
    def __init__(self):
        self.service = configure_vault()

    def set(self, name, value):
        # A session collection loses its contents on logout. Reject it explicitly.
        persistent_collection(self.service)
        super().set(name, value)


def credential_inventory():
    try:
        data = json.loads((STATE / 'credential_inventory.json').read_text())
        return {name for name in data.get('names', []) if isinstance(name, str)}
    except (OSError, ValueError, AttributeError):
        return set()


def remember_credentials(env):
    from integration.auren_settings import atomic_json
    from integration.auren_connection_registry import VAULT_NAMES
    with LOCK:
        names = credential_inventory() | {name for name in VAULT_NAMES if env.get(name)}
        if names != credential_inventory():
            atomic_json(STATE / 'credential_inventory.json', {'version': 1, 'names': sorted(names)})
