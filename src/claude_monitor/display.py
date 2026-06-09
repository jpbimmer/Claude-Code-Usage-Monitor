"""Rich live dashboard for Claude usage monitoring."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

PRO_LIMIT = 45


def _progress_bar(used: int, limit: int, width: int = 28) -> Text:
    pct = min(used / limit, 1.0) if limit else 0.0
    filled = round(pct * width)
    empty = width - filled
    color = "red" if pct >= 0.9 else "yellow" if pct >= 0.7 else "green"
    bar = Text()
    bar.append("█" * filled, style=color)
    bar.append("░" * empty, style="bright_black")
    return bar


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def _fmt_duration(td: timedelta) -> str:
    total = max(int(td.total_seconds()), 0)
    h, rem = divmod(total, 3600)
    m = rem // 60
    return f"{h}h {m:02d}m" if h > 0 else f"{m}m"


def _session_panel(local: Optional[Dict[str, Any]]) -> Panel:
    t = Table.grid(padding=(0, 1))
    t.add_column(justify="right", style="dim")
    t.add_column()

    if local is None:
        t.add_row("", Text("No JSONL data found in ~/.claude/projects", style="dim"))
        return Panel(t, title="[bold]Current session", border_style="bright_black", padding=(1, 2))

    ws = local["window_start"].astimezone()
    we = local["window_end"].astimezone()
    now = datetime.now(timezone.utc)
    remaining = we - now

    t.add_row("Window", Text(f"{ws.strftime('%b %d  %I:%M %p')} → {we.strftime('%I:%M %p')}"))

    if local["is_active"]:
        t.add_row("Remaining", Text(_fmt_duration(remaining), style="cyan"))
    else:
        t.add_row("Status", Text("Expired", style="dim"))

    msgs = local["messages"]
    t.add_row("Messages", Text(f"{msgs} / {PRO_LIMIT}  ({round(100 * msgs / PRO_LIMIT)}%)"))
    t.add_row("", _progress_bar(msgs, PRO_LIMIT))

    by_model = local.get("by_model", {})
    if by_model:
        t.add_row("", Text(""))
        model_table = Table(
            show_header=True, header_style="bold dim", box=None, padding=(0, 1)
        )
        model_table.add_column("Model")
        model_table.add_column("Calls", justify="right")
        model_table.add_column("Input", justify="right")
        model_table.add_column("Output", justify="right")
        model_table.add_column("Cache", justify="right")

        for model, stats in sorted(by_model.items(), key=lambda x: -x[1]["calls"]):
            model_table.add_row(
                model,
                str(stats["calls"]),
                _fmt_tokens(stats["input_tokens"]),
                _fmt_tokens(stats["output_tokens"]),
                _fmt_tokens(stats["cache_creation"] + stats["cache_read"]),
            )

        total_calls = sum(s["calls"] for s in by_model.values())
        total_in = sum(s["input_tokens"] for s in by_model.values())
        total_out = sum(s["output_tokens"] for s in by_model.values())
        total_cache = sum(s["cache_creation"] + s["cache_read"] for s in by_model.values())
        model_table.add_row(
            Text("Total", style="bold"),
            Text(str(total_calls), style="bold"),
            Text(_fmt_tokens(total_in), style="bold"),
            Text(_fmt_tokens(total_out), style="bold"),
            Text(_fmt_tokens(total_cache), style="bold"),
        )
        t.add_row("", model_table)

    return Panel(t, title="[bold]Current session", border_style="blue", padding=(1, 2))


def make_dashboard(local: Optional[Dict[str, Any]]) -> Panel:
    now = datetime.now().strftime("%b %d %Y  %I:%M:%S %p")
    header = Text(f"Claude Pro Usage  ·  {now}", style="bold", justify="center")
    return Panel(Group(header, _session_panel(local)), border_style="black", padding=0)
