"""HTTP time synchronisation for ESP32 MicroPython 1.22 (off the OLED thread)."""

import gc
import time
import network
import urequests
import ujson


class ClockSync:
    def __init__(self, rtc, ssid, password, retry_ms=30000, interval_ms=3600000):
        self.rtc = rtc
        self.ssid = ssid
        self.password = password
        self.retry_ms = retry_ms
        self.interval_ms = interval_ms
        self.synced = False
        self.status = "WAIT SYNC"
        self.last_error = None
        self._next_attempt = None
        self._started = False
        self.wlan = network.WLAN(network.STA_IF)

    def _connect_wifi(self):
        self.wlan.active(True)
        if not self.wlan.isconnected():
            self.wlan.connect(self.ssid, self.password)
            for _ in range(20):
                if self.wlan.isconnected():
                    break
                time.sleep(1)
        if not self.wlan.isconnected():
            raise OSError("Wi-Fi connection timed out")

    def _sync_time(self):
        response = None
        try:
            gc.collect()
            response = urequests.get(
                "https://worldtimeapi.org/api/timezone/Asia/Taipei", timeout=5
            )
            if response.status_code != 200:
                raise OSError("HTTP {}".format(response.status_code))
            data = ujson.loads(response.text)
            value = data["datetime"]
            if not value[19:].endswith("+08:00"):
                raise ValueError("Expected Asia/Taipei UTC+08:00 time")
            year, month, day = int(value[:4]), int(value[5:7]), int(value[8:10])
            hour, minute, second = int(value[11:13]), int(value[14:16]), int(value[17:19])
            weekday = int(data["day_of_week"])
            if not (1 <= month <= 12 and 1 <= day <= 31 and 0 <= weekday <= 6
                    and 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                raise ValueError("Invalid time response")
            # RTC.datetime uses Monday=0; the API uses Sunday=0.
            self.rtc.datetime((year, month, day, (weekday + 6) % 7,
                               hour, minute, second, 0))
        finally:
            if response is not None:
                response.close()

    def poll(self):
        """Perform a due attempt; call from the network worker, never the UI loop."""
        now = time.ticks_ms()
        if self._next_attempt is not None and time.ticks_diff(now, self._next_attempt) < 0:
            return
        try:
            self._connect_wifi()
            self._sync_time()
            self.synced = True
            self.status = "SYNC OK"
            self.last_error = None
            delay = self.interval_ms
        except Exception as error:
            # A failed refresh must keep the last good RTC time.
            self.last_error = str(error)
            self.status = "SYNC RETRY" if self.synced else "WAIT SYNC"
            print("Time sync:", error)
            delay = self.retry_ms
        self._next_attempt = time.ticks_add(time.ticks_ms(), delay)

    def _worker(self):
        while True:
            self.poll()
            time.sleep_ms(200)

    def start(self):
        if self._started:
            return
        try:
            import _thread
            _thread.start_new_thread(self._worker, ())
            self._started = True
        except Exception as error:
            self.last_error = str(error)
            self.status = "SYNC ERROR"
            print("Cannot start time sync worker:", error)
