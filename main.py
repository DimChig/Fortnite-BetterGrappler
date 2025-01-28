import os
import time
import random
import threading
import mss
import win32api
import win32con
import winsound
import keyboard
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw

# Global variables
last_action_time = 0
action_interval = 0.5  # Minimum interval in seconds to prevent spam

# Flags
running = True  # Controls whether the main loop is running
listener_thread = None

# MOST IMPORTANT
DELAY_SWAP = 0.3

# Step delays and random spread settings
delay_left_click = 0.02
spread_left_click = 0.002

delay_swap_slot = 0.001
spread_swap_slot = delay_swap_slot / 2

delay_control_key_press_down = 0.1
spread_control_key_press_down = 0.05

delay_control_key_press_up = 0.1
spread_control_key_press_up = delay_control_key_press_up / 2

delay_key_press_down = 0.01
spread_key_press_down = 0.001


from enum import Enum
class GrapplerType(Enum):
    REGULAR = 1
    MYTHIC_INFINITE = 2
    MYTHIC_BLACK = 3


grappler_type = GrapplerType.REGULAR
grappler_fire_rate_safe_margin = 0.01
grappler_fire_rates = {
    GrapplerType.REGULAR: 1 + grappler_fire_rate_safe_margin,
    GrapplerType.MYTHIC_INFINITE: 1 / 0.65 + grappler_fire_rate_safe_margin,
    GrapplerType.MYTHIC_BLACK: 0 + grappler_fire_rate_safe_margin
}


def get_pixel_color(x, y):
    """Get the color of a specific pixel at (x, y)."""
    with mss.mss() as sct:
        monitor = {"top": y, "left": x, "width": 1, "height": 1}
        pixel = sct.grab(monitor)
        return pixel.pixel(0, 0)


def is_pixel_color(coords, target_color):
    x, y = coords
    pixel_color = get_pixel_color(x, y)
    return pixel_color == target_color


def is_right_click_pressed():
    """Check if the right mouse button is pressed."""
    return win32api.GetKeyState(win32con.VK_RBUTTON) < 0


def get_random_delay(base_delay, spread):
    """Get a randomized delay based on the target delay and spread."""
    return random.uniform(base_delay - spread, base_delay + spread)


def sleep_mini():
    time.sleep(get_random_delay(delay_key_press_down, spread_key_press_down))


last_grappler_keypress_time = 0
key_held_grappler = False
last_ctrl_keypress_time = 0
key_held_ctrl = False
last_rmb_keypress_time = 0
mouse_right_button_held = False


def keyboard_listener():
    """Listener for key presses involving '3', 'Ctrl', and the Right Mouse Button."""
    global last_grappler_keypress_time, key_held_grappler
    global last_ctrl_keypress_time, key_held_ctrl
    global last_rmb_keypress_time, mouse_right_button_held

    # Event for pressing '3' with or without modifiers
    def on_press_3(event):
        global last_grappler_keypress_time, key_held_grappler
        if not key_held_grappler:  # Only trigger once per press
            last_grappler_keypress_time = time.time()
            key_held_grappler = True

    def on_release_3(event):
        global key_held_grappler
        key_held_grappler = False

    # Hook key press and release events for '3'
    keyboard.on_press_key('3', on_press_3)
    keyboard.on_release_key('3', on_release_3)

    # Event for pressing and releasing 'Ctrl'
    def on_press_ctrl(event):
        global last_ctrl_keypress_time, key_held_ctrl
        if not key_held_ctrl:  # Only trigger once per press
            last_ctrl_keypress_time = time.time()
            key_held_ctrl = True

    def on_release_ctrl(event):
        global key_held_ctrl
        key_held_ctrl = False

    # Hook key press and release events for 'Ctrl'
    keyboard.on_press_key('ctrl', on_press_ctrl)
    keyboard.on_release_key('ctrl', on_release_ctrl)

    # Event for Right Mouse Button (RMB)
    def on_press_rmb(event):
        global last_rmb_keypress_time, mouse_right_button_held
        if not mouse_right_button_held:  # Only trigger once per press
            last_rmb_keypress_time = time.time()
            mouse_right_button_held = True

    def on_release_rmb(event):
        global mouse_right_button_held
        mouse_right_button_held = False

    # Use a mouse listener for Right Mouse Button
    def mouse_listener():
        from pynput.mouse import Listener

        with Listener(on_click=lambda x, y, button, pressed: (
                on_press_rmb(None) if pressed and button.name == "right" else on_release_rmb(None)
        )) as listener:
            listener.join()

    # Start mouse listener in a thread
    mouse_thread = threading.Thread(target=mouse_listener, daemon=True)
    mouse_thread.start()


def is_grappler_grappler_able_to_shoot():
    global grappler_type
    if (time.time() - last_grappler_keypress_time) <= DELAY_SWAP:
        return False
    if (time.time() - last_action_time) <= grappler_fire_rates[grappler_type]:
        return False
    return True


def get_grappler_type_from_screen():
    # Check if grappler is unable to fire
    # if is_pixel_color((840, 540), (242, 0, 0)):
    #     return None

    if is_pixel_color((875, 540), (241, 0, 0)):
        return None

    # Check 4 pixels inside the slot
    # 2 corners
    target_color = [255, 255, 255]
    # if not is_pixel_color((1452, 930), (255, 255, 255)):
    #     return None
    # if not is_pixel_color((1518, 930), (255, 255, 255)):
    #     return None

    if not is_pixel_color((1513, 925), (255, 255, 255)):
        return None
    if not is_pixel_color((1582, 925), (255, 255, 255)):
        return None

    # grapplers
    c1 = get_pixel_color(1553, 943)  # red part
    c2 = get_pixel_color(1553, 968)  # gray handle
    # regular grappler (or regular mythic)
    # if c1 == (83, 2, 13) and c2 == (103, 103, 103):
    if c1 == (78, 10, 14) and c2 == (14, 14, 14):
        # regular grappler
        # if is_pixel_color((1506, 982), (255, 255, 255)):
        if is_pixel_color((1570, 982), (255, 255, 255)):
            return GrapplerType.MYTHIC_INFINITE
        return GrapplerType.REGULAR
    # mythic black
    # if c1 == (31, 31, 31) and c2 == (234, 173, 0):
    if c1 == (22, 22, 22) and c2 == (56, 60, 65):
        return GrapplerType.MYTHIC_BLACK
    return None


def is_grappler_available():
    global grappler_type
    if not is_grappler_grappler_able_to_shoot():
        # winsound.Beep(1000, 50)
        return False
    _grappler_type = get_grappler_type_from_screen()
    if _grappler_type is None:
        # winsound.Beep(1000, 1000)
        return False
    grappler_type = _grappler_type
    return True


def execute_action():
    """Your main action logic."""
    global running

    if not running:
        return

    global last_action_time

    current_time = time.time()
    if current_time - last_action_time < action_interval:
        return  # Prevent spamming

    if is_right_click_pressed() or current_time - last_rmb_keypress_time < DELAY_SWAP:
        if not is_grappler_available():
            return
        last_action_time = current_time
        # Unpress right click
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0)
        sleep_mini()

        # Press left click
        time.sleep(get_random_delay(delay_left_click, spread_left_click))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        sleep_mini()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

        # Press "2"
        time.sleep(get_random_delay(delay_swap_slot, spread_swap_slot))
        win32api.keybd_event(0x32, 0, 0, 0)  # Key "2" down
        sleep_mini()
        win32api.keybd_event(0x32, 0, win32con.KEYEVENTF_KEYUP, 0)  # Key "2" up

        # Press "Control"
        # Press "Control" only if not already pressed
        time.sleep(get_random_delay(delay_control_key_press_down, spread_control_key_press_down))
        if time.time() - last_ctrl_keypress_time > delay_control_key_press_down + DELAY_SWAP:  # If Ctrl is not currently pressed
            win32api.keybd_event(0x11, 0, 0, 0)  # Key "Ctrl" down
            time.sleep(get_random_delay(delay_control_key_press_up, spread_control_key_press_up))
            win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)  # Key "Ctrl" up



def main_loop():
    """Main loop to continuously execute actions."""
    while running:
        execute_action()
        time.sleep(0.01)  # Prevent CPU overuse


def stop_and_exit():
    """Stop the script gracefully and exit."""
    global running
    running = False
    icon.stop()  # Stops the tray icon


def create_image():
    """Create a simple tray icon image."""
    # Check if 'icon.png' exists in the current directory
    if os.path.exists("icon.png"):
        return Image.open("icon.png")
    elif os.path.exists("../icon.png"):  # Check in the parent directory
        return Image.open("../icon.png")
    else:
        raise FileNotFoundError("icon.png not found in the current or parent directory")


def setup_tray():
    """Setup the system tray icon."""
    menu = Menu(
        MenuItem("Stop and Exit", lambda: stop_and_exit(), default=True)
    )
    return Icon("BetterGrappler", create_image(), "BetterGrappler", menu)


if __name__ == "__main__":
    print("BetterGrappler Started")

    # Start the main loop in a separate thread
    main_thread = threading.Thread(target=main_loop, daemon=True)
    main_thread.start()

    # Start the keyboard listener in a separate thread
    listener_thread = threading.Thread(target=keyboard_listener, daemon=True)
    listener_thread.start()

    # Run the tray icon
    icon = setup_tray()
    icon.run()

    print("BetterGrappler Stopped")
