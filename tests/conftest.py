"""Pytest configuration and fixtures for Playwright e2e tests."""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "playwright: mark test as a Playwright e2e test")


@pytest.fixture(scope="session")
def frontend_url() -> str:
    """Return the frontend base URL."""
    return "http://localhost:5173"


@pytest.fixture(scope="session")
def backend_url() -> str:
    """Return the backend base URL."""
    return "http://localhost:8000"


@pytest.fixture(scope="session")
def browser():
    """Provide a Playwright Chromium browser instance for the test session."""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture
def page(browser):
    """Provide a fresh page for each test, automatically cleaned up."""
    ctx = browser.new_context()
    p = ctx.new_page()
    yield p
    ctx.close()
