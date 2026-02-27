mod screenshot;
mod shortcuts;

use pyo3::prelude::*;

#[pyfunction]
fn capture<'py>(py: Python<'py>, output_name: &str) -> PyResult<Bound<'py, numpy::PyArray3<u8>>> {
    screenshot::capture(py, output_name)
}

#[pyfunction]
fn capture_raw(output_name: &str) -> PyResult<(Vec<u8>, u32, u32)> {
    screenshot::capture_raw(output_name)
}

#[pyfunction]
fn list_outputs() -> PyResult<Vec<String>> {
    screenshot::list_outputs()
}

#[pymodule]
fn system_bridge(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(capture, m)?)?;
    m.add_function(wrap_pyfunction!(capture_raw, m)?)?;
    m.add_function(wrap_pyfunction!(list_outputs, m)?)?;
    m.add_class::<shortcuts::Shortcuts>()?;
    Ok(())
}
