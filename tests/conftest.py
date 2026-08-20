import os
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
