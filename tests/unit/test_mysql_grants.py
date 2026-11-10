"""Privilege checks must understand literal underscores without widening scope."""
import unittest


class MySQLGrantTests(unittest.TestCase):
    def test_literal_schema_escape_and_privilege_union(self):
        from aat_etl.loaders.privileges import mysql_permissions
        grants=[r"GRANT SELECT, INSERT ON `etl\_test`.* TO `fixture`@`%`",
                r"GRANT UPDATE, TRIGGER ON `etl\_test`.`target` TO `fixture`@`%`"]
        self.assertTrue({'INSERT','UPDATE','TRIGGER'}<=mysql_permissions(grants,'etl_test','target'))
        self.assertNotIn('UPDATE',mysql_permissions(grants,'etl_test','other'))
        self.assertFalse(mysql_permissions(grants,'etlXtest','target'))
        self.assertFalse(mysql_permissions(grants,'etl_test_extra','target'))
        self.assertFalse(mysql_permissions(["GRANT ALL PRIVILEGES ON `etl%`.* TO `fixture`@`%`"],'etl_test','target'))
        self.assertIn('DELETE',mysql_permissions(["GRANT ALL PRIVILEGES ON *.* TO `fixture`@`%`"],'etl_test','target'))
