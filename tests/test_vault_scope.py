# tests/test_vault_scope.py
# [TEST-VAULT-SCOPE] reveal() is scoped to one protect() call, single use and time limited. The case that
#   matters: two users share a vault, user B's text echoes user A's token, and B must not get A's value back.

import time
import unittest

import tarja
from tarja import (
    ProtectedText,
    Vault,
    VaultConsumedError,
    VaultExpiredError,
    VaultScopeError,
)

CPF_A = "529.982.247-25"
CPF_B = "111.444.777-35"


class TestScope(unittest.TestCase):
    # [TEST-SCOPE-CROSS] the threat this feature exists for
    def test_echoed_token_from_another_user_does_not_resolve(self):
        v = Vault()
        a = v.protect(f"cpf do cliente {CPF_A}")
        b = v.protect(f"cpf do cliente {CPF_B}")
        leaked = next(iter(a.tokens))
        # user B's answer smuggles user A's token
        answer = f"segue o dado: {leaked}"
        self.assertEqual(v.reveal(answer, issued_by=b), answer)
        # and A still gets their own value back
        self.assertIn(CPF_A, v.reveal(f"ok {leaked}", issued_by=a))

    def test_protected_text_is_a_str(self):
        v = Vault()
        prot = v.protect(f"cpf {CPF_A}")
        self.assertIsInstance(prot, str)
        self.assertIsInstance(prot, ProtectedText)
        self.assertEqual(prot, str(prot))
        self.assertNotIn(CPF_A, prot)

    def test_round_trip_without_issued_by(self):
        # the protected text itself carries its scope, so the simple case stays simple
        v = Vault()
        text = f"cpf {CPF_A}"
        self.assertEqual(v.reveal(v.protect(text)), text)

    def test_plain_string_needs_a_scope(self):
        v = Vault()
        prot = v.protect(f"cpf {CPF_A}")
        with self.assertRaises(VaultScopeError):
            v.reveal(f"resposta do modelo: {prot}")

    def test_any_token_opts_out(self):
        v = Vault()
        prot = v.protect(f"cpf {CPF_A}")
        self.assertIn(CPF_A, v.reveal(f"resposta: {prot}", any_token=True))

    def test_scope_from_another_vault_is_refused(self):
        a, b = Vault(), Vault()
        prot = a.protect(f"cpf {CPF_A}")
        with self.assertRaises(VaultScopeError):
            b.reveal("texto", issued_by=prot)

    def test_tokens_property(self):
        v = Vault()
        prot = v.protect(f"cpf {CPF_A} e cpf {CPF_B}")
        self.assertEqual(len(prot.tokens), 2)


class TestSingleUse(unittest.TestCase):
    # [TEST-SCOPE-ONCE]
    def test_second_reveal_raises(self):
        v = Vault()
        prot = v.protect(f"cpf {CPF_A}")
        v.reveal(prot)
        with self.assertRaises(VaultConsumedError):
            v.reveal(prot)

    def test_reuse_allows_it(self):
        v = Vault()
        text = f"cpf {CPF_A}"
        prot = v.protect(text)
        v.reveal(prot)
        self.assertEqual(v.reveal(prot, reuse=True), text)

    def test_any_token_does_not_consume(self):
        v = Vault()
        prot = v.protect(f"cpf {CPF_A}")
        v.reveal(prot, any_token=True)
        self.assertIn(CPF_A, v.reveal(prot))


class TestExpiry(unittest.TestCase):
    # [TEST-SCOPE-TTL]
    def test_expired_scope_raises(self):
        v = Vault(ttl=0.0)
        prot = v.protect(f"cpf {CPF_A}")
        time.sleep(0.01)
        with self.assertRaises(VaultExpiredError):
            v.reveal(prot)

    def test_ttl_none_never_expires(self):
        v = Vault(ttl=None)
        text = f"cpf {CPF_A}"
        prot = v.protect(text)
        self.assertEqual(v.reveal(prot), text)

    def test_per_call_ttl_overrides_the_vault(self):
        v = Vault(ttl=0.0)
        text = f"cpf {CPF_A}"
        self.assertEqual(v.reveal(v.protect(text, ttl=None)), text)

    def test_default_ttl_is_an_hour(self):
        from tarja.vault import DEFAULT_TTL

        self.assertEqual(DEFAULT_TTL, 3600.0)


class TestStillWorks(unittest.TestCase):
    # [TEST-SCOPE-REGRESSION] the scope must not change what protect() writes
    def test_residual_finds_nothing_after_protect(self):
        v = Vault()
        self.assertEqual(tarja.residual(v.protect(f"cpf {CPF_A}, cpf {CPF_B}")), [])

    def test_same_value_same_token_across_calls(self):
        v = Vault()
        a = v.protect(f"cpf {CPF_A}")
        b = v.protect(f"o cpf {CPF_A} de novo")
        self.assertEqual(a.tokens, b.tokens)


if __name__ == "__main__":
    unittest.main()
