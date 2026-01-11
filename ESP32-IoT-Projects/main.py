from machine import Pin, I2C, RTC
import ssd1306
import time
import network
import urequests
import ujson
import gc
from myfont import words

# Wi-Fi credentials
wifi_ssid = 'Wokwi-GUEST'
wifi_password = ''

# I2C 與 OLED 初始化
i2c = I2C(1, scl=Pin(25), sda=Pin(26))
oled = ssd1306.SSD1306_I2C(128, 64, i2c, 0x3c)

rtc = RTC()
newT = 0

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f'Connecting to WiFi: {wifi_ssid}')
        wlan.connect(wifi_ssid, wifi_password)
        for _ in range(20):
            print('.', end='')
            time.sleep(1)
            if wlan.isconnected():
                break
    if wlan.isconnected():
        print('\nWiFi connection OK!')
        print('Network Config =', wlan.ifconfig())
        return True
    else:
        print('\nWiFi connection Error')
        return False

def get_net_time():
    url = 'http://worldtimeapi.org/api/timezone/asia/taipei'
    global newT
    try:
        gc.collect()
        r = urequests.get(url)
        if r.status_code == 200:
            json_data = ujson.loads(r.text)['datetime']
            week_data = ujson.loads(r.text)['day_of_week']
            rtc.init((
                int(json_data[0:4]), int(json_data[5:7]), int(json_data[8:10]),
                int(week_data), int(json_data[11:13]), int(json_data[14:16]),
                int(json_data[17:19]), 0
            ))
            print("Time update OK")
            newT = 1
        else:
            print("Time update fail")
            newT = 0
        r.close()
        return newT == 1
    except Exception as e:
        print(e)
        print("Net time error, retrying WiFi...")
        connect_wifi()
        newT = 0
        return False

def draw_character(data, x, y):
    if len(data) > 16:
        for j in range(16):
            for byte_index in range(2):
                byte_val = data[j * 2 + byte_index]
                for i in range(8):
                    if byte_val & (1 << i):
                        oled.pixel(x + byte_index * 8 + i, y + j, 1)
    else:
        for j in range(16):
            byte_val = data[j]
            for i in range(8):
                if byte_val & (1 << i):
                    oled.pixel(x + i, y + j, 1)

def display_text_string(oled, text, start_x=0, start_y=0, spacing=1):
    x_offset = start_x
    for char in text:
        if char in words:
            char_data = words[char]
            draw_character(char_data, x_offset, start_y)
            x_offset += 16 + spacing if len(char_data) > 16 else 8 + spacing
        else:
            oled.text(char, x_offset, start_y, 1)
            x_offset += 8 + spacing

# 主程式
if __name__ == '__main__':
    connect_wifi()
    get_net_time()

    while True:
        oled.fill(0)

        # 顯示姓名 + 學號（中文 + 數字）
        display_text_string(oled, "謝富鈞", 0, 0)
        display_text_string(oled, "D", 50, 0)           # 英文用內建
        display_text_string(oled, "11013005", 58, 0)    # 數字用中文字型

        # 保留原本 RTC 字串顯示方式
        current_rtc_str = str(rtc.datetime())
        half = len(current_rtc_str) // 2
        oled.text(current_rtc_str[:half], 0, 30, 1)   # 上半行
        oled.text(current_rtc_str[half:], 0, 45, 1)   # 下半行

        oled.show()
        time.sleep(1)