import subprocess
import sys
import time
import numpy as np
import os
from PIL import Image

# --- Configuration ---
# NOTE: This PoC requires you to manually set your screen resolution.
# In a real application, this should be detected automatically.
# You can find your resolution with a command like `wlr-randr`.
SCREEN_WIDTH = 2560
SCREEN_HEIGHT = 1440

# Number of frames to capture for the benchmark
FRAMES_TO_FPS = 120
FRAME_COUNT = 60_000_000_000
OUTPUT_IMAGE_PATH = 'last_frame.png'


def run_benchmark():
    """
    Starts a screen recorder, captures a set number of frames,
    calculates the FPS, and saves the last frame.
    """
    # Command to run wf-recorder:
    # -c rawvideo: Use the raw video codec.
    # -p pixel_format=bgra: Set the pixel format to BGRA (Blue, Green, Red, Alpha).
    # -f -: Output to standard output.
    command = [
        './wf-recorder',
        '--codec=rawvideo',
        '--pixel-format=bgra',
        '-y',
        '-m',
        'rawvideo',
        '-o',
        'DP-2',
        '--framerate', '12',
        '-f',
        '-',
    ]

    # The number of bytes in a single frame
    frame_size = SCREEN_WIDTH * SCREEN_HEIGHT * 4  # 4 bytes for BGRA

    print('Starting screen capture...')

    # Start the wf-recorder process
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        frames_captured = 0
        last_frame_data = None

        # Give a moment for the process to start and for the user to click.
        time.sleep(0.1)

        print(f'Capturing {FRAME_COUNT} frames...')
        start_time = time.time()

        for i in range(FRAME_COUNT):
            # Read exactly one frame's worth of data from stdout
            frame_data = process.stdout.read(frame_size)
            if len(frame_data) == 0:
                continue

            if len(frame_data) < frame_size:
                print(
                    f'Error: Incomplete frame data received. Stream may have ended unexpectedly. {len(frame_data)=}'
                )
                break

            frames_captured += 1
            last_frame_data = frame_data
            print('.', end='')
            sys.stdout.flush()

            if i % FRAMES_TO_FPS == 0:
                end_time = time.time()

                # --- Performance Calculation ---
                duration = end_time - start_time
                if duration > 0.1:
                    fps = FRAMES_TO_FPS / duration
                    print('\n--- Benchmark Results ---')
                    print(f'Captured {FRAMES_TO_FPS} frames in {duration:.2f} seconds.')
                    print(f'Average FPS: {fps:.2f}')
                    print('-------------------------')
                start_time = time.time()

        # --- Save and Display Last Frame ---
        if last_frame_data:
            print(f"Saving last frame to '{OUTPUT_IMAGE_PATH}'...")
            # Create a NumPy array from the raw byte data
            # This is a fast, zero-copy operation.
            frame_np = np.frombuffer(last_frame_data, dtype=np.uint8)
            # Reshape the array to the screen dimensions
            frame_np = frame_np.reshape((SCREEN_HEIGHT, SCREEN_WIDTH, 4))

            # Convert BGRA (from wf-recorder) to RGBA (for Pillow)
            # BGRA -> RGBA by swapping the 0th (B) and 2nd (R) channels
            frame_rgba = frame_np[:, :, [2, 1, 0, 3]]

            # Create an image from the NumPy array
            img = Image.fromarray(frame_rgba, 'RGBA')
            img.save(OUTPUT_IMAGE_PATH)

            print(f"Displaying '{OUTPUT_IMAGE_PATH}' with feh...")
            os.system(f'feh {OUTPUT_IMAGE_PATH}')

    except KeyboardInterrupt:
        print('\nBenchmark interrupted by user.')
    finally:
        # Ensure the subprocess is terminated
        if process.poll() is None:
            print('Terminating wf-recorder process...')
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print('Process did not terminate gracefully, killing.')
                process.kill()

        # Print any errors from the recorder
        stderr_output = process.stderr.read().decode()
        if stderr_output:
            print('\n--- wf-recorder errors ---')
            print(stderr_output)
            print('--------------------------')


if __name__ == '__main__':
    run_benchmark()
