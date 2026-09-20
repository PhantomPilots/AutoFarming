import argparse
import time

import utilities.vision_images as vio
from utilities.utilities import capture_window, find, find_and_click

parser = argparse.ArgumentParser()
parser.add_argument("--max-tickets", type=int, default=50, help="Maximum number of rerolls")
args = parser.parse_args()

used_skip_tickets = 0

print(f"Farming food up to {args.max_tickets} tickets.")


while used_skip_tickets < args.max_tickets:

    screenshot, window_location = capture_window()

    find_and_click(vio.daily_result, screenshot, window_location)

    # We're using skip tickets :)
    if find(vio.max_skip_tickets, screenshot):
        # Click on MAX twice, then click on START auto-clear!
        find_and_click(vio.max_skip_tickets, screenshot, window_location, sleep_time=0.5)
        find_and_click(vio.max_skip_tickets, screenshot, window_location, sleep_time=0.5)
        if find_and_click(vio.strart_auto_clear, screenshot, window_location):
            used_skip_tickets += 30
            print(f"We've used {used_skip_tickets} skip tickets so far.")

    # If not, try to click on auto-clear
    else:
        find_and_click(vio.auto_clear, screenshot, window_location)

    time.sleep(1)

print("Finished farming food, stopping.")
