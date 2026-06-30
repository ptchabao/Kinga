"""
Kinga — Service de chiffrement AES-256-GCM pour les seeds de masquage.

Le seed de chaque MaskingRuleSet est chiffré avec une clé symétrique AES-256-GCM
stockée dans la variable d'environnement ENCRYPTION_KEY.
Les administrateurs ne voient jamais le seed en clair.
Seul le service de brouillage peut le déchiffrer au moment du masquage.

Historique :
  - v1 : chiffrement XOR (dev uniquement) — OBSOLÈTE
  - v2 : AES-256-GCM via le package `cryptography` — PRODUCTION READY
"""

import os
import secrets
import hashlib
import base64

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ─── CONFIGURATION ──────────────────────────────────────────────
_ENV_KEY = os.environ.get("ENCRYPTION_KEY", "kinga-dev-local-fallback-key-do-not-use-in-prod")

# Salt fixe pour PBKDF2 (constant par déploiement — changeable via env)
_PBKDF2_SALT = os.environ.get("ENCRYPTION_SALT", "kinga-pbkdf2-salt-2026").encode("utf-8")
_PBKDF2_ITERATIONS = 480_000  # OWASP 2024 recommendation for SHA-256


def _derive_key(passphrase: str) -> bytes:
    """Dérive une clé AES-256 (32 bytes) via PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode("utf-8"),
        _PBKDF2_SALT,
        _PBKDF2_ITERATIONS,
    )


# ─── LEGACY XOR (read-only, pour migration) ────────────────────

def _legacy_derive_key(passphrase: str) -> bytes:
    """Ancienne dérivation SHA-256 simple (v1 — XOR)."""
    return hashlib.sha256(passphrase.encode("utf-8")).digest()


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    """XOR chaque octet de data avec la clé (cyclique). Utilisé uniquement pour décrypter les anciens seeds."""
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))


def _legacy_decrypt(encrypted: str) -> str:
    """Déchiffre un seed chiffré avec l'ancien algorithme XOR (v1)."""
    key = _legacy_derive_key(_ENV_KEY)
    payload = base64.urlsafe_b64decode(encrypted.encode("utf-8"))
    nonce = payload[:16]
    ciphertext = payload[16:]
    plaintext = _xor_bytes(ciphertext, key + nonce)
    return plaintext.decode("utf-8")


def _is_legacy_format(encrypted: str) -> bool:
    """
    Heuristique pour détecter l'ancien format XOR.
    Le nouveau format AES-GCM commence par le préfixe 'aes:' en Base64.
    """
    return not encrypted.startswith("aes:")


# ─── AES-256-GCM ───────────────────────────────────────────────

def generate_seed() -> str:
    """Génère un seed aléatoire de 32 octets, retourné en hexadécimal."""
    return secrets.token_hex(32)


def encrypt_seed(seed: str) -> str:
    """
    Chiffre un seed en clair avec AES-256-GCM.
    
    Format de sortie : "aes:" + Base64(nonce_12bytes || ciphertext || tag_16bytes)
    
    Le tag GCM garantit l'intégrité et l'authenticité des données.
    """
    key = _derive_key(_ENV_KEY)
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)  # 96 bits — taille recommandée pour GCM
    plaintext = seed.encode("utf-8")
    
    # AESGCM.encrypt retourne ciphertext || tag (16 bytes)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    
    payload = nonce + ciphertext_with_tag
    encoded = base64.urlsafe_b64encode(payload).decode("utf-8")
    return f"aes:{encoded}"


def decrypt_seed(encrypted: str) -> str:
    """
    Déchiffre un seed. Supporte les deux formats :
      - Nouveau format AES-256-GCM : "aes:<base64>"
      - Ancien format XOR (v1) : base64 brut (rétrocompatibilité)
    
    Si un ancien format est détecté, le seed est déchiffré avec XOR.
    L'appelant devrait re-chiffrer le seed avec le nouveau format
    lors de la prochaine rotation.
    """
    if _is_legacy_format(encrypted):
        print("[Chiffrement] ⚠️  Détection d'un seed au format XOR legacy. "
              "Il sera re-chiffré en AES-256-GCM lors de la prochaine rotation.")
        return _legacy_decrypt(encrypted)
    
    # Nouveau format : retirer le préfixe "aes:"
    encoded = encrypted[4:]
    payload = base64.urlsafe_b64decode(encoded.encode("utf-8"))
    
    nonce = payload[:12]
    ciphertext_with_tag = payload[12:]
    
    key = _derive_key(_ENV_KEY)
    aesgcm = AESGCM(key)
    
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Échec du déchiffrement AES-256-GCM : {e}. "
                         "Vérifiez que ENCRYPTION_KEY est correcte.") from e


def mask_seed_for_display(encrypted: str) -> str:
    """
    Retourne une version masquée du seed pour l'affichage admin.
    Ex: "sk_****...a3f2"
    """
    if len(encrypted) < 12:
        return "sk_****"
    return f"sk_****...{encrypted[-4:]}"
