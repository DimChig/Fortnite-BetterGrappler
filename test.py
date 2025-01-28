import time

import winsound

from main import get_pixel_color, get_grappler_type_from_screen

while True:
    time.sleep(0.1)
    print(f"p1: {get_pixel_color(1553, 943)}")  # red part
    print(f"p2: {get_pixel_color(1553, 968)}")
    type = get_grappler_type_from_screen()
    if type is not None:
        print(type)
        winsound.Beep(1000, 50)