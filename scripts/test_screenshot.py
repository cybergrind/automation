from fan_tools.unix import succ
from PIL import Image

from capture.utils import ctx


def main():
    np_screenshot = ctx.screenshot()
    im = Image.fromarray(np_screenshot)
    im.save('/tmp/a.png')
    succ('feh --zoom 75 /tmp/a.png')


if __name__ == '__main__':
    main()
