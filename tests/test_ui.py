import pytest
from unittest.mock import patch
import rich.progress


def test_select_quality_audio_returns_valid_option():
    with patch("ui.Prompt.ask", return_value="1"):
        import ui
        result = ui.select_quality("audio", "320")
    assert result in ("320", "192", "128", "flac")


def test_select_quality_video_returns_valid_option():
    with patch("ui.Prompt.ask", return_value="1"):
        import ui
        result = ui.select_quality("video", "1080")
    assert result in ("1080", "720", "480", "360")


def test_select_quality_audio_first_option_is_320():
    with patch("ui.Prompt.ask", return_value="1"):
        import ui
        result = ui.select_quality("audio", "320")
    assert result == "320"


def test_confirm_download_single_track_returns_true():
    info = {"title": "My Song", "uploader": "Artist", "duration": 180,
            "is_playlist": False, "entries": None}
    with patch("ui.Confirm.ask", return_value=True):
        import ui
        result = ui.confirm_download(info)
    assert result is True


def test_confirm_download_returns_false_on_no():
    info = {"title": "Song", "uploader": "X", "duration": 60,
            "is_playlist": False, "entries": None}
    with patch("ui.Confirm.ask", return_value=False):
        import ui
        result = ui.confirm_download(info)
    assert result is False


def test_confirm_download_playlist():
    info = {"title": "My Playlist", "uploader": "Artist", "duration": None,
            "is_playlist": True, "entries": [{"title": "Track 1"}, {"title": "Track 2"}]}
    with patch("ui.Confirm.ask", return_value=True):
        import ui
        result = ui.confirm_download(info)
    assert result is True


def test_show_summary_handles_empty_results():
    import ui
    ui.show_summary([])  # should not raise


def test_show_summary_shows_errors():
    import ui
    results = [
        {"title": "Good Song", "path": "/music/good.mp3", "error": None},
        {"title": "Bad Song", "path": None, "error": "Network error"},
    ]
    ui.show_summary(results)  # should not raise


def test_show_banner():
    import ui
    ui.show_banner()  # should execute without error


def test_show_main_menu():
    with patch("ui.Prompt.ask", return_value="1"):
        import ui
        assert ui.show_main_menu() == "download"
    with patch("ui.Prompt.ask", return_value="2"):
        import ui
        assert ui.show_main_menu() == "settings"
    with patch("ui.Prompt.ask", return_value="3"):
        import ui
        assert ui.show_main_menu() == "exit"


def test_prompt_url():
    # First prompt invalid, second valid youtube link
    with patch("ui.Prompt.ask", side_effect=["invalid", "https://youtube.com/watch?v=123"]):
        import ui
        url = ui.prompt_url()
    assert url == "https://youtube.com/watch?v=123"


def test_prompt_url_youtu_be():
    with patch("ui.Prompt.ask", return_value="https://youtu.be/123"):
        import ui
        url = ui.prompt_url()
    assert url == "https://youtu.be/123"


def test_select_mode():
    with patch("ui.Prompt.ask", return_value="1"):
        import ui
        assert ui.select_mode() == "audio"
    with patch("ui.Prompt.ask", return_value="2"):
        import ui
        assert ui.select_mode() == "video"


def test_make_progress():
    import ui
    prog = ui.make_progress()
    assert isinstance(prog, rich.progress.Progress)


def test_show_settings_menu():
    config = {"download_dir": "~/Music", "default_quality": "320"}
    with patch("ui.Prompt.ask", side_effect=["~/NewMusic", "2"]):
        import ui
        updated = ui.show_settings_menu(config)
    assert updated["download_dir"] == "~/NewMusic"
    assert updated["default_quality"] == "192"


def test_show_error_and_success():
    import ui
    ui.show_error("Test error")
    ui.show_success("Test success")
