import pytest
from unittest.mock import patch, MagicMock, call
import yt_dlp
import downloader


def test_get_track_info_single_track():
    fake_info = {
        "title": "Test Song",
        "uploader": "Test Artist",
        "duration": 240,
        "_type": "video",
        "entries": None,
    }
    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info.return_value = fake_info
    with patch("downloader.yt_dlp.YoutubeDL", return_value=mock_ydl):
        result = downloader.get_track_info("https://youtube.com/watch?v=test")
    assert result["title"] == "Test Song"
    assert result["uploader"] == "Test Artist"
    assert result["duration"] == 240
    assert result["is_playlist"] is False
    assert result["entries"] is None


def test_get_track_info_playlist():
    fake_info = {
        "title": "My Playlist",
        "uploader": "Channel",
        "duration": None,
        "_type": "playlist",
        "entries": [{"title": "Song 1"}, {"title": "Song 2"}],
    }
    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info.return_value = fake_info
    with patch("downloader.yt_dlp.YoutubeDL", return_value=mock_ydl):
        result = downloader.get_track_info("https://youtube.com/playlist?list=test")
    assert result["is_playlist"] is True
    assert len(result["entries"]) == 2


def test_build_audio_opts_mp3_320():
    opts = downloader._build_audio_opts("320", "/tmp/music")
    assert opts["format"] == "bestaudio/best"
    pp = opts["postprocessors"][0]
    assert pp["key"] == "FFmpegExtractAudio"
    assert pp["preferredcodec"] == "mp3"
    assert pp["preferredquality"] == "320"


def test_build_audio_opts_flac():
    opts = downloader._build_audio_opts("flac", "/tmp/music")
    pp = opts["postprocessors"][0]
    assert pp["preferredcodec"] == "flac"


def test_build_video_opts_1080():
    opts = downloader._build_video_opts("1080", "/tmp/video")
    assert "height<=1080" in opts["format"]


def test_build_video_opts_720():
    opts = downloader._build_video_opts("720", "/tmp/video")
    assert "height<=720" in opts["format"]


def test_check_ffmpeg_raises_if_missing():
    with patch("downloader.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="ffmpeg"):
            downloader.check_ffmpeg()


def test_check_ffmpeg_passes_if_present():
    with patch("downloader.shutil.which", return_value="/usr/bin/ffmpeg"):
        downloader.check_ffmpeg()  # should not raise


def test_download_audio():
    with patch("downloader._download_with_retry", return_value="/tmp/music/song.mp3") as mock_retry:
        res = downloader.download_audio("https://youtube.com/watch?v=123", "320", "/tmp/music")
        assert res == "/tmp/music/song.mp3"
        mock_retry.assert_called_once()


def test_download_video():
    with patch("downloader._download_with_retry", return_value="/tmp/video/vid.mp4") as mock_retry:
        res = downloader.download_video("https://youtube.com/watch?v=123", "1080", "/tmp/video")
        assert res == "/tmp/video/vid.mp4"
        mock_retry.assert_called_once()


def test_download_playlist():
    fake_info = {
        "title": "Playlist",
        "uploader": "User",
        "duration": None,
        "is_playlist": True,
        "entries": [
            {"id": "abc", "title": "Song A"},
            {"url": "https://youtube.com/watch?v=def", "title": "Song B"},
        ],
    }
    on_start = MagicMock()
    on_done = MagicMock()

    with patch("downloader.get_track_info", return_value=fake_info):
        with patch("downloader.download_audio", side_effect=["/tmp/a.mp3", Exception("Download failed")]):
            results = downloader.download_playlist(
                "https://youtube.com/playlist?list=xyz",
                "audio",
                "320",
                "/tmp/music",
                on_track_start=on_start,
                on_track_done=on_done,
            )

    assert len(results) == 2
    assert results[0] == {"title": "Song A", "path": "/tmp/a.mp3", "error": None}
    assert results[1] == {"title": "Song B", "path": None, "error": "Download failed"}
    assert on_start.call_count == 2
    assert on_done.call_count == 2


def test_download_with_retry_success():
    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info.return_value = {"title": "test"}
    mock_ydl.prepare_filename.return_value = "/tmp/test.mp3"

    progress_fn = MagicMock()
    opts = {"quiet": True}

    with patch("downloader.yt_dlp.YoutubeDL", return_value=mock_ydl) as mock_ydl_cls:
        res = downloader._download_with_retry("https://youtube.com/watch?v=test", opts, progress_fn)
        assert res == "/tmp/test.mp3"
        mock_ydl_cls.assert_called_once_with({"quiet": True, "progress_hooks": [progress_fn]})


def test_download_with_retry_failure():
    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("Network error")

    with patch("downloader.yt_dlp.YoutubeDL", return_value=mock_ydl):
        with patch("downloader.time.sleep") as mock_sleep:
            with pytest.raises(yt_dlp.utils.DownloadError, match="Network error"):
                downloader._download_with_retry("https://youtube.com/watch?v=test", {}, None)
            assert mock_sleep.call_count == 3
            mock_sleep.assert_has_calls([call(2), call(4), call(8)])
