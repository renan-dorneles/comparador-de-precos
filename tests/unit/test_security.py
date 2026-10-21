# ============================================================
# tests/unit/test_security.py
# ============================================================
"""Testes unitários de hash de senha e tokens JWT."""

from comparador_precos.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify_roundtrip(self):
        senha = "senha-super-secreta-123"
        hash_ = get_password_hash(senha)

        assert hash_ != senha
        assert verify_password(senha, hash_)

    def test_verify_rejects_wrong_password(self):
        hash_ = get_password_hash("senha-correta-123")

        assert not verify_password("senha-errada-123", hash_)

    def test_hash_is_salted(self):
        """Dois hashes da mesma senha devem ser diferentes (salt aleatório)."""
        hash1 = get_password_hash("mesma-senha")
        hash2 = get_password_hash("mesma-senha")

        assert hash1 != hash2
        assert verify_password("mesma-senha", hash1)
        assert verify_password("mesma-senha", hash2)


class TestAccessToken:
    def test_create_and_decode_token(self):
        token = create_access_token(data={"sub": "42", "email": "user@test.com"})

        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["email"] == "user@test.com"
        assert "exp" in payload

    def test_decode_invalid_token_returns_none(self):
        assert decode_access_token("token.invalido.aqui") is None

    def test_decode_tampered_token_returns_none(self):
        token = create_access_token(data={"sub": "1"})
        payload = decode_access_token(token + "x")

        assert payload is None

    def test_expired_token_returns_none(self):
        from datetime import timedelta

        token = create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(seconds=-10),
        )

        assert decode_access_token(token) is None
