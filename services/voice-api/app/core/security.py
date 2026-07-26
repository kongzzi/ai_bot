import hmac


def parse_device_tokens(raw: str) -> dict[str, str]:
    """"device-001:token-a,device-002:token-b" 형식을 파싱한다."""
    tokens: dict[str, str] = {}
    for pair in raw.split(","):
        device_id, _, token = pair.strip().partition(":")
        if device_id and token:
            tokens[device_id.strip()] = token.strip()
    return tokens


def verify_device(device_id: str, token: str, registry: dict[str, str]) -> bool:
    expected = registry.get(device_id)
    if expected is None:
        return False
    return hmac.compare_digest(expected, token)
