"""
src/pulse/security/crypto.py

Vetted cryptographic primitives using standard PyCA cryptography library:
  - Ed25519 digital signatures and verification
  - X25519 key exchange + HKDF-SHA256 key derivation
  - AES-256-GCM authenticated encryption (AEAD) with 96-bit unique nonces
"""

from __future__ import annotations

import os
from typing import Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

from ..core.errors import SignatureVerificationError, AuthenticationError


class CryptoEngine:
    """
    Standard vetted cryptographic operations.
    """

    # --- Ed25519 Digital Signatures ---
    @staticmethod
    def generate_ed25519_keypair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        priv = ed25519.Ed25519PrivateKey.generate()
        pub = priv.public_key()
        return priv, pub

    @staticmethod
    def sign_ed25519(private_key: ed25519.Ed25519PrivateKey, data: bytes) -> bytes:
        return private_key.sign(data)

    @staticmethod
    def verify_ed25519(public_key: ed25519.Ed25519PublicKey, signature: bytes, data: bytes) -> bool:
        try:
            public_key.verify(signature, data)
            return True
        except InvalidSignature:
            raise SignatureVerificationError("Ed25519 signature verification failed")

    # --- X25519 Key Agreement & HKDF Key Derivation ---
    @staticmethod
    def generate_x25519_keypair() -> Tuple[x25519.X25519PrivateKey, x25519.X25519PublicKey]:
        priv = x25519.X25519PrivateKey.generate()
        pub = priv.public_key()
        return priv, pub

    @staticmethod
    def derive_shared_secret(
        private_key: x25519.X25519PrivateKey,
        peer_public_key: x25519.X25519PublicKey,
        salt: bytes | None = None,
        info: bytes = b"pulse-v1-session-key",
    ) -> bytes:
        """
        Derive 32-byte (256-bit) shared symmetric key using X25519 + HKDF-SHA256.
        """
        raw_shared = private_key.exchange(peer_public_key)
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt or b"pulse-salt-v1",
            info=info,
        )
        return hkdf.derive(raw_shared)

    # --- AES-256-GCM AEAD Encryption ---
    @staticmethod
    def encrypt_aes_gcm(key: bytes, plaintext: bytes, associated_data: bytes | None = None) -> Tuple[bytes, bytes]:
        """
        Encrypt plaintext using AES-256-GCM with a fresh random 96-bit (12-byte) nonce.
        Returns:
            Tuple of (nonce, ciphertext_with_tag)
        """
        if len(key) != 32:
            raise ValueError(f"AES-256 key must be exactly 32 bytes, got {len(key)}")
        nonce = os.urandom(12)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce, ciphertext

    @staticmethod
    def decrypt_aes_gcm(key: bytes, nonce: bytes, ciphertext: bytes, associated_data: bytes | None = None) -> bytes:
        """
        Decrypt ciphertext using AES-256-GCM.
        Raises AuthenticationError if tag or ciphertext has been tampered with.
        """
        if len(key) != 32:
            raise ValueError(f"AES-256 key must be exactly 32 bytes, got {len(key)}")
        if len(nonce) != 12:
            raise ValueError(f"AES-GCM nonce must be 12 bytes, got {len(nonce)}")
        aesgcm = AESGCM(key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, associated_data)
        except Exception as exc:
            raise AuthenticationError(f"AEAD decryption failed; ciphertext or tag tampered: {str(exc)}")
