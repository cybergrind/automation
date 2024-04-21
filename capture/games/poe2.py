#!/usr/bin/env python3
import argparse
import logging
import time
import pyautogui

from system_hotkey import SystemHotkey

from capture.utils import ctx, dtime, spell, throttle


hk = SystemHotkey()
kb = ('kp_next',)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log = logging.getLogger('poe2')


def go_instance():
    log.info('go new instance')
    #ctx.gui.click(0, 0)
    with pyautogui.hold('ctrl'):
        pyautogui.moveTo(1270, 640)
        time.sleep(0.01)
        pyautogui.click(1270, 640, duration=0.02)
        time.sleep(0.02)
        #time.sleep(0.05)
        #pyautogui.move(481, 634)
        pyautogui.moveTo(481, 634)
        time.sleep(0.01)
        pyautogui.click(481, 634, duration=0.05)
        time.sleep(0.5)
        #pyautogui.move(593, 440)
        pyautogui.moveTo(593, 440)
        time.sleep(0.1)
        pyautogui.click(593, 440, duration=0.05)
        pyautogui.keyUp('control')
    


def main():
    log.info('register')
    #go_instance()
    hk.register(kb, callback=lambda x: go_instance(), overwrite=True)
    #hk.register(('escape',), callback=lambda e: print('hi'))
    
    while True:
        time.sleep(0.1)
        #print(pyautogui.position())


if __name__ == '__main__':
    main()
