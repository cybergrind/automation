// Minimal Hyprland global shortcut test using hyprland-global-shortcuts-v1 protocol
// Compile: gcc global_shortcut.c -o global_shortcut $(pkg-config --cflags --libs wayland-client)
// Usage: ./global_shortcut

#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wayland-client.h>

// Protocol definitions for hyprland-global-shortcuts-v1 (inline, no wayland-scanner)
struct hyprland_global_shortcuts_manager_v1;
struct hyprland_global_shortcut_v1;

static const struct wl_interface hyprland_global_shortcut_v1_interface;

static const struct wl_interface *shortcut_types[] = {
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    &hyprland_global_shortcut_v1_interface,
};

// Manager requests: register_shortcut(new_id, string id, string app_id, string description, string trigger_description)
static const struct wl_message hyprland_global_shortcuts_manager_v1_requests[] = {
    { "register_shortcut", "nssss", shortcut_types + 5 },
    { "destroy", "", shortcut_types },
};

static const struct wl_interface hyprland_global_shortcuts_manager_v1_interface = {
    "hyprland_global_shortcuts_manager_v1", 1,
    2, hyprland_global_shortcuts_manager_v1_requests,
    0, NULL,
};

// Shortcut requests and events
static const struct wl_message hyprland_global_shortcut_v1_requests[] = {
    { "destroy", "", shortcut_types },
};

// pressed(tv_sec_hi, tv_sec_lo, tv_nsec), released(tv_sec_hi, tv_sec_lo, tv_nsec)
static const struct wl_message hyprland_global_shortcut_v1_events[] = {
    { "pressed", "uuu", shortcut_types },
    { "released", "uuu", shortcut_types },
};

static const struct wl_interface hyprland_global_shortcut_v1_interface = {
    "hyprland_global_shortcut_v1", 1,
    1, hyprland_global_shortcut_v1_requests,
    2, hyprland_global_shortcut_v1_events,
};

// Listener struct for shortcut events
struct hyprland_global_shortcut_v1_listener {
    void (*pressed)(void *data, struct hyprland_global_shortcut_v1 *shortcut,
                    uint32_t tv_sec_hi, uint32_t tv_sec_lo, uint32_t tv_nsec);
    void (*released)(void *data, struct hyprland_global_shortcut_v1 *shortcut,
                     uint32_t tv_sec_hi, uint32_t tv_sec_lo, uint32_t tv_nsec);
};

static inline int hyprland_global_shortcut_v1_add_listener(
    struct hyprland_global_shortcut_v1 *shortcut,
    const struct hyprland_global_shortcut_v1_listener *listener, void *data) {
    return wl_proxy_add_listener((struct wl_proxy *)shortcut, (void (**)(void))listener, data);
}

static inline struct hyprland_global_shortcut_v1 *
hyprland_global_shortcuts_manager_v1_register_shortcut(
    struct hyprland_global_shortcuts_manager_v1 *manager,
    const char *id, const char *app_id, const char *description, const char *trigger_description) {
    struct wl_proxy *proxy = wl_proxy_marshal_flags((struct wl_proxy *)manager,
        0, &hyprland_global_shortcut_v1_interface, wl_proxy_get_version((struct wl_proxy *)manager),
        0, NULL, id, app_id, description, trigger_description);
    return (struct hyprland_global_shortcut_v1 *)proxy;
}

// Global state
static struct wl_display *display;
static struct hyprland_global_shortcuts_manager_v1 *shortcuts_manager;
static struct hyprland_global_shortcut_v1 *shortcut;
static volatile bool running = true;

#define APP_ID "shortcut_test"
#define SHORTCUT_ID "kp_next"

// Shortcut event handlers
static void shortcut_pressed(void *data, struct hyprland_global_shortcut_v1 *sc,
                             uint32_t tv_sec_hi, uint32_t tv_sec_lo, uint32_t tv_nsec) {
    uint64_t sec = ((uint64_t)tv_sec_hi << 32) | tv_sec_lo;
    printf("PRESSED! time=%lu.%09u\n", sec, tv_nsec);
    fflush(stdout);
}

static void shortcut_released(void *data, struct hyprland_global_shortcut_v1 *sc,
                              uint32_t tv_sec_hi, uint32_t tv_sec_lo, uint32_t tv_nsec) {
    uint64_t sec = ((uint64_t)tv_sec_hi << 32) | tv_sec_lo;
    printf("RELEASED! time=%lu.%09u\n", sec, tv_nsec);
    fflush(stdout);
}

static const struct hyprland_global_shortcut_v1_listener shortcut_listener = {
    .pressed = shortcut_pressed,
    .released = shortcut_released,
};

// Registry listener
static void registry_global(void *data, struct wl_registry *registry,
                            uint32_t name, const char *interface, uint32_t version) {
    if (strcmp(interface, "hyprland_global_shortcuts_manager_v1") == 0) {
        shortcuts_manager = wl_registry_bind(registry, name,
            &hyprland_global_shortcuts_manager_v1_interface, 1);
        printf("Found hyprland_global_shortcuts_manager_v1\n");
    }
}

static void registry_global_remove(void *data, struct wl_registry *registry, uint32_t name) {}

static const struct wl_registry_listener registry_listener = {
    .global = registry_global,
    .global_remove = registry_global_remove,
};

// Signal handler for clean exit
static void handle_signal(int sig) {
    running = false;
}

int main(int argc, char *argv[]) {
    // Set up signal handlers for clean exit
    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    // Connect to Wayland display
    display = wl_display_connect(NULL);
    if (!display) {
        fprintf(stderr, "Failed to connect to Wayland display\n");
        return 1;
    }

    struct wl_registry *registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, NULL);
    wl_display_roundtrip(display);

    if (!shortcuts_manager) {
        fprintf(stderr, "hyprland_global_shortcuts_manager_v1 not available\n");
        wl_display_disconnect(display);
        return 1;
    }

    // Register the shortcut
    shortcut = hyprland_global_shortcuts_manager_v1_register_shortcut(
        shortcuts_manager, SHORTCUT_ID, APP_ID, "Test KP_Next shortcut", "KP_Next");
    if (!shortcut) {
        fprintf(stderr, "Failed to register shortcut\n");
        wl_display_disconnect(display);
        return 1;
    }

    hyprland_global_shortcut_v1_add_listener(shortcut, &shortcut_listener, NULL);
    wl_display_roundtrip(display);

    printf("Registered shortcut: %s:%s\n", APP_ID, SHORTCUT_ID);

    // Dynamically bind KP_Next to our shortcut via hyprctl
    printf("Binding KP_Next to shortcut...\n");
    int ret = system("hyprctl keyword bind ,KP_Next,global," APP_ID ":" SHORTCUT_ID);
    if (ret != 0) {
        fprintf(stderr, "Warning: hyprctl bind failed (ret=%d)\n", ret);
    }

    printf("Waiting for KP_Next key events... (Ctrl+C to exit)\n");

    // Event loop with poll to allow clean signal handling
    struct pollfd pfd = {
        .fd = wl_display_get_fd(display),
        .events = POLLIN,
    };

    while (running) {
        // Flush outgoing requests
        while (wl_display_prepare_read(display) != 0) {
            wl_display_dispatch_pending(display);
        }
        wl_display_flush(display);

        // Poll with 100ms timeout to check running flag
        int ret = poll(&pfd, 1, 100);
        if (ret < 0) {
            wl_display_cancel_read(display);
            break;
        }

        if (ret > 0) {
            wl_display_read_events(display);
            wl_display_dispatch_pending(display);
        } else {
            wl_display_cancel_read(display);
        }
    }

    // Cleanup: unbind the key
    printf("\nUnbinding KP_Next...\n");
    system("hyprctl keyword unbind ,KP_Next");

    wl_display_disconnect(display);
    printf("Done.\n");
    return 0;
}
