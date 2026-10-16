"""128x64 OLED clock with custom scaled Chinese glyphs and HTTP time sync."""

from myfont import words


def draw_character(oled, data, x, y, scale=0.65):
    if scale <= 0:
        raise ValueError("scale must be positive")
    columns = 2 if len(data) > 16 else 1
    for row in range(16):
        for column in range(columns):
            byte = data[row * columns + column]
            for bit in range(8):
                if byte & (1 << bit):
                    oled.pixel(int(x + (column * 8 + bit) * scale),
                               int(y + row * scale), 1)


def display_text_string(oled, text, start_x=0, start_y=0, spacing=0, scale=0.65):
    x = start_x
    for char in text:
        if char in words:
            data = words[char]
            draw_character(oled, data, x, start_y, scale)
            x += (16 if len(data) > 16 else 8) * scale + spacing
        else:
            oled.text(char, int(x), int(start_y), 1)
            x += 8 + spacing


def render_clock(oled, rtc, sync):
    # The network worker can complete its first sync during this frame.
    synced = sync.synced
    oled.fill(0)
    display_text_string(oled, "謝富鈞", 0, 0)
    display_text_string(oled, "D11013005", 50, 0)
    oled.text(sync.status, 0, 15)
    if synced:
        year, month, day, weekday, hour, minute, second, _ = rtc.datetime()
        date_text = "{:04d}/{:02d}/{:02d}".format(year, month, day)
        weekday_text = str(weekday + 1)
        time_text = "{:02d}:{:02d}:{:02d}".format(hour, minute, second)
    else:
        date_text, weekday_text, time_text = "----/--/--", "?", "--:--:--"
    display_text_string(oled, "年/月/日:", 0, 29)
    if synced:
        display_text_string(oled, date_text, 63, 29)
    else:
        oled.text(date_text, 48, 29)
    display_text_string(oled, "星期:", 0, 41)
    display_text_string(oled, weekday_text, 63, 41)
    display_text_string(oled, "時/分/秒:", 0, 53)
    display_text_string(oled, time_text, 63, 53)
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
