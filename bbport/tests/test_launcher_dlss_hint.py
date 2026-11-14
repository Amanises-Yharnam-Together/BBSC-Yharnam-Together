"""The DLSS note in Graphics names the install's bin folder and says which DLSS files are missing there. It said
'next to the game', and a v1.2.1 player looked for them in his Bloodborne game folder."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))

if sys.platform in ('win32', 'linux'):
    import bbport_launcher_win as launcher


@unittest.skipUnless(sys.platform == 'win32', 'the Windows launcher')
class DlssFilesHintTests(unittest.TestCase):
    def install(self, files):
        root = Path(tempfile.mkdtemp())
        (root / 'bin').mkdir()
        for name in files:
            (root / 'bin' / name).write_bytes(b'')
        return root

    def test_all_files_present_names_the_bin_folder(self):
        root = self.install(launcher.DLSS_FILES)
        hint = launcher.dlss_files_hint(root)
        self.assertIn(str(root / 'bin'), hint)
        self.assertIn('found', hint)
        self.assertNotIn('next to the game', hint)

    def test_missing_files_are_named(self):
        root = self.install(['bbport_dlss.dll', 'nvngx_dlss.dll'])
        hint = launcher.dlss_files_hint(root)
        self.assertIn(str(root / 'bin'), hint)
        self.assertIn('nvngx_dlssg.dll missing', hint)

    def test_files_in_the_install_root_do_not_count(self):
        root = self.install([])
        for name in launcher.DLSS_FILES:
            (root / name).write_bytes(b'')
        self.assertIn('missing', launcher.dlss_files_hint(root))


@unittest.skipUnless(sys.platform == 'linux', 'the launcher on Linux')
class DlssFilesHintLinuxTests(unittest.TestCase):
    # Linux: the .so bridge and NVIDIA's versioned libraries beside bb-probe (out/ as build.sh leaves them,
    # bin/ when packaged), never the Windows .dll names.
    def install(self, folder, files):
        root = Path(tempfile.mkdtemp())
        (root / folder).mkdir()
        for name in files:
            (root / folder / name).write_bytes(b'')
        return root

    def test_found_in_out(self):
        root = self.install('out', ['libbbport_dlss.so', 'libnvidia-ngx-dlss.so.310.9.16',
                                    'libnvidia-ngx-dlssg.so.310.9.16'])
        hint = launcher.dlss_files_hint(root)
        self.assertIn(str(root / 'out'), hint)
        self.assertIn('found', hint)
        self.assertNotIn('.dll', hint)

    def test_frame_generation_library_missing(self):
        root = self.install('out', ['libbbport_dlss.so', 'libnvidia-ngx-dlss.so.310.9.16'])
        self.assertIn('libnvidia-ngx-dlssg.so.* missing', launcher.dlss_files_hint(root))

    def test_packaged_bin_folder(self):
        root = self.install('bin', ['bb-probe', 'libbbport_dlss.so', 'libnvidia-ngx-dlss.so.1',
                                    'libnvidia-ngx-dlssg.so.1'])
        self.assertIn(str(root / 'bin'), launcher.dlss_files_hint(root))

    def test_the_side_label_names_linux(self):
        self.assertEqual(launcher.platform_text('native port · Windows'), 'native port · Linux')


if __name__ == '__main__':
    unittest.main()
