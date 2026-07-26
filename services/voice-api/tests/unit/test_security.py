from app.core.security import parse_device_tokens, verify_device


def test_parse_device_tokens():
    registry = parse_device_tokens("device-001:tok-a, device-002:tok-b ,,bad-entry")
    assert registry == {"device-001": "tok-a", "device-002": "tok-b"}


def test_verify_device():
    registry = {"device-001": "tok-a"}
    assert verify_device("device-001", "tok-a", registry)
    assert not verify_device("device-001", "wrong", registry)
    assert not verify_device("unknown", "tok-a", registry)
