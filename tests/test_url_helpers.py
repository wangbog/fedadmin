from app.utils.url_helpers import is_valid_http_url, safe_redirect_target


def test_safe_redirect_target_allows_local_absolute_path():
    assert safe_redirect_target("/federation/?page=1", "/fallback") == "/federation/?page=1"


def test_safe_redirect_target_rejects_external_urls():
    assert safe_redirect_target("https://example.com/login", "/fallback") == "/fallback"
    assert safe_redirect_target("//example.com/login", "/fallback") == "/fallback"


def test_safe_redirect_target_rejects_relative_without_leading_slash():
    assert safe_redirect_target("federation/", "/fallback") == "/fallback"


def test_is_valid_http_url_accepts_http_and_https():
    assert is_valid_http_url("https://example.org/logo.png")
    assert is_valid_http_url("http://example.org/logo.png")


def test_is_valid_http_url_rejects_missing_scheme_or_host():
    assert not is_valid_http_url("example.org/logo.png")
    assert not is_valid_http_url("https:///logo.png")
    assert not is_valid_http_url("javascript:alert(1)")


def test_is_valid_http_url_can_require_https():
    assert is_valid_http_url("https://example.org", require_https=True)
    assert not is_valid_http_url("http://example.org", require_https=True)
