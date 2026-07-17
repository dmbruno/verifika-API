import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from dotenv import load_dotenv

load_dotenv()

import app.db as db_module
from app import app as flask_app


@pytest.fixture(scope="session")
def client(tmp_path_factory):
    test_db_path = str(tmp_path_factory.mktemp("data") / "test_verifika.db")
    db_module.DB_PATH = test_db_path
    db_module.init_db()

    flask_app.testing = True
    return flask_app.test_client()
