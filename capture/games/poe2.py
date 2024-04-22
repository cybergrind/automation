#!/usr/bin/env python3
import logging
import time

import pyautogui
from system_hotkey import SystemHotkey

from fan_tools.python import rel_path

from capture.cv import imread, match
from capture.utils import ctx, dtime, spell, throttle


T_DIR = rel_path('../../templates/poe')


hk = SystemHotkey()
KB_NEW_INSTANCE = ('kp_next',)
KB_WP_CLICK = ('kp_down',)
WP_IMAGE = imread(T_DIR / 'wp.png')
RESS_IMAGE = imread(T_DIR / 'ress.png')

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log = logging.getLogger('poe2')


def go_instance():
    log.info('go new instance')
    # ctx.gui.click(0, 0)
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
        pyautogui.keyUp('control')


def click_waypoint():
    log.info('click waypoint')
    screen = ctx.screenshot()

    # if need resurrect
    if coord := match(screen, RESS_IMAGE):
        log.info('need resurrect')
        pyautogui.moveTo(coord.x + 15, coord.y + 10)
        time.sleep(0.03)
        pyautogui.click()
        time.sleep(0.2)
        screen = ctx.screenshot()

    if coord := match(screen, WP_IMAGE):
        pyautogui.moveTo(coord.x + 6, coord.y + 2)
        time.sleep(0.03)
        pyautogui.click(coord.x + 6, coord.y + 2, duration=0.05)
    else:
        log.info('no wp found')


def main():
    log.info('register')
    hk.register(KB_NEW_INSTANCE, callback=lambda x: go_instance(), overwrite=True)
    hk.register(KB_WP_CLICK, callback=lambda x: click_waypoint(), overwrite=True)

    while True:
        time.sleep(0.1)
        # print(pyautogui.position())


if __name__ == '__main__':
    main()
