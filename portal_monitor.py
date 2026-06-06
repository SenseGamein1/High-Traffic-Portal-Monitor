import os
import sys
import time
import threading
import ctypes

# =========================================================
# AUTO-INSTALL SELENIUM IF NEEDED
# =========================================================
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, WebDriverException
except ImportError:
    import subprocess
    print("selenium not found, installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "selenium"])
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, WebDriverException

# =========================================================
# CONFIG
# =========================================================
TARGET_URL = "https://cbseacadit.nic.in/pvr/auth/login"

SESSION_COUNT = 3

PAGE_TIMEOUT = 15
REFRESH_INTERVAL = 25
POLL_INTERVAL = 0.25
STAGGER_STEP = 1.5

ENABLE_SCREENSHOT_ON_SUCCESS = True
SUCCESS_SCREENSHOT_FILE = "cbse_success.png"

TRIGGER_WORDS = [
    "Login",
    "Password",
    "Register",
    "Photocopy",
    "Post Result",
    "Central Board",
    "CBSE",
]

ERROR_KEYWORDS = [
    "503",
    "502",
    "504",
    "bad gateway",
    "service unavailable",
    "temporarily unavailable",
    "forbidden",
    "access denied",
    "captcha",
    "just a moment",
    "timed out",
    "this site can't be reached",
    "this site can’t be reached",
    "err_connection_timed_out",
]

# =========================================================
# GLOBAL STOP
# =========================================================
stop_event = threading.Event()
result_lock = threading.Lock()
winner_session = {"id": None}

# =========================================================
# ALERT
# =========================================================
def play_alarm():
    print("\n" + "=" * 72)
    print("SUCCESS — REAL LOGIN PAGE DETECTED")
    print("=" * 72)

    ctypes.windll.user32.MessageBoxW(0, "CBSE site is UP! Login now!", "ALERT", 0x40 | 0x1)

    try:
        if sys.platform == "win32":
            import winsound
            for _ in range(12):
                winsound.Beep(2200, 220)
                winsound.Beep(2600, 220)
                time.sleep(0.03)
        else:
            for _ in range(24):
                print("\a", end="", flush=True)
                time.sleep(0.12)
    except Exception:
        pass

# =========================================================
# DRIVER SETUP
# =========================================================
def create_driver(session_id: int):
    options = Options()

    # Keep browser open after script exits
    options.add_experimental_option("detach", True)

    # Reduce noise
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    # We inspect page content ourselves
    options.page_load_strategy = "none"

    # Stability / performance
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")

    # Reduce heavy resources
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.fonts": 2,
        "profile.managed_default_content_settings.media_stream": 2,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)

    # Make each session a bit more isolated / stable
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(PAGE_TIMEOUT)
    return driver

# =========================================================
# SNAPSHOT / DETECTION
# =========================================================
SNAPSHOT_JS = r"""
return (() => {
    const isVisible = (el) => {
        if (!el) return false;
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return !!style &&
               style.visibility !== 'hidden' &&
               style.display !== 'none' &&
               rect.width > 0 &&
               rect.height > 0;
    };

    const bodyText = (document.body && document.body.innerText ? document.body.innerText : '')
        .replace(/\s+/g, ' ')
        .trim();

    const title = (document.title || '').trim();
    const combined = (title + ' ' + bodyText).toLowerCase();

    const visibleControls = [...document.querySelectorAll('input, button, select, textarea, a, form')]
        .filter(isVisible);

    const visiblePasswordInputs = [...document.querySelectorAll('input[type="password"]')]
        .filter(isVisible);

    const visibleTextInputs = [...document.querySelectorAll(
        'input[type="text"], input[type="email"], input:not([type]), textarea'
    )].filter(isVisible);

    const visibleSubmitButtons = [...document.querySelectorAll(
        'button, input[type="submit"], input[type="button"]'
    )]
    .filter(isVisible)
    .filter(el => /login|sign in|submit|continue|proceed|verify|log in/i.test((el.innerText || el.value || '')));

    const hasError = /503|502|504|bad gateway|service unavailable|temporarily unavailable|forbidden|access denied|captcha|just a moment|timed out|this site can't be reached|this site can’t be reached|err_connection_timed_out/i.test(combined);

    return {
        readyState: document.readyState,
        title,
        textLen: bodyText.length,
        visibleControlCount: visibleControls.length,
        visiblePasswordInputCount: visiblePasswordInputs.length,
        visibleTextInputCount: visibleTextInputs.length,
        visibleSubmitButtonCount: visibleSubmitButtons.length,
        hasError,
        href: location.href,
        bodyText
    };
})();
"""

def read_snapshot(driver):
    return driver.execute_script(SNAPSHOT_JS)

def contains_trigger_word(text: str) -> bool:
    t = (text or "").lower()
    return any(word.lower() in t for word in TRIGGER_WORDS)

def is_real_login_page(snapshot):
    if not snapshot:
        return False

    if snapshot.get("readyState") != "complete":
        return False

    if snapshot.get("hasError"):
        return False

    text_len = int(snapshot.get("textLen") or 0)
    controls = int(snapshot.get("visibleControlCount") or 0)
    pw = int(snapshot.get("visiblePasswordInputCount") or 0)
    tx = int(snapshot.get("visibleTextInputCount") or 0)
    submit = int(snapshot.get("visibleSubmitButtonCount") or 0)

    # Timeout / error pages should never pass this
    if text_len < 10:
        return False

    # Blank page / empty shell should never pass this
    if controls < 2:
        return False

    body = snapshot.get("bodyText") or ""
    trigger_hit = contains_trigger_word(body)

    # Real login form: trigger word + real visible form elements
    if trigger_hit and (pw >= 1 or tx >= 1 or submit >= 1):
        return True

    return False

def page_is_alive(snapshot):
    if not snapshot:
        return False
    if snapshot.get("hasError"):
        return False
    if int(snapshot.get("textLen") or 0) > 100:
        return True
    if int(snapshot.get("visibleControlCount") or 0) > 0:
        return True
    return False

# =========================================================
# WORKER
# =========================================================
def worker(session_id: int, start_delay: float):
    time.sleep(start_delay)

    driver = None
    try:
        driver = create_driver(session_id)
        driver.get("about:blank")

        attempt = 0
        first_load = True

        while not stop_event.is_set():
            attempt += 1
            current_time = time.strftime("%H:%M:%S")
            print(f"[{current_time}] S{session_id} attempt #{attempt} ...", flush=True)

            try:
                if first_load:
                    driver.get(TARGET_URL)
                    first_load = False
                else:
                    driver.refresh()
            except TimeoutException:
                try:
                    driver.execute_script("window.stop();")
                except Exception:
                    pass
            except WebDriverException as e:
                print(f"[{current_time}] S{session_id} WebDriver error: {type(e).__name__}")
                time.sleep(REFRESH_INTERVAL + start_delay)
                continue

            start = time.monotonic()
            last_snapshot = None

            while time.monotonic() - start < PAGE_TIMEOUT and not stop_event.is_set():
                try:
                    last_snapshot = read_snapshot(driver)

                    if is_real_login_page(last_snapshot):
                        with result_lock:
                            if not stop_event.is_set():
                                winner_session["id"] = session_id
                                stop_event.set()

                        print(f"[{time.strftime('%H:%M:%S')}] S{session_id} SUCCESS!")
                        print("\nDetected page state:")
                        print(f"  URL: {last_snapshot.get('href')}")
                        print(f"  Title: {last_snapshot.get('title')}")
                        print(f"  Text length: {last_snapshot.get('textLen')}")
                        print(f"  Visible controls: {last_snapshot.get('visibleControlCount')}")
                        print(f"  Password inputs: {last_snapshot.get('visiblePasswordInputCount')}")
                        print(f"  Text inputs: {last_snapshot.get('visibleTextInputCount')}")
                        print(f"  Submit buttons: {last_snapshot.get('visibleSubmitButtonCount')}")

                        if ENABLE_SCREENSHOT_ON_SUCCESS:
                            try:
                                fname = f"cbse_success_session_{session_id}.png"
                                driver.save_screenshot(fname)
                                print(f"Saved screenshot: {fname}")
                            except Exception:
                                pass

                        play_alarm()
                        return

                    time.sleep(POLL_INTERVAL)

                except WebDriverException:
                    break
                except Exception:
                    time.sleep(POLL_INTERVAL)

            try:
                driver.execute_script("window.stop();")
            except Exception:
                pass

            if last_snapshot and page_is_alive(last_snapshot):
                print(f"[{time.strftime('%H:%M:%S')}] S{session_id} page partially alive; retry in ~{REFRESH_INTERVAL + start_delay:.1f}s")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] S{session_id} retry in ~{REFRESH_INTERVAL + start_delay:.1f}s")

            time.sleep(REFRESH_INTERVAL + start_delay)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[S{session_id}] Critical error: {e}")
    finally:
        # detach=True keeps the browser open if you want it open
        pass

# =========================================================
# MAIN
# =========================================================
def main():
    print("=" * 72)
    print("CBSE WEBSITE MONITOR — 3 INDEPENDENT CHROME SESSIONS")
    print("=" * 72)
    print(f"Target: {TARGET_URL}")
    print(f"Sessions: {SESSION_COUNT}")
    print(f"Page timeout: {PAGE_TIMEOUT}s")
    print(f"Refresh interval: {REFRESH_INTERVAL}s")
    print(f"Stagger step: {STAGGER_STEP}s")
    print("=" * 72)
    print("\nThis version avoids the false positive from timeout/error pages.\n")

    threads = []

    try:
        for i in range(SESSION_COUNT):
            session_id = i + 1
            delay = i * STAGGER_STEP
            t = threading.Thread(
                target=worker,
                args=(session_id, delay),
                daemon=True
            )
            threads.append(t)
            t.start()
            time.sleep(0.4)

        while not stop_event.is_set():
            time.sleep(0.5)

        print(f"\nWinner session: S{winner_session['id']}")
        print("Keeping browsers open.")

        while True:
            time.sleep(60)

    except KeyboardInterrupt:
        print("\nStopped manually.")
        stop_event.set()

    except Exception as e:
        print(f"\nCritical error: {e}")
        stop_event.set()

if __name__ == "__main__":
    main()