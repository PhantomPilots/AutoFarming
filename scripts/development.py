"""Public, one-shot DevTest tools, usable from the GUI or command line."""

import argparse
import contextlib
import ctypes
import json
import math
import os
import sys
import time
from pathlib import Path


def initialize_dpi_awareness():
    """Use physical screen coordinates, matching the regular Qt GUI's Resize button."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    # Qt's Windows GUI uses DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE (-3).
    # Set the default before imports such as pyautogui can choose system awareness.
    context = ctypes.c_void_p(-3)
    set_process = user32.SetProcessDpiAwarenessContext
    set_process.argtypes = [ctypes.c_void_p]
    set_process.restype = ctypes.c_int
    set_process(context)
    # A bundled launcher or previous import may already have fixed the process
    # default. The thread override still keeps resize and capture in GUI pixels.
    set_thread = user32.SetThreadDpiAwarenessContext
    set_thread.argtypes = [ctypes.c_void_p]
    set_thread.restype = ctypes.c_void_p
    if not set_thread(context):
        raise RuntimeError("Could not prepare screen scaling for DevTest. Please try again.")


def valid_threshold(value):
    try:
        threshold = float(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("Enter a threshold between 0 and 1.") from None
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise argparse.ArgumentTypeError("Enter a threshold between 0 and 1.")
    return threshold


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("list-visions", help="List public and installed private vision names as JSON.")
    for action in ("screenshot-test", "coordinates", "capture-hand", "card-types", "screenshot", "crop"):
        command = commands.add_parser(action)
        command.add_argument("--output", type=Path, help="Optional PNG output after the image window closes.")
        if action == "screenshot-test":
            command.add_argument("--vision", required=True, help="Public or installed private vision name, without vio.")
            command.add_argument("--threshold", type=valid_threshold, default=0.7)
        elif action in ("capture-hand", "card-types"):
            command.add_argument("--units", type=int, choices=(3, 4), default=4)
    return parser


def public_visions():
    import utilities.vision_images as vio
    from utilities.vision import Vision

    return {
        name: value for name, value in vars(vio).items()
        if name.isidentifier() and not name.startswith("_") and isinstance(value, Vision)
    }


def installed_vision_bundles():
    from utilities.compiled_extensions import discover_compiled_extensions

    return discover_compiled_extensions(Path(__file__).resolve().parent / "vendor")


def private_vision_provider(module):
    listing = getattr(module, "list_devtest_visions", None)
    lookup = getattr(module, "get_devtest_vision", None)
    if not callable(listing) or not callable(lookup):
        raise ValueError("This Farmer needs a newer build for DevTest.")
    return listing, lookup


def vision_catalog():
    from compiled_extension_runner import load_validated_extension

    # Keep JSON on stdout, even if an imported module prints a message.
    with contextlib.redirect_stdout(sys.stderr):
        names = set(public_visions())
        bundles, warnings = installed_vision_bundles()
        for bundle in bundles:
            try:
                with load_validated_extension(Path(bundle["bundle_dir"])) as (module, _contract):
                    listing, _lookup = private_vision_provider(module)
                    private_names = listing()
                    if not isinstance(private_names, (list, tuple)) or any(
                        not isinstance(name, str) or not name.isidentifier() or name.startswith("_")
                        for name in private_names
                    ):
                        raise ValueError("This Farmer returned an invalid vision list.")
                    names.update(private_names)
            except Exception:
                warnings.append(f"{bundle['display_name']} vision suggestions are unavailable. Its build may need updating.")
    return {"names": sorted(names), "warnings": warnings}


def resolve_vision(name):
    name = name.strip()
    if not name.isidentifier() or name.startswith("_"):
        raise ValueError("Enter a vision name without 'vio.', such as 'startbutton'.")
    vision = public_visions().get(name)
    if vision is not None:
        return vision

    from compiled_extension_runner import load_validated_extension
    from utilities.vision import Vision

    bundles, warnings = installed_vision_bundles()
    for bundle in bundles:
        try:
            with load_validated_extension(Path(bundle["bundle_dir"])) as (module, _contract):
                _listing, lookup = private_vision_provider(module)
                vision = lookup(name)
                if vision is not None:
                    if not isinstance(vision, Vision):
                        raise ValueError("This Farmer returned an invalid vision object.")
                    return vision
        except Exception:
            warnings.append(f"{bundle['display_name']} images are unavailable. Its build may need updating.")
    for warning in warnings:
        print(warning, flush=True)
    raise ValueError(f"No vision named '{name}' was found. Check its spelling and installed Farmer builds.")


def show_image(image, title, callback=None):
    """Pump OpenCV events until Escape or the title-bar close button is used."""
    import cv2

    if image is None or not image.size:
        raise ValueError("The image is empty. Check the game screen and try again.")
    cv2.namedWindow(title, cv2.WINDOW_AUTOSIZE)
    try:
        cv2.imshow(title, image)
        if callback is not None:
            cv2.setMouseCallback(title, callback)
        print("Close the image window or press Escape to finish.", flush=True)
        while True:
            if cv2.waitKey(30) & 0xFF == 27:
                break
            try:
                if cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                    break
            except cv2.error:
                break
    finally:
        cv2.destroyAllWindows()


def screenshot_testing(screenshot, vision_image, threshold=0.7, *, best_only=False):
    """Draw every match, displaying the screenshot even when nothing matches."""
    import cv2

    if best_only:
        raise ValueError("DevTest always shows all matches.")
    matches = vision_image.find_all_rectangles(screenshot, threshold=threshold)
    if matches is None:
        raise ValueError("The image template could not be loaded. Check its image file.")
    rectangles, _ = matches
    result = screenshot.copy()
    for x, y, width, height in rectangles:
        cv2.rectangle(result, (int(x), int(y)), (int(x + width), int(y + height)), (0, 255, 0), 2)
    print(f"Found {len(rectangles)} matches." if len(rectangles) else "No matches found.", flush=True)
    show_image(result, "DevTest - Screenshot testing")
    return result


def determine_relative_coordinates(screenshot):
    import cv2

    def clicked(event, x, y, _flags, _params):
        if event == cv2.EVENT_LBUTTONDOWN:
            print(f"Coordinates: ({x}, {y})", flush=True)

    print("Click the image to read coordinates from its top-left corner.", flush=True)
    show_image(screenshot, "DevTest - Coordinates", clicked)
    return screenshot


def concatenate_images(images):
    import numpy as np

    if not images or any(image is None or not image.size for image in images):
        raise ValueError("Some card images are empty. Open a battle hand and try again.")
    return np.concatenate(images, axis=1)


def card_type_label(card_type):
    return {
        "ATTACK_DEBUFF": "Attack with debuff",
        "GROUND": "Empty slot",
        "NONE": "Unknown",
    }.get(card_type.name, card_type.name.replace("_", " ").capitalize())


def capture_cards(num_units, *, types_only=False):
    from utilities.utilities import get_card_type_image, get_hand_cards

    cards = get_hand_cards(num_units=num_units)
    expected = 7 if num_units == 3 else 8
    if len(cards) != expected:
        raise ValueError(f"Expected {expected} card slots. Open a battle hand and try again.")
    images = []
    print(f"Cards from left to right ({num_units} units):", flush=True)
    for index, card in enumerate(cards, 1):
        label = card_type_label(card.card_type)
        if not types_only:
            rank = "Unknown" if card.card_rank.name == "NONE" else card.card_rank.name.capitalize()
            label += f" — {rank}"
        print(f"Card {index}: {label}", flush=True)
        images.append(get_card_type_image(card.card_image, num_units=num_units) if types_only else card.card_image)
    result = concatenate_images(images)
    show_image(result, "DevTest - Card types" if types_only else "DevTest - Hand")
    return result


def crop_region_from_points(shape, start, end):
    height, width = shape[:2]
    x1, x2 = sorted((max(0, min(width, start[0])), max(0, min(width, end[0]))))
    y1, y2 = sorted((max(0, min(height, start[1])), max(0, min(height, end[1]))))
    return (x1, y1, x2, y2) if x1 < x2 and y1 < y2 else None


def pick_crop(screenshot):
    import cv2

    title = "DevTest - Select crop"
    state = {"start": None, "region": None}

    def dragged(event, x, y, _flags, _params):
        if event == cv2.EVENT_LBUTTONDOWN:
            state["start"] = (x, y)
            state["region"] = None
        elif state["start"] is not None and event in (cv2.EVENT_MOUSEMOVE, cv2.EVENT_LBUTTONUP):
            region = crop_region_from_points(screenshot.shape, state["start"], (x, y))
            preview = screenshot.copy()
            if region:
                cv2.rectangle(preview, region[:2], region[2:], (0, 255, 0), 1)
            cv2.imshow(title, preview)
            if event == cv2.EVENT_LBUTTONUP:
                state["start"] = None
                state["region"] = region
                if region is None:
                    print("Select a larger area and try again.", flush=True)

    print("Drag over the area to crop, then press Enter. Escape cancels.", flush=True)
    cv2.namedWindow(title, cv2.WINDOW_AUTOSIZE)
    try:
        cv2.imshow(title, screenshot)
        cv2.setMouseCallback(title, dragged)
        while True:
            key = cv2.waitKey(30) & 0xFF
            if key == 27:
                return None
            if key in (10, 13) and state["region"]:
                break
            try:
                if cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                    return None
            except cv2.error:
                return None
    finally:
        cv2.destroyAllWindows()
    x1, y1, x2, y2 = state["region"]
    result = screenshot[y1:y2, x1:x2].copy()
    print(f"Crop: ({x1}, {y1}, {x2}, {y2}) — {x2 - x1} × {y2 - y1} pixels", flush=True)
    show_image(result, "DevTest - Crop")
    return result


def run_action(args):
    initialize_dpi_awareness()
    from utilities.capture_window import capture_window, resize_7ds_window

    # Validate names before moving the game window.
    vision = resolve_vision(args.vision) if args.action == "screenshot-test" else None
    print("Resizing the game window...", flush=True)
    if not resize_7ds_window(width=538, height=921):
        raise RuntimeError("Could not resize the game window. Open the selected game client and try again.")
    time.sleep(0.5)
    if args.action in ("capture-hand", "card-types"):
        return capture_cards(args.units, types_only=args.action == "card-types")
    screenshot, _ = capture_window()
    print(f"Screenshot: {screenshot.shape[1]} × {screenshot.shape[0]} pixels", flush=True)
    if args.action == "screenshot-test":
        return screenshot_testing(screenshot, vision, args.threshold, best_only=False)
    if args.action == "coordinates":
        return determine_relative_coordinates(screenshot)
    if args.action == "crop":
        return pick_crop(screenshot)
    show_image(screenshot, "DevTest - Screenshot")
    return screenshot


def main(argv=None):
    args = build_parser().parse_args(argv)
    if getattr(args, "output", None):
        args.output = args.output.resolve()
    # Model files use paths relative to scripts, also for standalone launches.
    os.chdir(Path(__file__).resolve().parent)
    if args.action == "list-visions":
        try:
            print(json.dumps(vision_catalog(), ensure_ascii=False), flush=True)
            return 0
        except Exception:
            print("Could not load vision suggestions. You can still enter a name.", file=sys.stderr, flush=True)
            return 1
    try:
        result = run_action(args)
        if result is None:
            print("Selection cancelled.", flush=True)
            return 2
        if args.output:
            import cv2

            ok, encoded = cv2.imencode(".png", result)
            if not ok:
                raise RuntimeError("Could not prepare the image for saving.")
            args.output.write_bytes(encoded.tobytes())
        print("Finished.", flush=True)
        return 0
    except KeyboardInterrupt:
        print("Stopped.", flush=True)
        return 130
    except Exception as exc:
        print(f"[ERROR] Could not finish the tool: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
