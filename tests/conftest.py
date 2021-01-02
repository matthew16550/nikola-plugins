import os

from pytest import fixture

from nikola.utils import LocaleBorg


@fixture(scope="session")
def default_locale() -> str:
    return os.environ.get("NIKOLA_LOCALE_DEFAULT", "en")


@fixture(scope="module", autouse=True)
def localeborg_setup(default_locale):
    """
    Reset the LocaleBorg before and after every test.
    """
    LocaleBorg.reset()
    LocaleBorg.initialize({}, default_locale)
    try:
        yield
    finally:
        LocaleBorg.reset()
