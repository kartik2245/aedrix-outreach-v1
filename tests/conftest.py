import os
import pytest
import urllib.request
import src.database.connection

# Save the original is_database_enabled function
_original_is_db_enabled = src.database.connection.is_database_enabled

def custom_is_db_enabled() -> bool:
    """
    Dynamically resolves whether database is enabled.
    Returns the real value if the current pytest test is from test_database.py,
    otherwise returns False to isolate unit tests from PostgreSQL crosstalk.
    """
    current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
    if "test_database" in current_test:
        return _original_is_db_enabled()
    return False

# Monkeypatch the function globally at the source module
src.database.connection.is_database_enabled = custom_is_db_enabled


@pytest.fixture(autouse=True)
def isolate_test_environment_from_live_apis(monkeypatch):
    """
    Global test safety isolation:
    1. Sets DEEPLINE_LIVE="false" and DEEPLINE_RUN_CONFIRMATION="false" by default so all test
       runs execute completely offline without consuming API credits or making external HTTP requests.
    2. Intercepts urllib.request.urlopen to catch any unexpected outbound calls to external APIs.
    """
    monkeypatch.setenv("DEEPLINE_LIVE", "false")
    monkeypatch.setenv("DEEPLINE_RUN_CONFIRMATION", "false")

    real_urlopen = urllib.request.urlopen

    def guarded_urlopen(url, *args, **kwargs):
        url_str = url.full_url if hasattr(url, "full_url") else str(url)
        if "deepline.com" in url_str or "amazonaws.com" in url_str or "smartlead.ai" in url_str:
            raise RuntimeError(
                f"SAFETY GUARDRAIL TRIGGERED: Blocked un-mocked outbound HTTP call to '{url_str}'. "
                "Pytest test suite must execute offline without external API calls."
            )
        return real_urlopen(url, *args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", guarded_urlopen)

