#!/usr/bin/env python3
import screenshot_rs
import numpy as np
import time

print('Available outputs:', screenshot_rs.list_outputs())

# Benchmark: capture 60 screenshots
NUM_CAPTURES = 60
print(f'\nBenchmarking {NUM_CAPTURES} captures...')

start = time.perf_counter()
for i in range(NUM_CAPTURES):
    img = screenshot_rs.capture('DP-1')
end = time.perf_counter()

elapsed = end - start
fps = NUM_CAPTURES / elapsed
print(f'Total time: {elapsed:.3f}s')
print(f'Average per capture: {elapsed / NUM_CAPTURES * 1000:.2f}ms')
print(f'FPS: {fps:.2f}')

print(f'\nLast frame - Shape: {img.shape}, dtype: {img.dtype}')

# Save the last frame
from PIL import Image
Image.fromarray(img).save('output.png')
print('Saved to output.png')
