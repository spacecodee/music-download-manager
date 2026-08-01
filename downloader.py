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


def _download_with_retry(url: str, opts: dict, progress_hook: callable = None) -> str:
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
