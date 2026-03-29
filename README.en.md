# pyvgmstream

中文说明见 `README.md`

`pyvgmstream` is a Python wrapper around `vgmstream`'s public `libvgmstream` API.

## Public API

- `probe()`: read stream metadata
- `open_stream()`: open a decoded stream while keeping the upstream output sample format
- `decode_to_wav_file()`: decode and export to a WAV file
- `decode_to_wav_bytes()`: decode and export to WAV bytes
- `transcode_many()` / `transcode_tree()`: batch-transcode into WAV
- `PlaybackSession` / `PlaybackSnapshot` / `PCM16Sink`: playback control core
- `pyvgmstream.playback.backends.sounddevice.create_sounddevice_session()`: default optional playback backend

The returned `StreamHandle` currently exposes:

- generic frame reads in the current output format: `read_frames(frame_count)`
- explicit PCM16 convenience reads: `read_pcm16(frame_count)` when the stream is already PCM16 or was requested as PCM16
- progress queries: `tell_samples()` / `tell_seconds()` / `done`
- stream position control: `seek_samples()` / `seek_seconds()` / `reset()`
- upstream-backed format metadata: `sample_format` / `sample_size` / `input_channels` / `channel_layout` / `stream_samples` / `play_samples` / `duration_seconds` / `stream_bitrate` / `loop_start` / `loop_end` / `play_forever`

## Install and Build

If a release already provides a wheel matching your Python version and platform, prefer the wheel path:

- `pip install pyvgmstream`

If no matching wheel is available, prepare the source-build environment below.

### Source build prerequisites

- Windows:
  - Python `>=3.10`
  - CMake `>=3.20`
  - MSBuild / Visual Studio Build Tools
  - the `Desktop development with C++` workload
- macOS:
  - Python `>=3.10`
  - Xcode Command Line Tools
  - `brew install cmake pkg-config libvorbis`
- Linux:
  - Python `>=3.10`
  - `sudo apt-get update`
  - `sudo apt-get install -y gcc g++ make cmake build-essential git pkg-config libvorbis-dev`

If you need the upstream build reference, also consult:

- `vendor/vgmstream/doc/BUILD.md`
- `vendor/vgmstream/doc/BUILD-LIB.md`

If you are installing from a GitHub checkout, make sure submodules are available:

- `git clone --recursive https://github.com/Virace/pyvgmstream`
- or run `git submodule update --init --recursive` after cloning

If you are installing from a PyPI source distribution, the vendored `vgmstream` sources are already included in the sdist, so you do not need to initialize submodules, but you still need a local build environment.

### Common installation paths

Build a wheel from the current repository:

- `uv build --wheel`

Install from the current repository:

- `uv pip install .`
- `pip install .`

If you want the default local playback backend, install the optional extra:

- `pip install "pyvgmstream[playback]"`

Force a source build:

- `pip install --no-binary pyvgmstream pyvgmstream`

### Current note

- The project's officially supported Python range currently starts at `>=3.10`.
- The release workflow builds three platforms starting from Python `3.10`.
- The current platform targets are:
  - Windows: `x64`
  - Linux: `x86_64`
  - macOS: `arm64`
- macOS `x64` wheels are not planned at the moment.

## Usage Examples

Read metadata:

```python
from pyvgmstream import probe

info = probe("example.wem")
print(info.sample_rate, info.channels, info.duration_seconds, info.codec_name)
```

Read a decoded stream in its current output format:

```python
from pyvgmstream import open_stream

with open_stream("example.wem") as stream:
    chunk = stream.read_frames(4096)
    print(stream.sample_format, stream.sample_size, len(chunk))
    print(stream.tell_seconds(), stream.duration_seconds, stream.done)
```

If you explicitly need the PCM16 convenience layer:

```python
from pyvgmstream import DecodeConfig, SampleFormat, open_stream

with open_stream("example.wem", config=DecodeConfig(sample_format=SampleFormat.PCM16)) as stream:
    chunk = stream.read_pcm16(4096)
    print(len(chunk))
```

Export a WAV file:

```python
from pyvgmstream import decode_to_wav_file

result = decode_to_wav_file("example.wem", "example.wav")
print(result.output_path, result.frame_count)
```

By default WAV export preserves the current upstream output format. If a downstream wants to request `PCM16` / `PCM24` / `PCM32` explicitly, pass the corresponding `SampleFormat` via `config`.

Export WAV bytes:

```python
from pyvgmstream import decode_to_wav_bytes

payload = decode_to_wav_bytes("example.wem")
print(len(payload))
```

Recursively batch-transcode into WAV:

```python
from pyvgmstream import transcode_tree

summary = transcode_tree("input_wem", "output_wav", workers=4)
print(summary.processed_count, summary.failed_count)
```

Use the default optional playback backend:

```python
from pyvgmstream.playback.backends.sounddevice import create_sounddevice_session

session = create_sounddevice_session("example.wem", volume_percent=25.0)
session.start()
session.wait()
print(session.snapshot().duration_seconds)
```

For the fuller API surface, see:

- `docs/api.md`

## License

- The wrapper code is licensed under `BSD-3-Clause`; see `LICENSE`
- Third-party components and license texts are listed in `THIRD_PARTY_NOTICES.md`
- The currently included third-party license texts include:
  - `LICENSES/pybind11.txt`
  - `vendor/vgmstream/COPYING`
  - `vendor/vgmstream/ext_libs/licenses/*`
