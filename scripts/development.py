import time

import cv2
import numpy as np
import utilities.vision_images as vio
from utilities.utilities import capture_window


def detect_template_hits(screenshot, vision_image, side: str, threshold=0.8) -> list[dict]:
    template = vision_image.needle_img
    if template is None:
        return []

    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    match_locations = np.where(result >= threshold)
    template_height, template_width = template.shape[:2]

    rectangles = []
    for x, y in zip(match_locations[1], match_locations[0]):
        rectangles.append([int(x), int(y), int(template_width), int(template_height)])
        rectangles.append([int(x), int(y), int(template_width), int(template_height)])

    if not rectangles:
        return []

    grouped_rectangles, grouped_weights = cv2.groupRectangles(rectangles, groupThreshold=1, eps=0.5)
    if len(grouped_rectangles) == 0:
        return []

    hits = []
    for rect, weight in zip(grouped_rectangles, grouped_weights):
        x, y, width, height = rect
        hits.append(
            {
                "x": int(x),
                "y": int(y),
                "w": int(width),
                "h": int(height),
                "side": side,
                "weight": int(weight),
            }
        )

    hits.sort(key=lambda hit: (hit["x"], hit["y"]))
    return hits


def development():
    print("Watching for Escalin talent variants. Press CTRL+C to stop.")
    last_state = None

    talent_templates = [
        ("dogs_escalin_talent", vio.dogs_escalin_talent),
        ("dogs_escalin_talent_min1", vio.dogs_escalin_talent_min1),
        ("dogs_escalin_talent_min2", vio.dogs_escalin_talent_min2),
    ]

    while True:
        screenshot, _ = capture_window()

        detected_name = None
        detected_hits = []

        for template_name, template_obj in talent_templates:
            hits = detect_template_hits(
                screenshot,
                template_obj,
                side=template_name,
                threshold=0.8
            )

            if hits:
                detected_name = template_name
                detected_hits = hits
                break

        state = detected_name

        if state != last_state:
            if detected_name is None:
                print("escalin talent detection -> none")
            else:
                print(
                    "escalin talent detection -> "
                    f"seeing={detected_name}"
                )
            last_state = state

        time.sleep(0.15)


if __name__ == "__main__":
    try:
        development()
    except KeyboardInterrupt:
        print("\nStopped Escalin talent detector.")