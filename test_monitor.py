"""
Tests for monitor.py — real psutil readings (checked for valid
range/shape, since exact values are system-dependent), formatting, and
the actual DoD check: the update loop runs on an interval for multiple
iterations without crashing, even when a reading fails.
"""

import unittest
from unittest.mock import patch

from monitor import (
    PeakTracker,
    format_bar,
    format_bytes,
    get_cpu_usage,
    get_disk_usage,
    get_memory_usage,
    render_snapshot,
    run_monitor,
)


class TestRealReadings(unittest.TestCase):
    """These call the real psutil functions — the exact numbers vary by
    machine, so what's checked is that the readings are valid and
    correctly shaped, not a specific value."""

    def test_cpu_usage_is_a_valid_percentage(self):
        cpu = get_cpu_usage(interval=0.1)
        self.assertGreaterEqual(cpu, 0.0)
        self.assertLessEqual(cpu, 100.0)

    def test_memory_usage_has_expected_keys_and_valid_percent(self):
        memory = get_memory_usage()
        self.assertIn("total", memory)
        self.assertIn("used", memory)
        self.assertIn("percent", memory)
        self.assertGreaterEqual(memory["percent"], 0.0)
        self.assertLessEqual(memory["percent"], 100.0)
        self.assertGreater(memory["total"], 0)

    def test_disk_usage_has_expected_keys_and_valid_percent(self):
        disk = get_disk_usage("/")
        self.assertIn("total", disk)
        self.assertIn("used", disk)
        self.assertIn("percent", disk)
        self.assertGreaterEqual(disk["percent"], 0.0)
        self.assertLessEqual(disk["percent"], 100.0)


class TestFormatBytes(unittest.TestCase):
    def test_bytes_and_kb(self):
        self.assertEqual(format_bytes(500), "500.0 B")
        self.assertEqual(format_bytes(2048), "2.0 KB")

    def test_gb(self):
        self.assertEqual(format_bytes(3 * 1024 ** 3), "3.0 GB")


class TestFormatBar(unittest.TestCase):
    def test_zero_percent_is_all_dashes(self):
        bar = format_bar(0, width=10)
        self.assertEqual(bar, "[----------]   0.0%")

    def test_hundred_percent_is_all_hashes(self):
        bar = format_bar(100, width=10)
        self.assertEqual(bar, "[##########] 100.0%")

    def test_clamps_out_of_range_values(self):
        # a transient psutil hiccup could report slightly outside 0-100
        over = format_bar(150, width=10)
        under = format_bar(-10, width=10)
        self.assertIn("100.0%", over)
        self.assertIn("0.0%", under)


class TestPeakTracker(unittest.TestCase):
    def test_tracks_maximum_across_updates(self):
        peaks = PeakTracker()
        peaks.update(cpu_percent=10, memory_percent=40, disk_percent=60)
        peaks.update(cpu_percent=80, memory_percent=30, disk_percent=65)
        self.assertEqual(peaks.peak_cpu, 80)
        self.assertEqual(peaks.peak_memory, 40)
        self.assertEqual(peaks.peak_disk, 65)


class TestRenderSnapshot(unittest.TestCase):
    def test_includes_cpu_memory_and_disk_lines(self):
        memory = {"total": 8 * 1024 ** 3, "used": 4 * 1024 ** 3, "percent": 50.0}
        disk = {"total": 100 * 1024 ** 3, "used": 60 * 1024 ** 3, "percent": 60.0}
        text = render_snapshot(45.0, memory, disk)
        self.assertIn("CPU", text)
        self.assertIn("Memory", text)
        self.assertIn("Disk", text)
        self.assertIn("45.0%", text)

    def test_includes_peaks_line_when_given(self):
        memory = {"total": 1, "used": 1, "percent": 20.0}
        disk = {"total": 1, "used": 1, "percent": 30.0}
        peaks = PeakTracker()
        peaks.update(20.0, 20.0, 30.0)
        text = render_snapshot(20.0, memory, disk, peaks=peaks)
        self.assertIn("Peaks", text)


class TestRunMonitor(unittest.TestCase):
    """The actual DoD check: correct live readings, updates on an
    interval, without crashing — run for several iterations against
    real psutil calls, with sleep mocked out so the test is instant."""

    def test_runs_for_the_requested_count_without_crashing(self):
        outputs = []
        peaks = run_monitor(interval=1.0, count=4, sink=outputs.append, sleep_fn=lambda s: None)
        self.assertEqual(len(outputs), 4)
        for output in outputs:
            self.assertIn("CPU", output)
        self.assertIsInstance(peaks, PeakTracker)

    def test_sleep_is_called_with_the_remaining_interval(self):
        sleep_calls = []
        run_monitor(interval=3.0, count=2, sink=lambda text: None, sleep_fn=sleep_calls.append)
        # get_cpu_usage already blocks for min(interval, 1.0)=1.0s, so
        # only the remaining 2.0s should be an explicit sleep call
        self.assertTrue(all(abs(call - 2.0) < 0.01 for call in sleep_calls))

    def test_a_failing_reading_is_reported_not_raised(self):
        outputs = []
        with patch("monitor.get_disk_usage", side_effect=OSError("disk unavailable")):
            run_monitor(interval=1.0, count=2, sink=outputs.append, sleep_fn=lambda s: None)
        self.assertEqual(len(outputs), 2)
        for output in outputs:
            self.assertIn("monitor error", output)

    def test_zero_count_runs_no_iterations(self):
        outputs = []
        run_monitor(interval=1.0, count=0, sink=outputs.append, sleep_fn=lambda s: None)
        self.assertEqual(outputs, [])


if __name__ == "__main__":
    unittest.main()
