import fault.logging


def test_logging_smoke():
    fault.logging.info("some info msg")
    fault.logging.warning("some warning msg")
    fault.logging.error("some error msg")
