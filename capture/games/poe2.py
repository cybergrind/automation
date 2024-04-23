#!/usr/bin/env python3
import logging
import time
from subprocess import run

import numpy as np
import pyautogui
from system_hotkey import SystemHotkey

from fan_tools.python import rel_path

from capture.common import crop
from capture.cv import imread, match
from capture.types import Rect
from capture.utils import ctx, dtime, spell, throttle


T_DIR = rel_path('../../templates/poe')


hk = SystemHotkey()
KB_NEW_INSTANCE = ('kp_next',)
KB_WP_CLICK = ('kp_down',)
KP_UP = ('kp_up',)
KP_END = ('kp_end',)
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


def get_single():
    # shift + click, then enter
    with pyautogui.hold('shift'):
        pyautogui.click()
    time.sleep(0.02)
    pyautogui.press('enter')


def clicks():
    with pyautogui.hold('ctrl'):
        for _ in range(5):
            pyautogui.click()
            time.sleep(0.01)


def main():
    log.info('register')
    hk.register(KB_NEW_INSTANCE, callback=lambda x: go_instance(), overwrite=True)
    hk.register(KB_WP_CLICK, callback=lambda x: click_waypoint(), overwrite=True)
    hk.register(KP_UP, callback=lambda x: get_single(), overwrite=True)
    hk.register(KP_END, callback=lambda x: clicks(), overwrite=True)

    while True:
        time.sleep(0.1)
        # log.debug(pyautogui.position())


if __name__ == '__main__':
    main()
