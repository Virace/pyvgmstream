#include <pybind11/pybind11.h>

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

extern "C" {
#include "libvgmstream.h"
#include "libvgmstream_streamfile.h"
}

namespace py = pybind11;

namespace {

// pyvgmstream 到 vendored libvgmstream 公共头的本地桥接层。
// 该文件属于 pyvgmstream 自有文件，不是从上游直接复制过来的。
// 上游溯源：
// - vendor/vgmstream @ 5d01f5717c1489101918258fbed97659a390c356
// - 当前对接的上游公共头：
//   - vendor/vgmstream/src/libvgmstream.h
//   - vendor/vgmstream/src/libvgmstream_streamfile.h

constexpr const char* kBackendName = "pyvgmstream-libvgmstream";

using VgmstreamPtr = std::unique_ptr<libvgmstream_t, decltype(&libvgmstream_free)>;
using StreamfilePtr = std::unique_ptr<libstreamfile_t, decltype(&libstreamfile_close)>;

struct MemoryFile {
    std::string name;
    std::string data;
};

struct MemoryStreamfilePriv {
    std::shared_ptr<MemoryFile> file;
};

std::mutex g_log_callback_mutex;
PyObject* g_python_log_callback = nullptr;

struct FormatSnapshot {
    int sample_rate;
    libvgmstream_sfmt_t sample_format;
    int sample_size;
    int channels;
    int input_channels;
    uint32_t channel_layout;
    int subsong_index;
    int subsong_count;
    int64_t stream_samples;
    int64_t play_samples;
    int stream_bitrate;
    int64_t loop_start;
    int64_t loop_end;
    bool loop_flag;
    bool play_forever;
    std::string codec_name;
    std::string layout_name;
    std::string meta_name;
};

struct DecoderSnapshot {
    int buf_bytes;
    bool done;
};

struct DecodePolicy {
    int ignore_loop;
    libvgmstream_sfmt_t force_sample_format;
};

VgmstreamPtr create_context_or_throw() {
    VgmstreamPtr lib(libvgmstream_init(), &libvgmstream_free);
    if (!lib) {
        throw std::runtime_error("failed to initialize libvgmstream");
    }
    return lib;
}

StreamfilePtr open_input_streamfile_or_throw(const std::string& source_path) {
    StreamfilePtr streamfile(libstreamfile_open_from_stdio(source_path.c_str()), &libstreamfile_close);
    if (!streamfile) {
        throw py::value_error("could not open input file");
    }
    return streamfile;
}

int memory_streamfile_read(void* user_data, uint8_t* dst, int64_t offset, int length) {
    auto* priv = static_cast<MemoryStreamfilePriv*>(user_data);
    if (!priv || !priv->file || !dst || offset < 0 || length <= 0) {
        return 0;
    }

    const auto& data = priv->file->data;
    const auto data_size = static_cast<int64_t>(data.size());
    if (offset >= data_size) {
        return 0;
    }

    const auto remaining = static_cast<size_t>(data_size - offset);
    const auto to_copy = std::min(remaining, static_cast<size_t>(length));
    std::memcpy(dst, data.data() + offset, to_copy);
    return static_cast<int>(to_copy);
}

int64_t memory_streamfile_get_size(void* user_data) {
    auto* priv = static_cast<MemoryStreamfilePriv*>(user_data);
    if (!priv || !priv->file) {
        return 0;
    }
    return static_cast<int64_t>(priv->file->data.size());
}

const char* memory_streamfile_get_name(void* user_data) {
    auto* priv = static_cast<MemoryStreamfilePriv*>(user_data);
    if (!priv || !priv->file) {
        return "";
    }
    return priv->file->name.c_str();
}

libstreamfile_t* create_memory_streamfile_base(std::shared_ptr<MemoryFile> file);

libstreamfile_t* memory_streamfile_open(void* user_data, const char* filename) {
    auto* priv = static_cast<MemoryStreamfilePriv*>(user_data);
    if (!priv || !priv->file || !filename) {
        return nullptr;
    }

    if (priv->file->name != filename) {
        return nullptr;
    }

    return create_memory_streamfile_base(priv->file);
}

void memory_streamfile_close(libstreamfile_t* libsf) {
    if (!libsf) {
        return;
    }

    auto* priv = static_cast<MemoryStreamfilePriv*>(libsf->user_data);
    delete priv;
    std::free(libsf);
}

libstreamfile_t* create_memory_streamfile_base(std::shared_ptr<MemoryFile> file) {
    if (!file) {
        return nullptr;
    }

    auto* libsf = static_cast<libstreamfile_t*>(std::calloc(1, sizeof(libstreamfile_t)));
    if (!libsf) {
        return nullptr;
    }

    auto* priv = new MemoryStreamfilePriv{std::move(file)};
    libsf->user_data = priv;
    libsf->read = memory_streamfile_read;
    libsf->get_size = memory_streamfile_get_size;
    libsf->get_name = memory_streamfile_get_name;
    libsf->open = memory_streamfile_open;
    libsf->close = memory_streamfile_close;
    return libsf;
}

StreamfilePtr open_input_memory_streamfile_or_throw(
    const std::string& buffer_data,
    const std::string& filename_hint
) {
    if (filename_hint.empty()) {
        throw py::value_error("filename_hint must not be empty");
    }

    auto file = std::make_shared<MemoryFile>(MemoryFile{filename_hint, buffer_data});
    libstreamfile_t* libsf = create_memory_streamfile_base(file);
    if (!libsf) {
        throw std::runtime_error("failed to allocate in-memory streamfile");
    }
    return StreamfilePtr(libsf, &libstreamfile_close);
}

DecodePolicy build_default_decode_policy() {
    // 如果以后要调整默认解码语义，优先改这个本地 policy，
    // 不要直接在打开流程里散写 libvgmstream_config_t 字段。
    return DecodePolicy{
        false,
        static_cast<libvgmstream_sfmt_t>(0),
    };
}

libvgmstream_config_t build_default_decode_config() {
    const auto policy = build_default_decode_policy();
    libvgmstream_config_t cfg = {};
    if (policy.ignore_loop >= 0) {
        cfg.ignore_loop = policy.ignore_loop != 0;
    }
    if (policy.force_sample_format) {
        cfg.force_sfmt = policy.force_sample_format;
    }
    return cfg;
}

void apply_decode_policy(libvgmstream_t* lib, const DecodePolicy& policy) {
    libvgmstream_config_t cfg = {};
    if (policy.ignore_loop >= 0) {
        cfg.ignore_loop = policy.ignore_loop != 0;
    }
    if (policy.force_sample_format) {
        cfg.force_sfmt = policy.force_sample_format;
    }
    libvgmstream_setup(lib, &cfg);
}

void apply_default_decode_policy(libvgmstream_t* lib) {
    const auto policy = build_default_decode_policy();
    apply_decode_policy(lib, policy);
}

void clear_python_log_callback_unlocked() {
    Py_XDECREF(g_python_log_callback);
    g_python_log_callback = nullptr;
}

libvgmstream_loglevel_t coerce_log_level(int level) {
    switch (level) {
        case LIBVGMSTREAM_LOG_LEVEL_ALL:
            return LIBVGMSTREAM_LOG_LEVEL_ALL;
        case LIBVGMSTREAM_LOG_LEVEL_DEBUG:
            return LIBVGMSTREAM_LOG_LEVEL_DEBUG;
        case LIBVGMSTREAM_LOG_LEVEL_INFO:
            return LIBVGMSTREAM_LOG_LEVEL_INFO;
        case LIBVGMSTREAM_LOG_LEVEL_NONE:
            return LIBVGMSTREAM_LOG_LEVEL_NONE;
        default:
            throw py::value_error("unsupported libvgmstream log level");
    }
}

void python_log_callback_bridge(int level, const char* str) {
    py::gil_scoped_acquire gil;

    PyObject* callback = nullptr;
    {
        std::scoped_lock lock(g_log_callback_mutex);
        callback = g_python_log_callback;
        Py_XINCREF(callback);
    }
    if (!callback) {
        return;
    }

    PyObject* result = PyObject_CallFunction(callback, "is", level, str ? str : "");
    if (!result) {
        PyErr_WriteUnraisable(callback);
    }
    else {
        Py_DECREF(result);
    }
    Py_DECREF(callback);
}

void set_log_callback(int level, py::object callback) {
    const auto log_level = coerce_log_level(level);

    if (!callback.is_none() && !PyCallable_Check(callback.ptr())) {
        throw py::type_error("callback must be callable or None");
    }

    std::scoped_lock lock(g_log_callback_mutex);
    clear_python_log_callback_unlocked();

    if (log_level == LIBVGMSTREAM_LOG_LEVEL_NONE) {
        libvgmstream_set_log(log_level, nullptr);
        return;
    }

    if (callback.is_none()) {
        libvgmstream_set_log(log_level, nullptr);
        return;
    }

    Py_INCREF(callback.ptr());
    g_python_log_callback = callback.ptr();
    libvgmstream_set_log(log_level, &python_log_callback_bridge);
}

void disable_log_callback() {
    std::scoped_lock lock(g_log_callback_mutex);
    clear_python_log_callback_unlocked();
    libvgmstream_set_log(LIBVGMSTREAM_LOG_LEVEL_NONE, nullptr);
}

void emit_test_log_for_tests(int level, const std::string& message) {
    python_log_callback_bridge(level, message.c_str());
}

// 先把上游公开结构拍平成当前桥接层自己的快照，
// 避免后续逻辑分散依赖上游字段名和 Python 侧语义。
// 如果后续升级上游后 metadata / done / buf_bytes 行为变化，
// 维护者应优先检查这两个 snapshot helper。
FormatSnapshot snapshot_format(const libvgmstream_t* lib) {
    if (!lib || !lib->format) {
        throw std::runtime_error("libvgmstream format is unavailable");
    }

    const auto& format = *lib->format;
    return FormatSnapshot{
        format.sample_rate,
        format.sample_format,
        format.sample_size,
        format.channels,
        format.input_channels,
        format.channel_layout,
        format.subsong_index,
        format.subsong_count,
        format.stream_samples,
        format.play_samples,
        format.stream_bitrate,
        format.loop_start,
        format.loop_end,
        format.loop_flag,
        format.play_forever,
        std::string(format.codec_name),
        std::string(format.layout_name),
        std::string(format.meta_name),
    };
}

DecoderSnapshot snapshot_decoder(const libvgmstream_t* lib) {
    if (!lib || !lib->decoder) {
        throw std::runtime_error("libvgmstream decoder state is unavailable");
    }

    const auto& decoder = *lib->decoder;
    return DecoderSnapshot{
        decoder.buf_bytes,
        decoder.done,
    };
}

int resolve_subsong_index(const libvgmstream_t* lib, int requested_subsong) {
    const auto format = snapshot_format(lib);
    return format.subsong_index > 0 ? format.subsong_index : requested_subsong;
}

py::dict make_probe_result(const std::string& source_path, int requested_subsong, const libvgmstream_t* lib) {
    const auto format = snapshot_format(lib);

    py::dict result;
    result["source_path"] = source_path;
    result["subsong"] = resolve_subsong_index(lib, requested_subsong);
    result["backend_name"] = kBackendName;
    result["sample_rate"] = format.sample_rate;
    result["sample_format"] = static_cast<int>(format.sample_format);
    result["sample_size"] = format.sample_size;
    result["channels"] = format.channels;
    result["input_channels"] = format.input_channels;
    result["channel_layout"] = format.channel_layout;
    result["subsong_count"] = format.subsong_count;
    result["stream_samples"] = format.stream_samples;
    result["play_samples"] = format.play_samples;
    result["duration_seconds"] = format.sample_rate > 0
        ? static_cast<double>(format.play_samples) / static_cast<double>(format.sample_rate)
        : 0.0;
    result["stream_bitrate"] = format.stream_bitrate;
    result["loop_start"] = format.loop_start;
    result["loop_end"] = format.loop_end;
    result["loop_flag"] = format.loop_flag;
    result["play_forever"] = format.play_forever;
    result["codec_name"] = format.codec_name;
    result["layout_name"] = format.layout_name;
    result["meta_name"] = format.meta_name;
    return result;
}

const char* backend_name() {
    return kBackendName;
}

}  // namespace

class NativeStreamHandleBase {
public:
    py::bytes read_frames(int frame_count) {
        ensure_open();
        if (frame_count <= 0) {
            return py::bytes();
        }

        const auto format = snapshot_format(lib_.get());
        const size_t sample_bytes = static_cast<size_t>(format.sample_size);
        const size_t total_bytes =
            static_cast<size_t>(frame_count) * static_cast<size_t>(format.channels) * sample_bytes;
        std::vector<uint8_t> buffer(total_bytes);
        const int err = libvgmstream_fill(lib_.get(), buffer.data(), frame_count);
        if (err < 0) {
            throw std::runtime_error("libvgmstream_fill failed");
        }

        const auto decoder = snapshot_decoder(lib_.get());
        return py::bytes(
            reinterpret_cast<const char*>(buffer.data()),
            static_cast<py::ssize_t>(decoder.buf_bytes)
        );
    }

    int64_t tell_samples() {
        ensure_open();
        return libvgmstream_get_play_position(lib_.get());
    }

    void seek_samples(int64_t position) {
        ensure_open();
        libvgmstream_seek(lib_.get(), position);
    }

    void reset() {
        ensure_open();
        libvgmstream_reset(lib_.get());
    }

    void close() {
        lib_.reset();
    }

    int sample_rate() const {
        ensure_open();
        return snapshot_format(lib_.get()).sample_rate;
    }

    int sample_format() const {
        ensure_open();
        return static_cast<int>(snapshot_format(lib_.get()).sample_format);
    }

    int sample_size() const {
        ensure_open();
        return snapshot_format(lib_.get()).sample_size;
    }

    int channels() const {
        ensure_open();
        return snapshot_format(lib_.get()).channels;
    }

    int input_channels() const {
        ensure_open();
        return snapshot_format(lib_.get()).input_channels;
    }

    uint32_t channel_layout() const {
        ensure_open();
        return snapshot_format(lib_.get()).channel_layout;
    }

    int64_t stream_samples() const {
        ensure_open();
        return snapshot_format(lib_.get()).stream_samples;
    }

    int64_t play_samples() const {
        ensure_open();
        return snapshot_format(lib_.get()).play_samples;
    }

    int stream_bitrate() const {
        ensure_open();
        return snapshot_format(lib_.get()).stream_bitrate;
    }

    int64_t loop_start() const {
        ensure_open();
        return snapshot_format(lib_.get()).loop_start;
    }

    int64_t loop_end() const {
        ensure_open();
        return snapshot_format(lib_.get()).loop_end;
    }

    bool play_forever() const {
        ensure_open();
        return snapshot_format(lib_.get()).play_forever;
    }

    bool done() const {
        ensure_open();
        return snapshot_decoder(lib_.get()).done;
    }

protected:
    void ensure_open() const {
        if (!lib_) {
            throw std::runtime_error("stream handle is closed");
        }
    }

    void initialize_stream(
        StreamfilePtr&& streamfile,
        int subsong,
        int sample_format,
        int ignore_loop
    ) {
        lib_ = create_context_or_throw();
        auto policy = build_default_decode_policy();
        if (sample_format != 0) {
            policy.force_sample_format = static_cast<libvgmstream_sfmt_t>(sample_format);
        }
        if (ignore_loop >= 0) {
            policy.ignore_loop = ignore_loop;
        }
        apply_decode_policy(lib_.get(), policy);

        const int open_result = libvgmstream_open_stream(lib_.get(), streamfile.get(), subsong);
        if (open_result < 0) {
            throw py::value_error("not a valid or supported stream");
        }
    }

    VgmstreamPtr lib_{nullptr, &libvgmstream_free};
};

class NativeStreamHandle : public NativeStreamHandleBase {
public:
    NativeStreamHandle(
        const std::string& source_path,
        int subsong,
        int sample_format,
        int ignore_loop
    ) {
        initialize_stream(
            open_input_streamfile_or_throw(source_path),
            subsong,
            sample_format,
            ignore_loop
        );
    }
};

class NativeBufferStreamHandle : public NativeStreamHandleBase {
public:
    NativeBufferStreamHandle(
        py::bytes buffer_data,
        const std::string& filename_hint,
        int subsong,
        int sample_format,
        int ignore_loop
    ) {
        initialize_stream(
            open_input_memory_streamfile_or_throw(
                static_cast<std::string>(buffer_data),
                filename_hint
            ),
            subsong,
            sample_format,
            ignore_loop
        );
    }
};

unsigned int vgmstream_version() {
    return libvgmstream_get_version();
}

py::dict probe(const std::string& source_path, int subsong, int sample_format, int ignore_loop) {
    auto streamfile = open_input_streamfile_or_throw(source_path);
    auto lib = create_context_or_throw();
    auto policy = build_default_decode_policy();
    if (sample_format != 0) {
        policy.force_sample_format = static_cast<libvgmstream_sfmt_t>(sample_format);
    }
    if (ignore_loop >= 0) {
        policy.ignore_loop = ignore_loop;
    }
    apply_decode_policy(lib.get(), policy);

    const int open_result = libvgmstream_open_stream(lib.get(), streamfile.get(), subsong);
    if (open_result < 0) {
        throw py::value_error("not a valid or supported stream");
    }

    return make_probe_result(source_path, subsong, lib.get());
}

py::dict probe_buffer(
    py::bytes buffer_data,
    const std::string& filename_hint,
    int subsong,
    int sample_format,
    int ignore_loop
) {
    auto streamfile = open_input_memory_streamfile_or_throw(
        static_cast<std::string>(buffer_data),
        filename_hint
    );
    auto lib = create_context_or_throw();
    auto policy = build_default_decode_policy();
    if (sample_format != 0) {
        policy.force_sample_format = static_cast<libvgmstream_sfmt_t>(sample_format);
    }
    if (ignore_loop >= 0) {
        policy.ignore_loop = ignore_loop;
    }
    apply_decode_policy(lib.get(), policy);

    const int open_result = libvgmstream_open_stream(lib.get(), streamfile.get(), subsong);
    if (open_result < 0) {
        throw py::value_error("not a valid or supported stream");
    }

    return make_probe_result(filename_hint, subsong, lib.get());
}

template <typename T>
void bind_stream_handle_common(py::class_<T>& cls) {
    cls.def("read_frames", &T::read_frames, py::arg("frame_count"))
        .def("tell_samples", &T::tell_samples)
        .def("seek_samples", &T::seek_samples, py::arg("position"))
        .def("reset", &T::reset)
        .def("close", &T::close)
        .def_property_readonly("sample_rate", &T::sample_rate)
        .def_property_readonly("sample_format", &T::sample_format)
        .def_property_readonly("sample_size", &T::sample_size)
        .def_property_readonly("channels", &T::channels)
        .def_property_readonly("input_channels", &T::input_channels)
        .def_property_readonly("channel_layout", &T::channel_layout)
        .def_property_readonly("stream_samples", &T::stream_samples)
        .def_property_readonly("play_samples", &T::play_samples)
        .def_property_readonly("stream_bitrate", &T::stream_bitrate)
        .def_property_readonly("loop_start", &T::loop_start)
        .def_property_readonly("loop_end", &T::loop_end)
        .def_property_readonly("play_forever", &T::play_forever)
        .def_property_readonly("done", &T::done);
}

PYBIND11_MODULE(_native, module, py::mod_gil_not_used()) {
    module.doc() = "Native libvgmstream bindings for pyvgmstream.";
    module.def("backend_name", &backend_name, "Return the current native backend marker.");
    module.def("vgmstream_version", &vgmstream_version, "Return the linked libvgmstream version.");
    module.def(
        "set_log_callback",
        &set_log_callback,
        py::arg("level"),
        py::arg("callback") = py::none(),
        "Configure libvgmstream global log callback."
    );
    module.def("disable_log_callback", &disable_log_callback, "Disable current libvgmstream log callback.");
    module.def(
        "_emit_test_log_for_tests",
        &emit_test_log_for_tests,
        py::arg("level"),
        py::arg("message"),
        "Testing helper that triggers the currently installed Python log bridge."
    );
    module.def(
        "probe",
        &probe,
        py::arg("source_path"),
        py::arg("subsong") = 0,
        py::arg("sample_format") = 0,
        py::arg("ignore_loop") = -1,
        "Return probe information from libvgmstream."
    );
    module.def(
        "probe_buffer",
        &probe_buffer,
        py::arg("buffer_data"),
        py::arg("filename_hint"),
        py::arg("subsong") = 0,
        py::arg("sample_format") = 0,
        py::arg("ignore_loop") = -1,
        "Return probe information from in-memory input."
    );
    auto native_stream_handle = py::class_<NativeStreamHandle>(module, "NativeStreamHandle");
    native_stream_handle
        .def(
            py::init<const std::string&, int, int, int>(),
            py::arg("source_path"),
            py::arg("subsong") = 0,
            py::arg("sample_format") = 0,
            py::arg("ignore_loop") = -1
        );
    bind_stream_handle_common(native_stream_handle);

    auto native_buffer_stream_handle = py::class_<NativeBufferStreamHandle>(module, "NativeBufferStreamHandle");
    native_buffer_stream_handle
        .def(
            py::init<py::bytes, const std::string&, int, int, int>(),
            py::arg("buffer_data"),
            py::arg("filename_hint"),
            py::arg("subsong") = 0,
            py::arg("sample_format") = 0,
            py::arg("ignore_loop") = -1
        );
    bind_stream_handle_common(native_buffer_stream_handle);
}
