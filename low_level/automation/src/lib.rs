//! Wayland automation library with screenshot and global shortcuts
//!
//! This library provides Python bindings for:
//! - Screenshot capture via wlr-screencopy protocol
//! - Global shortcuts via hyprland-global-shortcuts-v1 protocol

mod screenshot;
mod shortcuts;

use pyo3::prelude::*;

/// Capture a screenshot from the specified output and return as numpy array
/// Returns: numpy array with shape (height, width, 3) in RGB format
#[pyfunction]
fn capture<'py>(py: Python<'py>, output_name: &str) -> PyResult<Bound<'py, numpy::PyArray3<u8>>> {
    screenshot::capture(py, output_name)
}

/// Capture a screenshot and return raw bytes along with dimensions
/// Returns: (bytes, width, height)
#[pyfunction]
fn capture_raw(output_name: &str) -> PyResult<(Vec<u8>, u32, u32)> {
    screenshot::capture_raw(output_name)
}

/// List available Wayland outputs
#[pyfunction]
fn list_outputs() -> PyResult<Vec<String>> {
    screenshot::list_outputs()
}

/// Python module definition
#[pymodule]
fn automation(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Screenshot functions
    m.add_function(wrap_pyfunction!(capture, m)?)?;
    m.add_function(wrap_pyfunction!(capture_raw, m)?)?;
    m.add_function(wrap_pyfunction!(list_outputs, m)?)?;

    // Shortcuts class
    m.add_class::<shortcuts::Shortcuts>()?;

    Ok(())
}
