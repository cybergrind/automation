#!/usr/bin/env python3
import logging
import time

import pyautogui
import uinput
from pynput.keyboard import Controller
from system_hotkey import SystemHotkey


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log = logging.getLogger('nms')


KP_LEFT = ('kp_left',)  # 6
hk = SystemHotkey(use_xlib=True)
kb = Controller()
device = uinput.Device([uinput.KEY_D])


def press_with_uinput(key):
    device.emit(key, 1)
    time.sleep(0.017)
    device.emit(key, 0)
    time.sleep(0.017)


def press_with_pyautogui(key):
    pyautogui.keyDown(key, _pause=False)
    time.sleep(0.035)
    pyautogui.keyUp(key, _pause=False)
    time.sleep(0.035)


# modprobe uinput
def handle_repeat_d(param):
    log.debug('press d 10 times')
    for i in range(20):
        # press_with_uinput(uinput.KEY_D)
        press_with_pyautogui('d')
    log.debug('press d done')


def main():
    hk.register(KP_LEFT, callback=lambda x: handle_repeat_d(x), overwrite=True)
    try:
        while True:
            time.sleep(0.1)
    except Exception:
        pass


if __name__ == '__main__':
    main()
