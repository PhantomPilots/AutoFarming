import time

import numpy as np
import win32con
import win32gui
import win32ui


def get_window_size():
    """Get the size of the 7DS window"""
    hwnd_target = win32gui.FindWindow(None, r"7DS")
    window_rect = win32gui.GetWindowRect(hwnd_target)
    w = window_rect[2] - window_rect[0]
    h = window_rect[3] - window_rect[1]

    return w, h


def capture_window() -> tuple[np.ndarray, tuple[int, int]]:
    """Make a screenshot of the 7DS window.
    Returns:
        tuple[np.ndarray, list[float]]: The image as a numpy array, and a list of the top-left corner of the window as [x,y]
    """
    hwnd_target = win32gui.FindWindow(None, r"7DS")
    window_rect = win32gui.GetWindowRect(hwnd_target)
    w = window_rect[2] - window_rect[0]
    h = window_rect[3] - window_rect[1]
    window_location = [window_rect[0], window_rect[1]]

    # Remove border pixels -- TODO: Necessary?
    border_pixels = 2
    w = w - (border_pixels * 2)
    h = h - 20

    i = 0
    num_attempts = 5
    while True:
        try:
            # Whatever these lines are?
            hdesktop = win32gui.GetDesktopWindow()
            hwndDC = win32gui.GetWindowDC(hdesktop)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

            saveDC.SelectObject(saveBitMap)
            saveDC.BitBlt((0, 0), (w, h), mfcDC, (window_rect[0], window_rect[1]), win32con.SRCCOPY)

            # bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)

            # convert the raw data into a format opencv can read
            img = np.frombuffer(bmpstr, dtype="uint8")
            # Reshape the array
            img = img.reshape(h, w, 4)

            # free resources
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hdesktop, hwndDC)
            img = img[..., :3]

            img = np.ascontiguousarray(img)
            # get updated window location
            window_rect = win32gui.GetWindowRect(hwnd_target)
            window_location = [window_rect[0], window_rect[1]]

            break

        except Exception as e:
            if i >= num_attempts:
                print(f"[ERROR] Failed to capture window after {num_attempts} attempts.")
                raise e
            print("[WARN] CompatibleDC failed, retrying...")
            time.sleep(0.02)  # Wait a bit before retrying

        i += 1

    return img, window_location


def capture_screen() -> np.ndarray:
    """Make a screenshot of the entire screen.
    Returns:
        np.ndarray: The image as a numpy array
    """
    # Get the screen dimensions
    hdesktop = win32gui.GetDesktopWindow()
    window_rect = win32gui.GetWindowRect(hdesktop)
    w = window_rect[2] - window_rect[0]
    h = window_rect[3] - window_rect[1]

    succeed = False
    while not succeed:
        try:
            hwndDC = win32gui.GetWindowDC(hdesktop)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

            saveDC.SelectObject(saveBitMap)
            saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)

            bmpstr = saveBitMap.GetBitmapBits(True)

            # convert the raw data into a format opencv can read
            img = np.frombuffer(bmpstr, dtype="uint8")
            # Reshape the array
            img = img.reshape(h, w, 4)

            # free resources
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hdesktop, hwndDC)
            img = img[..., :3]

            img = np.ascontiguousarray(img)
            succeed = True

        except Exception:
            print("[WARN] CompatibleDC failed, but we caught it successfully!")
            continue

    return img


def is_7ds_window_open() -> bool:
    """Check if the 7DS window is open and visible.
    Returns:
        bool: True if the window exists and is visible, False otherwise
    """
    hwnd = win32gui.FindWindow(None, r"7DS")
    return hwnd != 0
