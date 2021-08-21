import time
from capture.utils import spell


def test_01_ctx(ctx):
    print(f'{ctx=}')
    assert 'time' not in ctx
    assert time.time() - ctx.time() < 1

    ctx['time'] = 1
    assert time.time() - ctx.time() > 1000


@spell(cooldown=0, cast_time=0.5)
def c1():
    return True


@spell(cooldown=0, cast_time=0.5)
def c2():
    return True


def test_02_ctx_time(ctx):
    with ctx.mock_all():
        assert c1()
        assert not c2()
