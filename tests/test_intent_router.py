from src.intent_router import Intent, route


def test_open_chrome_english():
    cmd = route("open chrome")
    assert cmd.intent is Intent.OPEN_APP
    assert cmd.target == "chrome"


def test_open_chrome_hinglish():
    cmd = route("chrome khol do")
    assert cmd.intent is Intent.OPEN_APP
    assert cmd.target == "chrome"


def test_open_notepad():
    cmd = route("please open notepad")
    assert cmd.intent is Intent.OPEN_APP
    assert cmd.target == "notepad"


def test_play_song_on_youtube():
    cmd = route("play believer on youtube")
    assert cmd.intent is Intent.PLAY_MEDIA
    assert "believer" in cmd.target


def test_play_song_hindi_trigger():
    cmd = route("tum bajao arijit singh wala gaana")
    assert cmd.intent is Intent.PLAY_MEDIA


def test_close_app():
    cmd = route("close chrome")
    assert cmd.intent is Intent.CLOSE_APP
    assert cmd.target == "chrome"


def test_search_web():
    cmd = route("search for best laptops 2026")
    assert cmd.intent is Intent.SEARCH_WEB
    assert "best laptops 2026" in cmd.target


def test_plain_chat_falls_through():
    cmd = route("how are you doing today")
    assert cmd.intent is Intent.CHAT


def test_empty_text_is_chat():
    cmd = route("")
    assert cmd.intent is Intent.CHAT


def test_hindi_chat_not_misrouted():
    cmd = route("aaj mausam kaisa hai")
    assert cmd.intent is Intent.CHAT
