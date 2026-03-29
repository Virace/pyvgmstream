# pyvgmstream

English version: `README.en.md`

`pyvgmstream` 是一个面向 Python 的 `vgmstream` 公共 API 包装层，当前以 `.wem` 主路径为重点。

## 公开 API

- `probe()`：读取流元数据
- `open_stream()`：打开 PCM16 解码流
- `decode_to_wav_file()`：解码并导出为 WAV 文件
- `decode_to_wav_bytes()`：解码并导出为 WAV 字节

基于 `open_stream()` 返回的 `StreamHandle`，当前可用的方法和属性包括：

- 查询解码进度：`tell_samples()` / `tell_seconds()` / `done`
- 流位置控制：`seek_samples()` / `seek_seconds()` / `reset()`

## 安装与构建

获取仓库时，请确保 submodule 一起拉取：

- `git clone --recursive https://github.com/Virace/pyvgmstream`
- 或者在 clone 后执行 `git submodule update --init --recursive`

正常源码构建与安装路径：

- 构建 wheel：`uv build --wheel`
- 使用 uv 安装：`uv pip install .`
- 使用 pip 安装：`pip install .`

## 使用示例

读取元数据：

```python
from pyvgmstream import probe

info = probe("example.wem")
print(info.sample_rate, info.channels, info.codec_name)
```

读取 PCM16 解码流：

```python
from pyvgmstream import open_stream

with open_stream("example.wem") as stream:
    chunk = stream.read_pcm16(4096)
    print(stream.tell_seconds(), stream.done)
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

## 许可证

- 包装层自有代码使用 `BSD-3-Clause`，见 `LICENSE`
- 第三方组件与许可证文本见 `THIRD_PARTY_NOTICES.md`
- 当前收录的第三方许可证文本包括：
  - `LICENSES/pybind11.txt`
  - `vendor/vgmstream/COPYING`
