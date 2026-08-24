from unittest.mock import MagicMock, patch

from src.actions import close_app, execute, open_app, open_url, play_media, search_web
from src.intent_router import Command, Intent


@patch("src.actions.subprocess.Popen")
def test_open_app_launches_known_app(mock_popen):
    result = open_app("notepad")
    assert mock_popen.called
    assert "khol diya" in result


def test_open_app_unknown_app_returns_friendly_message():
    result = open_app("some_random_unknown_app")
    assert "nahi aata" in result


@patch("src.actions.webbrowser.open_new_tab")
def test_open_url_adds_scheme(mock_open):
    open_url("example.com")
    mock_open.assert_called_once_with("https://example.com")


@patch("src.actions.webbrowser.open_new_tab")
def test_search_web_builds_google_query(mock_open):
    search_web("best pizza near me")
    args, _ = mock_open.call_args
    assert "google.com/search" in args[0]
    assert "best+pizza+near+me" in args[0] or "best%20pizza%20near%20me" in args[0]


@patch("src.actions.psutil.process_iter")
def test_close_app_terminates_matching_process(mock_iter):
    fake_proc = MagicMock()
    fake_proc.info = {"name": "chrome.exe"}
    mock_iter.return_value = [fake_proc]

    result = close_app("chrome")
    fake_proc.terminate.assert_called_once()
    assert "band kar diya" in result


@patch("src.actions.psutil.process_iter", return_value=[])
def test_close_app_when_not_running(mock_iter):
    result = close_app("chrome")
    assert "chal hi nahi raha" in result


@patch("src.actions.webbrowser.open_new_tab")
def test_execute_dispatches_open_url(mock_open):
    cmd = Command(Intent.OPEN_URL, target="example.com")
    execute(cmd)
    assert mock_open.called


def test_execute_raises_on_chat_intent():
    cmd = Command(Intent.CHAT, target="")
    try:
        execute(cmd)
        assert False, "expected ValueError"
    except ValueError:
        pass


@patch("pywhatkit.playonyt")
def test_play_media_uses_pywhatkit(mock_playonyt):
    result = play_media("believer imagine dragons")
    mock_playonyt.assert_called_once_with("believer imagine dragons")
    assert "bajaa raha hoon" in result
