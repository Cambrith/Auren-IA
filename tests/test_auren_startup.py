"""Cold start, wallet identity and network failures without actual credentials."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from integration import auren_credentials as vault
from integration import lunvri_connections as connections
from integration import auren_settings as settings

class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.patches=[patch.object(module,'STATE',self.root) for module in (vault,connections,settings)]
        self.patches += [patch.dict(os.environ,{'XDG_CURRENT_DESKTOP':'KDE'},clear=False)]
        for p in self.patches:p.start()
        self.old=(connections._catalog,connections._updated,connections._refreshing,connections._attempted)
        connections._catalog=None;connections._updated=0;connections._refreshing=False;connections._attempted=0
    def tearDown(self):
        connections._catalog,connections._updated,connections._refreshing,connections._attempted=self.old
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()
    def pin(self):
        (self.root/'credential_backend.json').write_text(json.dumps({'version':1,'service':'org.kde.secretservicecompat'}))
    def test_pinned_wallet_survives_different_desktop_and_generic_owner(self):
        self.pin()
        with patch.dict(os.environ,{'XDG_CURRENT_DESKTOP':'GNOME','SECRET_SERVICE_BUS_NAME':'org.freedesktop.secrets'}):
            self.assertEqual(vault.configure_vault(),'org.kde.secretservicecompat')
            self.assertEqual(os.environ['SECRET_SERVICE_BUS_NAME'],'org.kde.secretservicecompat')
        self.assertEqual(vault.configure_vault(),'org.kde.secretservicecompat')
    def test_kde_first_start_persists_private_address_only(self):
        with patch.object(vault.Path,'exists',autospec=True,side_effect=lambda p: True if str(p).endswith('org.kde.secretservicecompat.service') else Path.is_file(p)):
            self.assertEqual(vault.configure_vault(),'org.kde.secretservicecompat')
        p=self.root/'credential_backend.json'
        self.assertEqual(p.stat().st_mode&0o777,0o600)
        self.assertEqual(set(json.loads(p.read_text())),{'version','service'})
    def test_corrupted_pin_fails_closed_instead_of_switching_wallet(self):
        (self.root/'credential_backend.json').write_text('{bad')
        with self.assertRaises(OSError):vault.configure_vault()
    def test_session_collection_rejected_before_store(self):
        self.pin()
        result=SimpleNamespace(returncode=0,stdout=json.dumps({'data':['/org/freedesktop/secrets/collection/session']}))
        with patch.object(vault.subprocess,'run',return_value=result),patch.object(vault.SecretServiceBackend,'set') as store:
            with self.assertRaises(OSError):vault.AurenVault().set('TEST','synthetic')
            store.assert_not_called()
    def test_missing_collection_rejected_before_store(self):
        for path in ['/','/org/freedesktop/secrets/collection/session']:
            with patch.object(vault.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps({'data':[path]}))):
                with self.assertRaises(OSError):vault.persistent_collection('org.kde.secretservicecompat')
    def test_inventory_records_names_only_and_does_not_expire(self):
        vault.remember_credentials({'COHERE_API_KEY':'synthetic-secret'})
        p=self.root/'credential_inventory.json';before=p.read_text()
        vault.remember_credentials({})
        self.assertEqual(before,p.read_text());self.assertNotIn('synthetic-secret',before)
        self.assertEqual(p.stat().st_mode&0o777,0o600)
    def snapshot(self):
        m=connections.model_entry('cavren:cohere:example',{'label':'Example','provider':'cohere','capabilities':{'image_generation':False}})
        data={'models':[m],'providers':{'cohere':{'connected':True,'count':1}},'updated':1}
        (self.root/'models.json').write_text(json.dumps(data));return m
    def test_cold_start_uses_old_disk_snapshot_without_waiting_for_network(self):
        m=self.snapshot()
        with patch.object(connections.threading,'Thread') as thread,patch.object(connections,'connection_settings') as config,patch.object(connections,'validated_catalog',side_effect=lambda m:m):
            start=time.monotonic(); result=connections.catalog()
            self.assertLess(time.monotonic()-start,.1);self.assertEqual(result,[m])
            config.assert_not_called();thread.return_value.start.assert_called_once()
    def test_in_progress_refresh_does_not_block_read(self):
        m=self.snapshot();connections._catalog=[m];connections._refreshing=True
        with patch.object(connections,'validated_catalog',side_effect=lambda m:m):self.assertEqual(connections.catalog(),[m])
    def test_failed_provider_preserves_model_metadata(self):
        m=self.snapshot();connections._catalog=[m]
        config=SimpleNamespace(providers={'cohere':SimpleNamespace(api_key='synthetic')})
        with patch.object(connections,'connection_settings',return_value=config),patch.object(connections.CavrenHandler,'_integrated_models',return_value=[]),patch.object(connections,'discover',return_value=([],{'connected':False,'status':'unavailable'})),patch.object(connections,'validated_catalog',side_effect=lambda m:m):
            result=connections.catalog(refresh=True)
        self.assertIn(m,result)
        self.assertEqual(json.loads((self.root/'models.json').read_text())['providers']['cohere']['status'],'unavailable')
    def test_temporarily_unreadable_key_preserves_model_and_saved_state(self):
        m=self.snapshot();connections._catalog=[m]
        with patch.object(connections,'connection_settings',return_value=SimpleNamespace(providers={})),patch.object(connections.CavrenHandler,'_integrated_models',return_value=[]),patch.object(connections,'validated_catalog',side_effect=lambda m:m):connections.catalog(refresh=True)
        with patch.object(settings,'catalog',return_value=[m]),patch.object(settings,'connection_settings',side_effect=OSError('locked')):
            state=settings.public_state()
        c=next(c for c in state['connections'] if c['id']=='cohere')
        self.assertTrue(c['credential_saved']);self.assertEqual(c['state'],'vault_unavailable')
    def test_vault_error_does_not_replace_disk_snapshot(self):
        self.snapshot();before=(self.root/'models.json').read_text()
        with patch.object(connections,'connection_settings',side_effect=OSError('locked')):connections._catalog_background()
        self.assertEqual(before,(self.root/'models.json').read_text());self.assertFalse(connections._refreshing)

if __name__=='__main__':unittest.main()
