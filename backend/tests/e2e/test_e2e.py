"""E2E Tests for Frontend + Backend flows using pytest-playwright."""
import pytest

# Skip entire module if playwright not available
pytest.importorskip("playwright")

from playwright.sync_api import sync_playwright
import time


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


def test_signup_login_recognize(browser):
    """E2E: signup -> login -> enroll -> recognize -> dashboard."""
    page = browser.new_page()
    page.goto("http://localhost:3000")  # UI dev server
    # Stub flows - expand with real selectors
    page.fill("input[name='email']", "test@example.com")
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")
    assert "dashboard" in page.url
    page.close()


def test_billing_flow(browser):
    """E2E: Subscription -> webhook -> quota."""
    page = browser.new_page()
    page.goto("http://localhost:3000/dashboard")
    page.click("text=Billing")
    page.click("button:has-text('Pro Plan')")
    # Stripe checkout stub
    assert "checkout.stripe" in page.url or "subscription" in page.content()
    page.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])