import uuid
from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password_roundtrip():
    hashed = hash_password("demo1234")
    assert hashed != "demo1234"
    assert verify_password("demo1234", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("demo1234")
    assert verify_password("wrong-password", hashed) is False


def test_create_and_decode_access_token_roundtrip():
    user_id = uuid.uuid4()
    branch_id = uuid.uuid4()
    token = create_access_token(subject=user_id, role="OWNER", branch_id=branch_id)

    payload = decode_access_token(token)

    assert payload.sub == str(user_id)
    assert payload.role == "OWNER"
    assert payload.branch_id == str(branch_id)


def test_decode_access_token_handles_null_branch_id():
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id, role="OWNER", branch_id=None)

    payload = decode_access_token(token)

    assert payload.branch_id is None


def test_decode_expired_token_raises():
    user_id = uuid.uuid4()
    token = create_access_token(
        subject=user_id, role="OWNER", branch_id=None, expires_delta=timedelta(seconds=-1)
    )

    with pytest.raises(ValueError):
        decode_access_token(token)


def test_decode_garbage_token_raises():
    with pytest.raises(ValueError):
        decode_access_token("not-a-real-token")
