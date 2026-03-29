# pyvgmstream

中文说明见 `README.md`

`pyvgmstream` is a Python wrapper around `vgmstream`'s public `libvgmstream` API, currently focused on the `.wem` path.

## Public API

- `probe()`: read stream metadata
- `open_stream()`: open a decoded PCM16 stream
- `decode_to_wav_file()`: decode and export to a WAV file
- `decode_to_wav_bytes()`: decode and export to WAV bytes

The returned `StreamHandle` currently exposes:

- progress queries: `tell_samples()` / `tell_seconds()` / `done`
- stream position control: `seek_samples()` / `seek_seconds()` / `reset()`

## Install and Build

Make sure submodules are available when cloning the repository:

- `git clone --recursive https://github.com/Virace/pyvgmstream`
- or run `git submodule update --init --recursive` after cloning

Normal source build and installation paths:

- build a wheel: `uv build --wheel`
- install with uv: `uv pip install .`
- install with pip: `pip install .`

## Usage Examples

Read metadata:

```python
from pyvgmstream import probe

info = probe("example.wem")
print(info.sample_rate, info.channels, info.codec_name)
```

Read a PCM16 decoded stream:

```python
from pyvgmstream import open_stream

with open_stream("example.wem") as stream:
    chunk = stream.read_pcm16(4096)
    print(stream.tell_seconds(), stream.done)
```

Export a WAV file:

```python
from pyvgmstream import decode_to_wav_file

result = decode_to_wav_file("example.wem", "example.wav")
print(result.output_path, result.frame_count)
```

Export WAV bytes:

```python
from pyvgmstream import decode_to_wav_bytes

payload = decode_to_wav_bytes("example.wem")
print(len(payload))
```

## License

- The wrapper code is licensed under `BSD-3-Clause`; see `LICENSE`
- Third-party components and license texts are listed in `THIRD_PARTY_NOTICES.md`
- The currently included third-party license texts include:
  - `LICENSES/pybind11.txt`
  - `vendor/vgmstream/COPYING`
