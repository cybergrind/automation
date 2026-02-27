# automation

Screen automation toolkit with native Wayland integration.

## Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Rust toolchain (for building `system_bridge` native extension)
- Wayland compositor with wlr-screencopy support (e.g. Hyprland)

## Setup

```bash
uv sync
```

This installs all Python dependencies and builds the `system_bridge` Rust extension automatically.

## Usage

```bash
uv run python scripts/test_screenshot.py
```

## Native extension (`system_bridge`)

Located in `low_level/system_bridge/`. Provides:

- `system_bridge.capture(output_name)` -- screenshot as numpy array (H, W, 3) RGB
- `system_bridge.capture_raw(output_name)` -- screenshot as raw bytes + dimensions
- `system_bridge.list_outputs()` -- list available Wayland outputs
- `system_bridge.Shortcuts` -- global shortcuts via Hyprland protocol

## Tests

```bash
uv run pytest capture/tests/ -v
```
