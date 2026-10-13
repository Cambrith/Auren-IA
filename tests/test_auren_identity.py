"""Auren icon installation and recovery; temporary files, no desktop mutations."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import auren_identity as identity


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / 'auren'
        self.root.mkdir()
        self.home = self.base / 'user'
        source = identity.ROOT.parent / 'cavren-nextchat/src/cavren/assets/hicolor'
        self.assets = self.base / 'cavren-nextchat/src/cavren/assets/hicolor'
        shutil.copytree(source, self.assets)

    def tearDown(self):
        self.temp.cleanup()

    def test_all_sizes_and_legacy_aliases_are_installed(self):
        icon, changed = identity.ensure_icons(self.home, self.root)
        self.assertTrue(changed)
        self.assertTrue(icon.is_file())
        for size in identity.SIZES:
            expected = (self.assets / f'{size}x{size}/apps/cavren.png').read_bytes()
            for name in ('auren', 'lunvri', 'cavren'):
                self.assertEqual((self.home / f'.local/share/icons/hicolor/{size}x{size}/apps/{name}.png').read_bytes(), expected)

    def test_second_install_preserves_files_and_missing_icon_recovers(self):
        icon, _ = identity.ensure_icons(self.home, self.root)
        stamp = icon.stat().st_mtime_ns
        self.assertFalse(identity.ensure_icons(self.home, self.root)[1])
        self.assertEqual(icon.stat().st_mtime_ns, stamp)
        icon.unlink()
        self.assertTrue(identity.ensure_icons(self.home, self.root)[1])
        self.assertTrue(icon.is_file())

    def test_invalid_source_does_not_replace_installed_artwork(self):
        icon, _ = identity.ensure_icons(self.home, self.root)
        previous = icon.read_bytes()
        (self.assets / '512x512/apps/cavren.png').write_bytes(b'broken')
        with self.assertRaises(OSError): identity.ensure_icons(self.home, self.root)
        self.assertEqual(icon.read_bytes(), previous)

    def test_launcher_changes_only_main_icon(self):
        p = self.base / 'Auren.desktop'
        p.write_text('[Desktop Entry]\nName=Auren\nExec=existing-command\nIcon=broken\nStartupWMClass=cavren\n[Desktop Action Extra]\nIcon=other-app\n')
        identity.update_launcher(p, Path('/absolute/auren.png'))
        text = p.read_text()
        self.assertIn('Icon=/absolute/auren.png', text)
        self.assertIn('Exec=existing-command', text)
        self.assertIn('StartupWMClass=cavren', text)
        self.assertIn('Icon=other-app', text)

    def test_new_desktop_shortcut_is_executable(self):
        p = self.base / 'Desktop/Auren.desktop'
        identity.update_launcher(p, Path('/absolute/auren.png'), '[Desktop Entry]\nType=Application\nName=Auren\nExec=command\n')
        self.assertEqual(p.stat().st_mode & 0o777, 0o755)
        self.assertIn('Icon=/absolute/auren.png', p.read_text())


if __name__ == '__main__': unittest.main()
