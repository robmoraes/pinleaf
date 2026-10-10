from __future__ import annotations

import unittest

from pinleaf.models import Group
from pinleaf.organization import OrganizationError, group_label, name_key, validate_name


class OrganizationNameTests(unittest.TestCase):
    def test_unicode_keys_and_original_spelling(self) -> None:
        self.assertEqual(name_key(' Café '), name_key('CAFE\u0301'))
        self.assertEqual(name_key('Straße'), name_key('STRASSE'))
        self.assertEqual(validate_name('  Café  '), ('Café', 'café'))

    def test_boundaries_and_reserved_group_names(self) -> None:
        self.assertEqual(validate_name('G' * 80)[0], 'G' * 80)
        for name in (' ', 'G' * 81, 'General', ' GERAL '):
            with self.subTest(name=name), self.assertRaises(OrganizationError):
                validate_name(name, group=True)

    def test_general_label_does_not_change_identity_or_custom_name(self) -> None:
        group = Group('stable', 'profile', 'General', True)
        self.assertEqual(group_label(group, 'pt-BR'), 'Geral')
        self.assertEqual(group_label(group, 'en'), 'General')
        custom = Group('custom', 'profile', 'Minha Lista', False)
        self.assertEqual(group_label(custom, 'en'), 'Minha Lista')
