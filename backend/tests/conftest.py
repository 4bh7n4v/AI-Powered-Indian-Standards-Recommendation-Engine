import os
import tempfile

os.environ["ISRE_VAR_DIR"] = tempfile.mkdtemp(prefix="isre-test-")  # never touch the real audit log
os.environ["ISRE_LOG_DIR"] = tempfile.mkdtemp(prefix="isre-logs-")
os.environ.setdefault("ISRE_DENSE", "off")  # tests run on the lexical baseline
os.environ.setdefault("ISRE_SAMPLES_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "samples"))

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)
