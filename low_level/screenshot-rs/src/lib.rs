use numpy::ndarray::Array3;
use numpy::PyArray3;
use pyo3::prelude::*;
use std::os::fd::AsFd;
use std::os::unix::io::OwnedFd;
use wayland_client::{
    delegate_noop,
    protocol::{wl_buffer, wl_output, wl_registry, wl_shm, wl_shm_pool},
    Connection, Dispatch, QueueHandle, WEnum,
};
use wayland_protocols_wlr::screencopy::v1::client::{
    zwlr_screencopy_frame_v1, zwlr_screencopy_manager_v1,
};

struct OutputInfo {
    output: wl_output::WlOutput,
    name: Option<String>,
}

struct FrameData {
    format: Option<wl_shm::Format>,
    width: u32,
    height: u32,
    stride: u32,
    ready: bool,
    failed: bool,
}

struct AppState {
    shm: Option<wl_shm::WlShm>,
    screencopy_manager: Option<zwlr_screencopy_manager_v1::ZwlrScreencopyManagerV1>,
    outputs: Vec<OutputInfo>,
    frame_data: FrameData,
}

impl AppState {
    fn new() -> Self {
        Self {
            shm: None,
            screencopy_manager: None,
            outputs: Vec::new(),
            frame_data: FrameData {
                format: None,
                width: 0,
                height: 0,
                stride: 0,
                ready: false,
                failed: false,
            },
        }
    }
}

impl Dispatch<wl_registry::WlRegistry, ()> for AppState {
    fn event(
        state: &mut Self,
        registry: &wl_registry::WlRegistry,
        event: wl_registry::Event,
        _: &(),
        _conn: &Connection,
        qh: &QueueHandle<Self>,
    ) {
        if let wl_registry::Event::Global { name, interface, version } = event {
            match interface.as_str() {
                "wl_shm" => {
                    state.shm = Some(registry.bind::<wl_shm::WlShm, _, _>(name, version, qh, ()));
                }
                "wl_output" => {
                    let output = registry.bind::<wl_output::WlOutput, _, _>(name, version.min(4), qh, ());
                    state.outputs.push(OutputInfo { output, name: None });
                }
                "zwlr_screencopy_manager_v1" => {
                    state.screencopy_manager = Some(
                        registry.bind::<zwlr_screencopy_manager_v1::ZwlrScreencopyManagerV1, _, _>(
                            name, version.min(3), qh, (),
                        ),
                    );
                }
                _ => {}
            }
        }
    }
}

impl Dispatch<wl_output::WlOutput, ()> for AppState {
    fn event(
        state: &mut Self,
        output: &wl_output::WlOutput,
        event: wl_output::Event,
        _: &(),
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
        if let wl_output::Event::Name { name } = event {
            if let Some(info) = state.outputs.iter_mut().find(|o| o.output == *output) {
                info.name = Some(name);
            }
        }
    }
}

impl Dispatch<zwlr_screencopy_frame_v1::ZwlrScreencopyFrameV1, ()> for AppState {
    fn event(
        state: &mut Self,
        _frame: &zwlr_screencopy_frame_v1::ZwlrScreencopyFrameV1,
        event: zwlr_screencopy_frame_v1::Event,
        _: &(),
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
        match event {
            zwlr_screencopy_frame_v1::Event::Buffer { format, width, height, stride } => {
                if let WEnum::Value(fmt) = format {
                    // Prefer XRGB8888 or ARGB8888
                    if fmt == wl_shm::Format::Xrgb8888 || fmt == wl_shm::Format::Argb8888 {
                        state.frame_data.format = Some(fmt);
                        state.frame_data.width = width;
                        state.frame_data.height = height;
                        state.frame_data.stride = stride;
                    }
                }
            }
            zwlr_screencopy_frame_v1::Event::Ready { .. } => {
                state.frame_data.ready = true;
            }
            zwlr_screencopy_frame_v1::Event::Failed => {
                state.frame_data.failed = true;
            }
            zwlr_screencopy_frame_v1::Event::Flags { .. } => {}
            _ => {}
        }
    }
}

delegate_noop!(AppState: ignore wl_shm::WlShm);
delegate_noop!(AppState: ignore wl_shm_pool::WlShmPool);
delegate_noop!(AppState: ignore wl_buffer::WlBuffer);
delegate_noop!(AppState: ignore zwlr_screencopy_manager_v1::ZwlrScreencopyManagerV1);

fn create_shm_file(size: usize) -> std::io::Result<OwnedFd> {
    use nix::sys::memfd::{memfd_create, MemFdCreateFlag};
    use std::ffi::CString;

    let name = CString::new("wl_shm").unwrap();
    let fd = memfd_create(&name, MemFdCreateFlag::MFD_CLOEXEC)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;

    nix::unistd::ftruncate(&fd, size as i64)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;

    Ok(fd)
}

fn capture_screenshot_impl(output_name: &str) -> PyResult<(Vec<u8>, u32, u32)> {
    let conn = Connection::connect_to_env()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to connect to Wayland: {}", e)))?;

    let mut event_queue = conn.new_event_queue();
    let qh = event_queue.handle();
    let display = conn.display();

    let mut state = AppState::new();
    display.get_registry(&qh, ());

    // First roundtrip to get globals
    event_queue.roundtrip(&mut state)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Roundtrip failed: {}", e)))?;
    // Second roundtrip to get output names
    event_queue.roundtrip(&mut state)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Roundtrip failed: {}", e)))?;

    // Check required globals
    if state.shm.is_none() {
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("wl_shm not available"));
    }
    if state.screencopy_manager.is_none() {
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("zwlr_screencopy_manager_v1 not available"));
    }

    // Find target output
    let target_output_idx = state.outputs.iter()
        .position(|o| o.name.as_deref() == Some(output_name))
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Output '{}' not found", output_name)))?;

    // Start capture - clone references before mutable borrow
    let frame = state.screencopy_manager.as_ref().unwrap()
        .capture_output(0, &state.outputs[target_output_idx].output, &qh, ());

    // Wait for buffer info
    while state.frame_data.format.is_none() && !state.frame_data.failed {
        event_queue.blocking_dispatch(&mut state)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Dispatch failed: {}", e)))?;
    }

    if state.frame_data.failed {
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Frame capture failed"));
    }

    let width = state.frame_data.width;
    let height = state.frame_data.height;
    let stride = state.frame_data.stride;
    let format = state.frame_data.format.unwrap();
    let size = (stride * height) as usize;

    // Create shm buffer
    let fd = create_shm_file(size)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create shm file: {}", e)))?;

    let pool = state.shm.as_ref().unwrap().create_pool(fd.as_fd(), size as i32, &qh, ());
    let buffer = pool.create_buffer(0, width as i32, height as i32, stride as i32, format, &qh, ());

    // Memory map for reading
    let mmap = unsafe {
        nix::sys::mman::mmap(
            None,
            std::num::NonZeroUsize::new(size).unwrap(),
            nix::sys::mman::ProtFlags::PROT_READ | nix::sys::mman::ProtFlags::PROT_WRITE,
            nix::sys::mman::MapFlags::MAP_SHARED,
            &fd,
            0,
        )
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("mmap failed: {}", e)))?
    };

    // Copy frame
    frame.copy(&buffer);

    // Wait for ready
    while !state.frame_data.ready && !state.frame_data.failed {
        event_queue.blocking_dispatch(&mut state)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Dispatch failed: {}", e)))?;
    }

    if state.frame_data.failed {
        unsafe { nix::sys::mman::munmap(mmap, size).ok(); }
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Frame capture failed"));
    }

    // Convert to RGB (from BGRX)
    let src = unsafe { std::slice::from_raw_parts(mmap.as_ptr() as *const u8, size) };
    let mut rgb_data = Vec::with_capacity((width * height * 3) as usize);

    for y in 0..height {
        let row_start = (y * stride) as usize;
        for x in 0..width {
            let pixel_start = row_start + (x * 4) as usize;
            // XRGB8888/ARGB8888: memory layout is B, G, R, X/A on little-endian
            rgb_data.push(src[pixel_start + 2]); // R
            rgb_data.push(src[pixel_start + 1]); // G
            rgb_data.push(src[pixel_start]);     // B
        }
    }

    // Cleanup
    unsafe { nix::sys::mman::munmap(mmap, size).ok(); }
    buffer.destroy();
    pool.destroy();
    frame.destroy();

    Ok((rgb_data, width, height))
}

/// Capture a screenshot from the specified output and return as numpy array
/// Returns: numpy array with shape (height, width, 3) in RGB format
#[pyfunction]
fn capture<'py>(py: Python<'py>, output_name: &str) -> PyResult<Bound<'py, PyArray3<u8>>> {
    let (rgb_data, width, height) = capture_screenshot_impl(output_name)?;

    let array = Array3::from_shape_vec((height as usize, width as usize, 3), rgb_data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Array shape error: {}", e)))?;
    Ok(PyArray3::from_owned_array_bound(py, array))
}

/// Capture a screenshot and return raw bytes along with dimensions
/// Returns: (bytes, width, height)
#[pyfunction]
fn capture_raw(output_name: &str) -> PyResult<(Vec<u8>, u32, u32)> {
    capture_screenshot_impl(output_name)
}

/// List available outputs
#[pyfunction]
fn list_outputs() -> PyResult<Vec<String>> {
    let conn = Connection::connect_to_env()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to connect to Wayland: {}", e)))?;

    let mut event_queue = conn.new_event_queue();
    let qh = event_queue.handle();
    let display = conn.display();

    let mut state = AppState::new();
    display.get_registry(&qh, ());

    event_queue.roundtrip(&mut state).ok();
    event_queue.roundtrip(&mut state).ok();

    Ok(state.outputs.iter()
        .filter_map(|o| o.name.clone())
        .collect())
}

#[pymodule]
fn screenshot_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(capture, m)?)?;
    m.add_function(wrap_pyfunction!(capture_raw, m)?)?;
    m.add_function(wrap_pyfunction!(list_outputs, m)?)?;
    Ok(())
}
