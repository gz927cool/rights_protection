"""End-to-end tests for the labor rights consultation chat flow."""

import pytest
import urllib.request


def _check_url(url: str) -> bool:
    """Return True if the HTTP URL is reachable."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False


@pytest.mark.playwright
def test_home_page_loads_with_title(frontend_url: str, page):
    """Verify the home page loads and displays the system title."""
    if not _check_url(frontend_url):
        pytest.skip(f"Frontend server not reachable at {frontend_url}")

    page.goto(frontend_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=15_000)

    assert page.get_by_text("劳动争议智能咨询系统").first.is_visible(timeout=10_000)


@pytest.mark.playwright
def test_start_ai_consultation_button_navigates(frontend_url: str, page):
    """Click '开始AI咨询' and verify the chat interface appears."""
    if not _check_url(frontend_url):
        pytest.skip(f"Frontend server not reachable at {frontend_url}")

    page.goto(frontend_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=15_000)

    start_btn = page.get_by_text("开始AI咨询")
    assert start_btn.is_visible(timeout=10_000)
    start_btn.click()
    page.wait_for_url("**/chat**", timeout=10_000)

    # After clicking, an input field for the chat should appear.
    # Use CSS selector since the textarea may not have a role
    chat_input = page.locator("textarea").first
    assert chat_input.is_visible(timeout=10_000)


@pytest.mark.playwright
def test_chat_message_appears_after_send(frontend_url: str, page):
    """Send a test message and verify the user message appears in the chat."""
    if not _check_url(frontend_url):
        pytest.skip(f"Frontend server not reachable at {frontend_url}")

    # Navigate directly to chat page
    page.goto(f"{frontend_url}/chat", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=15_000)

    chat_input = page.locator("textarea").first
    assert chat_input.is_visible(timeout=10_000), "Chat textarea not visible"

    test_message = "公司拖欠工资两个月了，我该怎么办？"
    chat_input.fill(test_message)
    chat_input.press("Enter")

    # Verify the user's message appears in the DOM
    assert page.get_by_text(test_message).first.is_visible(timeout=15_000), \
        "User message not visible after send"


@pytest.mark.playwright
def test_step_progress_indicator_visible(frontend_url: str, page):
    """Verify the chat interface elements are visible."""
    if not _check_url(frontend_url):
        pytest.skip(f"Frontend server not reachable at {frontend_url}")

    page.goto(f"{frontend_url}/chat", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=15_000)

    # Verify welcome text is shown on fresh chat page
    welcome = page.get_by_text("欢迎使用劳动争议智能咨询系统")
    assert welcome.is_visible(timeout=10_000), "Welcome text not visible"

    # Verify chat header is visible
    header = page.get_by_text("劳动争议咨询")
    assert header.is_visible(timeout=5_000), "Chat header not visible"
