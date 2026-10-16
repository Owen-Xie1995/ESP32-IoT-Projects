"""Hardware-free behavioural checks; no network or ESP32 is required."""

import calendar
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ("02_NTP_Clock_Basic", "03_Advanced_Clock_Scaling")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeRTC:
    def __init__(self):
        self.value = (2026, 10, 16, 4, 23, 59, 59, 0)
        self.writes = []

    def datetime(self, value=None):
        if value is not None:
            self.writes.append(value)
            self.value = value
        return self.value


class FakeTime:
    PERIOD = 1 << 30

    def __init__(self):
        self.now = 0

    def ticks_ms(self):
        return self.now % self.PERIOD

    def ticks_add(self, value, delta):
        return (value + delta) % self.PERIOD

    def ticks_diff(self, a, b):
        return (a - b + self.PERIOD // 2) % self.PERIOD - self.PERIOD // 2

    def sleep(self, seconds):
        self.now += int(seconds * 1000)


class FakeWLAN:
    def __init__(self):
        self.connected = True

    def active(self, value):
        pass

    def connect(self, ssid, password):
        pass

    def isconnected(self):
        return self.connected


class FakeResponse:
    def __init__(self, status=200, text=None):
        self.status_code = status
        self.text = text if text is not None else json.dumps({
            "datetime": "2026-10-18T23:59:58.123456+08:00", "day_of_week": 0})
        self.closed = False

    def close(self):
        self.closed = True


class FakeOLED:
    def __init__(self):
        self.pixels = []
        self.texts = []
        self.frames = 0

    def fill(self, value):
        self.pixels = []
        self.texts = []

    def pixel(self, x, y, value):
        assert isinstance(x, int) and isinstance(y, int)
        assert 0 <= x < 128 and 0 <= y < 64, (x, y)
        self.pixels.append((x, y))

    def text(self, text, x, y, value=1):
        assert isinstance(x, int) and isinstance(y, int)
        assert 0 <= x and x + len(text) * 8 <= 128, (text, x)
        assert 0 <= y and y + 8 <= 64
        self.texts.append(text)

    def show(self):
        self.frames += 1


class ClockSyncTests(unittest.TestCase):
    def setUp(self):
        self.wlan = FakeWLAN()
        modules = {"network": types.SimpleNamespace(STA_IF=0, WLAN=lambda _: self.wlan),
                   "urequests": types.SimpleNamespace(), "ujson": json}
        with patch.dict(sys.modules, modules):
            self.module = load(EXAMPLES[0] + "/clock_sync.py", "test_clock_sync")
        self.time = FakeTime()
        self.module.time = self.time
        self.rtc = FakeRTC()
        self.sync = self.module.ClockSync(self.rtc, "test", "test")
        self.response = FakeResponse()
        self.request = unittest.mock.Mock(return_value=self.response)
        self.module.urequests.get = self.request

    def test_success_sets_local_time_closes_response_and_waits_for_hourly_refresh(self):
        self.sync.poll()
        self.assertTrue(self.sync.synced)
        self.assertEqual(self.rtc.value, (2026, 10, 18, 6, 23, 59, 58, 0))
        self.assertEqual(self.sync.status, "SYNC OK")
        self.assertTrue(self.response.closed)
        self.assertEqual(self.request.call_args.kwargs, {"timeout": 5})
        self.time.now = 3599999
        self.sync.poll()
        self.assertEqual(self.request.call_count, 1)
        self.time.now = 3600000
        self.sync.poll()
        self.assertEqual(self.request.call_count, 2)

    def test_wifi_timeout_is_bounded_then_retries_after_30_seconds(self):
        self.wlan.connected = False
        self.sync.poll()
        self.assertEqual(self.time.now, 20000)
        self.assertFalse(self.sync.synced)
        self.assertEqual(self.sync.status, "WAIT SYNC")
        self.request.assert_not_called()
        self.wlan.connected = True
        self.time.now = 49999
        self.sync.poll()
        self.request.assert_not_called()
        self.time.now = 50000
        self.sync.poll()
        self.assertTrue(self.sync.synced)

    def test_http_error_and_malformed_body_close_response_without_setting_rtc(self):
        for response in (FakeResponse(503), FakeResponse(text="broken json"),
                         FakeResponse(text=json.dumps({"datetime": "2026-10-18T99:59:58+08:00",
                                                       "day_of_week": 0}))):
            with self.subTest(response=response.text):
                self.sync._next_attempt = None
                self.request.return_value = response
                self.sync.poll()
                self.assertTrue(response.closed)
                self.assertFalse(self.sync.synced)
                self.assertEqual(self.rtc.writes, [])

    def test_request_timeout_keeps_previous_good_time_and_schedules_retry(self):
        self.sync.poll()
        previous = self.rtc.value
        self.request.side_effect = OSError("socket timeout")
        self.time.now = 3600000
        self.sync.poll()
        self.assertTrue(self.sync.synced)
        self.assertEqual(self.sync.status, "SYNC RETRY")
        self.assertEqual(self.rtc.value, previous)
        self.assertEqual(self.sync._next_attempt, 3630000)

    def test_retry_deadline_survives_tick_wrap(self):
        self.time.now = self.time.PERIOD - 100
        self.request.side_effect = OSError("timeout")
        self.sync.poll()
        self.time.now += 29999
        self.sync.poll()
        self.assertEqual(self.request.call_count, 1)
        self.time.now += 1
        self.sync.poll()
        self.assertEqual(self.request.call_count, 2)

    def test_start_schedules_worker_once_without_blocking_caller(self):
        starter = unittest.mock.Mock()
        with patch.dict(sys.modules, {"_thread": types.SimpleNamespace(start_new_thread=starter)}):
            self.sync.start()
            self.sync.start()
        starter.assert_called_once_with(self.sync._worker, ())
        self.request.assert_not_called()

    def test_thread_failure_is_visible_without_setting_invalid_time(self):
        starter = unittest.mock.Mock(side_effect=OSError("no thread"))
        with patch.dict(sys.modules, {"_thread": types.SimpleNamespace(start_new_thread=starter)}):
            self.sync.start()
        self.assertEqual(self.sync.status, "SYNC ERROR")
        self.assertFalse(self.sync.synced)

    def test_standalone_examples_ship_identical_sync_logic(self):
        self.assertEqual((ROOT / EXAMPLES[0] / "clock_sync.py").read_bytes(),
                         (ROOT / EXAMPLES[1] / "clock_sync.py").read_bytes())


class DisplayTests(unittest.TestCase):
    def test_every_calendar_date_and_time_edges_fit_on_128x64(self):
        rtc = FakeRTC()
        sync = types.SimpleNamespace(synced=True, status="SYNC RETRY")
        for example in EXAMPLES:
            font = load(example + "/myfont.py", "test_font")
            with patch.dict(sys.modules, {"myfont": font}):
                module = load(example + "/main.py", "test_main")
            oled = FakeOLED()
            for month in range(1, 13):
                for day in range(1, calendar.monthrange(2026, month)[1] + 1):
                    for hour, minute, second in ((0, 0, 0), (23, 59, 59)):
                        rtc.value = (2026, month, day, day % 7, hour, minute, second, 0)
                        module.render_clock(oled, rtc, sync)
            self.assertEqual(oled.frames, 730)
            self.assertTrue(oled.pixels)

    def test_unsynced_screen_uses_placeholders_and_never_reads_unset_rtc(self):
        for example in EXAMPLES:
            font = load(example + "/myfont.py", "test_font")
            with patch.dict(sys.modules, {"myfont": font}):
                module = load(example + "/main.py", "test_main")
            rtc = types.SimpleNamespace(datetime=unittest.mock.Mock(side_effect=AssertionError("unset RTC")))
            oled = FakeOLED()
            module.render_clock(oled, rtc, types.SimpleNamespace(synced=False, status="WAIT SYNC"))
            self.assertIn("WAIT SYNC", oled.texts)
            self.assertEqual(oled.frames, 1)
            rtc.datetime.assert_not_called()


if __name__ == "__main__":
    unittest.main()
