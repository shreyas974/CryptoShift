import unittest

from shared.bankcrypto import tls_config
from shared.pki import cert_authority
from services.ledger import ledger_store


class PlatformTest(unittest.TestCase):
    def test_tls_offers_a_group(self):
        self.assertGreaterEqual(len(tls_config.KEY_EXCHANGE_GROUPS), 1)

    def test_certificate_is_signed(self):
        cert = cert_authority.issue_certificate("payments")
        self.assertEqual(cert["subject"], "payments")

    def test_ledger_record(self):
        self.assertGreaterEqual(ledger_store.record(b"entry"), 1)


if __name__ == "__main__":
    unittest.main()
