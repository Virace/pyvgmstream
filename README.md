# pyvgmstream

[![PyPI version](https://img.shields.io/pypi/v/pyvgmstream)](https://pypi.org/project/pyvgmstream/)

English version: `README.en.md`

`pyvgmstream` 是一个面向 Python 的 `vgmstream` 公共 API 包装层。

## 公开 API

- `probe()`：读取流元数据
- `probe_buffer()`：读取内存输入的流元数据
- `open_stream()`：打开保持上游输出采样格式的解码流
- `open_stream_from_buffer()`：从内存输入打开解码流
- `set_log_callback()` / `disable_log_callback()`：配置或关闭上游全局日志回调
- `decode_to_wav_file()`：解码并导出为 WAV 文件
- `decode_to_wav_bytes()`：解码并导出为 WAV 字节
- `decode_buffer_to_wav_file()` / `decode_buffer_to_wav_bytes()`：把内存输入解码并导出为 WAV
- `transcode_many()` / `transcode_tree()`：批量转码为 WAV
- `BatchTranscodeProgress`：批量转码进度快照
- `PlaybackSession` / `PlaybackSnapshot` / `PCM16Sink`：播放控制核心
- `pyvgmstream.playback.backends.sounddevice.create_sounddevice_session()`：默认可选播放后端

基于 `open_stream()` 返回的 `StreamHandle`，当前可用的方法和属性包括：

- 读取当前输出格式帧数据：`read_frames(frame_count)`
- 显式读取 PCM16：`read_pcm16(frame_count)`，仅在当前流已经是 PCM16 或显式请求 PCM16 时可用
- 查询解码进度：`tell_samples()` / `tell_seconds()` / `done`
- 流位置控制：`seek_samples()` / `seek_seconds()` / `reset()`
- 读取上游格式元信息：`sample_format` / `sample_size` / `input_channels` / `channel_layout` / `stream_samples` / `play_samples` / `duration_seconds` / `stream_bitrate` / `loop_start` / `loop_end` / `play_forever`

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

读取内存中的 `.wem` 数据：

```python
from pyvgmstream import probe_buffer

buffer_info = probe_buffer(wem_bytes, filename_hint="sound.wem")
print(buffer_info.sample_rate, buffer_info.sample_format)
```

接入上游日志：

```python
from pyvgmstream import LogLevel, disable_log_callback, set_log_callback

set_log_callback(lambda level, message: print(level, message), level=LogLevel.INFO)
# ... 执行 probe/open_stream/decode 等操作
disable_log_callback()
```

读取保持上游输出采样格式的解码流：

```python
from pyvgmstream import open_stream

with open_stream("example.wem") as stream:
    chunk = stream.read_frames(4096)
    print(stream.sample_format, stream.sample_size, len(chunk))
    print(stream.tell_seconds(), stream.duration_seconds, stream.done)
```

从内存输入打开解码流：

```python
from pyvgmstream import open_stream_from_buffer

with open_stream_from_buffer(wem_bytes, filename_hint="sound.wem") as stream:
    chunk = stream.read_frames(4096)
    print(stream.sample_rate, len(chunk))
```

如果你明确需要 PCM16 便捷层，可以显式请求：

```python
from pyvgmstream import DecodeConfig, SampleFormat, open_stream

with open_stream("example.wem", config=DecodeConfig(sample_format=SampleFormat.PCM16)) as stream:
    chunk = stream.read_pcm16(4096)
    print(len(chunk))
```

导出 WAV 文件：

```python
from pyvgmstream import decode_to_wav_file

result = decode_to_wav_file("example.wem", "example.wav")
print(result.output_path, result.frame_count)
```

默认 WAV 导出会保留当前流的上游输出格式；如果下游想显式请求 `PCM16` / `PCM24` / `PCM32`，可以在 `config` 里传入对应的 `SampleFormat`。

导出 WAV 字节：

```python
from pyvgmstream import decode_to_wav_bytes

payload = decode_to_wav_bytes("example.wem")
print(len(payload))
```

直接把内存中的数据转成 WAV：

```python
from pyvgmstream import decode_buffer_to_wav_bytes

payload = decode_buffer_to_wav_bytes(wem_bytes, filename_hint="sound.wem")
print(len(payload))
```

递归批量转码为 WAV：

```python
from pyvgmstream import BatchTranscodeProgress, transcode_tree


def on_progress(progress: BatchTranscodeProgress) -> None:
    print(progress.completed_count, progress.total_count, progress.failed_count)

summary = transcode_tree("input_wem", "output_wav", workers=4, progress_callback=on_progress)
print(summary.processed_count, summary.failed_count)
```

`progress_callback` 会在父进程汇总结果时异步收到 `BatchTranscodeProgress`，回调异常不会中断转码。

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
