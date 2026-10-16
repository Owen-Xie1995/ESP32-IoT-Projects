"""Basic OLED clock; time comes from an HTTP API, not the NTP protocol."""

from myfont import words


def draw_character(oled, data, x, y):
    columns = 2 if len(data) > 16 else 1
    for row in range(16):
        for column in range(columns):
            byte = data[row * columns + column]
            for bit in range(8):
                if byte & (1 << bit):
                    oled.pixel(x + column * 8 + bit, y + row, 1)


def display_text_string(oled, text, start_x=0, start_y=0, spacing=1):
    x = start_x
    for char in text:
        if char in words:
            data = words[char]
            draw_character(oled, data, x, start_y)
            x += (16 if len(data) > 16 else 8) + spacing
        else:
            oled.text(char, x, start_y, 1)
            x += 8 + spacing


def render_clock(oled, rtc, sync):
    oled.fill(0)
    display_text_string(oled, "謝富鈞", 0, 0)
    oled.text("D11013005", 56, 0)
    oled.text(sync.status, 0, 18)
    if sync.synced:
        year, month, day, _, hour, minute, second, _ = rtc.datetime()
        oled.text("{:04d}/{:02d}/{:02d}".format(year, month, day), 0, 32)
        oled.text("{:02d}:{:02d}:{:02d}".format(hour, minute, second), 0, 46)
    else:
        oled.text("----/--/--", 0, 32)
        oled.text("--:--:--", 0, 46)
    oled.show()


def main():
    from machine import Pin, I2C, RTC
    import ssd1306
    import time
    from clock_sync import ClockSync

    oled = ssd1306.SSD1306_I2C(128, 64, I2C(1, scl=Pin(25), sda=Pin(26)))
    rtc = RTC()
    sync = ClockSync(rtc, "Wokwi-GUEST", "")  # Change for a physical ESP32.
    sync.start()
    while True:
        render_clock(oled, rtc, sync)
        time.sleep(1)


if __name__ == "__main__":
    main()
