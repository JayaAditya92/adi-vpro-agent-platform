
import sys


def test_python_version():
    """Verify that the project uses Python 3.12 or above."""
    assert sys.version_info >= (3, 12)


def test_testing_environment():
    """Verify that pytest is available."""
    import pytest

    assert pytest.__version__ is not None


def test_backend_package():
    """Verify that the backend application package is accessible."""
    import app

    assert app is not None