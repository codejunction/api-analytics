from datetime import date, timedelta

from server.database.sanitize import valid_date, valid_hostname, valid_ip_address, valid_location, valid_path, valid_status, valid_string, valid_user_agent, valid_user_id


def test_validation_accepts_sdk_request_values() -> None:
    assert valid_string("hello")
    assert valid_hostname("api.example.com")
    assert valid_path("/v1/widgets?limit=10")
    assert valid_user_agent("Mozilla/5.0")
    assert valid_user_id("client-123")
    assert valid_ip_address("2001:db8::1")
    assert valid_location("GB")
    assert valid_status(201)
    assert valid_date(date.today() - timedelta(days=1))


def test_validation_rejects_unsafe_values() -> None:
    assert not valid_string("SELECT * FROM users")
    assert not valid_hostname("")
    assert not valid_path("\x00")
    assert not valid_user_agent("")
    assert not valid_user_id("x" * 256)
    assert not valid_ip_address("not-an-ip")
    assert not valid_location("gb")
    assert not valid_status(600)
