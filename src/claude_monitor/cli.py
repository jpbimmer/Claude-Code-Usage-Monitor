"""Live dashboard — reloads local JSONL every 10s, refreshes display every second."""

import time
from typing import Optional

from rich.live import Live

from claude_monitor.display import make_dashboard
from claude_monitor.reader import load_current_window

LOCAL_INTERVAL = 10


def run(data_path: Optional[str] = None, refresh_rate: float = 1.0) -> None:
    last_local = 0.0
    local_data = None

    with Live(refresh_per_second=int(1 / refresh_rate), screen=True) as live:
        try:
            while True:
                now = time.monotonic()
                if now - last_local >= LOCAL_INTERVAL:
                    local_data = load_current_window(data_path)
                    last_local = now
                live.update(make_dashboard(local_data))
                time.sleep(refresh_rate)
        except KeyboardInterrupt:
            pass
