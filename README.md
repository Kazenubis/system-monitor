# System Monitor

Live CPU, memory, and disk usage in the terminal, updating on an
interval — a quick-glance resource monitor with no dashboard app to
open.

Real output, captured from this actual machine:

```
CPU     [------------------------------]   1.5%
Memory  [##----------------------------]   7.9%  (634.0 MB / 7.8 GB)
Disk    [#########---------------------]  29.6%  (12.4 GB / 252.0 GB)
Peaks   CPU 1.5%  Memory 7.9%  Disk 29.6%
--------------------------------------------------
CPU     [------------------------------]   0.5%
Memory  [##----------------------------]   7.9%  (634.0 MB / 7.8 GB)
Disk    [#########---------------------]  29.6%  (12.4 GB / 252.0 GB)
Peaks   CPU 1.5%  Memory 7.9%  Disk 29.6%
--------------------------------------------------
```

## Features

- Real CPU/memory/disk readings via `psutil`, rendered as ASCII
  progress bars with human-readable byte sizes
- Tracks the peak value seen for each metric across the whole
  monitoring session, shown alongside the live reading
- A failed reading (a transient `psutil` error, an unreadable disk
  path) is caught and reported inline rather than crashing the whole
  monitor — one bad sample shouldn't end the session
- `--count` runs for a fixed number of updates (useful for scripting
  or testing); omit it to run until you `Ctrl+C`

## Tech Stack

Python 3 · `psutil`

## Getting Started

```bash
git clone https://github.com/Kazenubis/system-monitor.git
cd system-monitor
pip install -r requirements.txt
python3 monitor.py --interval 2
```

Run a fixed number of updates instead of forever:

```bash
python3 monitor.py --interval 1 --count 5
```

Run the tests:

```bash
python3 -m unittest test_monitor.py -v
```

## What I Learned

Testing something that reads *real, machine-dependent* values (CPU
load right now, disk usage right now) meant the tests can't assert
exact numbers — only that a reading is a valid percentage (0-100) and
correctly shaped. The more interesting test turned out to be
`test_a_failing_reading_is_reported_not_raised`: patching
`get_disk_usage` to raise confirmed the monitor loop actually catches
a bad reading and keeps going, rather than the whole tool dying on one
transient error — which is the actual "without crashing" requirement,
not just "it ran once successfully."
