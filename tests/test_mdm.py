import pytest
from unittest.mock import patch, MagicMock


def test_main_exits_on_keyboard_interrupt():
    with patch("mdm.ui.show_banner"), \
         patch("mdm.downloader.check_ffmpeg"), \
         patch("mdm.cfg.load_config", return_value={"download_dir": "/tmp", "default_quality": "320"}), \
         patch("mdm.ui.show_main_menu", side_effect=KeyboardInterrupt), \
         patch("mdm.ui.show_success") as mock_success:
        import mdm
        try:
            mdm.main()
        except SystemExit:
            pass  # acceptable — clean exit
        mock_success.assert_called_once_with("Goodbye!")


def test_main_download_audio_single_track():
    fake_info = {
        "title": "Test Song", "uploader": "Artist",
        "duration": 200, "is_playlist": False, "entries": None,
    }
    mock_prog = MagicMock()
    mock_prog.__enter__ = MagicMock(return_value=MagicMock())
    mock_prog.__exit__ = MagicMock(return_value=False)

    with patch("mdm.ui.show_banner"), \
         patch("mdm.downloader.check_ffmpeg"), \
         patch("mdm.cfg.load_config", return_value={"download_dir": "/tmp/music", "default_quality": "320"}), \
         patch("mdm.cfg.save_config"), \
         patch("mdm.ui.show_main_menu", side_effect=["download", "exit"]), \
         patch("mdm.ui.prompt_url", return_value="https://youtube.com/watch?v=abc"), \
         patch("mdm.downloader.get_track_info", return_value=fake_info), \
         patch("mdm.ui.select_mode", return_value="audio"), \
         patch("mdm.ui.select_quality", return_value="320"), \
         patch("mdm.ui.confirm_download", return_value=True), \
         patch("mdm.downloader.download_audio", return_value="/tmp/music/Test Song.mp3") as mock_dl, \
         patch("mdm.ui.show_summary"), \
         patch("mdm.ui.make_progress", return_value=mock_prog):
        import mdm
        mdm.main()
    mock_dl.assert_called_once()


def test_main_settings_saves_config():
    new_config = {"download_dir": "/new/path", "default_quality": "192"}
    with patch("mdm.ui.show_banner"), \
         patch("mdm.downloader.check_ffmpeg"), \
         patch("mdm.cfg.load_config", return_value={"download_dir": "/tmp", "default_quality": "320"}), \
         patch("mdm.cfg.save_config") as mock_save, \
         patch("mdm.ui.show_main_menu", side_effect=["settings", "exit"]), \
         patch("mdm.ui.show_settings_menu", return_value=new_config):
        import mdm
        mdm.main()
    mock_save.assert_called_once_with(new_config)


def test_main_settings_keyboard_interrupt_handled():
    with patch("mdm.ui.show_banner"), \
         patch("mdm.downloader.check_ffmpeg"), \
         patch("mdm.cfg.load_config", return_value={"download_dir": "/tmp", "default_quality": "320"}), \
         patch("mdm.ui.show_main_menu", side_effect=["settings", "exit"]), \
         patch("mdm.ui.show_settings_menu", side_effect=KeyboardInterrupt), \
         patch("mdm.ui.show_error") as mock_err:
        import mdm
        mdm.main()
    mock_err.assert_called_once_with("Settings cancelled.")


def test_main_ffmpeg_missing_exits():
    with patch("mdm.ui.show_banner"), \
         patch("mdm.downloader.check_ffmpeg", side_effect=RuntimeError("ffmpeg not found")), \
         patch("mdm.ui.show_error") as mock_err, \
         pytest.raises(SystemExit):
        import mdm
        mdm.main()
    mock_err.assert_called_once_with("ffmpeg not found")


def test_main_download_video_single_track():
    fake_info = {
        "title": "Test Video", "uploader": "Creator",
        "duration": 120, "is_playlist": False, "entries": None,
    }
    mock_prog = MagicMock()
    mock_prog.__enter__ = MagicMock(return_value=MagicMock())
    mock_prog.__exit__ = MagicMock(return_value=False)

    with patch("mdm.ui.show_banner"), \
         patch("mdm.downloader.check_ffmpeg"), \
         patch("mdm.cfg.load_config", return_value={"download_dir": "/tmp/videos", "default_quality": "1080p"}), \
         patch("mdm.ui.show_main_menu", side_effect=["download", "exit"]), \
         patch("mdm.ui.prompt_url", return_value="https://youtube.com/watch?v=xyz"), \
         patch("mdm.downloader.get_track_info", return_value=fake_info), \
         patch("mdm.ui.select_mode", return_value="video"), \
         patch("mdm.ui.select_quality", return_value="1080p"), \
         patch("mdm.ui.confirm_download", return_value=True), \
         patch("mdm.downloader.download_video", return_value="/tmp/videos/Test Video.mp4") as mock_dl_vid, \
         patch("mdm.ui.show_summary"), \
         patch("mdm.ui.make_progress", return_value=mock_prog):
        import mdm
        mdm.main()
    mock_dl_vid.assert_called_once()


def test_main_download_playlist():
    fake_info = {
        "title": "Test Playlist", "uploader": "Creator",
        "duration": None, "is_playlist": True,
        "entries": [{"title": "Track 1"}, {"title": "Track 2"}],
    }
    mock_prog = MagicMock()
    mock_prog.__enter__ = MagicMock(return_value=MagicMock())
    mock_prog.__exit__ = MagicMock(return_value=False)

    with patch("mdm.ui.show_banner"), \
         patch("mdm.downloader.check_ffmpeg"), \
         patch("mdm.cfg.load_config", return_value={"download_dir": "/tmp/music", "default_quality": "320"}), \
         patch("mdm.ui.show_main_menu", side_effect=["download", "exit"]), \
         patch("mdm.ui.prompt_url", return_value="https://youtube.com/playlist?list=123"), \
         patch("mdm.downloader.get_track_info", return_value=fake_info), \
         patch("mdm.ui.select_mode", return_value="audio"), \
         patch("mdm.ui.select_quality", return_value="320"), \
         patch("mdm.ui.confirm_download", return_value=True), \
         patch("mdm.downloader.download_playlist", return_value=[{"title": "Track 1", "path": "/tmp/music/1.mp3", "error": None}]) as mock_dl_pl, \
         patch("mdm.ui.show_summary"), \
         patch("mdm.ui.make_progress", return_value=mock_prog):
        import mdm
        mdm.main()
    mock_dl_pl.assert_called_once()


def test_main_get_track_info_error_handled():
    with patch("mdm.ui.show_banner"), \
         patch("mdm.downloader.check_ffmpeg"), \
         patch("mdm.cfg.load_config", return_value={"download_dir": "/tmp", "default_quality": "320"}), \
         patch("mdm.ui.show_main_menu", side_effect=["download", "exit"]), \
         patch("mdm.ui.prompt_url", return_value="https://invalid-url.com"), \
         patch("mdm.downloader.get_track_info", side_effect=Exception("Invalid URL")), \
         patch("mdm.ui.show_error") as mock_err:
        import mdm
        mdm.main()
    mock_err.assert_called_once_with("Could not fetch info: Invalid URL")


def test_main_confirm_download_declined():
    fake_info = {
        "title": "Test Song", "uploader": "Artist",
        "duration": 200, "is_playlist": False, "entries": None,
    }
    with patch("mdm.ui.show_banner"), \
         patch("mdm.downloader.check_ffmpeg"), \
         patch("mdm.cfg.load_config", return_value={"download_dir": "/tmp", "default_quality": "320"}), \
         patch("mdm.ui.show_main_menu", side_effect=["download", "exit"]), \
         patch("mdm.ui.prompt_url", return_value="https://youtube.com/watch?v=abc"), \
         patch("mdm.downloader.get_track_info", return_value=fake_info), \
         patch("mdm.ui.select_mode", return_value="audio"), \
         patch("mdm.ui.select_quality", return_value="320"), \
         patch("mdm.ui.confirm_download", return_value=False), \
         patch("mdm.downloader.download_audio") as mock_dl:
        import mdm
        mdm.main()
    mock_dl.assert_not_called()
