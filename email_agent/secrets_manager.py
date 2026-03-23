"""AWS Secrets Manager helpers for fetching secrets at runtime.

This keeps credentials out of .env files when running on AWS (e.g. EC2 with IAM role).
"""

from __future__ import annotations

import base64
from functools import lru_cache
from typing import Any


def _get_boto3_client(*, region: str) -> Any:
    try:
        import boto3  # type: ignore
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "boto3 is required for AWS Secrets Manager. "
            "Run: pip install -r requirements.txt"
        ) from e

    return boto3.client("secretsmanager", region_name=region)


@lru_cache(maxsize=64)
def get_secret_string(*, secret_id: str, region: str) -> str:
    """Fetch a secret value as a string from AWS Secrets Manager."""
    client = _get_boto3_client(region=region)
    resp = client.get_secret_value(SecretId=secret_id)

    if "SecretString" in resp and resp["SecretString"]:
        return str(resp["SecretString"])

    if "SecretBinary" in resp and resp["SecretBinary"]:
        # AWS returns bytes-like base64; decode to UTF-8.
        raw = resp["SecretBinary"]
        if isinstance(raw, (bytes, bytearray)):
            decoded = base64.b64decode(raw)
        else:
            decoded = base64.b64decode(str(raw))
        return decoded.decode("utf-8", errors="replace")

    return ""

