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
        default=config.get("download_dir", "~/Music/Songs-Downloaded"),
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
    choice = Prompt.ask("[cyan]Quality[/cyan]", choices=[str(i + 1) for i in range(len(AUDIO_QUALITIES))], default=default_idx)
    new_quality = AUDIO_QUALITIES[int(choice) - 1][0]
    return {**config, "download_dir": new_dir, "default_quality": new_quality}


def show_error(message: str) -> None:
    console.print(f"[bold red]✗ Error:[/bold red] {message}")


def show_success(message: str) -> None:
    console.print(f"[bold green]✓[/bold green] {message}")
