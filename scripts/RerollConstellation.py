import argparse
import time

import utilities.vision_images as vio
from utilities.utilities import capture_window, find, find_and_click

parser = argparse.ArgumentParser()
parser.add_argument("--max-rerolls", type=str, default=50, help="Maximum number of rerolls")
args = parser.parse_args()

if (max_rerolls := float(args.max_rerolls)) < float("inf"):
    print(f"We'll reroll at most {int(max_rerolls)} times")

num_rerolls = 0

while num_rerolls < max_rerolls:

    screenshot, window_location = capture_window()

    if find_and_click(vio.change_stats, screenshot, window_location):
        num_rerolls += 1
        print(f"Rerolled {num_rerolls} times.")
        time.sleep(4)
    else:
        time.sleep(0.1)
