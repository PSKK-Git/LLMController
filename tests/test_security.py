from llmcontroller.auth.security import KEY_PREFIX, generate_api_key, hash_api_key


def test_hash_is_deterministic():
    assert hash_api_key("sk-abc") == hash_api_key("sk-abc")


def test_hash_is_64_hex_chars():
    h = hash_api_key("sk-abc")
    assert len(h) == 64
    int(h, 16)  # raises if not hex


def test_generate_returns_prefixed_key_and_matching_hash():
    plaintext, key_hash = generate_api_key()
    assert plaintext.startswith(KEY_PREFIX)
    assert key_hash == hash_api_key(plaintext)


def test_generated_keys_are_unique():
    k1, _ = generate_api_key()
    k2, _ = generate_api_key()
    assert k1 != k2
