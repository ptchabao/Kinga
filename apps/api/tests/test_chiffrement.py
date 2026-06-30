from services.chiffrement import encrypt_seed, decrypt_seed


def test_round_trip_aes_gcm():
    seed = "demo-seed-123"
    encrypted = encrypt_seed(seed)
    assert encrypted.startswith("aes:")
    assert decrypt_seed(encrypted) == seed
