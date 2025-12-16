// Minimal Wayland screenshot using wlr-screencopy protocol
// Compile: gcc screenshot.c -o screenshot $(pkg-config --cflags --libs wayland-client) -lpng
// Usage: ./screenshot

#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <wayland-client.h>
#include <png.h>

// Protocol headers - inline definitions for wlr-screencopy-unstable-v1
// zwlr_screencopy_manager_v1
struct zwlr_screencopy_manager_v1;
struct zwlr_screencopy_frame_v1;

static const struct wl_interface zwlr_screencopy_frame_v1_interface;

static const struct wl_interface *types[] = {
    NULL,
    NULL,
    NULL,
    NULL,
    &zwlr_screencopy_frame_v1_interface,
    &wl_output_interface,
    &zwlr_screencopy_frame_v1_interface,
    &wl_output_interface,
    NULL,
    NULL,
    &wl_buffer_interface,
};

static const struct wl_message zwlr_screencopy_manager_v1_requests[] = {
    { "capture_output", "nio", types + 4 },
    { "capture_output_region", "nioiiii", types + 7 },
    { "destroy", "", types + 0 },
};

static const struct wl_interface zwlr_screencopy_manager_v1_interface = {
    "zwlr_screencopy_manager_v1", 3,
    3, zwlr_screencopy_manager_v1_requests,
    0, NULL,
};

static const struct wl_message zwlr_screencopy_frame_v1_requests[] = {
    { "copy", "o", types + 10 },
    { "destroy", "", types + 0 },
    { "copy_with_damage", "2o", types + 10 },
};

enum zwlr_screencopy_frame_v1_flags {
    ZWLR_SCREENCOPY_FRAME_V1_FLAGS_Y_INVERT = 1,
};

static const struct wl_message zwlr_screencopy_frame_v1_events[] = {
    { "buffer", "uuuu", types + 0 },
    { "flags", "u", types + 0 },
    { "ready", "uuu", types + 0 },
    { "failed", "", types + 0 },
    { "damage", "3uuuu", types + 0 },
    { "linux_dmabuf", "3uuu", types + 0 },
    { "buffer_done", "3", types + 0 },
};

static const struct wl_interface zwlr_screencopy_frame_v1_interface = {
    "zwlr_screencopy_frame_v1", 3,
    3, zwlr_screencopy_frame_v1_requests,
    7, zwlr_screencopy_frame_v1_events,
};

struct zwlr_screencopy_frame_v1_listener {
    void (*buffer)(void *data, struct zwlr_screencopy_frame_v1 *frame,
                   uint32_t format, uint32_t width, uint32_t height, uint32_t stride);
    void (*flags)(void *data, struct zwlr_screencopy_frame_v1 *frame, uint32_t flags);
    void (*ready)(void *data, struct zwlr_screencopy_frame_v1 *frame,
                  uint32_t tv_sec_hi, uint32_t tv_sec_lo, uint32_t tv_nsec);
    void (*failed)(void *data, struct zwlr_screencopy_frame_v1 *frame);
    void (*damage)(void *data, struct zwlr_screencopy_frame_v1 *frame,
                   uint32_t x, uint32_t y, uint32_t width, uint32_t height);
    void (*linux_dmabuf)(void *data, struct zwlr_screencopy_frame_v1 *frame,
                         uint32_t format, uint32_t width, uint32_t height);
    void (*buffer_done)(void *data, struct zwlr_screencopy_frame_v1 *frame);
};

static inline int zwlr_screencopy_frame_v1_add_listener(
    struct zwlr_screencopy_frame_v1 *frame,
    const struct zwlr_screencopy_frame_v1_listener *listener, void *data) {
    return wl_proxy_add_listener((struct wl_proxy *)frame, (void (**)(void))listener, data);
}

static inline struct zwlr_screencopy_frame_v1 *
zwlr_screencopy_manager_v1_capture_output(struct zwlr_screencopy_manager_v1 *manager,
                                          int32_t overlay_cursor, struct wl_output *output) {
    struct wl_proxy *id = wl_proxy_marshal_flags((struct wl_proxy *)manager,
        0, &zwlr_screencopy_frame_v1_interface, wl_proxy_get_version((struct wl_proxy *)manager),
        0, NULL, overlay_cursor, output);
    return (struct zwlr_screencopy_frame_v1 *)id;
}

static inline void zwlr_screencopy_frame_v1_copy(
    struct zwlr_screencopy_frame_v1 *frame, struct wl_buffer *buffer) {
    wl_proxy_marshal_flags((struct wl_proxy *)frame, 0, NULL,
        wl_proxy_get_version((struct wl_proxy *)frame), 0, buffer);
}

static inline void zwlr_screencopy_frame_v1_destroy(struct zwlr_screencopy_frame_v1 *frame) {
    wl_proxy_marshal_flags((struct wl_proxy *)frame, 1, NULL,
        wl_proxy_get_version((struct wl_proxy *)frame), WL_MARSHAL_FLAG_DESTROY);
}

// Target output name
#define TARGET_OUTPUT "DP-2"

// Global state
static struct wl_display *display;
static struct wl_registry *registry;
static struct wl_shm *shm;
static struct wl_output *target_output;
static struct zwlr_screencopy_manager_v1 *screencopy_manager;

static struct {
    uint32_t format;
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    bool buffer_ready;
    bool y_invert;
    bool done;
    bool failed;
    void *data;
    size_t size;
} buffer_info = {0};

static char *current_output_name = NULL;
static bool output_name_pending = false;

// wl_output listener
static void output_geometry(void *data, struct wl_output *output,
    int32_t x, int32_t y, int32_t pw, int32_t ph, int32_t subpixel,
    const char *make, const char *model, int32_t transform) {}

static void output_mode(void *data, struct wl_output *output,
    uint32_t flags, int32_t width, int32_t height, int32_t refresh) {}

static void output_done(void *data, struct wl_output *output) {
    if (output_name_pending && current_output_name) {
        if (strcmp(current_output_name, TARGET_OUTPUT) == 0) {
            target_output = output;
            printf("Found target output: %s\n", current_output_name);
        }
        free(current_output_name);
        current_output_name = NULL;
        output_name_pending = false;
    }
}

static void output_scale(void *data, struct wl_output *output, int32_t scale) {}

static void output_name(void *data, struct wl_output *output, const char *name) {
    current_output_name = strdup(name);
    output_name_pending = true;
}

static void output_description(void *data, struct wl_output *output, const char *desc) {}

static const struct wl_output_listener output_listener = {
    .geometry = output_geometry,
    .mode = output_mode,
    .done = output_done,
    .scale = output_scale,
    .name = output_name,
    .description = output_description,
};

// Create shared memory file
static int create_shm_file(size_t size) {
    char name[] = "/wl_shm-XXXXXX";
    int fd = memfd_create(name, MFD_CLOEXEC);
    if (fd < 0) return -1;
    if (ftruncate(fd, size) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

// Frame listener callbacks
static void frame_buffer(void *data, struct zwlr_screencopy_frame_v1 *frame,
                         uint32_t format, uint32_t width, uint32_t height, uint32_t stride) {
    buffer_info.format = format;
    buffer_info.width = width;
    buffer_info.height = height;
    buffer_info.stride = stride;
    buffer_info.size = stride * height;
    buffer_info.buffer_ready = true;
    printf("Buffer info: %ux%u, stride=%u, format=0x%x\n", width, height, stride, format);
}

static void frame_flags(void *data, struct zwlr_screencopy_frame_v1 *frame, uint32_t flags) {
    buffer_info.y_invert = (flags & ZWLR_SCREENCOPY_FRAME_V1_FLAGS_Y_INVERT) != 0;
}

static void frame_ready(void *data, struct zwlr_screencopy_frame_v1 *frame,
                        uint32_t tv_sec_hi, uint32_t tv_sec_lo, uint32_t tv_nsec) {
    buffer_info.done = true;
    printf("Frame ready!\n");
}

static void frame_failed(void *data, struct zwlr_screencopy_frame_v1 *frame) {
    buffer_info.failed = true;
    fprintf(stderr, "Frame capture failed!\n");
}

static void frame_damage(void *data, struct zwlr_screencopy_frame_v1 *frame,
                         uint32_t x, uint32_t y, uint32_t width, uint32_t height) {}

static void frame_linux_dmabuf(void *data, struct zwlr_screencopy_frame_v1 *frame,
                               uint32_t format, uint32_t width, uint32_t height) {}

static void frame_buffer_done(void *data, struct zwlr_screencopy_frame_v1 *frame) {}

static const struct zwlr_screencopy_frame_v1_listener frame_listener = {
    .buffer = frame_buffer,
    .flags = frame_flags,
    .ready = frame_ready,
    .failed = frame_failed,
    .damage = frame_damage,
    .linux_dmabuf = frame_linux_dmabuf,
    .buffer_done = frame_buffer_done,
};

// Registry listener
static void registry_global(void *data, struct wl_registry *registry,
                            uint32_t name, const char *interface, uint32_t version) {
    if (strcmp(interface, "wl_shm") == 0) {
        shm = wl_registry_bind(registry, name, &wl_shm_interface, 1);
    } else if (strcmp(interface, "wl_output") == 0) {
        struct wl_output *output = wl_registry_bind(registry, name, &wl_output_interface, 4);
        wl_output_add_listener(output, &output_listener, NULL);
    } else if (strcmp(interface, "zwlr_screencopy_manager_v1") == 0) {
        screencopy_manager = wl_registry_bind(registry, name,
            &zwlr_screencopy_manager_v1_interface, version < 3 ? version : 3);
    }
}

static void registry_global_remove(void *data, struct wl_registry *registry, uint32_t name) {}

static const struct wl_registry_listener registry_listener = {
    .global = registry_global,
    .global_remove = registry_global_remove,
};

// Save buffer as PNG (handles XRGB8888 and XBGR8888)
static bool save_png(const char *filename) {
    FILE *fp = fopen(filename, "wb");
    if (!fp) {
        perror("fopen");
        return false;
    }

    png_structp png = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    if (!png) {
        fclose(fp);
        return false;
    }

    png_infop info = png_create_info_struct(png);
    if (!info) {
        png_destroy_write_struct(&png, NULL);
        fclose(fp);
        return false;
    }

    if (setjmp(png_jmpbuf(png))) {
        png_destroy_write_struct(&png, &info);
        fclose(fp);
        return false;
    }

    png_init_io(png, fp);
    png_set_IHDR(png, info, buffer_info.width, buffer_info.height, 8,
                 PNG_COLOR_TYPE_RGB, PNG_INTERLACE_NONE,
                 PNG_COMPRESSION_TYPE_DEFAULT, PNG_FILTER_TYPE_DEFAULT);
    png_write_info(png, info);

    // Allocate row buffer (RGB)
    uint8_t *row = malloc(buffer_info.width * 3);
    if (!row) {
        png_destroy_write_struct(&png, &info);
        fclose(fp);
        return false;
    }

    // wl_shm format enum values (not DRM fourcc):
    // WL_SHM_FORMAT_ARGB8888 = 0  -> memory: B, G, R, A (little-endian)
    // WL_SHM_FORMAT_XRGB8888 = 1  -> memory: B, G, R, X (little-endian)
    // WL_SHM_FORMAT_XBGR8888 = 2  -> memory: R, G, B, X (little-endian)
    bool is_bgr = (buffer_info.format == 0 || buffer_info.format == 1);

    for (uint32_t y = 0; y < buffer_info.height; y++) {
        uint32_t src_y = buffer_info.y_invert ? (buffer_info.height - 1 - y) : y;
        uint8_t *src = (uint8_t *)buffer_info.data + src_y * buffer_info.stride;

        for (uint32_t x = 0; x < buffer_info.width; x++) {
            if (is_bgr) {
                // ARGB/XRGB: memory is B, G, R, A/X
                row[x * 3 + 0] = src[x * 4 + 2]; // R
                row[x * 3 + 1] = src[x * 4 + 1]; // G
                row[x * 3 + 2] = src[x * 4 + 0]; // B
            } else {
                // ABGR/XBGR: memory is R, G, B, A/X
                row[x * 3 + 0] = src[x * 4 + 0]; // R
                row[x * 3 + 1] = src[x * 4 + 1]; // G
                row[x * 3 + 2] = src[x * 4 + 2]; // B
            }
        }
        png_write_row(png, row);
    }

    free(row);
    png_write_end(png, NULL);
    png_destroy_write_struct(&png, &info);
    fclose(fp);
    return true;
}

int main(int argc, char *argv[]) {
    // Connect to Wayland display
    display = wl_display_connect(NULL);
    if (!display) {
        fprintf(stderr, "Failed to connect to Wayland display\n");
        return 1;
    }

    registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, NULL);
    wl_display_roundtrip(display);
    wl_display_roundtrip(display); // Second roundtrip for output names

    if (!shm) {
        fprintf(stderr, "wl_shm not available\n");
        return 1;
    }
    if (!screencopy_manager) {
        fprintf(stderr, "zwlr_screencopy_manager_v1 not available (need wlroots compositor)\n");
        return 1;
    }
    if (!target_output) {
        fprintf(stderr, "Output '%s' not found\n", TARGET_OUTPUT);
        return 1;
    }

    // Start capture
    struct zwlr_screencopy_frame_v1 *frame =
        zwlr_screencopy_manager_v1_capture_output(screencopy_manager, 0, target_output);
    zwlr_screencopy_frame_v1_add_listener(frame, &frame_listener, NULL);

    // Wait for buffer info
    while (!buffer_info.buffer_ready && !buffer_info.failed) {
        wl_display_roundtrip(display);
    }
    if (buffer_info.failed) return 1;

    // Create shm buffer
    int fd = create_shm_file(buffer_info.size);
    if (fd < 0) {
        fprintf(stderr, "Failed to create shm file\n");
        return 1;
    }

    buffer_info.data = mmap(NULL, buffer_info.size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (buffer_info.data == MAP_FAILED) {
        close(fd);
        fprintf(stderr, "mmap failed\n");
        return 1;
    }

    struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, buffer_info.size);
    struct wl_buffer *buffer = wl_shm_pool_create_buffer(pool, 0,
        buffer_info.width, buffer_info.height, buffer_info.stride, buffer_info.format);
    wl_shm_pool_destroy(pool);
    close(fd);

    // Copy frame to buffer
    zwlr_screencopy_frame_v1_copy(frame, buffer);

    // Wait for completion
    while (!buffer_info.done && !buffer_info.failed) {
        wl_display_roundtrip(display);
    }

    if (buffer_info.failed) {
        munmap(buffer_info.data, buffer_info.size);
        return 1;
    }

    // Save as PNG
    if (save_png("output.png")) {
        printf("Screenshot saved to output.png\n");
    } else {
        fprintf(stderr, "Failed to save PNG\n");
        munmap(buffer_info.data, buffer_info.size);
        return 1;
    }

    // Cleanup
    munmap(buffer_info.data, buffer_info.size);
    wl_buffer_destroy(buffer);
    zwlr_screencopy_frame_v1_destroy(frame);
    wl_display_disconnect(display);

    return 0;
}
