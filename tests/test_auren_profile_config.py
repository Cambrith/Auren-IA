"""Profile validation and persisted config against a separate temporary database."""
import datetime
import os
import tempfile
import unittest
from unittest.mock import patch
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from open_webui.models.users import UpdateProfileForm
from open_webui.models.config import Config
from pydantic import ValidationError

class ProfileTests(unittest.TestCase):
    def test_original_local_photo_and_iso_date_are_valid(self):
        form=UpdateProfileForm(name='Test User',profile_image_url='/cambrith-avatar.png',date_of_birth='2008-04-08')
        self.assertEqual(form.date_of_birth,datetime.date(2008,4,8))
    def test_rejects_invalid_dates_and_unsafe_photo_paths(self):
        for value in ['2023-02-29','2008-13-04','2999-01-01','08/04/2008']:
            with self.assertRaises(ValidationError):UpdateProfileForm(name='Test',profile_image_url='/cambrith-avatar.png',date_of_birth=value)
        for value in ['/etc/passwd','file:///private','javascript:alert(1)','/cambrith-avatar.png/../private']:
            with self.assertRaises(ValidationError):UpdateProfileForm(name='Test',profile_image_url=value)

class ConfigTests(unittest.IsolatedAsyncioTestCase):
    async def test_bridge_ephemeral_but_user_settings_persist(self):
        defaults={'openai.api_base_urls':['http://127.0.0.1:1234/v1'],'openai.api_keys':['ephemeral'],'ui.test_setting':False}
        old=(Config.DEFAULTS,Config.PERSISTENT_ENABLED,Config.OAUTH_PERSISTENT_ENABLED)
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'LUNVRI_LOCAL_PREVIEW':'1'}):
            engine=create_async_engine('sqlite+aiosqlite:///'+directory+'/test.db')
            async with engine.begin() as connection:await connection.run_sync(Config.__table__.create)
            factory=async_sessionmaker(engine,expire_on_commit=False)
            @asynccontextmanager
            async def db():
                async with factory() as session:yield session
            try:
                Config.configure(defaults=defaults)
                with patch('open_webui.models.config.get_async_db',db):
                    await Config.seed_defaults(defaults)
                    await Config.upsert({'ui.test_setting':True})
                    # A stale row from an older launch cannot replace this launch's bridge URL/key.
                    async with factory() as session:
                        session.add(Config(key='openai.api_keys',value=['stale-secret']));await session.commit()
                    self.assertEqual(await Config.get('openai.api_keys'),['ephemeral'])
                    self.assertEqual((await Config.get_all())['openai.api_keys'],['ephemeral'])
                    self.assertEqual((await Config.get_namespace('openai'))['openai.api_keys'],['ephemeral'])
                    self.assertEqual((await Config.get_many('openai.api_keys','ui.test_setting'))['openai.api_keys'],['ephemeral'])
                    # Reset in-memory defaults as a restart would.
                    Config.configure(defaults=defaults)
                    self.assertTrue(await Config.get('ui.test_setting'))
                    self.assertEqual(await Config.get('openai.api_keys'),['ephemeral'])
            finally:
                Config.DEFAULTS,Config.PERSISTENT_ENABLED,Config.OAUTH_PERSISTENT_ENABLED=old
                await engine.dispose()

if __name__=='__main__':unittest.main()
