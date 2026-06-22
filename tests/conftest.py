def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests that scan the full dataset (deselect with '-m \"not slow\"')"
    )
