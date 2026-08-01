# Music Download Manager — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python terminal app with an interactive Rich UI to download audio/video from YouTube (single tracks and playlists) with configurable quality and metadata embedding.

**Architecture:** Four focused modules — `config.py` (settings persistence), `downloader.py` (yt-dlp integration), `ui.py` (Rich menus and progress), and `mdm.py` (orchestrator). Each module has a single responsibility and communicates through well-defined function interfaces.

**Tech Stack:** Python 3.10+, yt-dlp, Rich, ffmpeg (system), pytest

## Global Constraints

- Python 3.10+ required
- Default audio quality: 320 kbps MP3
- Config stored at `~/.config/mdm/config.json`
- Default download dir: `~/Music/Downloads`
- ffmpeg must be installed on the system; app checks at startup
- All terminal output goes through Rich — no bare `print()` calls in ui.py
- Retry logic: 3 attempts with backoff 2s, 4s, 8s per track
- Failed playlist tracks are logged and skipped; download continues

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: working `.venv` with yt-dlp and rich installed; `pytest` runs without errors

- [ ] **Step 1: Create `requirements.txt`**

```
yt-dlp>=2024.1.1
rich>=13.7.0
pytest>=8.0.0
```

- [ ] **Step 2: Create virtual environment and install dependencies**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 3: Verify installs**

```bash
python -c "import yt_dlp; import rich; print('OK')"
```

Expected output: `OK`

- [ ] **Step 4: Create tests directory**

```bash
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 5: Run empty test suite to confirm pytest works**

```bash
pytest tests/ -v
```

Expected: `no tests ran` (exit 0)

- [ ] **Step 6: Commit**

```bash
git add requirements.txt tests/
git commit -m "chore: project scaffolding with dependencies and test setup"
```

---

## Task 2: Config Module (`config.py`)

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `load_config() -> dict` — returns config dict with keys `download_dir` (str) and `default_quality` (str)
  - `save_config(config: dict) -> None` — writes config dict to `~/.config/mdm/config.json`
  - `DEFAULT_CONFIG: dict` — `{"download_dir": "~/Music/Downloads", "default_quality": "320"}`

- [ ] **Step 1: Write failing tests**

Create `tests/test_config.py`:

```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch


def test_load_config_returns_defaults_when_no_file_exists(tmp_path):
    config_path = tmp_path / "config.json"
    with patch("config.CONFIG_PATH", config_path):
        from importlib import reload
        import config as cfg
        reload(cfg)
        result = cfg.load_config()
    assert result["default_quality"] == "320"
    assert result["download_dir"] == str(Path("~/Music/Downloads").expanduser())


def test_load_config_reads_existing_file(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"download_dir": "/custom/path", "default_quality": "192"}))
    with patch("config.CONFIG_PATH", config_path):
        from importlib import reload
        import config as cfg
        reload(cfg)
        result = cfg.load_config()
    assert result["download_dir"] == "/custom/path"
    assert result["default_quality"] == "192"


def test_save_config_writes_json(tmp_path):
    config_path = tmp_path / "config.json"
    with patch("config.CONFIG_PATH", config_path):
        from importlib import reload
        import config as cfg
        reload(cfg)
        cfg.save_config({"download_dir": "/new/path", "default_quality": "128"})
    data = json.loads(config_path.read_text())
    assert data["download_dir"] == "/new/path"
    assert data["default_quality"] == "128"


def test_save_config_creates_parent_dirs(tmp_path):
    config_path = tmp_path / "nested" / "deep" / "config.json"
    with patch("config.CONFIG_PATH", config_path):
        from importlib import reload
        import config as cfg
        reload(cfg)
        cfg.save_config({"download_dir": "/x", "default_quality": "320"})
    assert config_path.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Implement `config.py`**

```python
import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "mdm" / "config.json"

DEFAULT_CONFIG: dict = {
    "download_dir": str(Path("~/Music/Downloads").expanduser()),
    "default_quality": "320",
}


def load_config() -> dict:
    """Load config from disk, returning defaults merged with stored values."""
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()
    try:
        stored = json.loads(CONFIG_PATH.read_text())
        return {**DEFAULT_CONFIG, **stored}
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Write config dict to disk as JSON, creating parent dirs if needed."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add config module with load/save and defaults"
```

---

## Task 3: Downloader Module (`downloader.py`)

**Files:**
- Create: `downloader.py`
- Create: `tests/test_downloader.py`

**Interfaces:**
- Produces:
  - `check_ffmpeg() -> None` — raises `RuntimeError` if ffmpeg not on PATH
  - `get_track_info(url: str) -> dict` — returns `{"title": str, "uploader": str, "duration": int, "is_playlist": bool, "entries": list | None}`
  - `download_audio(url: str, quality: str, output_dir: str, progress_hook: callable) -> str`
  - `download_video(url: str, quality: str, output_dir: str, progress_hook: callable) -> str`
  - `download_playlist(url: str, mode: str, quality: str, output_dir: str, on_track_start: callable, on_track_done: callable) -> list[dict]`
  - `_build_audio_opts(quality: str, output_dir: str) -> dict`
  - `_build_video_opts(quality: str, output_dir: str) -> dict`

- [ ] **Step 1: Write failing tests**

Create `tests/test_downloader.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import downloader


def test_get_track_info_single_track():
    fake_info = {
        "title": "Test Song", "uploader": "Test Artist",
        "duration": 240, "_type": "video", "entries": None,
    }
    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info.return_value = fake_info
    with patch("downloader.yt_dlp.YoutubeDL", return_value=mock_ydl):
        result = downloader.get_track_info("https://youtube.com/watch?v=test")
    assert result["title"] == "Test Song"
    assert result["is_playlist"] is False


def test_get_track_info_playlist():
    fake_info = {
        "title": "My Playlist", "uploader": "Channel",
        "duration": None, "_type": "playlist",
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_downloader.py -v
```

Expected: `ModuleNotFoundError: No module named 'downloader'`

- [ ] **Step 3: Implement `downloader.py`**

```python
import shutil
import time
from pathlib import Path
import yt_dlp

RETRY_DELAYS = [2, 4, 8]


def check_ffmpeg() -> None:
    """Raise RuntimeError if ffmpeg is not found on PATH."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg not found. Install it with: brew install ffmpeg (macOS) "
            "or sudo apt install ffmpeg (Linux)"
        )


def get_track_info(url: str) -> dict:
    """Fetch metadata for a URL without downloading."""
    opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist"}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    is_playlist = info.get("_type") == "playlist"
    return {
        "title": info.get("title", "Unknown"),
        "uploader": info.get("uploader", "Unknown"),
        "duration": info.get("duration"),
        "is_playlist": is_playlist,
        "entries": list(info.get("entries", []) or []) if is_playlist else None,
    }


def _build_audio_opts(quality: str, output_dir: str) -> dict:
    """Build yt-dlp options dict for audio download."""
    codec = "flac" if quality == "flac" else "mp3"
    pp = {"key": "FFmpegExtractAudio", "preferredcodec": codec}
    if codec == "mp3":
        pp["preferredquality"] = quality
    return {
        "format": "bestaudio/best",
        "outtmpl": str(Path(output_dir) / "%(title)s.%(ext)s"),
        "postprocessors": [
            pp,
            {"key": "FFmpegMetadata", "add_metadata": True},
            {"key": "EmbedThumbnail"},
        ],
        "writethumbnail": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
    }


def _build_video_opts(quality: str, output_dir: str) -> dict:
    """Build yt-dlp options dict for video download."""
    fmt = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
    return {
        "format": fmt,
        "outtmpl": str(Path(output_dir) / "%(title)s.%(ext)s"),
        "merge_output_format": "mp4",
        "postprocessors": [{"key": "FFmpegMetadata", "add_metadata": True}],
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
    }


def _download_with_retry(url: str, opts: dict, progress_hook: callable) -> str:
    """Download URL with opts, retrying up to 3 times."""
    if progress_hook:
        opts = {**opts, "progress_hooks": [progress_hook]}
    last_error = None
    for delay in [0] + RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        except yt_dlp.utils.DownloadError as e:
            last_error = e
    raise last_error


def download_audio(url: str, quality: str, output_dir: str, progress_hook: callable = None) -> str:
    """Download audio from URL at given quality. Returns output filepath."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return _download_with_retry(url, _build_audio_opts(quality, output_dir), progress_hook)


def download_video(url: str, quality: str, output_dir: str, progress_hook: callable = None) -> str:
    """Download video from URL at given quality. Returns output filepath."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return _download_with_retry(url, _build_video_opts(quality, output_dir), progress_hook)


def download_playlist(
    url: str, mode: str, quality: str, output_dir: str,
    on_track_start: callable = None, on_track_done: callable = None,
) -> list[dict]:
    """Download all tracks in a playlist. mode: 'audio' or 'video'."""
    info = get_track_info(url)
    results = []
    for i, entry in enumerate(info.get("entries") or []):
        track_url = entry.get("url") or f"https://youtube.com/watch?v={entry.get('id', '')}"
        title = entry.get("title", f"Track {i + 1}")
        if on_track_start:
            on_track_start(i, title)
        try:
            if mode == "audio":
                path = download_audio(track_url, quality, output_dir)
            else:
                path = download_video(track_url, quality, output_dir)
            results.append({"title": title, "path": path, "error": None})
        except Exception as e:
            results.append({"title": title, "path": None, "error": str(e)})
        if on_track_done:
            on_track_done(i, results[-1])
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_downloader.py -v
```

Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add downloader.py tests/test_downloader.py
git commit -m "feat: add downloader module with audio/video/playlist support"
```

---

## Task 4: UI Module (`ui.py`)

**Files:**
- Create: `ui.py`
- Create: `tests/test_ui.py`

**Interfaces:**
- Produces:
  - `console: Console` — shared Rich console instance
  - `show_banner() -> None`
  - `show_main_menu() -> str` — returns `"download"`, `"settings"`, or `"exit"`
  - `prompt_url() -> str` — returns validated YouTube URL
  - `select_mode() -> str` — returns `"audio"` or `"video"`
  - `select_quality(mode: str, default_quality: str) -> str` — returns quality string e.g. `"320"`, `"flac"`, `"1080"`
  - `confirm_download(info: dict) -> bool`
  - `make_progress() -> rich.progress.Progress`
  - `show_summary(results: list[dict]) -> None`
  - `show_settings_menu(config: dict) -> dict`
  - `show_error(message: str) -> None`
  - `show_success(message: str) -> None`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ui.py`:

```python
import pytest
from unittest.mock import patch


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ui.py -v
```

Expected: `ModuleNotFoundError: No module named 'ui'`

- [ ] **Step 3: Implement `ui.py`**

```python
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.text import Text
from rich import box

console = Console()

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


def show_banner() -> None:
    banner = Text()
    banner.append("🎵 ", style="bold")
    banner.append("Music Download Manager", style="bold magenta")
    banner.append("  v1.0", style="dim")
    console.print(Panel(banner, border_style="magenta", padding=(0, 2)))


def show_main_menu() -> str:
    console.print()
    table = Table(show_header=False, box=box.ROUNDED, border_style="magenta", padding=(0, 2))
    table.add_column("num", style="bold cyan", width=4)
    table.add_column("action")
    table.add_row("1", "Download a track or playlist")
    table.add_row("2", "Settings")
    table.add_row("3", "Exit")
    console.print(table)
    choice = Prompt.ask("[bold cyan]Select[/bold cyan]", choices=["1", "2", "3"], default="1")
    return {"1": "download", "2": "settings", "3": "exit"}[choice]


def prompt_url() -> str:
    while True:
        url = Prompt.ask("[bold cyan]YouTube URL[/bold cyan]").strip()
        if url.startswith("http") and ("youtube.com" in url or "youtu.be" in url):
            return url
        show_error("Invalid URL. Must be a youtube.com or youtu.be link.")


def select_mode() -> str:
    console.print()
    table = Table(show_header=False, box=box.ROUNDED, border_style="cyan", padding=(0, 2))
    table.add_column("num", style="bold cyan", width=4)
    table.add_column("mode")
    table.add_row("1", "Audio  (MP3 / FLAC)")
    table.add_row("2", "Video  (MP4)")
    console.print(table)
    choice = Prompt.ask("[bold cyan]Type[/bold cyan]", choices=["1", "2"], default="1")
    return "audio" if choice == "1" else "video"


def select_quality(mode: str, default_quality: str) -> str:
    qualities = AUDIO_QUALITIES if mode == "audio" else VIDEO_QUALITIES
    default_idx = next(
        (str(i + 1) for i, (q, _) in enumerate(qualities) if q == default_quality), "1"
    )
    console.print()
    table = Table(show_header=False, box=box.ROUNDED, border_style="cyan", padding=(0, 2))
    table.add_column("num", style="bold cyan", width=4)
    table.add_column("quality")
    for i, (_, label) in enumerate(qualities):
        suffix = "  [dim](default)[/dim]" if str(i + 1) == default_idx else ""
        table.add_row(str(i + 1), label + suffix)
    console.print(table)
    choices = [str(i + 1) for i in range(len(qualities))]
    choice = Prompt.ask("[bold cyan]Quality[/bold cyan]", choices=choices, default=default_idx)
    return qualities[int(choice) - 1][0]


def confirm_download(info: dict) -> bool:
    console.print()
    if info["is_playlist"]:
        count = len(info.get("entries") or [])
        console.print(f"[bold]Playlist:[/bold] {info['title']}  [dim]({count} tracks)[/dim]")
    else:
        mins, secs = divmod(info.get("duration") or 0, 60)
        console.print(
            f"[bold]Track:[/bold] {info['title']}  "
            f"[dim]by {info['uploader']} · {mins}:{secs:02d}[/dim]"
        )
    return Confirm.ask("[bold cyan]Download?[/bold cyan]", default=True)


def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold magenta]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[cyan]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )


def show_summary(results: list[dict]) -> None:
    console.print()
    table = Table(title="Download Summary", box=box.ROUNDED, border_style="magenta")
    table.add_column("Title", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")
    for r in results:
        if r["error"] is None:
            table.add_row(r["title"], "[green]✓ OK[/green]", r.get("path", ""))
        else:
            table.add_row(r["title"], "[red]✗ FAIL[/red]", r["error"])
    if not results:
        table.add_row("[dim]No results[/dim]", "", "")
    console.print(table)


def show_settings_menu(config: dict) -> dict:
    console.print()
    console.print(Panel("[bold]Settings[/bold]", border_style="magenta"))
    new_dir = Prompt.ask(
        "[cyan]Download folder[/cyan]",
        default=config.get("download_dir", "~/Music/Downloads"),
    )
    console.print()
    console.print("[dim]Default audio quality:[/dim]")
    table = Table(show_header=False, box=box.ROUNDED, border_style="cyan", padding=(0, 2))
    table.add_column("num", style="bold cyan", width=4)
    table.add_column("quality")
    for i, (_, label) in enumerate(AUDIO_QUALITIES):
        table.add_row(str(i + 1), label)
    console.print(table)
    current_q = config.get("default_quality", "320")
    default_idx = next(
        (str(i + 1) for i, (q, _) in enumerate(AUDIO_QUALITIES) if q == current_q), "1"
    )
    choice = Prompt.ask("[cyan]Quality[/cyan]", choices=["1", "2", "3", "4"], default=default_idx)
    new_quality = AUDIO_QUALITIES[int(choice) - 1][0]
    return {**config, "download_dir": new_dir, "default_quality": new_quality}


def show_error(message: str) -> None:
    console.print(f"[bold red]✗ Error:[/bold red] {message}")


def show_success(message: str) -> None:
    console.print(f"[bold green]✓[/bold green] {message}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_ui.py -v
```

Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add ui.py tests/test_ui.py
git commit -m "feat: add Rich UI module with menus, progress, and summary"
```

---

## Task 5: Main Orchestrator (`mdm.py`) + Integration

**Files:**
- Create: `mdm.py`
- Create: `tests/test_mdm.py`

**Interfaces:**
- Consumes: all functions from Tasks 2, 3, 4
- Produces: executable entry point (`python mdm.py`)

- [ ] **Step 1: Write failing tests**

Create `tests/test_mdm.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


def test_main_exits_on_keyboard_interrupt():
    with patch("mdm.ui.show_banner"), \
         patch("mdm.downloader.check_ffmpeg"), \
         patch("mdm.cfg.load_config", return_value={"download_dir": "/tmp", "default_quality": "320"}), \
         patch("mdm.ui.show_main_menu", side_effect=KeyboardInterrupt):
        import mdm
        try:
            mdm.main()
        except SystemExit:
            pass  # acceptable — clean exit


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_mdm.py -v
```

Expected: `ModuleNotFoundError: No module named 'mdm'`

- [ ] **Step 3: Implement `mdm.py`**

```python
#!/usr/bin/env python3
"""Music Download Manager — entry point."""

import sys
import config as cfg
import downloader
import ui


def _run_single_download(url: str, info: dict, mode: str, quality: str, output_dir: str) -> None:
    results = []
    with ui.make_progress() as progress:
        task = progress.add_task(f"Downloading: {info['title']}", total=100)

        def hook(d: dict) -> None:
            if d["status"] == "downloading":
                pct_str = d.get("_percent_str", "0%").strip().rstrip("%")
                try:
                    progress.update(task, completed=float(pct_str))
                except ValueError:
                    pass

        try:
            if mode == "audio":
                path = downloader.download_audio(url, quality, output_dir, progress_hook=hook)
            else:
                path = downloader.download_video(url, quality, output_dir, progress_hook=hook)
            progress.update(task, completed=100)
            results.append({"title": info["title"], "path": path, "error": None})
        except Exception as e:
            results.append({"title": info["title"], "path": None, "error": str(e)})

    ui.show_summary(results)


def _run_playlist_download(url: str, info: dict, mode: str, quality: str, output_dir: str) -> None:
    entries = info.get("entries") or []
    total = len(entries)

    with ui.make_progress() as progress:
        overall = progress.add_task(f"Playlist ({total} tracks)", total=total)
        track_task = progress.add_task("", total=100)

        def on_track_start(idx: int, title: str) -> None:
            progress.reset(track_task)
            progress.update(track_task, description=f"[{idx + 1}/{total}] {title}")

        def on_track_done(idx: int, result: dict) -> None:
            progress.update(overall, advance=1)

        results = downloader.download_playlist(
            url, mode, quality, output_dir,
            on_track_start=on_track_start,
            on_track_done=on_track_done,
        )

    ui.show_summary(results)


def main() -> None:
    ui.show_banner()

    try:
        downloader.check_ffmpeg()
    except RuntimeError as e:
        ui.show_error(str(e))
        sys.exit(1)

    config = cfg.load_config()

    while True:
        try:
            choice = ui.show_main_menu()
        except KeyboardInterrupt:
            ui.show_success("Goodbye!")
            return

        if choice == "exit":
            ui.show_success("Goodbye!")
            return

        if choice == "settings":
            config = ui.show_settings_menu(config)
            cfg.save_config(config)
            ui.show_success("Settings saved.")
            continue

        # choice == "download"
        try:
            url = ui.prompt_url()
            ui.console.print("\n[dim]Fetching info…[/dim]")
            try:
                info = downloader.get_track_info(url)
            except Exception as e:
                ui.show_error(f"Could not fetch info: {e}")
                continue

            mode = ui.select_mode()
            quality = ui.select_quality(mode, config.get("default_quality", "320"))
            output_dir = config.get("download_dir", "~/Music/Downloads")

            if not ui.confirm_download(info):
                continue

            if info["is_playlist"]:
                _run_playlist_download(url, info, mode, quality, output_dir)
            else:
                _run_single_download(url, info, mode, quality, output_dir)

        except KeyboardInterrupt:
            ui.show_error("Download cancelled.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_mdm.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all 22 tests PASS

- [ ] **Step 6: Smoke test — verify the app launches**

```bash
python mdm.py
```

Expected: banner and main menu appear in terminal

- [ ] **Step 7: Commit**

```bash
git add mdm.py tests/test_mdm.py
git commit -m "feat: add main orchestrator and complete integration"
```

---

## Final Checklist

- [ ] All tests pass: `pytest tests/ -v`
- [ ] App runs: `python mdm.py`
- [ ] ffmpeg check works (try `brew install ffmpeg` if not present)
- [ ] Config persists between runs (`~/.config/mdm/config.json` exists after first run)
- [ ] Audio download at 320kbps works on a real URL
- [ ] Playlist download works (use a short playlist for testing)
- [ ] Ctrl+C during download exits cleanly
