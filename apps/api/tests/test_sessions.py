from uuid import uuid4

from veriflow_api.services.sessions import hash_session_token, session_key


def test_session_token_is_hashed_before_becoming_a_redis_key() -> None:
    token = "private-session-token"
    token_hash = hash_session_token(token)

    assert token not in token_hash
    assert len(token_hash) == 64
    assert session_key(token).endswith(token_hash)


def test_session_hash_is_deterministic() -> None:
    user_id = uuid4()
    token = str(user_id)

    assert hash_session_token(token) == hash_session_token(token)
