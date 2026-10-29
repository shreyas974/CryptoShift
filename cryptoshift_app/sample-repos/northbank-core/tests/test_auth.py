import unittest

from services.auth import token_service, session_keys


class TokenServiceTest(unittest.TestCase):
    def test_round_trip(self):
        token = token_service.issue_token("cust-42")
        self.assertTrue(token_service.verify_token(token))

    def test_tampered_token_rejected(self):
        token = token_service.issue_token("cust-42")
        token["claims"] = b"sub=cust-43;ttl=900"
        self.assertFalse(token_service.verify_token(token))

    def test_session_has_key_agreement(self):
        session = session_keys.session_for("cust-42")
        self.assertIn(session["kex"], ("ECDH-P256", "X25519", "ML-KEM-768"))


if __name__ == "__main__":
    unittest.main()
