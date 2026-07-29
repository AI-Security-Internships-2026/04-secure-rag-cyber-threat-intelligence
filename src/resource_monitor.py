"""
resource_monitor.py — samples CPU% and RAM% in the background while a block
of work runs, to measure "how much CPU/RAM did this cost".

Background thread:
psutil.cpu_percent() measures CPU usage OVER A TIME WINDOW, not at an instant
(there's no such thing as "CPU usage right now" — it's always "usage during
the last N seconds"). A single before/after snapshot would miss short bursts.
Sampling repeatedly in the background (every 0.2s here) while the main work
runs gives a much more honest picture — we can report the average AND the
peak, not just one number.

Usage:
    monitor = ResourceMonitor()
    monitor.start()
    ... do the work to be measured ...
    stats = monitor.stop()
    print(stats)  # {"avg_cpu_pct": ..., "max_cpu_pct": ..., "avg_ram_pct": ..., ...}
"""
import psutil
import threading
import time


class ResourceMonitor:
    def __init__(self, sample_interval: float = 0.2):
        self.sample_interval = sample_interval
        self._cpu_samples = []
        self._ram_samples = []
        self._ram_mb_samples = []
        self._stop_flag = threading.Event()
        self._thread = None

    def _sample_loop(self):
        # Prime psutil's internal baseline — the first call to cpu_percent()
        # after this always returns a meaningless 0.0, so we throw it away.
        psutil.cpu_percent(interval=None)

        while not self._stop_flag.is_set():
            # This call BLOCKS for sample_interval seconds and returns the
            # average system-wide CPU% over that exact window.
            cpu = psutil.cpu_percent(interval=self.sample_interval)
            ram = psutil.virtual_memory()

            self._cpu_samples.append(cpu)
            self._ram_samples.append(ram.percent)
            self._ram_mb_samples.append(ram.used / (1024 ** 2))

    def start(self):
        self._cpu_samples = []
        self._ram_samples = []
        self._ram_mb_samples = []
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> dict:
        self._stop_flag.set()
        if self._thread:
            self._thread.join(timeout=self.sample_interval + 1)

        if not self._cpu_samples:
            return {
                "avg_cpu_pct": 0.0, "max_cpu_pct": 0.0,
                "avg_ram_pct": 0.0, "max_ram_pct": 0.0,
                "avg_ram_used_mb": 0.0, "max_ram_used_mb": 0.0,
                "samples_collected": 0,
            }

        return {
            "avg_cpu_pct": round(sum(self._cpu_samples) / len(self._cpu_samples), 2),
            "max_cpu_pct": round(max(self._cpu_samples), 2),
            "avg_ram_pct": round(sum(self._ram_samples) / len(self._ram_samples), 2),
            "max_ram_pct": round(max(self._ram_samples), 2),
            "avg_ram_used_mb": round(sum(self._ram_mb_samples) / len(self._ram_mb_samples), 2),
            "max_ram_used_mb": round(max(self._ram_mb_samples), 2),
            "samples_collected": len(self._cpu_samples),
        }


if __name__ == "__main__":
    print("Baseline (idle) — 2 seconds:")
    m = ResourceMonitor(sample_interval=0.2)
    m.start()
    time.sleep(2)
    print(m.stop())

    print("\nUnder CPU load (busy loop) — 2 seconds:")
    m2 = ResourceMonitor(sample_interval=0.2)
    m2.start()
    t_end = time.time() + 2
    x = 0
    while time.time() < t_end:
        x += 1  # deliberately burn CPU so we can see the numbers move
    print(m2.stop())