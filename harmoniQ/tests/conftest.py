import os
import pytest


@pytest.fixture(autouse=True)
def set_env_vars():
    print("Setting env vars")
    os.environ["HARMONIQ_TESTING"] = "True"
