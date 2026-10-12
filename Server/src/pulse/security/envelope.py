"""
src/pulse/security/envelope.py

Envelope encryption for sensitive payloads.
Generates an ephemeral single-use Data Encryption Key (DEK) per payload,
encrypts the payload using AES-256-GCM, and wraps the DEK under a Key Encryption Key (KEK).
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from .crypto import CryptoEngine


@dataclass(frozen=True)
class EncryptedEnvelope:
    encrypted_dek_b64: str
    dek_nonce_b64: str
    ciphertext_b64: str
    payload_nonce_b64: str


class EnvelopeEncryptor:
    def __init__(self, kek: bytes) -> None:
        if len(kek) != 32:
            raise ValueError(f"KEK must be exactly 32 bytes, got {len(kek)}")
        self.kek = kek

    def encrypt_payload(self, plaintext: bytes) -> EncryptedEnvelope:
        # Generate single-use ephemeral DEK
        dek = os.urandom(32)

        # Encrypt plaintext under DEK
        p_nonce, p_ciphertext = CryptoEngine.encrypt_aes_gcm(dek, plaintext)

        # Wrap DEK under KEK
        dek_nonce, wrapped_dek = CryptoEngine.encrypt_aes_gcm(self.kek, dek)

        return EncryptedEnvelope(
            encrypted_dek_b64=base64.b64encode(wrapped_dek).decode("ascii"),
            dek_nonce_b64=base64.b64encode(dek_nonce).decode("ascii"),
            ciphertext_b64=base64.b64encode(p_ciphertext).decode("ascii"),
            payload_nonce_b64=base64.b64encode(p_nonce).decode("ascii"),
        )

    def decrypt_payload(self, envelope: EncryptedEnvelope) -> bytes:
        wrapped_dek = base64.b64decode(envelope.encrypted_dek_b64)
        dek_nonce = base64.b64decode(envelope.dek_nonce_b64)
        p_ciphertext = base64.b64decode(envelope.ciphertext_b64)
        p_nonce = base64.b64decode(envelope.payload_nonce_b64)

        # Unwrap DEK
        dek = CryptoEngine.decrypt_aes_gcm(self.kek, dek_nonce, wrapped_dek)

        # Decrypt payload
        return CryptoEngine.decrypt_aes_gcm(dek, p_nonce, p_ciphertext)
