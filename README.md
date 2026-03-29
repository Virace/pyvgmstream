# pyvgmstream

English version: `README.en.md`

`pyvgmstream` 是一个面向 Python 的 `vgmstream` 公共 API 包装层。

## 公开 API

- `probe()`：读取流元数据
- `open_stream()`：打开 PCM16 解码流
- `decode_to_wav_file()`：解码并导出为 WAV 文件
- `decode_to_wav_bytes()`：解码并导出为 WAV 字节
- `transcode_many()` / `transcode_tree()`：批量转码为 WAV
- `PlaybackSession` / `PlaybackSnapshot` / `PCM16Sink`：播放控制核心
- `pyvgmstream.playback.backends.sounddevice.create_sounddevice_session()`：默认可选播放后端

基于 `open_stream()` 返回的 `StreamHandle`，当前可用的方法和属性包括：

- 查询解码进度：`tell_samples()` / `tell_seconds()` / `done`
- 流位置控制：`seek_samples()` / `seek_seconds()` / `reset()`
- 读取上游格式元信息：`input_channels` / `channel_layout` / `stream_samples` / `play_samples` / `duration_seconds` / `stream_bitrate` / `loop_start` / `loop_end` / `play_forever`

## 安装与构建

如果发布产物中已经包含与你的 Python 版本和平台匹配的 wheel，优先使用 wheel 安装：

- `pip install pyvgmstream`

如果没有匹配的 wheel，请按下面的源码构建前提准备环境。

### 源码构建前提

- Windows：
  - Python `>=3.10`
  - CMake `>=3.20`
  - Visual Studio Build Tools
  - `Desktop development with C++`
- macOS：
  - Python `>=3.10`
  - Xcode Command Line Tools
  - `brew install cmake pkg-config libvorbis`
- Linux：
  - Python `>=3.10`
  - `sudo apt-get update`
  - `sudo apt-get install -y gcc g++ make cmake build-essential git pkg-config libvorbis-dev`

需要对照上游构建文档时，参考：

- `vendor/vgmstream/doc/BUILD.md`
- `vendor/vgmstream/doc/BUILD-LIB.md`

如果你是从 GitHub 仓库源码安装，还需要带上 submodule：

- `git clone --recursive https://github.com/Virace/pyvgmstream`
- 或者在 clone 后执行 `git submodule update --init --recursive`

如果你是从 PyPI 下载源码分发包，vendored `vgmstream` 已经包含在 sdist 中，不需要再额外初始化 submodule，但仍然需要本地编译环境。

### 常见安装路径

从当前仓库源码构建 wheel：

- `uv build --wheel`

从当前仓库源码安装：

- `uv pip install .`
- `pip install .`

如果需要默认的本地播放后端，可安装可选 extra：

- `pip install "pyvgmstream[playback]"`

强制走源码构建安装：

- `pip install --no-binary pyvgmstream pyvgmstream`

### 当前说明

- 当前项目的正式支持范围为 Python `>=3.10`。
- 发布 workflow 会从 Python `3.10` 起覆盖三平台构建。
- 平台目标当前收敛为：
  - Windows：`x64`
  - Linux：`x86_64`
  - macOS：`arm64`
- 当前不计划为 macOS 提供 `x64` wheel。

## 使用示例

读取元数据：

```python
from pyvgmstream import probe

info = probe("example.wem")
print(info.sample_rate, info.channels, info.duration_seconds, info.codec_name)
```

读取 PCM16 解码流：

```python
from pyvgmstream import open_stream

with open_stream("example.wem") as stream:
    chunk = stream.read_pcm16(4096)
    print(stream.tell_seconds(), stream.duration_seconds, stream.done)
```

导出 WAV 文件：

```python
from pyvgmstream import decode_to_wav_file

result = decode_to_wav_file("example.wem", "example.wav")
print(result.output_path, result.frame_count)
```

导出 WAV 字节：

```python
from pyvgmstream import decode_to_wav_bytes

payload = decode_to_wav_bytes("example.wem")
print(len(payload))
```

递归批量转码为 WAV：

```python
from pyvgmstream import transcode_tree

summary = transcode_tree("input_wem", "output_wav", workers=4)
print(summary.processed_count, summary.failed_count)
```

使用默认可选播放后端：

```python
from pyvgmstream.playback.backends.sounddevice import create_sounddevice_session

session = create_sounddevice_session("example.wem", volume_percent=25.0)
session.start()
session.wait()
print(session.snapshot().duration_seconds)
```

更完整的 API 说明见：

- `docs/api.md`

## 许可证

- 包装层自有代码使用 `BSD-3-Clause`，见 `LICENSE`
- 第三方组件与许可证文本见 `THIRD_PARTY_NOTICES.md`
- 当前收录的第三方许可证文本包括：
  - `LICENSES/pybind11.txt`
  - `vendor/vgmstream/COPYING`
  - `vendor/vgmstream/ext_libs/licenses/*`
