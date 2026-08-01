#!/usr/bin/env python3
"""Music Download Manager — entry point."""

import sys
import config as cfg
import downloader
import ui
from pathlib import Path


def _run_single_download(url: str, info: dict, mode: str, quality: str, output_dir: str) -> None:
    results = []
    with ui.make_progress() as progress:
        task = progress.add_task(f"Downloading: {info['title']}", total=100)

        def hook(d: dict) -> None:
            if d["status"] == "downloading":
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    progress.update(task, completed=(downloaded / total) * 100)

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

        def hook(d: dict) -> None:
            if d["status"] == "downloading":
                downloaded = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total_bytes > 0:
                    progress.update(track_task, completed=(downloaded / total_bytes) * 100)

        results = downloader.download_playlist(
            url, mode, quality, output_dir,
            on_track_start=on_track_start,
            on_track_done=on_track_done,
            progress_hook=hook,
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
            try:
                config = ui.show_settings_menu(config)
                cfg.save_config(config)
                ui.show_success("Settings saved.")
            except KeyboardInterrupt:
                ui.show_error("Settings cancelled.")
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
            output_dir = str(Path(output_dir).expanduser())

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
