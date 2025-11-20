#!/usr/bin/env python3
import logging

from fan_tools.python import rel_path

from capture.cv import imread
from capture.utils import ctx


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log = logging.getLogger('trade_cards')


T_DIR = rel_path('../../templates/poe')
DIVINATION_CARD = imread(T_DIR / 'divination_card.png')
TRADE_BUTTON = imread(T_DIR / 'trade_button.png')
TRADE_CLAIM = imread(T_DIR / 'trade_claim.png')
TRADE_WINDOW = imread(T_DIR / 'trade_window.png')


def trade_card() -> bool:
    if ctx.click_on(DIVINATION_CARD, ctrl=True):
        log.debug('click for trade')
        ctx.click_on(TRADE_BUTTON, offset=(10, 10))
        log.debug('click for claim')
        ctx.click_on(TRADE_CLAIM, offset=(10, 60), ctrl=True)
        log.debug('Click ok')
        return True
    return False


def main():
    if not ctx.detect(TRADE_WINDOW):
        log.info('Trade window is not open')
        log.info('Click alt+shift+click on Lily')
        return

    while trade_card():
        continue
    log.info('Finished')


if __name__ == '__main__':
    main()
