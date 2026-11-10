# SPDX-FileCopyrightText: Copyright 2026 shadPS4 Emulator Project
# SPDX-License-Identifier: GPL-2.0-or-later
"""The setup never touches a player's saves (red, 2026-11-06: "I updated with the installer and lost
our save files"): it installs nothing into user\\ or a savedata folder, whatever the staged release
holds, and none of its sections deletes there; the uninstall leaves user\\ too."""
import pathlib
import re
import unittest

RELEASE = pathlib.Path(__file__).resolve().parents[1]
SAVE_PLACES = ('user', 'savedata')


def sections(iss):
    """setup.iss as {section name: its lines}, comments and blank lines left out."""
    found, name = {}, None
    for line in iss.splitlines():
        line = line.strip()
        header = re.fullmatch(r'\[(\w+)\]', line)
        if header:
            name = header.group(1)
            found.setdefault(name, [])
        elif name and line and not line.startswith(';'):
            found[name].append(line)
    return found


class SetupLeavesSaves(unittest.TestCase):
    def setUp(self):
        self.sections = sections((RELEASE / 'setup.iss').read_text(encoding='utf-8-sig'))

    def test_nothing_is_installed_into_the_saves(self):
        files = self.sections['Files']
        self.assertTrue(files)
        for line in files:
            excludes = re.search(r'Excludes: "([^"]*)"', line)
            self.assertIsNotNone(excludes, line)
            patterns = excludes.group(1).lower().split(',')
            for place in SAVE_PLACES:
                self.assertIn(f'\\{place}\\*', patterns, line)

    def test_no_section_deletes_in_the_saves(self):
        for name in ('InstallDelete', 'UninstallDelete'):
            for line in self.sections.get(name, []):
                target = re.search(r'Name: "([^"]*)"', line).group(1).lower()
                self.assertTrue(target.startswith('{autoprograms}\\') or target.startswith('{autodesktop}\\'),
                                f'[{name}] deletes outside the shortcuts: {line}')
                for place in SAVE_PLACES:
                    self.assertNotIn(place, re.split(r'[\\/]', target), line)

    def test_the_code_deletes_no_files(self):
        code = '\n'.join(self.sections['Code'])
        for call in ('DelTree', 'DeleteFile', 'RemoveDir', 'RenameFile'):
            self.assertNotIn(call, code)


if __name__ == '__main__':
    unittest.main()
