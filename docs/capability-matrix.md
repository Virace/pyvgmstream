# pyvgmstream Capability Matrix

本文档同时面向用户和开发者，描述 `pyvgmstream` 当前已经支持的能力、当前不支持的能力，以及后续值得关注的扩展方向。

## 状态说明

| 状态 | 含义 |
| --- | --- |
| `已支持` | 当前仓库中已经实现，并且有实际验证覆盖 |
| `部分支持` | 有一部分底层能力，但不等于完整用户能力 |
| `未支持` | 当前仓库没有提供这项能力 |
| `候选` | 后续值得扩展，但当前不承诺 |

## 用户能力矩阵

| 能力 | 状态 | 当前入口 | 说明 |
| --- | --- | --- | --- |
| 读取流元数据 | `已支持` | `probe()` | 返回 `StreamInfo` |
| 打开解码流 | `已支持` | `open_stream()` | 返回 `StreamHandle` |
| 读取 PCM16 数据 | `已支持` | `StreamHandle.read_pcm16()` | 当前公开流格式为 PCM16 |
| 查询解码进度 | `已支持` | `tell_samples()` / `tell_seconds()` / `done` | 这是解码流进度，不是播放器时钟 |
| 跳转位置 | `已支持` | `seek_samples()` / `seek_seconds()` | 面向解码流 |
| 重置流位置 | `已支持` | `reset()` | 回到流起点 |
| 导出 WAV 文件 | `已支持` | `decode_to_wav_file()` | 当前唯一文件导出格式 |
| 导出 WAV 字节 | `已支持` | `decode_to_wav_bytes()` | 当前唯一字节导出格式 |
| 递归批量转 WAV | `已支持` | `transcode_tree()` | 保留相对目录结构，支持多进程 |
| 批量转 WAV（任意输入列表） | `已支持` | `transcode_many()` | 适合下游自行组织输入集合 |
| 读取总时长/总样本等元信息 | `已支持` | `StreamInfo` / `StreamHandle` | 直接投影上游公开 `format` 字段 |
| OGG 输出 | `未支持` | 无 | 当前不提供 OGG 编码或 OGG 导出 API |
| 音频设备播放 | `部分支持` | `PlaybackSession` + `SoundDeviceSink` | 核心播放 API 已提供；默认设备输出需要安装 `playback` optional extra，也可接自定义 sink |
| 播放暂停 / 恢复 | `已支持` | `PlaybackSession.pause()` / `resume()` | 属于播放会话控制，不依赖特定 UI |
| 停止播放 | `已支持` | `PlaybackSession.stop()` | 会话会等待后台播放线程退出 |
| 音量控制 | `已支持` | `PlaybackSession(volume_percent=...)` | 当前是简单线性缩放 |
| 倍速 | `未支持` | 无 | 当前没有时间拉伸或重采样控制层 |
| WEM-first 主路径 | `已支持` | `probe/open_stream/decode_to_wav_*` | 当前显式支持和测试覆盖集中在 `.wem` |
| 非 WEM 文件自然可用 | `部分支持` | 同上 | 如果 vendored `vgmstream` 当前配置能打开某些格式，API 可能自然可用，但当前不作为承诺能力 |
| clone 后源码安装 | `已支持` | `uv build --wheel` / `uv pip install .` / `pip install .` | clone 时需带上 submodule |

## 安装与构建模型

| 场景 | 当前方式 | 说明 |
| --- | --- | --- |
| 获取仓库 | `git clone --recursive` | 推荐方式 |
| 已 clone 但没带 submodule | `git submodule update --init --recursive` | 必须先准备 `vendor/vgmstream` |
| 构建 wheel | `uv build --wheel` | 当前可直接工作 |
| uv 源码安装 | `uv pip install .` | 当前可直接工作 |
| pip 源码安装 | `pip install .` | 当前可直接工作 |
| 维护者便捷构建 | `scripts/build_wheels.ps1` / `scripts/build_wheels.sh` | 不是用户安装前提 |

## WEM 播放控制说明

当前 API 对 “WEM 播放控制” 的支持分两层：

| 主题 | 状态 | 说明 |
| --- | --- | --- |
| 解码流进度 | `已支持` | `tell_samples()` / `tell_seconds()` / `done` |
| 解码流跳转 | `已支持` | `seek_samples()` / `seek_seconds()` / `reset()` |
| 播放会话状态 | `已支持` | `PlaybackState` / `PlaybackSnapshot` |
| 实际播放暂停 / 恢复 | `已支持` | `PlaybackSession.pause()` / `resume()` |
| 实际音频播放 | `部分支持` | 默认提供 `sounddevice` 示例后端，也允许下游实现自定义 sink |

因此，当前 `pyvgmstream` 同时支持“解码流控制”和“播放会话控制”；但具体音频设备输出后端仍保持可选和可替换。

## 开发者关注的 libvgmstream 公共接口

下面这些接口都来自公开头文件 `libvgmstream.h` / `libvgmstream_streamfile.h`，不是上游内部头。

| 接口/结构 | 当前情况 | 值得关注的原因 | 优先级 |
| --- | --- | --- | --- |
| `libvgmstream_setup` / `libvgmstream_config_t` | `部分支持` | 后续可暴露 loop / fade / stereo track / downmix / sample format 等控制 | `高` |
| `libvgmstream_set_log` | `未支持` | 后续可把上游日志接到 Python 日志层 | `高` |
| `libvgmstream_format_t` 中的总时长/loop/bitrate 等字段 | `已支持` | 现在已经透出到 `StreamInfo` / `StreamHandle` / `PlaybackSnapshot` | `高` |
| `libstreamfile_open_buffered` / 自定义 `libstreamfile_t` | `未支持` | 后续可扩展到内存流、自定义文件系统、非磁盘输入 | `高` |
| `libvgmstream_close_stream` | `未支持` | 后续可优化同一 context 下的多流切换 | `中` |
| `libvgmstream_get_title` | `未支持` | 后续可提供更友好的流标题/显示名 | `中` |
| `libvgmstream_format_describe` | `未支持` | 后续可提供更友好的格式说明 | `中` |
| `libvgmstream_is_valid` | `未支持` | 后续可用于文件筛选和快速拒绝 | `中` |
| `libvgmstream_get_extensions` / `libvgmstream_get_common_extensions` | `未支持` | 后续可用于 GUI/CLI 文件过滤器 | `低` |
| `libvgmstream_tags_*` | `未支持` | 后续如果要做 tags 能力可以接入 | `低` |

## 当前包能力的一句话总结

`pyvgmstream` 当前是一个面向 `.wem` 主路径的 Python 解码、WAV 导出和可选播放控制库。  
它已经支持 metadata、总时长/loop 等上游格式字段投影、PCM16 流读取、进度查询、seek/reset、批量 WAV 转码，以及基于可选 sink 的播放会话控制。
