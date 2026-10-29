import unittest

from services.payments import payment_signer, settlement_client
from services.api_gateway import gateway
from services.auth import token_service


class PaymentSignerTest(unittest.TestCase):
    def test_instruction_is_signed(self):
        signed = payment_signer.sign_instruction("A", "B", 1250)
        self.assertGreater(signed["sig"].length, 0)

    def test_settlement_network_accepts_signature(self):
        # The external settlement network rejects instructions signed with
        # algorithms it has not onboarded yet.
        algorithm = payment_signer.INSTRUCTION_KEY.algorithm
        self.assertTrue(settlement_client.accepts(algorithm), f"settlement network does not accept {algorithm}")

    def test_gateway_payment_flow(self):
        token = token_service.issue_token("cust-7")
        result = gateway.pay(token, "cust-7", "merchant-1", 999)
        self.assertEqual(result["status"], 202)


if __name__ == "__main__":
    unittest.main()
