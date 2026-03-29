#include <pybind11/pybind11.h>

#include <cstdint>
#include <memory>
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

struct FormatSnapshot {
    int sample_rate;
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
    bool ignore_loop;
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

DecodePolicy build_default_decode_policy() {
    // 如果以后要调整默认解码语义，优先改这个本地 policy，
    // 不要直接在打开流程里散写 libvgmstream_config_t 字段。
    return DecodePolicy{
        true,
        LIBVGMSTREAM_SFMT_PCM16,
    };
}

libvgmstream_config_t build_default_decode_config() {
    const auto policy = build_default_decode_policy();
    libvgmstream_config_t cfg = {};
    cfg.ignore_loop = policy.ignore_loop;
    cfg.force_sfmt = policy.force_sample_format;
    return cfg;
}

void apply_decode_policy(libvgmstream_t* lib, const DecodePolicy& policy) {
    libvgmstream_config_t cfg = {};
    cfg.ignore_loop = policy.ignore_loop;
    cfg.force_sfmt = policy.force_sample_format;
    libvgmstream_setup(lib, &cfg);
}

void apply_default_decode_policy(libvgmstream_t* lib) {
    const auto policy = build_default_decode_policy();
    apply_decode_policy(lib, policy);
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

class NativeStreamHandle {
public:
    NativeStreamHandle(const std::string& source_path, int subsong)
        : lib_(create_context_or_throw()) {
        apply_default_decode_policy(lib_.get());

        auto streamfile = open_input_streamfile_or_throw(source_path);
        const int open_result = libvgmstream_open_stream(lib_.get(), streamfile.get(), subsong);
        if (open_result < 0) {
            throw py::value_error("not a valid or supported stream");
        }
    }

    py::bytes read_pcm16(int frame_count) {
        ensure_open();
        if (frame_count <= 0) {
            return py::bytes();
        }

        const auto format = snapshot_format(lib_.get());
        std::vector<int16_t> buffer(static_cast<size_t>(frame_count) * static_cast<size_t>(format.channels));
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

private:
    void ensure_open() const {
        if (!lib_) {
            throw std::runtime_error("stream handle is closed");
        }
    }

    VgmstreamPtr lib_{nullptr, &libvgmstream_free};
};

unsigned int vgmstream_version() {
    return libvgmstream_get_version();
}

py::dict probe(const std::string& source_path, int subsong) {
    auto streamfile = open_input_streamfile_or_throw(source_path);
    auto lib = create_context_or_throw();

    const int open_result = libvgmstream_open_stream(lib.get(), streamfile.get(), subsong);
    if (open_result < 0) {
        throw py::value_error("not a valid or supported stream");
    }

    return make_probe_result(source_path, subsong, lib.get());
}

PYBIND11_MODULE(_native, module, py::mod_gil_not_used()) {
    module.doc() = "Native libvgmstream bindings for pyvgmstream.";
    module.def("backend_name", &backend_name, "Return the current native backend marker.");
    module.def("vgmstream_version", &vgmstream_version, "Return the linked libvgmstream version.");
    module.def("probe", &probe, "Return probe information from libvgmstream.");
    py::class_<NativeStreamHandle>(module, "NativeStreamHandle")
        .def(py::init<const std::string&, int>(), py::arg("source_path"), py::arg("subsong") = 0)
        .def("read_pcm16", &NativeStreamHandle::read_pcm16, py::arg("frame_count"))
        .def("tell_samples", &NativeStreamHandle::tell_samples)
        .def("seek_samples", &NativeStreamHandle::seek_samples, py::arg("position"))
        .def("reset", &NativeStreamHandle::reset)
        .def("close", &NativeStreamHandle::close)
        .def_property_readonly("sample_rate", &NativeStreamHandle::sample_rate)
        .def_property_readonly("channels", &NativeStreamHandle::channels)
        .def_property_readonly("input_channels", &NativeStreamHandle::input_channels)
        .def_property_readonly("channel_layout", &NativeStreamHandle::channel_layout)
        .def_property_readonly("stream_samples", &NativeStreamHandle::stream_samples)
        .def_property_readonly("play_samples", &NativeStreamHandle::play_samples)
        .def_property_readonly("stream_bitrate", &NativeStreamHandle::stream_bitrate)
        .def_property_readonly("loop_start", &NativeStreamHandle::loop_start)
        .def_property_readonly("loop_end", &NativeStreamHandle::loop_end)
        .def_property_readonly("play_forever", &NativeStreamHandle::play_forever)
        .def_property_readonly("done", &NativeStreamHandle::done);
}
