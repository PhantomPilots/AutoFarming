import ctypes
import threading
import time
from ctypes import wintypes

import numpy as np
import win32api
import win32con
import win32gui
import win32ui


_CAPTURE_LOCK = threading.RLock()
_DEFAULT_CAPTURE_RETRIES = 3
_RETRY_DELAY_SECONDS = 0.05


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
    return window_rect[2] - window_rect[0], window_rect[3] - window_rect[1]


def calculate_exact_border_sizes():
    """Calculate the exact border sizes of the 7DS window"""
    try:
        hwnd_target = win32gui.FindWindow(None, r"7DS")
        if hwnd_target == 0:
            return None, None

        window_rect = win32gui.GetWindowRect(hwnd_target)
        window_width = window_rect[2] - window_rect[0]
        window_height = window_rect[3] - window_rect[1]

        client_rect = win32gui.GetClientRect(hwnd_target)
        client_width = client_rect[2] - client_rect[0]
        client_height = client_rect[3] - client_rect[1]

        border_width = window_width - client_width
        border_height = window_height - client_height

        print(f"[DEBUG] Window size: {window_width}x{window_height}")
        print(f"[DEBUG] Client size: {client_width}x{client_height}")
        print(f"[DEBUG] Border sizes: {border_width}x{border_height}")

        return border_width, border_height

    except Exception as e:
        print(f"[ERROR] Could not calculate border sizes: {e}")
        return None, None


def _log_capture_failure(kind: str, stage: str, attempt: int, max_attempts: int, exc: Exception) -> None:
    level = "ERROR" if attempt >= max_attempts else "WARN"
    print(f"[{level}] {kind} failed at {stage} (attempt {attempt}/{max_attempts}): {type(exc).__name__}: {exc}")


def _safe_release_capture_objects(
    hdesktop,
    hwndDC,
    mfcDC,
    saveDC,
    saveBitMap,
    *,
    kind: str,
    attempt: int,
    max_attempts: int,
) -> None:
    cleanup_errors: list[tuple[str, Exception]] = []

    if saveBitMap is not None:
        try:
            win32gui.DeleteObject(saveBitMap.GetHandle())
        except Exception as exc:
            cleanup_errors.append(("DeleteObject", exc))

    if saveDC is not None:
        try:
            saveDC.DeleteDC()
        except Exception as exc:
            cleanup_errors.append(("DeleteDC(saveDC)", exc))

    if mfcDC is not None:
        try:
            mfcDC.DeleteDC()
        except Exception as exc:
            cleanup_errors.append(("DeleteDC(mfcDC)", exc))

    if hwndDC is not None and hdesktop is not None:
        try:
            win32gui.ReleaseDC(hdesktop, hwndDC)
        except Exception as exc:
            cleanup_errors.append(("ReleaseDC", exc))

    for cleanup_stage, cleanup_exc in cleanup_errors:
        _log_capture_failure(kind, cleanup_stage, attempt, max_attempts, cleanup_exc)


def _get_7ds_capture_region(*, kind: str, attempt: int, max_attempts: int) -> tuple[int, tuple[int, int], int, int]:
    stage = "FindWindow"
    try:
        hwnd_target = win32gui.FindWindow(None, r"7DS")
        if hwnd_target == 0:
            raise RuntimeError("7DS window not found")

        stage = "GetWindowRect"
        window_rect = win32gui.GetWindowRect(hwnd_target)
        capture_origin = (window_rect[0], window_rect[1])
        w = window_rect[2] - window_rect[0]
        h = window_rect[3] - window_rect[1]

        border_pixels = 2
        w = w - (border_pixels * 2)
        h = h - 20

        if w <= 0 or h <= 0:
            raise RuntimeError(f"Invalid 7DS capture dimensions: {w}x{h}")

        return hwnd_target, capture_origin, w, h
    except Exception as exc:
        _log_capture_failure(kind, stage, attempt, max_attempts, exc)
        raise


def _capture_bitmap_region(
    *,
    kind: str,
    capture_origin: tuple[int, int],
    width: int,
    height: int,
    attempt: int,
    max_attempts: int,
) -> np.ndarray:
    hdesktop = None
    hwndDC = None
    mfcDC = None
    saveDC = None
    saveBitMap = None
    stage = "GetDesktopWindow"

    try:
        hdesktop = win32gui.GetDesktopWindow()

        stage = "GetWindowDC"
        hwndDC = win32gui.GetWindowDC(hdesktop)
        if not hwndDC:
            raise RuntimeError("GetWindowDC returned a null handle")

        stage = "CreateDCFromHandle"
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)

        stage = "CreateCompatibleDC"
        saveDC = mfcDC.CreateCompatibleDC()

        stage = "CreateCompatibleBitmap"
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)

        stage = "SelectObject"
        saveDC.SelectObject(saveBitMap)

        stage = "BitBlt"
        saveDC.BitBlt((0, 0), (width, height), mfcDC, capture_origin, win32con.SRCCOPY)

        stage = "GetBitmapBits"
        bmpstr = saveBitMap.GetBitmapBits(True)

        stage = "reshape/array conversion"
        img = np.frombuffer(bmpstr, dtype="uint8").reshape(height, width, 4)
        return np.ascontiguousarray(img[..., :3])

    except Exception as exc:
        _log_capture_failure(kind, stage, attempt, max_attempts, exc)
        raise

    finally:
        _safe_release_capture_objects(
            hdesktop,
            hwndDC,
            mfcDC,
            saveDC,
            saveBitMap,
            kind=kind,
            attempt=attempt,
            max_attempts=max_attempts,
        )


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
    with _CAPTURE_LOCK:
        try:
            hwnd_target = win32gui.FindWindow(None, r"7DS")
            if hwnd_target == 0:
                print("[ERROR] 7DS window not found!")
                return False

            current_rect = win32gui.GetWindowRect(hwnd_target)
            current_x = current_rect[0]
            current_y = current_rect[1]

            current_style = win32gui.GetWindowLong(hwnd_target, win32con.GWL_STYLE)
            current_ex_style = win32gui.GetWindowLong(hwnd_target, win32con.GWL_EXSTYLE)

            print(f"[DEBUG] Current window style: {hex(current_style)}")
            print(f"[DEBUG] Current extended style: {hex(current_ex_style)}")

            total_width, total_height = _get_required_window_size_for_client(
                hwnd_target, width, height, current_style, current_ex_style
            )

            print(f"[DEBUG] Attempting aggressive resize to: {total_width}x{total_height}")

            try:
                new_style = current_style & ~win32con.WS_MAXIMIZEBOX & ~win32con.WS_MINIMIZEBOX
                new_style |= win32con.WS_OVERLAPPEDWINDOW

                print(f"[DEBUG] Setting new window style: {hex(new_style)}")
                win32gui.SetWindowLong(hwnd_target, win32con.GWL_STYLE, new_style)
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

            resize_success = False

            try:
                win32gui.SetWindowPos(
                    hwnd_target, win32con.HWND_TOP, current_x, current_y, total_width, total_height, win32con.SWP_SHOWWINDOW
                )
                time.sleep(0.3)

                new_rect = win32gui.GetWindowRect(hwnd_target)
                new_width = new_rect[2] - new_rect[0]
                new_height = new_rect[3] - new_rect[1]

                print(f"[DEBUG] After SetWindowPos: {new_width}x{new_height}")

                if abs(new_width - total_width) <= 15 and abs(new_height - total_height) <= 15:
                    resize_success = True
                    print("[SUCCESS] SetWindowPos worked!")
            except Exception as e:
                print(f"[WARNING] SetWindowPos failed: {e}")

            if not resize_success:
                try:
                    print("[DEBUG] Trying MoveWindow...")
                    win32gui.MoveWindow(hwnd_target, current_x, current_y, total_width, total_height, True)
                    time.sleep(0.3)

                    new_rect = win32gui.GetWindowRect(hwnd_target)
                    new_width = new_rect[2] - new_rect[0]
                    new_height = new_rect[3] - new_rect[1]

                    print(f"[DEBUG] After MoveWindow: {new_width}x{new_height}")

                    if abs(new_width - total_width) <= 15 and abs(new_height - total_height) <= 15:
                        resize_success = True
                        print("[SUCCESS] MoveWindow worked!")
                except Exception as e:
                    print(f"[WARNING] MoveWindow failed: {e}")

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

            final_rect = win32gui.GetWindowRect(hwnd_target)
            final_width = final_rect[2] - final_rect[0]
            final_height = final_rect[3] - final_rect[1]
            final_client_rect = win32gui.GetClientRect(hwnd_target)
            final_client_width = final_client_rect[2] - final_client_rect[0]
            final_client_height = final_client_rect[3] - final_client_rect[1]

            print(f"[DEBUG] Final window size: {final_width}x{final_height}")
            print(f"[DEBUG] Final client size: {final_client_width}x{final_client_height}")

            client_width_diff = abs(final_client_width - width)
            client_height_diff = abs(final_client_height - height)

            if client_width_diff <= 1 and client_height_diff <= 1:
                print(f"[SUCCESS] 7DS window client area resized to {final_client_width}x{final_client_height}")
                print(f"[INFO] Target was {width}x{height}, difference: {client_width_diff}x{client_height_diff}")

                move_window_to_visible_area(hwnd_target, final_width, final_height)
                return True

            print(f"[WARNING] Client area resize not exact. Got: {final_client_width}x{final_client_height}")
            print(f"[WARNING] Target was {width}x{height}, difference: {client_width_diff}x{client_height_diff}")

            if client_width_diff <= 20 and client_height_diff <= 20:
                print("[INFO] Close enough, considering resize successful")

                move_success = move_window_to_visible_area(hwnd_target, final_width, final_height)
                if move_success:
                    print("[SUCCESS] Window positioned to ensure full visibility")
                else:
                    print("[WARNING] Could not reposition window for full visibility")

                return True

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
    with _CAPTURE_LOCK:
        try:
            current_rect = win32gui.GetWindowRect(hwnd)
            current_x = current_rect[0]
            current_y = current_rect[1]

            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

            taskbar_height = win32api.GetSystemMetrics(win32con.SM_CYMENU)

            menu_bar_height = 40
            safe_top = menu_bar_height
            safe_bottom = screen_height - taskbar_height - 10

            target_x = current_x
            target_y = current_y

            if target_y < safe_top:
                target_y = safe_top
                print(f"[DEBUG] Window was covered by menu bar, moving down to y={target_y}")

            if target_y + window_height > safe_bottom:
                target_y = safe_bottom - window_height
                print(f"[DEBUG] Window was below safe area, moving up to y={target_y}")

            if target_y != current_y:
                print(f"[DEBUG] Screen dimensions: {screen_width}x{screen_height}")
                print(f"[DEBUG] Moving window from y={current_y} to y={target_y} (keeping x={current_x})")

                result = win32gui.SetWindowPos(
                    hwnd, win32con.HWND_TOP, target_x, target_y, window_width, window_height, win32con.SWP_SHOWWINDOW
                )
                return bool(result)

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
    with _CAPTURE_LOCK:
        for attempt in range(1, _DEFAULT_CAPTURE_RETRIES + 1):
            try:
                _, capture_origin, w, h = _get_7ds_capture_region(
                    kind="capture_window",
                    attempt=attempt,
                    max_attempts=_DEFAULT_CAPTURE_RETRIES,
                )
                img = _capture_bitmap_region(
                    kind="capture_window",
                    capture_origin=capture_origin,
                    width=w,
                    height=h,
                    attempt=attempt,
                    max_attempts=_DEFAULT_CAPTURE_RETRIES,
                )
                return img, capture_origin
            except Exception:
                if attempt >= _DEFAULT_CAPTURE_RETRIES:
                    raise
                time.sleep(_RETRY_DELAY_SECONDS)


def capture_screen() -> np.ndarray:
    """Make a screenshot of the entire screen.
    Returns:
        np.ndarray: The image as a numpy array
    """
    with _CAPTURE_LOCK:
        stage = "GetDesktopWindow"

        try:
            hdesktop = win32gui.GetDesktopWindow()
            stage = "GetWindowRect"
            window_rect = win32gui.GetWindowRect(hdesktop)
            w = window_rect[2] - window_rect[0]
            h = window_rect[3] - window_rect[1]
            if w <= 0 or h <= 0:
                raise RuntimeError(f"Invalid screen capture dimensions: {w}x{h}")
        except Exception as exc:
            _log_capture_failure("capture_screen", stage, 1, 1, exc)
            raise

        return _capture_bitmap_region(
            kind="capture_screen",
            capture_origin=(0, 0),
            width=w,
            height=h,
            attempt=1,
            max_attempts=1,
        )


def is_7ds_window_open() -> bool:
    """Check if the 7DS window is open and visible.
    Returns:
        bool: True if the window exists and is visible, False otherwise
    """
    hwnd = win32gui.FindWindow(None, r"7DS")
    return hwnd != 0
