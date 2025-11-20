import logging
import time
from contextlib import contextmanager
from subprocess import run

from fan_tools.python import rel_path

from capture.common import crop
from capture.cv import imread, match_image
from capture.types import Rect
from capture.utils import ctx


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log = logging.getLogger('poe3')

for name in ['PIL.PngImagePlugin']:
    logging.getLogger(name).setLevel(logging.INFO)


# Key codes from /usr/include/linux/input-event-codes.h
KEY_LEFTCTRL = 29
BTN_LEFT = 0x110
WIDTH_LEFT = 2560 / 2
ASHEN_COORD = (472, 651)
NEW_INST_COORD = (666, 449)


def mousemove(x, y):
    x_str = str(WIDTH_LEFT + x / 2)
    y_str = str(y / 2)
    log.info(f'Click to {x_str}, {y_str}')
    run(['ydotool', 'mousemove', '-a', x_str, y_str])


def click(x=None, y=None, duration=None):
    """Click at position. If x,y provided, moves there first."""
    if x is not None and y is not None:
        mousemove(x, y)
        if duration:
            time.sleep(duration)

    run(['ydotool', 'click', '0xC0'])  # 0xC0 is BTN_LEFT click


def press(key_code):
    run(['ydotool', 'key', f'{key_code}:1'])
    run(['ydotool', 'key', f'{key_code}:0'])


@contextmanager
def hold(key):
    key_map = {
        'ctrl': KEY_LEFTCTRL,
    }
    key_code = key_map[key]

    # Press key down
    run(['ydotool', 'key', f'{key_code}:1'])
    try:
        yield
    finally:
        # Release key
        run(['ydotool', 'key', f'{key_code}:0'])


T_DIR = rel_path('../../templates/poe')
WP_IMAGE = imread(T_DIR / 'wp.png')
RESS_IMAGE = imread(T_DIR / 'ress.png')
DEL_IMAGE = imread(T_DIR / 'delir.png')


def go_instance():
    log.info('go new instance')
    if detect_delirium():
        return True

    with hold('ctrl'):
        # mousemove(1270, 640)
        click_waypoint()
        log.debug('clicked waypoint')
        time.sleep(0.35)
        click(*ASHEN_COORD, duration=0.1)
        log.debug('clicked ashen')
        time.sleep(0.45)
        click(*NEW_INST_COORD, duration=0.1)
        log.debug('clicked new instance')
        time.sleep(0.1)

    time.sleep(3.0)
    detect_delirium()


def detect_delirium():
    log.info('check delirium')
    cropped = screen = ctx.screenshot()
    # cropped = crop(screen, Rect(2200, 10, 2560, 380))
    if match_image(cropped, DEL_IMAGE):
        # play beep with pulseaudio
        run(['paplay', '/usr/share/sounds/freedesktop/stereo/complete.oga'])
        return True


def click_waypoint():
    log.info('click waypoint')
    screen = ctx.screenshot()

    # if need resurrect
    if coord := match_image(screen, RESS_IMAGE):
        log.info('need resurrect')
        mousemove(coord.x + 15, coord.y + 10)
        time.sleep(0.03)
        click()
        time.sleep(0.3)
        screen = ctx.screenshot()

    if coord := match_image(screen, WP_IMAGE):
        log.info(f'Got waypoing: {coord}')
        mousemove(coord.x + 6, coord.y + 2)
        time.sleep(0.03)
        click(coord.x + 6, coord.y + 2, duration=0.05)
    else:
        log.info('no wp found')


def main():
    while True:
        if go_instance():
            break


if __name__ == '__main__':
    main()
