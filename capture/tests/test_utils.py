import time


def test_01_ctx(ctx):
    print(f'{ctx=}')
    assert 'time' not in ctx
    assert time.time() - ctx.time() < 1

    ctx['time'] = 1
    assert time.time() - ctx.time() > 1000


def test_01_ctx_time(ctx):
    with ctx.mock_gui():
        pass
