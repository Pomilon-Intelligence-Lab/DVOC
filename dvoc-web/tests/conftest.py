import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def playwright():
    pw = sync_playwright().start()
    yield pw
    pw.stop()


@pytest.fixture(scope="function")
def browser(playwright):
    browser = playwright.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def page(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    page = ctx.new_page()
    yield page
    page.close()
    ctx.close()
