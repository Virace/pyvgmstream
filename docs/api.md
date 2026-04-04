# pyvgmstream API 文档

本文档面向当前包使用者，汇总 `pyvgmstream` 现有公开 API 的入口、用途和基本调用方式。

## 1. 安装

基础安装：

- `pip install pyvgmstream`

如果需要默认的本地播放后端：

- `pip install "pyvgmstream[playback]"`

## 2. 元信息探测

入口：

- `probe(path, *, subsong=0) -> StreamInfo`
- `probe_buffer(data, *, filename_hint, subsong=0) -> StreamInfo`

主要返回字段：

- `sample_rate`
- `channels`
- `input_channels`
- `channel_layout`
- `stream_samples`
- `play_samples`
- `duration_seconds`
- `stream_bitrate`
- `loop_start`
- `loop_end`
- `loop_flag`
- `play_forever`
- `codec_name`
- `layout_name`
- `meta_name`

示例：

```python
from pyvgmstream import probe

info = probe("example.wem")
print(info.sample_rate)
print(info.duration_seconds)
print(info.play_samples)
print(info.codec_name)
```

```python
from pyvgmstream import probe_buffer

info = probe_buffer(wem_bytes, filename_hint="sound.wem")
print(info.sample_rate, info.sample_format)
```

## 3. 上游日志桥接

入口：

- `set_log_callback(callback=None, *, level=LogLevel.INFO) -> None`
- `disable_log_callback() -> None`

说明：

- 这层直接桥接上游 `libvgmstream_set_log()` 的全局日志回调
- 回调作用域是进程级，不是单个 `StreamHandle`
- `callback=None` 时，回退到上游默认 stdout 回调
- `disable_log_callback()` 会禁用当前日志回调

示例：

```python
from pyvgmstream import LogLevel, disable_log_callback, set_log_callback

set_log_callback(lambda level, message: print(level, message), level=LogLevel.DEBUG)
# ... 执行 probe/open_stream/decode 等操作
disable_log_callback()
```

## 4. 解码流读取

入口：

- `open_stream(path, *, subsong=0) -> StreamHandle`
- `open_stream_from_buffer(data, *, filename_hint, subsong=0) -> StreamHandle`

`StreamHandle` 主要能力：

- 读取当前输出格式帧数据：`read_frames(frame_count)`
- 读取 PCM16 便捷层：`read_pcm16(frame_count)`
- 查询位置：`tell_samples()` / `tell_seconds()`
- 跳转与重置：`seek_samples()` / `seek_seconds()` / `reset()`
- 结束状态：`done`
- 读取格式元信息：
  - `sample_rate`
  - `sample_format`
  - `sample_size`
  - `channels`
  - `input_channels`
  - `channel_layout`
  - `stream_samples`
  - `play_samples`
  - `duration_seconds`
  - `stream_bitrate`
  - `loop_start`
  - `loop_end`
  - `play_forever`

示例：

```python
from pyvgmstream import open_stream

with open_stream("example.wem") as stream:
    print(stream.duration_seconds)
    chunk = stream.read_frames(4096)
    print(len(chunk), stream.tell_seconds(), stream.done)
```

如果下游明确只想拿某种采样格式，可通过 `DecodeConfig(sample_format=...)` 显式请求。

## 5. 单文件 WAV 导出

入口：

- `decode_to_wav_file(in_path, out_path)`
- `decode_to_wav_bytes(path)`
- `decode_buffer_to_wav_file(data, out_path, *, filename_hint)`
- `decode_buffer_to_wav_bytes(data, *, filename_hint)`

说明：

- 这两个 API 都基于当前解码流能力导出 WAV
- 默认保留当前流的上游输出采样格式
- 如果下游想导出特定采样格式，需要通过 `DecodeConfig(sample_format=...)` 显式请求
- 当前不提供 OGG 导出 API

示例：

```python
from pyvgmstream import decode_to_wav_file

result = decode_to_wav_file("example.wem", "example.wav")
print(result.output_path, result.frame_count, result.byte_count)
```

```python
from pyvgmstream import decode_buffer_to_wav_bytes

payload = decode_buffer_to_wav_bytes(wem_bytes, filename_hint="sound.wem")
print(len(payload))
```

## 6. 批量转码

入口：

- `transcode_many(sources, output_root, *, input_root=None, workers=..., chunk_frames=..., dispatch_chunksize=..., progress_callback=None)`
- `transcode_tree(input_root, output_root, *, workers=..., chunk_frames=..., dispatch_chunksize=..., limit=None, pattern="*.wem", progress_callback=None)`

主要返回对象：

- `BatchTranscodeItemResult`
- `BatchTranscodeProgress`
- `BatchTranscodeSummary`

说明：

- `transcode_many()` 适合下游已经有自己的输入文件集合
- `transcode_tree()` 适合直接递归扫描目录
- 当前默认导出为 WAV，并保留相对目录结构
- `progress_callback` 会收到 `BatchTranscodeProgress`
- 进度通知由父进程异步分发，子进程不直接参与通知
- `progress_callback` 抛出异常时，不会中断当前转码

示例：

```python
from pyvgmstream import BatchTranscodeProgress, transcode_tree


def on_progress(progress: BatchTranscodeProgress) -> None:
    print(progress.completed_count, progress.total_count, progress.failed_count)

summary = transcode_tree("input_wem", "output_wav", workers=4, progress_callback=on_progress)
print(summary.processed_count, summary.failed_count)
for item in summary.results:
    if not item.success:
        print(item.source_path, item.error)
```

## 7. 播放控制核心

核心对象：

- `PlaybackSession`
- `PlaybackSnapshot`
- `PlaybackState`
- `PCM16Sink`

说明：

- `PlaybackSession` 负责后台读取解码流和调度播放状态
- `PCM16Sink` 是可替换后端协议，允许下游自己接入其他音频库
- `PlaybackSnapshot` 暴露当前位置、状态和格式元信息

`PlaybackSnapshot` 关键字段：

- `state`
- `position_samples`
- `position_seconds`
- `duration_seconds`
- `sample_rate`
- `channels`
- `input_channels`
- `channel_layout`
- `stream_samples`
- `play_samples`
- `stream_bitrate`
- `loop_start`
- `loop_end`
- `play_forever`
- `recent_error`

## 8. 默认可选播放后端

入口：

- `pyvgmstream.playback.backends.sounddevice.create_sounddevice_session(...)`

说明：

- 这个后端依赖 `sounddevice`
- 未安装 `playback` optional extra 时，不影响核心包导入
- 如果下游不想用 `sounddevice`，可以自己实现 `PCM16Sink`

示例：

```python
from pyvgmstream.playback.backends.sounddevice import create_sounddevice_session

session = create_sounddevice_session("example.wem", volume_percent=25.0)
session.start()
session.wait()
print(session.snapshot().duration_seconds)
```
