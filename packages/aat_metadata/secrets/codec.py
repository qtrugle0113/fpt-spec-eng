"""Fernet keyring được lưu tách khỏi ciphertext."""

import json
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken, MultiFernet


class SecretCodec:
    def __init__(self, keyring: Path):
        self.keyring = keyring
        try:
            self.current = json.loads((keyring / 'current.json').read_text())['key_id']
            self._fernet(self.current)
        except (OSError, KeyError, ValueError) as exc:
            raise RuntimeError('Encryption keyring unavailable; restore the original key volume') from exc

    def _fernet(self, key_id: str) -> Fernet:
        if len(key_id) != 32 or any(c not in '0123456789abcdef' for c in key_id):
            raise ValueError('Invalid encryption key identifier')
        try:
            return Fernet((self.keyring / f'{key_id}.key').read_bytes())
        except (OSError, ValueError) as exc:
            raise ValueError('Required encryption key unavailable') from exc

    def encrypt(self, plaintext: str) -> tuple[str, str]:
        return self.current, self._fernet(self.current).encrypt(plaintext.encode()).decode()

    def decrypt(self, key_id: str, ciphertext: str) -> str:
        try:
            return self._fernet(key_id).decrypt(ciphertext.encode()).decode()
        except (InvalidToken, UnicodeError) as exc:
            raise ValueError('Secret cannot be decrypted with the required key') from exc

    def rotate(self, key_id: str, ciphertext: str) -> tuple[str, str]:
        """Return a new token under the current existing key; never mutate history."""
        try:
            ring = MultiFernet([self._fernet(self.current), self._fernet(key_id)])
            return self.current, ring.rotate(ciphertext.encode()).decode()
        except (InvalidToken, UnicodeError, ValueError):
            raise ValueError('Secret cannot be rotated with the required keys') from None
