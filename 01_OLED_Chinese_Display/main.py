from machine import Pin,I2C
import ssd1306
import time
from framebuf import FrameBuffer, MONO_HMSB
from myfont import words

# ESP32 Pin assignment 
i2c = I2C(1, scl=Pin(25), sda=Pin(26))

oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

def draw_character(data, x, y):
    #print(len(data))
    if len(data) > 16:  #處理中文字
        for j in range(16):  # Rows
            for byte_index in range(2):  # Each row has 2 bytes of data
                byte_val = data[j * 2 + byte_index]  # Accessing the right byte
                for i in range(8):  # Bits in a byte
                    if byte_val & (1 << (i)):
                        oled.pixel(x + byte_index * 8 + i, y + j, 1)
    else:  #處理 ASCII 字
         for j in range(16):  # Rows
            for byte_index in range(1):  # Each row has 1 bytes of data
                byte_val = data[j * 1 + byte_index]  # Accessing the right byte
                for i in range(8):  # Bits in a byte
                    if byte_val & (1 << (i)):
                        oled.pixel(x + byte_index * 8 + i, y + j, 1)       

def display_text_string(oled, text, start_x=0, start_y=0, spacing=1):
    """Displays a string of characters on the OLED."""
    x_offset = start_x
    for char in text:
        if char in words:
            char = words[char]
            data = [] 
            for j in range(len(char)):
              data.append( char[j])
            draw_character(data, x_offset, start_y)
            #print(len(data))
            if len(data) > 16:  #處理中文字
                x_offset += 16 + spacing  # Move the x-offset for the next character
            else:  #處理 ASCII 字
                x_offset += 7   # Move the x-offset for the next character           

# Clear display
oled.fill(0)

spacing = 0
display_text_string(oled, "謝富鈞 D11013005", start_x=0, start_y=5)
#oled.text(" B10713999",45,10)
oled.show()
