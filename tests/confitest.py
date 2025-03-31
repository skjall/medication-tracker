import logging
import pytest


def pytest_configure(config):
    """
    Configure logging for the entire test run.
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s (%(filename)s:%(lineno)s)",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # You can also configure specific loggers
    # logging.getLogger("app.deduction_service").setLevel(logging.DEBUG)
