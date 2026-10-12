"""
tests/unit/test_crypto_security.py

Unit tests for cryptographic primitives and security mechanisms:
  - Ed25519 digital signatures and tampered signature rejection
  - X25519 + HKDF-SHA256 key derivation
  - AES-256-GCM authenticated encryption and tampered ciphertext rejection
  - TokenManager short-lived tokens, expiration, and signature tampering
  - ReplayGuard nonce duplicate detection and drift rejection
  - Envelope encryption round-trips
"""

import time
import os
import pytest

from pulse.security.crypto import CryptoEngine
from pulse.security.tokens import TokenManager
from pulse.security.replay_guard import ReplayGuard
from pulse.security.envelope import EnvelopeEncryptor
from pulse.core.errors import (
    SignatureVerificationError,
    AuthenticationError,
    ReplayAttackError,
)


class TestCryptoEngine:
    def test_ed25519_sign_verify_and_tamper(self):
        priv, pub = CryptoEngine.generate_ed25519_keypair()
        message = b"Canonical Pulse Message"
        sig = CryptoEngine.sign_ed25519(priv, message)

        # Verify valid signature
        assert CryptoEngine.verify_ed25519(pub, sig, message) is True

        # Tampered message
        with pytest.raises(SignatureVerificationError):
            CryptoEngine.verify_ed25519(pub, sig, b"Tampered Message")

        # Tampered signature
        tampered_sig = bytearray(sig)
        tampered_sig[0] ^= 0xFF
        with pytest.raises(SignatureVerificationError):
            CryptoEngine.verify_ed25519(pub, bytes(tampered_sig), message)

    def test_x25519_hkdf_key_agreement(self):
        priv_a, pub_a = CryptoEngine.generate_x25519_keypair()
        priv_b, pub_b = CryptoEngine.generate_x25519_keypair()

        shared_a = CryptoEngine.derive_shared_secret(priv_a, pub_b)
        shared_b = CryptoEngine.derive_shared_secret(priv_b, pub_a)

        assert len(shared_a) == 32
        assert shared_a == shared_b

    def test_aes_256_gcm_aead_and_tampered_ciphertext(self):
        key = os.urandom(32)
        plaintext = b"Confidential dataset record bytes"
        ad = b"associated_metadata"

        nonce, ciphertext = CryptoEngine.encrypt_aes_gcm(key, plaintext, ad)
        decrypted = CryptoEngine.decrypt_aes_gcm(key, nonce, ciphertext, ad)
        assert decrypted == plaintext

        # Tampered ciphertext
        tampered = bytearray(ciphertext)
        tampered[0] ^= 0x01
        with pytest.raises(AuthenticationError, match="AEAD decryption failed"):
            CryptoEngine.decrypt_aes_gcm(key, nonce, bytes(tampered), ad)

        # Tampered associated data
        with pytest.raises(AuthenticationError):
            CryptoEngine.decrypt_aes_gcm(key, nonce, ciphertext, b"tampered_ad")


class TestTokenManager:
    def test_token_issue_and_verify(self):
        secret = os.urandom(32)
        tm = TokenManager(secret, default_ttl_seconds=300)
        token = tm.issue_token("test_principal", claims={"role": "engineer"})

        claims = tm.verify_token(token)
        assert claims["sub"] == "test_principal"
        assert claims["claims"]["role"] == "engineer"

    def test_token_expiration(self):
        secret = os.urandom(32)
        # 1-second TTL
        tm = TokenManager(secret, default_ttl_seconds=1)
        token = tm.issue_token("expiring_user", ttl_seconds=-10) # Expired in past

        with pytest.raises(AuthenticationError, match="expired"):
            tm.verify_token(token)

    def test_tampered_token_signature(self):
        secret = os.urandom(32)
        tm = TokenManager(secret)
        token = tm.issue_token("user_1")
        parts = token.split(".")
        tampered_token = f"{parts[0]}.invalid_signature"

        with pytest.raises(AuthenticationError):
            tm.verify_token(tampered_token)


class TestReplayGuard:
    def test_replay_protection_sliding_window(self):
        guard = ReplayGuard(window_seconds=10.0)
        now = time.time()
        nonce = "unique_nonce_1"

        # First request succeeds
        guard.validate_and_record(nonce, now)

        # Duplicate request with same nonce fails
        with pytest.raises(ReplayAttackError, match="Duplicate nonce"):
            guard.validate_and_record(nonce, now)

        # Stale timestamp beyond window fails
        with pytest.raises(ReplayAttackError, match="drift"):
            guard.validate_and_record("stale_nonce", now - 20.0)


class TestEnvelopeEncryption:
    def test_envelope_roundtrip(self):
        kek = os.urandom(32)
        encryptor = EnvelopeEncryptor(kek)
        secret_data = b"Deep Secret Dataset Spec"

        envelope = encryptor.encrypt_payload(secret_data)
        assert envelope.encrypted_dek_b64 != ""
        assert envelope.ciphertext_b64 != ""

        decrypted = encryptor.decrypt_payload(envelope)
        assert decrypted == secret_data
