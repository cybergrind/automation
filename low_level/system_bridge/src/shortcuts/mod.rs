//! Global shortcuts module using hyprland-global-shortcuts-v1 protocol

mod protocol;

use parking_lot::Mutex;
use pyo3::prelude::*;
use std::collections::HashMap;
use std::os::fd::{AsFd, OwnedFd};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread::{self, JoinHandle};
use wayland_client::{
    delegate_noop,
    protocol::wl_registry,
    Connection, Dispatch, EventQueue, QueueHandle,
};

use protocol::{
    hyprland_global_shortcut_v1, hyprland_global_shortcuts_manager_v1,
};

/// Registered shortcut info
struct ShortcutInfo {
    #[allow(dead_code)]
    id: String,
    callback: Py<PyAny>,
}

/// State for the Wayland event loop
struct ShortcutsState {
    manager: Option<hyprland_global_shortcuts_manager_v1::HyprlandGlobalShortcutsManagerV1>,
    shortcuts: HashMap<String, ShortcutInfo>,
}

impl ShortcutsState {
    fn new() -> Self {
        Self {
            manager: None,
            shortcuts: HashMap::new(),
        }
    }
}

// Registry dispatch - discover the shortcuts manager
impl Dispatch<wl_registry::WlRegistry, ()> for ShortcutsState {
    fn event(
        state: &mut Self,
        registry: &wl_registry::WlRegistry,
        event: wl_registry::Event,
        _: &(),
        _conn: &Connection,
        qh: &QueueHandle<Self>,
    ) {
        if let wl_registry::Event::Global { name, interface, version } = event {
            if interface == "hyprland_global_shortcuts_manager_v1" {
                state.manager = Some(
                    registry.bind::<hyprland_global_shortcuts_manager_v1::HyprlandGlobalShortcutsManagerV1, _, _>(
                        name, version.min(1), qh, (),
                    ),
                );
            }
        }
    }
}

// Manager dispatch - no events to handle
delegate_noop!(ShortcutsState: ignore hyprland_global_shortcuts_manager_v1::HyprlandGlobalShortcutsManagerV1);

// Shortcut dispatch - handle pressed/released events
impl Dispatch<hyprland_global_shortcut_v1::HyprlandGlobalShortcutV1, String> for ShortcutsState {
    fn event(
        state: &mut Self,
        _shortcut: &hyprland_global_shortcut_v1::HyprlandGlobalShortcutV1,
        event: hyprland_global_shortcut_v1::Event,
        shortcut_id: &String,
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
        let (event_type, timestamp_ns) = match event {
            hyprland_global_shortcut_v1::Event::Pressed { tv_sec_hi, tv_sec_lo, tv_nsec } => {
                let secs = ((tv_sec_hi as u64) << 32) | (tv_sec_lo as u64);
                ("pressed", secs * 1_000_000_000 + tv_nsec as u64)
            }
            hyprland_global_shortcut_v1::Event::Released { tv_sec_hi, tv_sec_lo, tv_nsec } => {
                let secs = ((tv_sec_hi as u64) << 32) | (tv_sec_lo as u64);
                ("released", secs * 1_000_000_000 + tv_nsec as u64)
            }
        };

        // Find callback and invoke it
        if let Some(info) = state.shortcuts.get(shortcut_id) {
            // Acquire GIL and call Python callback
            Python::with_gil(|py| {
                let callback = info.callback.clone_ref(py);
                if let Err(e) = callback.call1(py, (event_type, timestamp_ns)) {
                    eprintln!("Shortcut callback error: {}", e);
                }
            });
        }
    }
}

/// Shared data between main thread and event loop thread
struct SharedData {
    state: Mutex<ShortcutsState>,
    running: AtomicBool,
}

/// Python-exposed shortcuts manager
#[pyclass]
pub struct Shortcuts {
    app_id: String,
    shared: Arc<SharedData>,
    event_queue: Arc<Mutex<EventQueue<ShortcutsState>>>,
    connection: Connection,
    thread_handle: Option<JoinHandle<()>>,
}

#[pymethods]
impl Shortcuts {
    /// Create a new shortcuts manager
    #[new]
    #[pyo3(signature = (app_id = "automation"))]
    fn new(app_id: &str) -> PyResult<Self> {
        let conn = Connection::connect_to_env()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to connect to Wayland: {}", e)
            ))?;

        let mut event_queue = conn.new_event_queue();
        let qh = event_queue.handle();
        let display = conn.display();

        let mut state = ShortcutsState::new();
        display.get_registry(&qh, ());

        // Roundtrip to discover globals
        event_queue.roundtrip(&mut state)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Roundtrip failed: {}", e)
            ))?;

        if state.manager.is_none() {
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                "hyprland_global_shortcuts_manager_v1 not available (requires Hyprland)"
            ));
        }

        let shared = Arc::new(SharedData {
            state: Mutex::new(state),
            running: AtomicBool::new(true),
        });

        let event_queue = Arc::new(Mutex::new(event_queue));

        // Start event loop thread
        let shared_clone = Arc::clone(&shared);
        let event_queue_clone = Arc::clone(&event_queue);
        let conn_fd = conn.as_fd().try_clone_to_owned()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to clone fd: {}", e)
            ))?;

        let thread_handle = thread::spawn(move || {
            run_event_loop(conn_fd, event_queue_clone, shared_clone);
        });

        Ok(Self {
            app_id: app_id.to_string(),
            shared,
            event_queue,
            connection: conn,
            thread_handle: Some(thread_handle),
        })
    }

    /// Register a new global shortcut
    #[pyo3(signature = (shortcut_id, description, trigger_description, callback))]
    fn register(
        &mut self,
        shortcut_id: &str,
        description: &str,
        trigger_description: &str,
        callback: Py<PyAny>,
    ) -> PyResult<()> {
        let event_queue = self.event_queue.lock();
        let qh = event_queue.handle();
        let mut state = self.shared.state.lock();

        let manager = state.manager.as_ref()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                "Shortcuts manager not initialized"
            ))?;

        // Register the shortcut with Wayland
        let _shortcut = manager.register_shortcut(
            shortcut_id.to_string(),
            self.app_id.clone(),
            description.to_string(),
            trigger_description.to_string(),
            &qh,
            shortcut_id.to_string(),
        );

        // Store callback
        state.shortcuts.insert(
            shortcut_id.to_string(),
            ShortcutInfo {
                id: shortcut_id.to_string(),
                callback,
            },
        );

        drop(state);

        // Flush to send request
        self.connection.flush()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to flush: {}", e)
            ))?;

        Ok(())
    }

    /// Bind a key to a shortcut via hyprctl
    fn bind(&self, shortcut_id: &str, key: &str) -> PyResult<()> {
        let bind_spec = format!(",{},global,{}:{}", key, self.app_id, shortcut_id);

        let output = Command::new("hyprctl")
            .args(["keyword", "bind", &bind_spec])
            .output()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to run hyprctl: {}", e)
            ))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("hyprctl bind failed: {}", stderr)
            ));
        }

        Ok(())
    }

    /// Unbind a key
    fn unbind(&self, key: &str) -> PyResult<()> {
        let unbind_spec = format!(",{}", key);

        let output = Command::new("hyprctl")
            .args(["keyword", "unbind", &unbind_spec])
            .output()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to run hyprctl: {}", e)
            ))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("hyprctl unbind failed: {}", stderr)
            ));
        }

        Ok(())
    }

    /// Stop the event loop
    fn stop(&mut self) -> PyResult<()> {
        self.shared.running.store(false, Ordering::SeqCst);

        if let Some(handle) = self.thread_handle.take() {
            handle.join().map_err(|_|
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Thread join failed")
            )?;
        }

        Ok(())
    }
}

impl Drop for Shortcuts {
    fn drop(&mut self) {
        self.shared.running.store(false, Ordering::SeqCst);
        if let Some(handle) = self.thread_handle.take() {
            let _ = handle.join();
        }
    }
}

/// Run the Wayland event loop in a background thread
fn run_event_loop(
    fd: OwnedFd,
    event_queue: Arc<Mutex<EventQueue<ShortcutsState>>>,
    shared: Arc<SharedData>,
) {
    use nix::poll::{poll, PollFd, PollFlags, PollTimeout};

    while shared.running.load(Ordering::SeqCst) {
        // Poll with 100ms timeout
        let mut poll_fds = [PollFd::new(fd.as_fd(), PollFlags::POLLIN)];
        match poll(&mut poll_fds, PollTimeout::from(100u16)) {
            Ok(n) if n > 0 => {
                // Events available, dispatch them
                let mut eq = event_queue.lock();
                let mut state = shared.state.lock();
                let _ = eq.blocking_dispatch(&mut *state);
            }
            Ok(_) => {
                // Timeout, just continue
            }
            Err(e) => {
                if e != nix::errno::Errno::EINTR {
                    eprintln!("Poll error: {}", e);
                    break;
                }
            }
        }
    }
}
