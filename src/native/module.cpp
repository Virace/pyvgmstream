#include <pybind11/pybind11.h>

#include <string>
#include <vector>

extern "C" {
#include "libvgmstream.h"
#include "libvgmstream_streamfile.h"
}

namespace py = pybind11;

class NativeStreamHandle {
public:
    NativeStreamHandle(const std::string& source_path, int subsong)
        : source_path_(source_path) {
        lib_ = libvgmstream_init();
        if (!lib_) {
            throw std::runtime_error("failed to initialize libvgmstream");
        }

        libvgmstream_config_t cfg = {};
        cfg.ignore_loop = true;
        cfg.force_sfmt = LIBVGMSTREAM_SFMT_PCM16;
        libvgmstream_setup(lib_, &cfg);

        libstreamfile_t* streamfile = libstreamfile_open_from_stdio(source_path.c_str());
        if (!streamfile) {
            libvgmstream_free(lib_);
            lib_ = nullptr;
            throw py::value_error("could not open input file");
        }

        const int open_result = libvgmstream_open_stream(lib_, streamfile, subsong);
        libstreamfile_close(streamfile);
        if (open_result < 0) {
            libvgmstream_free(lib_);
            lib_ = nullptr;
            throw py::value_error("not a valid or supported stream");
        }
    }

    ~NativeStreamHandle() {
        close();
    }

    py::bytes read_pcm16(int frame_count) {
        ensure_open();
        if (frame_count <= 0) {
            return py::bytes();
        }

        std::vector<int16_t> buffer(static_cast<size_t>(frame_count) * static_cast<size_t>(lib_->format->channels));
        const int err = libvgmstream_fill(lib_, buffer.data(), frame_count);
        if (err < 0) {
            throw std::runtime_error("libvgmstream_fill failed");
        }

        return py::bytes(
            reinterpret_cast<const char*>(buffer.data()),
            static_cast<py::ssize_t>(lib_->decoder->buf_bytes)
        );
    }

    int64_t tell_samples() {
        ensure_open();
        return libvgmstream_get_play_position(lib_);
    }

    void seek_samples(int64_t position) {
        ensure_open();
        libvgmstream_seek(lib_, position);
    }

    void reset() {
        ensure_open();
        libvgmstream_reset(lib_);
    }

    void close() {
        if (lib_) {
            libvgmstream_free(lib_);
            lib_ = nullptr;
        }
    }

    int sample_rate() const {
        ensure_open();
        return lib_->format->sample_rate;
    }

    int channels() const {
        ensure_open();
        return lib_->format->channels;
    }

    bool done() const {
        ensure_open();
        return lib_->decoder->done;
    }

private:
    void ensure_open() const {
        if (!lib_) {
            throw std::runtime_error("stream handle is closed");
        }
    }

    std::string source_path_;
    libvgmstream_t* lib_ = nullptr;
};

const char* backend_name() {
    return "pyvgmstream-libvgmstream";
}

unsigned int vgmstream_version() {
    return libvgmstream_get_version();
}

py::dict probe(const std::string& source_path, int subsong) {
    libstreamfile_t* streamfile = libstreamfile_open_from_stdio(source_path.c_str());
    if (!streamfile) {
        throw py::value_error("could not open input file");
    }

    libvgmstream_t* lib = libvgmstream_init();
    if (!lib) {
        libstreamfile_close(streamfile);
        throw std::runtime_error("failed to initialize libvgmstream");
    }

    const int open_result = libvgmstream_open_stream(lib, streamfile, subsong);
    libstreamfile_close(streamfile);
    if (open_result < 0) {
        libvgmstream_free(lib);
        throw py::value_error("not a valid or supported stream");
    }

    py::dict result;
    result["source_path"] = source_path;
    result["subsong"] = lib->format->subsong_index > 0 ? lib->format->subsong_index : subsong;
    result["backend_name"] = backend_name();
    result["sample_rate"] = lib->format->sample_rate;
    result["channels"] = lib->format->channels;
    result["subsong_count"] = lib->format->subsong_count;
    result["loop_flag"] = lib->format->loop_flag;
    result["codec_name"] = std::string(lib->format->codec_name);
    result["layout_name"] = std::string(lib->format->layout_name);
    result["meta_name"] = std::string(lib->format->meta_name);
    libvgmstream_free(lib);
    return result;
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
        .def_property_readonly("done", &NativeStreamHandle::done);
}
