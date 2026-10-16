# ESP32 OLED 中文顯示與網路時鐘

使用 ESP32、SSD1306 OLED 與 MicroPython 練習中文字型、I²C 顯示和網路對時。三個目錄各自可以上傳執行，從固定文字逐步加入時鐘與縮小字型。

| 範例 | 內容 | 原始 Wokwi 專案 |
| --- | --- | --- |
| [01：中文顯示](01_OLED_Chinese_Display) | 解析 16×16 中文與 8×16 英數點陣 | [開啟模擬](https://wokwi.com/projects/428149100195031041) |
| [02：基本網路時鐘](02_NTP_Clock_Basic) | Wi-Fi、HTTP API、RTC、連線狀態 | [開啟模擬](https://wokwi.com/projects/428154110092253185) |
| [03：縮放字型時鐘](03_Advanced_Clock_Scaling) | 將姓名、日期、星期和時間排入 128×64 螢幕 | [開啟模擬](https://wokwi.com/projects/428162165364620289) |

02 的目錄名稱 `02_NTP_Clock_Basic` 保留原名，方便對照舊連結；程式實際透過 **WorldTimeAPI 的 HTTPS REST API** 取得台北時間，沒有實作 NTP 協定。

## 執行

設定檔使用 ESP32 DevKit C V4、MicroPython **v1.22.0**（`micropython-20231227-v1.22.0`）。OLED 為 128×64、I²C 位址 `0x3c`。

| OLED | ESP32 |
| --- | --- |
| VCC | 3V3 |
| GND | GND |
| SCL | GPIO 25 |
| SDA | GPIO 26 |

1. 選一個範例。用 Wokwi 開啟上表連結，建立自己的副本；或透過 Thonny 將 MicroPython v1.22.0 燒錄至實體 ESP32。
2. 將該目錄的 `main.py`、`myfont.py`、`ssd1306.py` 放在裝置根目錄。02、03 還需複製 **`clock_sync.py`**。Wokwi 另以同目錄 `diagram.json` 更新接線。
3. 02、03 使用 `network`、`_thread`、`ujson`、`ussl` 和 `urequests`。官方 ESP32 MicroPython v1.22.0 已附這些模組，通常不用另外安裝套件；自訂韌體請先依下方方式檢查。
4. Wokwi 使用 `Wokwi-GUEST` 與空密碼。實體板請修改 `main.py` 中 `ClockSync(rtc, SSID, PASSWORD)` 的參數，個人 Wi-Fi 密碼勿提交到 Git。
5. 重啟裝置。01 顯示固定姓名／學號；02、03 先顯示 `WAIT SYNC` 和日期／時間佔位符，對時成功後才顯示實際時間。

上表是原始模擬專案連結，遠端內容不會隨此倉庫更新；請依第 2 步替換檔案後再測試。

### 檢查韌體模組

在 ESP32 的 REPL（例如 Thonny 下方 Shell）執行：

```python
import network, _thread, ujson, ussl, urequests
print(urequests.get)
```

官方 v1.22.0 的 [ESP32 模組清單](https://github.com/micropython/micropython/blob/v1.22.0/ports/esp32/boards/manifest.py) 會加入 [networking 套件組](https://github.com/micropython/micropython-lib/blob/v1.22.0/micropython/bundles/bundle-networking/manifest.py)，其中 `urequests` 轉接至 `requests`；該版 [requests 原始碼](https://github.com/micropython/micropython-lib/blob/v1.22.0/python-ecosys/requests/requests/__init__.py) 已支援本範例的 `timeout=5`。

若只有 `urequests`／`requests` 缺少，或出現不支援 `timeout` 的錯誤，請從同一版官方來源下載下面兩個檔案，用 Thonny 存到 ESP32 根目錄；Wokwi 則將兩個檔案加入專案後重新執行：

- [requests 原始檔](https://raw.githubusercontent.com/micropython/micropython-lib/v1.22.0/python-ecosys/requests/requests/__init__.py) → 存成 **`requests.py`**。
- [urequests 相容層](https://raw.githubusercontent.com/micropython/micropython-lib/v1.22.0/micropython/urequests/urequests.py) → 存成 **`urequests.py`**。

重新啟動後再執行上面的檢查。這裡固定使用 v1.22.0 的來源，避免安裝新版套件時引入舊韌體沒有的 API。若缺的是 `network`、`_thread`、`ujson` 或 `ussl`，請改用官方 ESP32 v1.22.0 韌體；它們不是透過桌面 `pip` 補裝的依賴。硬體程式也不能直接用桌面 CPython 執行。

## 對時與故障處理

網路工作由 ESP32 `_thread` 在背景執行，OLED 在主執行緒每秒更新。Wi-Fi 每次最多等 20 秒；HTTP 請求設定 5 秒 socket timeout。首次成功前顯示 `WAIT SYNC`，失敗後每 30 秒重試；成功後每小時校時。後續失敗保留最後成功的 RTC 時間並顯示 `SYNC RETRY`。`SYNC ERROR` 表示無法啟動背景執行緒，詳細錯誤會輸出到序列埠。

HTTP timeout 不能保證限制底層 DNS／TLS 的總耗時；背景執行緒用來讓這類等待不直接阻塞畫面。外部 API、Wi-Fi、韌體模組與實體接線都可能影響執行。RTC 在斷電後不保證保留時間。兩個時鐘目錄各附一份相同的 `clock_sync.py`，讓範例可獨立上傳；測試會檢查兩份保持一致。

## 本機檢查

Python 3.10 以上即可執行，不需要 ESP32、第三方套件或網路：

```sh
python3 -m unittest discover -s tests -v
```

測試用假的 OLED、RTC、Wi-Fi、HTTP 與時鐘，檢查 2026 年每個日期、午夜與 23:59:59 的畫面邊界、尚未校時的佔位符、失敗重試、每小時校時、tick 回繞與 HTTP 資源關閉。GitHub Actions 執行同一組檢查。

目前驗證限於上述無硬體測試；本次修改尚未在實體 ESP32 或 Wokwi 執行。字庫只包含範例所用字元，縮放是逐像素取整數，沒有抗鋸齒，也不會自動換行。倉庫目前沒有實機效能數據或展示影片。
