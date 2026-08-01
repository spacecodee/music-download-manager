# Music Download Manager — Design Spec

**Date:** 2026-08-01  
**Status:** Approved  
**Tech stack:** Python 3, yt-dlp, Rich, ffmpeg

---

## Overview

A terminal application for downloading music and video from YouTube. Supports single tracks and full playlists. Features an interactive terminal UI with menus, progress bars, and colored output. Embeds metadata (title, artist, album, cover art) into downloaded files.

---

## Architecture

```
music-download-manager/
├── mdm.py              # Entry point — launches interactive UI
├── downloader.py       # Download logic via yt-dlp
├── config.py           # Config management (folder, default quality)
├── ui.py               # Rich-based UI components and menus
└── requirements.txt    # Python dependencies
```

Each module has a single responsibility and communicates through well-defined interfaces. No circular imports.

---

## User Flow

1. **Main menu** — Options: Download Track, Download Playlist, Settings, Exit
2. **Enter URL** — User pastes a YouTube URL; the app auto-detects if it's a single track or playlist
3. **Select type** — Audio (MP3/FLAC) or Video (MP4)
4. **Select quality**
   - Audio: `320kbps` (default), `192kbps`, `128kbps`, `FLAC`
   - Video: `1080p`, `720p`, `480p`, `360p`
5. **Confirmation** — Displays track title (or playlist name + track count) before downloading
6. **Download with progress** — Per-track progress bar; overall playlist progress
7. **Summary** — Lists downloaded files, elapsed time, and any errors

---

## Components

### `config.py`
- Reads/writes `~/.config/mdm/config.json`
- Stores: `download_dir` (default: `~/Music/Downloads`), `default_quality` (default: `320`)
- Provides `load_config()` and `save_config(config: dict)` functions

### `downloader.py`
- `get_track_info(url) -> dict` — fetches title, uploader, duration via yt-dlp `extract_info`
- `download_audio(url, quality, output_dir, progress_hook)` — downloads and converts audio; embeds ID3 tags + thumbnail
- `download_video(url, quality, output_dir, progress_hook)` — downloads video at selected resolution
- `download_playlist(url, mode, quality, output_dir, progress_hooks)` — iterates tracks, calls audio/video downloader per track; skips and logs failed tracks without aborting
- Retry logic: 3 automatic retries per track on network error

### `ui.py`
- `show_main_menu() -> str` — renders main menu with Rich, returns user choice
- `prompt_url() -> str` — prompts for URL input with validation
- `select_quality(mode) -> str` — renders quality selection menu based on audio/video mode
- `show_progress(task_name)` — returns a Rich `Progress` context manager
- `show_summary(results: list[dict])` — prints download summary table

### `mdm.py`
- Orchestrates the flow: loads config → shows menu → calls ui/downloader functions → shows summary
- Handles `KeyboardInterrupt` gracefully (Ctrl+C exits cleanly)

---

## Data Flow

```
mdm.py
  │
  ├── config.py          (load/save settings)
  ├── ui.py              (all user interaction)
  └── downloader.py      (all download/conversion logic)
       └── yt-dlp + ffmpeg (external tools)
```

---

## Error Handling

- **Invalid URL**: validated before fetching info; user shown clear error and prompted again
- **Network error**: 3 retries with exponential backoff (2s, 4s, 8s)
- **Failed track in playlist**: logged to summary; remaining tracks continue downloading
- **ffmpeg not found**: detected at startup; user shown installation instructions and app exits gracefully
- **Keyboard interrupt (Ctrl+C)**: current download is cancelled cleanly; partial file is deleted

---

## Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| `yt-dlp` | latest | YouTube download and metadata extraction |
| `rich` | latest | Terminal UI (colors, menus, progress bars, tables) |
| `ffmpeg` | system | Audio conversion, metadata embedding, thumbnail embedding |

`ffmpeg` must be installed on the system (not a Python package). The app checks for it at startup.

---

## Configuration File

Location: `~/.config/mdm/config.json`

```json
{
  "download_dir": "~/Music/Downloads",
  "default_quality": "320"
}
```

---

## Quality Options

### Audio
| Label | yt-dlp format | Notes |
|---|---|---|
| 320 kbps (default) | `bestaudio` + postprocessor to mp3 at 320k | Highest quality MP3 |
| 192 kbps | `bestaudio` + postprocessor to mp3 at 192k | Good quality, smaller size |
| 128 kbps | `bestaudio` + postprocessor to mp3 at 128k | Smallest audio size |
| FLAC (lossless) | `bestaudio` + postprocessor to flac | Best quality, largest size |

### Video
| Label | yt-dlp format | Notes |
|---|---|---|
| 1080p | `bestvideo[height<=1080]+bestaudio` | Full HD |
| 720p | `bestvideo[height<=720]+bestaudio` | HD |
| 480p | `bestvideo[height<=480]+bestaudio` | SD |
| 360p | `bestvideo[height<=360]+bestaudio` | Low quality |

---

## Out of Scope

- Authentication / login for age-restricted videos
- Downloading from platforms other than YouTube
- Scheduling or queue management
- GUI or web interface
