from veriflow_api.security import hash_password, verify_password


async def test_password_hashing_round_trip() -> None:
    password = "A-strong-demo-password-2026"
    password_hash = await hash_password(password)

    assert password_hash != password
    assert await verify_password(password, password_hash) is True
    assert await verify_password("incorrect-password", password_hash) is False
