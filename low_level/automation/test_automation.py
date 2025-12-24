#!/usr/bin/env python3
"""Test script for the automation library."""

import automation
import time

print('=== Testing automation library ===\n')

# Test screenshot functionality
print('1. Testing screenshot functionality:')
try:
    outputs = automation.list_outputs()
    print(f'   Available outputs: {outputs}')

    if outputs:
        print(f'   Capturing screenshot from {outputs[0]}...')
        img = automation.capture(outputs[0])
        print(f'   Screenshot captured: shape={img.shape}, dtype={img.dtype}')

        # Save it
        from PIL import Image

        Image.fromarray(img).save('test_screenshot.png')
        print('   Saved to test_screenshot.png')
except Exception as e:
    print(f'   Screenshot test failed: {e}')

print()

# Test shortcuts functionality
print('2. Testing shortcuts functionality:')
try:

    def on_shortcut(event_type: str, timestamp_ns: int):
        print(f'   Shortcut {event_type} at {timestamp_ns}')

    shortcuts = automation.Shortcuts(app_id='test_app')
    print('   Shortcuts manager created')

    shortcuts.register('test_key', 'Test shortcut', 'KP_Next', on_shortcut)
    print("   Registered shortcut 'test_key'")

    shortcuts.bind('test_key', 'KP_Next')
    print('   Bound KP_Next to test_key')

    print('\n   Press KP_Next to test (waiting 5 seconds)...')
    time.sleep(5)

    shortcuts.unbind('KP_Next')
    print('   Unbound KP_Next')

    shortcuts.stop()
    print('   Shortcuts manager stopped')

except Exception as e:
    print(f'   Shortcuts test failed: {e}')

print('\n=== Tests complete ===')
