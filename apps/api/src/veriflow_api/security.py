from pwdlib import PasswordHash
from starlette.concurrency import run_in_threadpool

password_hasher = PasswordHash.recommended()


async def hash_password(password: str) -> str:
    """Hash a password without blocking the event loop."""

    return await run_in_threadpool(password_hasher.hash, password)


async def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password without blocking the event loop."""

    return await run_in_threadpool(password_hasher.verify, password, password_hash)
