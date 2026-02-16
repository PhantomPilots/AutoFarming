import ctypes
import time
from ctypes import wintypes

import numpy as np
import win32api
import win32con
import win32gui
import win32ui


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def _get_required_window_size_for_client(
    hwnd: int, client_width: int, client_height: int, style: int, ex_style: int
) -> tuple[int, int]:
    """Compute required outer window size for a desired client area, DPI-aware when available."""
    rect = _RECT(0, 0, client_width, client_height)

    user32 = ctypes.windll.user32
    adjusted = False

    try:
        if hasattr(user32, "GetDpiForWindow") and hasattr(user32, "AdjustWindowRectExForDpi"):
            dpi = user32.GetDpiForWindow(wintypes.HWND(hwnd))
            adjusted = bool(user32.AdjustWindowRectExForDpi(ctypes.byref(rect), style, False, ex_style, dpi))
    except Exception:
        adjusted = False

    if not adjusted:
        if not bool(user32.AdjustWindowRectEx(ctypes.byref(rect), style, False, ex_style)):
            raise ctypes.WinError()

    return rect.right - rect.left, rect.bottom - rect.top


def get_window_size():
    """Get the size of the 7DS window"""
    hwnd_target = win32gui.FindWindow(None, r"7DS")
    window_rect = win32gui.GetWindowRect(hwnd_target)
    w = window_rect[2] - window_rect[0]
    h = window_rect[3] - window_rect[1]

    return w, h


def calculate_exact_border_sizes():
    """Calculate the exact border sizes of the 7DS window"""
    try:
        hwnd_target = win32gui.FindWindow(None, r"7DS")
        if hwnd_target == 0:
            return None, None

        # Get window rectangle (includes borders and title bar)
        window_rect = win32gui.GetWindowRect(hwnd_target)
        window_width = window_rect[2] - window_rect[0]
        window_height = window_rect[3] - window_rect[1]

        # Get client rectangle (just the content area)
        client_rect = win32gui.GetClientRect(hwnd_target)
        client_width = client_rect[2] - client_rect[0]
        client_height = client_rect[3] - client_rect[1]

        # Calculate border sizes
        border_width = window_width - client_width
        border_height = window_height - client_height

        print(f"[DEBUG] Window size: {window_width}x{window_height}")
        print(f"[DEBUG] Client size: {client_width}x{client_height}")
        print(f"[DEBUG] Border sizes: {border_width}x{border_height}")

        return border_width, border_height

    except Exception as e:
        print(f"[ERROR] Could not calculate border sizes: {e}")
        return None, None


def resize_7ds_window(width=540, height=960):
    """Aggressively force resize the 7DS window by temporarily modifying window styles.
    This is a more aggressive approach that tries to bypass aspect ratio constraints.
    Also moves the window to ensure it's fully visible.

    Args:
        width (int): Target width of the window (default: 540)
        height (int): Target height of the window (default: 960)

    Returns:
        bool: True if resize was successful, False otherwise
    """
    try:
        # Find the 7DS window
        hwnd_target = win32gui.FindWindow(None, r"7DS")
        if hwnd_target == 0:
            print("[ERROR] 7DS window not found!")
            return False

        # Get current window position
        current_rect = win32gui.GetWindowRect(hwnd_target)
        current_x = current_rect[0]
        current_y = current_rect[1]

        # Get current window style
        current_style = win32gui.GetWindowLong(hwnd_target, win32con.GWL_STYLE)
        current_ex_style = win32gui.GetWindowLong(hwnd_target, win32con.GWL_EXSTYLE)

        print(f"[DEBUG] Current window style: {hex(current_style)}")
        print(f"[DEBUG] Current extended style: {hex(current_ex_style)}")

        # Calculate the required outer window size for the target client size (DPI-aware)
        total_width, total_height = _get_required_window_size_for_client(
            hwnd_target, width, height, current_style, current_ex_style
        )

        print(f"[DEBUG] Attempting aggressive resize to: {total_width}x{total_height}")

        # Method 1: Try to temporarily remove resize restrictions
        try:
            # Remove WS_MAXIMIZEBOX and WS_MINIMIZEBOX to prevent maximize/minimize interference
            new_style = current_style & ~win32con.WS_MAXIMIZEBOX & ~win32con.WS_MINIMIZEBOX
            # Ensure WS_OVERLAPPEDWINDOW is set for proper window behavior
            new_style |= win32con.WS_OVERLAPPEDWINDOW

            print(f"[DEBUG] Setting new window style: {hex(new_style)}")
            win32gui.SetWindowLong(hwnd_target, win32con.GWL_STYLE, new_style)

            # Force a window update - fixed argument count
            win32gui.SetWindowPos(
                hwnd_target,
                0,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED,
            )

            time.sleep(0.2)

        except Exception as e:
            print(f"[WARNING] Could not modify window style: {e}")

        # Method 2: Try multiple resize approaches
        resize_success = False

        # Approach 1: SetWindowPos with specific flags
        try:
            result = win32gui.SetWindowPos(
                hwnd_target, win32con.HWND_TOP, current_x, current_y, total_width, total_height, win32con.SWP_SHOWWINDOW
            )
            time.sleep(0.3)

            # Check if it worked
            new_rect = win32gui.GetWindowRect(hwnd_target)
            new_width = new_rect[2] - new_rect[0]
            new_height = new_rect[3] - new_rect[1]

            print(f"[DEBUG] After SetWindowPos: {new_width}x{new_height}")

            if abs(new_width - total_width) <= 15 and abs(new_height - total_height) <= 15:
                resize_success = True
                print("[SUCCESS] SetWindowPos worked!")

        except Exception as e:
            print(f"[WARNING] SetWindowPos failed: {e}")

        # Approach 2: MoveWindow if SetWindowPos didn't work
        if not resize_success:
            try:
                print("[DEBUG] Trying MoveWindow...")
                result = win32gui.MoveWindow(hwnd_target, current_x, current_y, total_width, total_height, True)
                time.sleep(0.3)

                # Check if it worked
                new_rect = win32gui.GetWindowRect(hwnd_target)
                new_width = new_rect[2] - new_rect[0]
                new_height = new_rect[3] - new_rect[1]

                print(f"[DEBUG] After MoveWindow: {new_width}x{new_height}")

                if abs(new_width - total_width) <= 15 and abs(new_height - total_height) <= 15:
                    resize_success = True
                    print("[SUCCESS] MoveWindow worked!")

            except Exception as e:
                print(f"[WARNING] MoveWindow failed: {e}")

        # Restore original window style - fixed argument count
        try:
            win32gui.SetWindowLong(hwnd_target, win32con.GWL_STYLE, current_style)
            win32gui.SetWindowPos(
                hwnd_target,
                0,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED,
            )
        except Exception as e:
            print(f"[WARNING] Could not restore window style: {e}")

        # Correction loop: measure actual client size and nudge if DWM/invisible-frame caused drift
        for attempt in range(3):
            final_client_rect = win32gui.GetClientRect(hwnd_target)
            final_client_width = final_client_rect[2] - final_client_rect[0]
            final_client_height = final_client_rect[3] - final_client_rect[1]

            width_diff = width - final_client_width
            height_diff = height - final_client_height

            if width_diff == 0 and height_diff == 0:
                break

            final_rect = win32gui.GetWindowRect(hwnd_target)
            corrected_width = (final_rect[2] - final_rect[0]) + width_diff
            corrected_height = (final_rect[3] - final_rect[1]) + height_diff

            print(f"[DEBUG] Correction pass {attempt + 1}: adjusting by {width_diff}x{height_diff}")

            win32gui.SetWindowPos(
                hwnd_target,
                win32con.HWND_TOP,
                current_x,
                current_y,
                corrected_width,
                corrected_height,
                win32con.SWP_SHOWWINDOW,
            )
            time.sleep(0.2)

        # Final check
        final_rect = win32gui.GetWindowRect(hwnd_target)
        final_width = final_rect[2] - final_rect[0]
        final_height = final_rect[3] - final_rect[1]

        # Get the actual client size after resize
        final_client_rect = win32gui.GetClientRect(hwnd_target)
        final_client_width = final_client_rect[2] - final_client_rect[0]
        final_client_height = final_client_rect[3] - final_client_rect[1]

        print(f"[DEBUG] Final window size: {final_width}x{final_height}")
        print(f"[DEBUG] Final client size: {final_client_width}x{final_client_height}")

        # Check if we achieved the target client size
        client_width_diff = abs(final_client_width - width)
        client_height_diff = abs(final_client_height - height)

        if client_width_diff <= 1 and client_height_diff <= 1:
            print(f"[SUCCESS] 7DS window client area resized to {final_client_width}x{final_client_height}")
            print(f"[INFO] Target was {width}x{height}, difference: {client_width_diff}x{client_height_diff}")

            # Now move the window to ensure it's fully visible
            move_window_to_visible_area(hwnd_target, final_width, final_height)

            return True
        else:
            print(f"[WARNING] Client area resize not exact. Got: {final_client_width}x{final_client_height}")
            print(f"[WARNING] Target was {width}x{height}, difference: {client_width_diff}x{client_height_diff}")

            # If we're close enough, still consider it a success
            if client_width_diff <= 20 and client_height_diff <= 20:
                print("[INFO] Close enough, considering resize successful")

                # Still try to move the window
                move_success = move_window_to_visible_area(hwnd_target, final_width, final_height)
                if move_success:
                    print("[SUCCESS] Window positioned to ensure full visibility")
                else:
                    print("[WARNING] Could not reposition window for full visibility")

                return True
            else:
                print("[ERROR] Resize failed - client area too different from target")
                return False

    except Exception as e:
        print(f"[ERROR] Exception in force resize: {e}")
        return False


def move_window_to_visible_area(hwnd, window_width, window_height):
    """Move the window vertically to ensure it's fully visible and not covered by menu bar or taskbar.
    Keeps the current horizontal position.

    Args:
        hwnd: Window handle
        window_width: Width of the window
        window_height: Height of the window

    Returns:
        bool: True if move was successful, False otherwise
    """
    try:
        # Get current window position
        current_rect = win32gui.GetWindowRect(hwnd)
        current_x = current_rect[0]
        current_y = current_rect[1]

        # Get screen dimensions using win32api
        screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

        # Get taskbar height (approximate)
        taskbar_height = win32api.GetSystemMetrics(win32con.SM_CYMENU)

        # Calculate safe area (avoiding menu bar at top and taskbar at bottom)
        # Menu bar is typically around 30-40 pixels, taskbar around 40-50 pixels
        menu_bar_height = 40  # Approximate menu bar height
        safe_top = menu_bar_height
        safe_bottom = screen_height - taskbar_height - 10  # 10 pixel margin

        # Keep the current horizontal position, only adjust vertical
        target_x = current_x
        target_y = current_y

        # Check if window is covered by menu bar at top
        if target_y < safe_top:
            target_y = safe_top
            print(f"[DEBUG] Window was covered by menu bar, moving down to y={target_y}")

        # Check if window goes below the safe area
        if target_y + window_height > safe_bottom:
            target_y = safe_bottom - window_height
            print(f"[DEBUG] Window was below safe area, moving up to y={target_y}")

        # Only move if position actually changed
        if target_y != current_y:
            print(f"[DEBUG] Screen dimensions: {screen_width}x{screen_height}")
            print(f"[DEBUG] Moving window from y={current_y} to y={target_y} (keeping x={current_x})")

            # Move the window to the calculated position
            result = win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOP, target_x, target_y, window_width, window_height, win32con.SWP_SHOWWINDOW
            )

            if result:
                # print(f"[SUCCESS] Window moved to ({target_x}, {target_y})")
                return True
            else:
                # print("[ERROR] Failed to move window")
                return False
        else:
            print(f"[INFO] Window is already in safe position ({current_x}, {current_y})")
            return True

    except Exception as e:
        print(f"[ERROR] Exception while moving window: {e}")
        return False


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
    NUM_ATTEMPTS = 1
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
            if i >= NUM_ATTEMPTS:
                print(f"[ERROR] Failed to capture window after {NUM_ATTEMPTS} attempts.")
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
