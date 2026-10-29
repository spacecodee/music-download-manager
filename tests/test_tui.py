import asyncio
from unittest.mock import patch

from textual.widgets import Button, DataTable, Input, Select, Static

import tui

INFO = {"title": "Song", "uploader": "Artist", "duration": 125, "is_playlist": False, "entries": None}
PLAYLIST = {"title": "List", "uploader": "X", "duration": None, "is_playlist": True,
            "entries": [{"title": "A"}, {"title": "B"}]}


def run(scenario, config=None):
    cfg = {"download_dir": "/tmp/mdm", "default_quality": "320", "browser_cookies": "none",
           "font_notice_shown": True, **(config or {})}

    async def go():
        with patch("tui.cfg.load_config", return_value=cfg), \
             patch("tui.downloader.check_ffmpeg"), \
             patch("tui.os_is_dark", return_value=True), \
             patch("tui.fonts.is_installed", return_value=True), \
             patch("tui.cfg.save_config"):
            app = tui.MdmApp()
            async with app.run_test(size=(120, 60)) as pilot:
                await scenario(app, pilot)

    asyncio.run(go())


async def _fetch(app, pilot, url="http://x"):
    app.query_one("#url", Input).value = url
    await pilot.click("#fetch")
    await app.workers.wait_for_complete()
    await pilot.pause()


def test_fetch_shows_info_and_enables_download():
    async def scenario(app, pilot):
        with patch("tui.downloader.get_track_info", return_value=INFO):
            await _fetch(app, pilot)
        assert "Song — Artist (2:05)" in str(app.query_one("#info", Static).render())
        assert not app.query_one("#download-btn", Button).disabled
    run(scenario)


def test_fetch_error_is_shown_and_download_stays_disabled():
    async def scenario(app, pilot):
        with patch("tui.downloader.get_track_info", side_effect=RuntimeError("boom")):
            await _fetch(app, pilot)
        assert "boom" in str(app.query_one("#info", Static).render())
        assert app.query_one("#download-btn", Button).disabled
    run(scenario)


def test_single_audio_download_reports_result():
    async def scenario(app, pilot):
        with patch("tui.downloader.get_track_info", return_value=INFO), \
             patch("tui.downloader.download_audio", return_value="/tmp/mdm/Song.mp3") as dl:
            await _fetch(app, pilot)
            await pilot.click("#download-btn")
            await app.workers.wait_for_complete()
            await pilot.pause()
        assert dl.call_args.args[:3] == ("http://x", "320", "/tmp/mdm")
        assert app.query_one("#results", DataTable).row_count == 1
        assert "1 succeeded, 0 failed" in str(app.query_one("#status", Static).render())
        assert not app.query_one("#download-btn", Button).disabled
    run(scenario)


def test_playlist_download_mixed_results():
    async def scenario(app, pilot):
        def fake_playlist(url, mode, quality, out, on_track_start, on_track_done, progress_hook, cookies):
            results = [{"title": "A", "path": "/a.mp3", "error": None},
                       {"title": "B", "path": None, "error": "nope"}]
            for i, r in enumerate(results):
                on_track_start(i, r["title"])
                on_track_done(i, r)
            return results

        with patch("tui.downloader.get_track_info", return_value=PLAYLIST), \
             patch("tui.downloader.download_playlist", side_effect=fake_playlist):
            await _fetch(app, pilot)
            await pilot.click("#download-btn")
            await app.workers.wait_for_complete()
            await pilot.pause()
        assert app.query_one("#results", DataTable).row_count == 2
        assert "1 succeeded, 1 failed" in str(app.query_one("#status", Static).render())
    run(scenario)


def test_download_failure_is_listed():
    async def scenario(app, pilot):
        with patch("tui.downloader.get_track_info", return_value=INFO), \
             patch("tui.downloader.download_audio", side_effect=RuntimeError("bad")):
            await _fetch(app, pilot)
            await pilot.click("#download-btn")
            await app.workers.wait_for_complete()
            await pilot.pause()
        assert "0 succeeded, 1 failed" in str(app.query_one("#status", Static).render())
    run(scenario)


def test_video_mode_uses_video_qualities():
    async def scenario(app, pilot):
        await pilot.click("#mode-video")
        await pilot.pause()
        assert app.query_one("#quality", Select).value == "1080"
    run(scenario)


def test_save_settings_persists_config():
    async def scenario(app, pilot):
        app.query_one("#set-dir", Input).value = "/tmp/other"
        app.query_one("#set-quality", Select).value = "flac"
        app.query_one("#set-cookies", Input).value = ""
        with patch("tui.cfg.save_config") as save:
            app._save()
        save.assert_called_once_with(
            {"download_dir": "/tmp/other", "default_quality": "flac", "theme": "auto",
             "browser_cookies": "none", "font_notice_shown": True})
    run(scenario)


def test_auto_theme_follows_os():
    async def scenario(app, pilot):
        assert app.theme == "catppuccin-mocha"
        app._apply_theme(False)
        assert app.theme == "catppuccin-latte"
        app._apply_theme(True)
        assert app.theme == "catppuccin-mocha"
    run(scenario)


def test_explicit_theme_ignores_os():
    async def scenario(app, pilot):
        assert app.theme == "catppuccin-frappe"
        app._apply_theme(False)
        assert app.theme == "catppuccin-frappe"
    run(scenario, {"theme": "catppuccin-frappe"})


def test_saving_theme_applies_it():
    async def scenario(app, pilot):
        app.query_one("#set-theme", Select).value = "catppuccin-macchiato"
        with patch("tui.cfg.save_config"):
            app._save()
        assert app.theme == "catppuccin-macchiato"
    run(scenario)


def test_os_is_dark_macos(monkeypatch):
    monkeypatch.setattr(tui.sys, "platform", "darwin")
    class R:  # noqa
        def __init__(self, rc, out): self.returncode, self.stdout = rc, out
    with patch("tui.subprocess.run", return_value=R(0, "Dark\n")):
        assert tui.os_is_dark() is True
    with patch("tui.subprocess.run", return_value=R(1, "")):
        assert tui.os_is_dark() is False


def test_font_notice_shown_once_when_font_present():
    async def scenario(app, pilot):
        await pilot.pause()
        assert isinstance(app.screen, tui.FontNotice)
        await pilot.click("#font-ok")
        await pilot.pause()
        assert not isinstance(app.screen, tui.FontNotice)
        assert app.config["font_notice_shown"] is True
    run(scenario, {"font_notice_shown": False})


def test_missing_font_is_installed_then_modal_shown():
    async def scenario(app, pilot):
        await app.workers.wait_for_complete()
        await pilot.pause()
        install.assert_called_once()
        assert isinstance(app.screen, tui.FontNotice)
        assert "has been installed" in str(app.screen.query_one("#font-title").render())

    with patch("tui.fonts.install") as install:
        async def go():
            with patch("tui.cfg.load_config", return_value={"font_notice_shown": False}), \
                 patch("tui.downloader.check_ffmpeg"), patch("tui.os_is_dark", return_value=True), \
                 patch("tui.fonts.is_installed", return_value=False), \
                 patch("tui.cfg.save_config"):
                app = tui.MdmApp()
                async with app.run_test(size=(120, 60)) as pilot:
                    await scenario(app, pilot)
        asyncio.run(go())


def test_icons_only_with_font():
    async def scenario(app, pilot):
        assert str(app.query_one("#fetch", Button).label).startswith(tui.GLYPHS["search"])
        assert app._icon("search").startswith(tui.GLYPHS["search"])
    run(scenario, {"font_notice_shown": True})
