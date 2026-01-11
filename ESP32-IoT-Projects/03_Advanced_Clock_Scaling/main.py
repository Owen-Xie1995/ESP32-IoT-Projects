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

def draw_character(data, x, y, scale=0.65):
    if len(data) > 16:  # 假設這是中文字型
        for j in range(16):  # 16行
            for byte_index in range(2):  # 每個字會有兩列資料
                byte_val = data[j * 2 + byte_index]
                for i in range(8):  # 每一行有8位
                    if byte_val & (1 << i):
                        # 取整數後顯示
                        oled.pixel(int(x + byte_index * 8 * scale + i * scale), int(y + j * scale), 1)
    else:  # ASCII字型
        for j in range(16):
            byte_val = data[j]
            for i in range(8):
                if byte_val & (1 << i):
                    # 取整數後顯示
                    oled.pixel(int(x + i * scale), int(y + j * scale), 1)  # 加入縮放（scale）

def display_text_string(oled, text, start_x=0, start_y=0, spacing=0, scale=0.75):
    """顯示字串的函數，縮放設為0.75"""
    x_offset = start_x
    for char in text:
        if char in words:
            char_data = words[char]
            draw_character(char_data, x_offset, start_y, scale)
            x_offset += (16 * scale) + spacing if len(char_data) > 16 else (8 * scale) + spacing
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
        display_text_string(oled, "謝富鈞", 0, 0, scale=0.65)
        display_text_string(oled, "D", 50, 0, scale=0.65)  # 英文用內建
        display_text_string(oled, "11013005", 58, 0, scale=0.65)  # 數字用中文字型

        # 自訂中文字型時間格式顯示
        year, month, day, weekday, hour, minute, second, _ = rtc.datetime()

        # 顯示「年/月/日:」
        date_str = "{}/{}/{}".format(year, month, day)
        display_text_string(oled, "年/月/日:", 0, 25, scale=0.65)
        display_text_string(oled, date_str, 80, 25, scale=0.65)

        # 顯示「星期:」
        display_text_string(oled, "星期:", 0, 40, scale=0.65)
        display_text_string(oled, str(weekday+1), 64, 40, scale=0.65)

        # 顯示「時/分/秒:」
        display_text_string(oled, "時/分/秒:", 0, 55, scale=0.65)
        time_str = "{:02d}:{:02d}:{:02d}".format(hour, minute, second)
        display_text_string(oled, time_str, 64, 55, scale=0.65)

        oled.show()
        time.sleep(1)

