"""Music Download Manager — Textual full-screen interface."""

import subprocess
import sys
import threading
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label, ProgressBar,
    RadioButton, RadioSet, Select, Static, TabbedContent, TabPane,
)
from yt_dlp.utils import DownloadCancelled

import config as cfg
import downloader
import fonts

AUDIO_QUALITIES = [
    ("320",  "320 kbps MP3  (default, best quality)"),
    ("192",  "192 kbps MP3"),
    ("128",  "128 kbps MP3  (smallest size)"),
    ("flac", "FLAC          (lossless, largest size)"),
]

VIDEO_QUALITIES = [
    ("1080", "1080p Full HD"),
    ("720",  "720p HD"),
    ("480",  "480p SD"),
    ("360",  "360p Low"),
]


THEMES = [
    ("auto", "Auto (follow OS)"),
    ("catppuccin-latte", "Catppuccin Latte (light)"),
    ("catppuccin-frappe", "Catppuccin Frappé (dark)"),
    ("catppuccin-macchiato", "Catppuccin Macchiato (dark)"),
    ("catppuccin-mocha", "Catppuccin Mocha (dark)"),
]
AUTO_DARK, AUTO_LIGHT = "catppuccin-mocha", "catppuccin-latte"
OS_THEME_POLL_SECONDS = 3


def os_is_dark() -> bool | None:
    """Return True/False for the OS dark-mode setting, or None if it can't be determined."""
    if sys.platform == "darwin":
        cmd = ["defaults", "read", "-g", "AppleInterfaceStyle"]
        # Key is absent in light mode (command fails); "Dark" in dark mode.
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        except (OSError, subprocess.SubprocessError):
            return None
        return out.returncode == 0 and out.stdout.strip() == "Dark"
    if sys.platform.startswith("linux"):
        try:
            out = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if out.returncode != 0:
            return None
        return "dark" in out.stdout
    return None


# Nerd Font (Font Awesome range) glyphs; shown only when the font is installed.
GLYPHS = {"music": "\uf001", "download": "\uf019", "settings": "\uf013",
          "search": "\uf002", "save": "\uf0c7"}


class FontNotice(ModalScreen):
    """Tell the user to select the Nerd Font in their terminal settings."""

    BINDINGS = [("escape", "dismiss", "Close")]
    DEFAULT_CSS = """
    FontNotice { align: center middle; }
    FontNotice > Vertical { width: 64; height: auto; padding: 1 2;
        background: $panel; border: thick $primary; }
    FontNotice Button { margin-top: 1; }
    """

    def __init__(self, just_installed: bool) -> None:
        super().__init__()
        self.just_installed = just_installed

    def compose(self) -> ComposeResult:
        state = "has been installed" if self.just_installed else "is installed"
        with Vertical():
            yield Label(f"{fonts.FONT_NAME} {state}.", id="font-title")
            yield Static(
                "\nTo show the icons, set your terminal's font to:\n\n"
                f"  [b]{fonts.FONT_NAME}[/b]\n\n"
                "(Terminal → Settings/Preferences → Profile → Font), "
                "then restart this app."
            )
            yield Button("Got it", variant="primary", id="font-ok")

    @on(Button.Pressed, "#font-ok")
    def _ok(self) -> None:
        self.dismiss()


def _options(qualities: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return [(label, value) for value, label in qualities]


def _describe(info: dict) -> str:
    if info["is_playlist"]:
        return f"Playlist: {info['title']} — {len(info['entries'] or [])} tracks"
    duration = info.get("duration")
    length = f" ({int(duration) // 60}:{int(duration) % 60:02d})" if duration else ""
    return f"{info['title']} — {info['uploader']}{length}"


class MdmApp(App):
    TITLE = "Music Download Manager"
    BINDINGS = [("f1", "show_tab('download')", "Download"), ("f2", "show_tab('settings')", "Settings")]
    CSS = """
    TabPane { padding: 1 3; }
    #download-pane > * { margin-bottom: 1; }
    #download-pane { height: 1fr; }
    #url-row { height: auto; }
    #url { width: 1fr; }
    #info, #status { height: auto; }
    RadioSet, Select { width: 100%; }
    Button { min-width: 20; }
    DataTable { height: 1fr; min-height: 6; margin-bottom: 0; }
    TabPane Label { margin-top: 1; text-style: bold; }
    TabPane Label:first-of-type { margin-top: 0; }
    #set-dir, #set-quality, #set-theme, #set-cookies { margin-bottom: 1; }
    #save { margin-top: 1; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.config = cfg.load_config()
        self._info: dict | None = None
        self._info_url = ""
        self._stop = threading.Event()
        self._busy = False
        self._os_dark: bool | None = None
        self._font_ready = fonts.is_installed()

    def _icon(self, name: str) -> str:
        return GLYPHS[name] + " " if self._font_ready else ""

    # ---- layout -------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="download"):
            with TabPane(f"{self._icon('download')}Download", id="download"):
                with VerticalScroll(id="download-pane"):
                    with Vertical(id="url-row"):
                        yield Input(placeholder="Track or playlist URL", id="url")
                    yield Button(f"{self._icon('search')}Fetch info", id="fetch")
                    yield Static("", id="info")
                    with RadioSet(id="mode"):
                        yield RadioButton("Audio (MP3 / FLAC)", value=True, id="mode-audio")
                        yield RadioButton("Video (MP4)", id="mode-video")
                    yield Select(_options(AUDIO_QUALITIES), id="quality", allow_blank=False)
                    yield Button(f"{self._icon('download')}Download", id="download-btn", variant="success", disabled=True)
                    yield Static("", id="status")
                    yield ProgressBar(total=100, show_eta=False, id="overall")
                    yield ProgressBar(total=100, show_eta=False, id="track")
                    yield DataTable(id="results")
            with TabPane(f"{self._icon('settings')}Settings", id="settings"):
                with VerticalScroll():
                    yield Label("Download folder")
                    yield Input(id="set-dir")
                    yield Label("Default audio quality")
                    yield Select(_options(AUDIO_QUALITIES), id="set-quality", allow_blank=False)
                    yield Label("Theme")
                    yield Select(_options(THEMES), id="set-theme", allow_blank=False)
                    yield Label("Browser name (chrome, safari, firefox, edge) or path to cookies.txt")
                    yield Input(id="set-cookies")
                    yield Button(f"{self._icon('save')}Save settings", id="save", variant="primary")
                    yield Static("", id="save-status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#set-dir", Input).value = self.config.get("download_dir", "")
        self.query_one("#set-cookies", Input).value = self.config.get("browser_cookies", "none")
        quality = self.config.get("default_quality", "320")
        if quality in dict(AUDIO_QUALITIES):
            self.query_one("#set-quality", Select).value = quality
        theme = self.config.get("theme", "auto")
        if theme in dict(THEMES):
            self.query_one("#set-theme", Select).value = theme
        self.query_one("#results", DataTable).add_columns("Title", "Status", "Details")
        self._apply_theme(os_is_dark())
        self.set_interval(OS_THEME_POLL_SECONDS, self._poll_os_theme)
        self.title = f"{self._icon('music')}Music Download Manager"
        if not self._font_ready:
            self.notify(f"Installing {fonts.FONT_NAME}…")
            self._install_font()
        else:
            self._font_notice(just_installed=False)
        self._reset_quality_options()
        try:
            downloader.check_ffmpeg()
        except RuntimeError as e:
            self.notify(str(e), severity="error", timeout=15)

    def on_unmount(self) -> None:
        self._stop.set()

    @work(thread=True, group="font", exclusive=True)
    def _install_font(self) -> None:
        try:
            fonts.install()
        except Exception as e:
            self._ui(self.notify, f"Font install failed: {e}", severity="error", timeout=15)
        else:
            self._ui(self._font_notice, True)

    def _font_notice(self, just_installed: bool) -> None:
        """Show the terminal-configuration modal once."""
        if self.config.get("font_notice_shown"):
            return
        self.config = {**self.config, "font_notice_shown": True}
        try:
            cfg.save_config(self.config)
        except OSError:
            pass
        self.push_screen(FontNotice(just_installed))

    def _apply_theme(self, os_dark: bool | None) -> None:
        """Set the app theme from config; 'auto' follows the OS (dark when unknown)."""
        self._os_dark = os_dark
        theme = self.config.get("theme", "auto")
        if theme == "auto":
            theme = AUTO_LIGHT if os_dark is False else AUTO_DARK
        if theme in dict(THEMES):
            self.theme = theme

    @work(thread=True, group="theme", exclusive=True)
    def _poll_os_theme(self) -> None:
        dark = os_is_dark()
        if dark is not None and dark != self._os_dark:
            self._ui(self._apply_theme, dark)

    def action_show_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab

    # ---- helpers ------------------------------------------------------
    @property
    def _mode(self) -> str:
        return "audio" if self.query_one("#mode-audio", RadioButton).value else "video"

    def _reset_quality_options(self) -> None:
        select = self.query_one("#quality", Select)
        qualities = AUDIO_QUALITIES if self._mode == "audio" else VIDEO_QUALITIES
        select.set_options(_options(qualities))
        default = self.config.get("default_quality", "320")
        select.value = default if default in dict(qualities) else qualities[0][0]

    def _set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)

    def _ui(self, fn, *args) -> None:
        """Call fn on the UI thread from a worker thread; no-op once the app is closing."""
        if self._stop.is_set():
            return
        try:
            self.call_from_thread(fn, *args)
        except RuntimeError:
            pass

    @on(RadioSet.Changed, "#mode")
    def _mode_changed(self) -> None:
        self._reset_quality_options()

    @on(Input.Changed, "#url")
    def _url_changed(self) -> None:
        self.query_one("#download-btn", Button).disabled = True
        self._info = None

    # ---- fetch --------------------------------------------------------
    @on(Input.Submitted, "#url")
    @on(Button.Pressed, "#fetch")
    def _fetch(self) -> None:
        url = self.query_one("#url", Input).value.strip()
        if not url or self._busy:
            return
        self._busy = True
        self._info_url = url
        self.query_one("#info", Static).update("Fetching info…")
        self._fetch_worker(url, self.config.get("browser_cookies", "none"))

    @work(thread=True)
    def _fetch_worker(self, url: str, cookies: str) -> None:
        try:
            info = downloader.get_track_info(url, cookies)
        except Exception as e:
            self._ui(self._fetch_done, url, None, str(e))
        else:
            self._ui(self._fetch_done, url, info, None)

    def _fetch_done(self, url: str, info: dict | None, error: str | None) -> None:
        self._busy = False
        if error is not None:
            self.query_one("#info", Static).update(f"[red]Could not fetch info: {error}[/red]")
            return
        if url != self.query_one("#url", Input).value.strip():
            self.query_one("#info", Static).update("")
            return
        self._info = info
        self.query_one("#info", Static).update(_describe(info))
        self.query_one("#download-btn", Button).disabled = False

    # ---- download -----------------------------------------------------
    @on(Button.Pressed, "#download-btn")
    def _download(self) -> None:
        if self._info is None or self._busy:
            return
        self._busy = True
        self.query_one("#download-btn", Button).disabled = True
        self.query_one("#fetch", Button).disabled = True
        self.query_one("#results", DataTable).clear()
        for bar in ("#overall", "#track"):
            self.query_one(bar, ProgressBar).update(total=100, progress=0)
        output_dir = str(Path(self.config.get("download_dir", "~/Music/Songs-Downloaded")).expanduser())
        self._download_worker(
            self._info_url, self._info, self._mode,
            self.query_one("#quality", Select).value, output_dir,
            self.config.get("browser_cookies", "none"),
        )

    @work(thread=True)
    def _download_worker(self, url: str, info: dict, mode: str, quality: str,
                         output_dir: str, cookies: str) -> None:
        def hook(d: dict) -> None:
            if self._stop.is_set():
                raise DownloadCancelled()
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                if total > 0:
                    self._ui(self._set_track_progress, d.get("downloaded_bytes", 0) / total * 100)

        results: list[dict] = []
        try:
            if info["is_playlist"]:
                total = len(info.get("entries") or [])
                self._ui(self._begin_playlist, total)
                results = downloader.download_playlist(
                    url, mode, quality, output_dir,
                    on_track_start=lambda i, title: self._ui(self._track_started, i, total, title),
                    on_track_done=lambda i, r: self._ui(self._track_done, r),
                    progress_hook=hook, cookies=cookies,
                )
            else:
                self._ui(self._set_status, f"Downloading: {info['title']}")
                fn = downloader.download_audio if mode == "audio" else downloader.download_video
                try:
                    path = fn(url, quality, output_dir, progress_hook=hook, cookies=cookies)
                    results.append({"title": info["title"], "path": path, "error": None})
                except Exception as e:
                    results.append({"title": info["title"], "path": None, "error": str(e)})
                self._ui(self._track_done, results[-1])
        except Exception as e:
            results.append({"title": info["title"], "path": None, "error": str(e)})
            self._ui(self._track_done, results[-1])
        self._ui(self._download_finished, results)

    def _set_track_progress(self, percent: float) -> None:
        self.query_one("#track", ProgressBar).update(progress=percent)

    def _begin_playlist(self, total: int) -> None:
        self.query_one("#overall", ProgressBar).update(total=max(total, 1), progress=0)

    def _track_started(self, idx: int, total: int, title: str) -> None:
        self.query_one("#track", ProgressBar).update(progress=0)
        self._set_status(f"[{idx + 1}/{total}] {title}")

    def _track_done(self, result: dict) -> None:
        ok = result["error"] is None
        self.query_one("#results", DataTable).add_row(
            result["title"],
            "[green]✓ OK[/green]" if ok else "[red]✗ FAIL[/red]",
            (result.get("path") or "") if ok else result["error"],
        )
        self.query_one("#overall", ProgressBar).advance(1)
        if ok:
            self.query_one("#track", ProgressBar).update(progress=100)

    def _download_finished(self, results: list[dict]) -> None:
        failed = sum(1 for r in results if r["error"] is not None)
        self._set_status(f"Done: {len(results) - failed} succeeded, {failed} failed.")
        self._busy = False
        self.query_one("#download-btn", Button).disabled = False
        self.query_one("#fetch", Button).disabled = False

    # ---- settings -----------------------------------------------------
    @on(Button.Pressed, "#save")
    def _save(self) -> None:
        self.config = {
            **self.config,
            "download_dir": self.query_one("#set-dir", Input).value.strip()
            or self.config.get("download_dir", "~/Music/Songs-Downloaded"),
            "default_quality": self.query_one("#set-quality", Select).value,
            "theme": self.query_one("#set-theme", Select).value,
            "browser_cookies": self.query_one("#set-cookies", Input).value.strip() or "none",
        }
        try:
            cfg.save_config(self.config)
        except OSError as e:
            self.query_one("#save-status", Static).update(f"[red]Could not save: {e}[/red]")
            return
        self.query_one("#save-status", Static).update("[green]Settings saved.[/green]")
        self._reset_quality_options()
        self._apply_theme(self._os_dark)


def main() -> None:
    MdmApp().run()


if __name__ == "__main__":
    main()
