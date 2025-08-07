import time

import utilities.vision_images as vio
from utilities.utilities import capture_window, find_and_click

while True:

    screenshot, window_location = capture_window()

    if find_and_click(vio.change_stats, screenshot, window_location):
        time.sleep(2)
    else:
        time.sleep(0.1)
