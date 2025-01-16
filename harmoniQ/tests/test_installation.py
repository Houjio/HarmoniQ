import pytest


def test_hello_world():
    assert "Hello, World!" == "Hello, World!"


def test_database_variable():
    try:
        from harmoniq import DB_PATH
    except ImportError:
        pytest.fail("DB_PATH pas trouver dans harmoniq/__init__.py")


def test_database_file():
    try:
        from harmoniq import DB_PATH

        assert DB_PATH.exists()
    except ImportError:
        pytest.fail("DB_PATH ne correspond pas a un fichier")
