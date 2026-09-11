"""
System Monitor — live CPU/memory/disk usage in the terminal, updating
on an interval, via psutil.
"""

import argparse
import time

import psutil

BAR_WIDTH = 30


def get_cpu_usage(interval=0.5):
    """Blocking for `interval` seconds — psutil needs a real sampling
    window to report a meaningful (non-zero-on-first-call) percentage."""
    return psutil.cpu_percent(interval=interval)


def get_per_core_usage(interval=0.5):
    return psutil.cpu_percent(interval=interval, percpu=True)


def get_memory_usage():
    vm = psutil.virtual_memory()
    return {"total": vm.total, "used": vm.used, "percent": vm.percent}


def get_disk_usage(path="/"):
    du = psutil.disk_usage(path)
    return {"total": du.total, "used": du.used, "percent": du.percent}


def format_bytes(num_bytes):
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024


def format_bar(percent, width=BAR_WIDTH):
    percent = max(0.0, min(100.0, percent))
    filled = round(width * percent / 100)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {percent:5.1f}%"


class PeakTracker:
    """Tracks the highest CPU/memory/disk percentage seen across calls
    to `update` in this monitoring session."""

    def __init__(self):
        self.peak_cpu = 0.0
        self.peak_memory = 0.0
        self.peak_disk = 0.0

    def update(self, cpu_percent, memory_percent, disk_percent):
        self.peak_cpu = max(self.peak_cpu, cpu_percent)
        self.peak_memory = max(self.peak_memory, memory_percent)
        self.peak_disk = max(self.peak_disk, disk_percent)


def render_snapshot(cpu_percent, memory, disk, peaks=None):
    lines = [
        f"CPU     {format_bar(cpu_percent)}",
        f"Memory  {format_bar(memory['percent'])}  ({format_bytes(memory['used'])} / {format_bytes(memory['total'])})",
        f"Disk    {format_bar(disk['percent'])}  ({format_bytes(disk['used'])} / {format_bytes(disk['total'])})",
    ]
    if peaks is not None:
        lines.append(
            f"Peaks   CPU {peaks.peak_cpu:.1f}%  Memory {peaks.peak_memory:.1f}%  Disk {peaks.peak_disk:.1f}%"
        )
    return "\n".join(lines)


def run_monitor(interval=1.0, count=None, disk_path="/", sink=print, sleep_fn=time.sleep):
    """Runs the monitoring loop. `count=None` means run forever (real
    interactive use); a finite `count` is what makes this testable
    without hanging. Any per-iteration error is caught and reported
    through `sink` rather than crashing the whole loop — a transient
    psutil read failure shouldn't kill an otherwise-working monitor."""
    peaks = PeakTracker()
    iterations = 0

    while count is None or iterations < count:
        try:
            cpu_percent = get_cpu_usage(interval=min(interval, 1.0))
            memory = get_memory_usage()
            disk = get_disk_usage(disk_path)
            peaks.update(cpu_percent, memory["percent"], disk["percent"])
            sink(render_snapshot(cpu_percent, memory, disk, peaks))
        except Exception as e:  # noqa: BLE001 - deliberately broad: keep monitoring alive
            sink(f"[monitor error: {e}]")

        iterations += 1
        remaining_sleep = interval - min(interval, 1.0)
        if remaining_sleep > 0 and (count is None or iterations < count):
            sleep_fn(remaining_sleep)

    return peaks


def main():
    parser = argparse.ArgumentParser(description="System Monitor")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between updates")
    parser.add_argument("--count", type=int, default=None, help="Number of updates (default: run forever)")
    parser.add_argument("--disk-path", default="/")
    args = parser.parse_args()

    def sink(text):
        print(text)
        print("-" * 50)

    try:
        run_monitor(interval=args.interval, count=args.count, disk_path=args.disk_path, sink=sink)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
