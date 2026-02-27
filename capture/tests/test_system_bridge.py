import system_bridge


def test_list_outputs():
    outputs = system_bridge.list_outputs()
    assert isinstance(outputs, list)
    for name in outputs:
        assert isinstance(name, str)


def test_capture_callable():
    assert callable(system_bridge.capture)


def test_capture_raw_callable():
    assert callable(system_bridge.capture_raw)


def test_shortcuts_class():
    assert hasattr(system_bridge, 'Shortcuts')
    assert isinstance(system_bridge.Shortcuts, type)
