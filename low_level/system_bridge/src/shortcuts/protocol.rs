//! Generated bindings for hyprland-global-shortcuts-v1 protocol

// Re-export wayland_client so macros can find it
pub use wayland_client;

pub mod __interfaces {
    use wayland_client::backend as wayland_backend;
    wayland_scanner::generate_interfaces!("protocols/hyprland-global-shortcuts-v1.xml");
}

// Re-export interfaces so generate_client_code can find them
pub use __interfaces::*;

wayland_scanner::generate_client_code!("protocols/hyprland-global-shortcuts-v1.xml");
