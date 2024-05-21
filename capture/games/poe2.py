#!/usr/bin/env python3
import logging
import threading
import time
from dataclasses import dataclass
from subprocess import run
from uuid import uuid4

import pyautogui
from fan_tools.python import rel_path
from pynput import mouse
from system_hotkey import SystemHotkey

from capture.common import crop
from capture.cv import imread, match
from capture.types import Rect
from capture.utils import ctx


T_DIR = rel_path('../../templates/poe')


hk = SystemHotkey()
KB_NEW_INSTANCE = ('kp_next',)
KB_WP_CLICK = ('kp_down',)
KP_UP = ('kp_up',)
KP_END = ('kp_end',)
KP_LEFT = ('kp_left',)  # 6
WP_IMAGE = imread(T_DIR / 'wp.png')
RESS_IMAGE = imread(T_DIR / 'ress.png')
DEL_IMAGE = imread(T_DIR / 'delir.png')

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log = logging.getLogger('poe2')


def go_instance():
    log.info('go new instance')
    if detect_delirium():
        return

    with pyautogui.hold('ctrl'):
        # pyautogui.moveTo(1270, 640)
        click_waypoint()
        time.sleep(0.01)
        pyautogui.click(1270, 640, duration=0.02)
        time.sleep(0.02)
        # time.sleep(0.05)
        # pyautogui.move(481, 634)
        pyautogui.moveTo(481, 634)
        time.sleep(0.01)
        pyautogui.click(481, 634, duration=0.05)
        time.sleep(0.5)
        # pyautogui.move(593, 440)
        pyautogui.moveTo(593, 440)
        time.sleep(0.1)
        pyautogui.click(593, 440, duration=0.05)

    time.sleep(3.5)
    detect_delirium()


def detect_delirium():
    log.info('check delirium')
    screen = ctx.screenshot()
    cropped = crop(screen, Rect(2200, 10, 2560, 380))
    if match(cropped, DEL_IMAGE):
        # play beep with pulseaudio
        run(['paplay', '/usr/share/sounds/freedesktop/stereo/complete.oga'])
        return True


def click_waypoint():
    log.info('click waypoint')
    screen = ctx.screenshot()

    # if need resurrect
    if coord := match(screen, RESS_IMAGE):
        log.info('need resurrect')
        pyautogui.moveTo(coord.x + 15, coord.y + 10)
        time.sleep(0.03)
        pyautogui.click()
        time.sleep(0.4)
        screen = ctx.screenshot()

    if coord := match(screen, WP_IMAGE):
        pyautogui.moveTo(coord.x + 6, coord.y + 2)
        time.sleep(0.03)
        pyautogui.click(coord.x + 6, coord.y + 2, duration=0.05)
    else:
        log.info('no wp found')


CLICKS_UUID = uuid4()


def register_clicks():
    global CLICKS_UUID
    our_uuid = uuid4()
    CLICKS_UUID = our_uuid

    def clicks():
        if CLICKS_UUID != our_uuid:
            # long press repeated uuids
            return

        hk.unregister(KP_END)
        with pyautogui.hold('ctrl'):
            for _ in range(8):
                pyautogui.click()
                time.sleep(0.01)
        register_clicks()

    hk.register(KP_END, callback=lambda x: clicks(), overwrite=True)


def ensure_press(key, delay=0.23):
    """
    variants:
    pynput
    python-evdev
    uinput

    xdotool
    """
    with pyautogui.hold(key, _pause=True):
        time.sleep(delay)
    return


@dataclass
class SoulrendLoop:
    enabled: bool = False
    active: bool = False
    last_life: float = 0
    last_malevolence: float = 0
    iteration: int = 0
    exit: bool = False


SOULREND_LOOP = SoulrendLoop()
LIFE_TICK = 4.7
MALEVOLENCE_TICK = 18.5


def run_soulrend_loop():
    while not SOULREND_LOOP.exit:
        time.sleep(0.1)
        SOULREND_LOOP.iteration += 1
        if SOULREND_LOOP.iteration < 8:
            continue
        if not SOULREND_LOOP.enabled:
            continue
        if not SOULREND_LOOP.active:
           continue
        t = time.time()
        if SOULREND_LOOP.last_life + LIFE_TICK < t:
            log.debug('press t')
            ensure_press('t')
            SOULREND_LOOP.last_life = t
        elif SOULREND_LOOP.last_malevolence + MALEVOLENCE_TICK < t:
            log.debug('press a')
            ensure_press('a')
            SOULREND_LOOP.last_malevolence = t


def pressed_soulrend_loop(param):
    log.debug(f'{param=}')
    SOULREND_LOOP.enabled = not SOULREND_LOOP.enabled
    SOULREND_LOOP.iteration = 0


def get_single():
    # shift + click, then enter
    with pyautogui.hold('shift'):
        pyautogui.click()
    time.sleep(0.02)
    pyautogui.press('enter')


def mouse_click(x, y, button, pressed):
    if button == mouse.Button.right:
        SOULREND_LOOP.active = pressed


def main():
    log.info('register')
    hk.register(KB_NEW_INSTANCE, callback=lambda x: go_instance(), overwrite=True)
    hk.register(KB_WP_CLICK, callback=lambda x: click_waypoint(), overwrite=True)
    hk.register(KP_UP, callback=lambda x: get_single(), overwrite=True)
    sl_loop = threading.Thread(target=run_soulrend_loop)
    sl_loop.start()
    hk.register(KP_LEFT, callback=lambda x: pressed_soulrend_loop(x), overwrite=True)
    # hk.register(KP_END, callback=lambda x: clicks(), overwrite=True)
    register_clicks()
    mouse_listener = mouse.Listener(on_click=mouse_click)
    mouse_listener.start()
    try:
        while True:
            time.sleep(0.1)
            # log.debug(pyautogui.position())
    except:
        SOULREND_LOOP.exit = True
        mouse_listener.stop()


if __name__ == '__main__':
    main()
