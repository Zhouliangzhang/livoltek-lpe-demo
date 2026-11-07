from pathlib import Path
from uuid import uuid4

def pytest_configure(config):
    # Isolate runs across Windows user accounts; never delete another run's directory.
    if not config.option.basetemp:
        config.option.basetemp = str(Path(__file__).resolve().parents[1] / ('.test-run-' + uuid4().hex))
