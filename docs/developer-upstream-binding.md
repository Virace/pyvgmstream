# pyvgmstream 上游绑定说明

本文档面向仓库维护者，说明 `pyvgmstream` 当前 API 基于上游 `vgmstream` 的哪些部分构建、运行原理是什么，以及当前耦合点主要落在哪些层。

## 1. 结论先行

当前实现可以分成三层：

1. Python 公共 API 层：`src/pyvgmstream/*.py`
2. 本地原生绑定层：`src/native/module.cpp`
3. 上游 `vgmstream` 公共 API 与构建输入：`vendor/vgmstream`

其中：

- Python 层基本是薄封装，只负责参数整理、结果投影、异常语义和 WAV 导出。
- C++ 层只包含上游公开头文件 `libvgmstream.h` 与 `libvgmstream_streamfile.h`，没有直接依赖上游内部头 `vgmstream.h`。
- 构建层当前直接依赖 vendored 上游仓库的目录结构、CMake 入口和目标名，因此“运行时 API 耦合”不算高，但“源码仓库 / 构建系统耦合”相对更高。

## 2. 当前直接依赖的上游部分

### 2.0 当前 vendored 上游修订

当前仓库锁定的 vendored 上游提交为：

- `vendor/vgmstream @ 5d01f5717c1489101918258fbed97659a390c356`

为了方便重入和后续升级，下面这张表把“本地文件”和“对应上游文件”先对齐出来。

| 本地文件 | 角色 | 上游文件 | 说明 |
| --- | --- | --- | --- |
| `CMakeLists.txt` | 本仓库顶层入口 | 无 | 这是本地文件，不是上游文件；它只负责编排本包构建 |
| `cmake/resolve_vgmstream.cmake` | 本地上游适配层 | `vendor/vgmstream/CMakeLists.txt` | 本地文件，负责吸收 vendored 上游仓库布局与构建入口差异 |
| `cmake/resolve_vgmstream.cmake` | 本地上游适配层 | `vendor/vgmstream/cmake/vgmstream.cmake` | 本地文件，负责连接上游 CMake helper 和本地逻辑目标 |
| `cmake/resolve_vgmstream.cmake` | 本地上游适配层 | `vendor/vgmstream/src/CMakeLists.txt` | 本地文件，负责把上游源码子目录接入本仓库构建 |
| `src/native/module.cpp` | 本地原生桥接层 | `vendor/vgmstream/src/libvgmstream.h` | 本地文件，基于上游公共头做 Python 绑定桥接 |
| `src/native/module.cpp` | 本地原生桥接层 | `vendor/vgmstream/src/libvgmstream_streamfile.h` | 本地文件，基于上游公共 IO 头做路径输入桥接 |

### 2.1 公开头文件

当前原生绑定只直接包含两份上游公开头文件：

- `vendor/vgmstream/src/libvgmstream.h`
- `vendor/vgmstream/src/libvgmstream_streamfile.h`

对应绑定入口见 `src/native/module.cpp`：

- `#include "libvgmstream.h"`
- `#include "libvgmstream_streamfile.h"`

这与上游头文件中的说明一致：`libvgmstream.h` 被定义为 `vgmstream's public API`，同时上游明确提醒不要依赖内部实现细节，内部头未来会变动。

### 2.2 当前实际调用的公开函数

`pyvgmstream` 当前使用的上游公开函数主要有：

- `libvgmstream_get_version`
- `libvgmstream_init`
- `libvgmstream_free`
- `libvgmstream_setup`
- `libvgmstream_open_stream`
- `libvgmstream_fill`
- `libvgmstream_get_play_position`
- `libvgmstream_seek`
- `libvgmstream_reset`
- `libstreamfile_open_from_stdio`
- `libstreamfile_close`

这些函数的职责大致如下：

- `libvgmstream_init` / `libvgmstream_free`：创建和释放解码上下文
- `libvgmstream_setup`：应用当前解码配置
- `libvgmstream_open_stream`：基于 `libstreamfile_t` 打开目标流
- `libvgmstream_fill`：向外部 buffer 填充 PCM 数据
- `libvgmstream_get_play_position` / `libvgmstream_seek` / `libvgmstream_reset`：提供解码流位置控制
- `libstreamfile_open_from_stdio` / `libstreamfile_close`：使用上游公开 IO 包装以打开本地文件

### 2.3 当前实际读取的公开结构与字段

虽然当前代码没有包含上游内部头，但绑定层不只是“调用函数”，还直接读取了公开结构中的字段。

当前读取的主要字段包括：

- `libvgmstream_t::format`
- `libvgmstream_t::decoder`
- `libvgmstream_format_t::sample_rate`
- `libvgmstream_format_t::channels`
- `libvgmstream_format_t::subsong_index`
- `libvgmstream_format_t::subsong_count`
- `libvgmstream_format_t::loop_flag`
- `libvgmstream_format_t::codec_name`
- `libvgmstream_format_t::layout_name`
- `libvgmstream_format_t::meta_name`
- `libvgmstream_decoder_t::buf_bytes`
- `libvgmstream_decoder_t::done`

这意味着当前绑定依赖的不只是函数名和返回值，还依赖了上游公开结构的字段存在性与语义稳定性。

### 2.4 当前直接依赖的上游构建部分

当前构建系统不是“链接一个外部已安装的 `libvgmstream`”，而是直接把 vendored 上游仓库作为构建输入。

`CMakeLists.txt` 当前直接依赖：

- `vendor/vgmstream` 这个 submodule 路径存在
- `vendor/vgmstream/CMakeLists.txt` 存在
- `include(vgmstream)` 这个 CMake 模块可用
- `add_subdirectory("${VGM_SOURCE_DIR}/src" ...)` 这条路径和上游目录布局保持稳定
- `libvgmstream` 这个目标名保持不变
- Windows 下 `ext_libs/libvorbis.def` 与 `dll-x64/libvorbis.dll` 的布局保持稳定

因此当前仓库对上游的构建输入和目录布局有显式依赖。

## 3. 当前 API 的工作原理

### 3.1 `probe()` 的原理

`probe()` 的路径是：

1. Python 层 `probe(path, subsong=0)` 调用 `_native.probe(...)`
2. 原生层创建 `libstreamfile_t*`
3. 原生层创建 `libvgmstream_t*`
4. 原生层执行 `libvgmstream_open_stream(...)`
5. 原生层从 `lib->format` 读取元数据字段
6. Python 层把字典投影为 `StreamInfo`

也就是说，`probe()` 本质上不是“纯文件头猜测”，而是一次最小化的真实打开过程，然后把上游公开 `format` 结构中的结果投影到 Python 数据模型。

### 3.2 `open_stream()` 的原理

`open_stream()` 的路径是：

1. Python 层调用 `_native.NativeStreamHandle(path, subsong)`
2. 原生层初始化 `libvgmstream`
3. 应用固定配置：
   - `ignore_loop = true`
   - `force_sfmt = LIBVGMSTREAM_SFMT_PCM16`
4. 通过 `libstreamfile_open_from_stdio(...)` 打开本地文件
5. 通过 `libvgmstream_open_stream(...)` 打开目标流
6. 返回 `NativeStreamHandle`
7. Python 层再包一层 `StreamHandle`

因此当前 `open_stream()` 返回的不是任意采样格式流，而是已经被固定成 PCM16 的解码流句柄。

当前实现里，这组默认值不再直接散落在打开流程中，而是先收敛到本地 policy 命名层，再转换成上游配置结构：

- `DecodePolicy`
- `build_default_decode_policy()`
- `apply_decode_policy(...)`
- `build_default_decode_config()`

### 3.3 `StreamHandle` 方法的原理

`StreamHandle` 基本不持有业务状态，而是把调用转发给原生句柄：

- `read_pcm16(frame_count)` -> `libvgmstream_fill(...)`
- `tell_samples()` -> `libvgmstream_get_play_position(...)`
- `seek_samples(position)` -> `libvgmstream_seek(...)`
- `reset()` -> `libvgmstream_reset(...)`
- `done` -> 读取 `lib->decoder->done`
- `sample_rate` / `channels` -> 读取 `lib->format`

其中 `read_pcm16()` 的关键点是：

- Python 侧要求“读取 N 帧 PCM16”
- 原生侧先按 `channels * frame_count` 分配 `int16_t` buffer
- 调 `libvgmstream_fill(...)` 让上游填充
- 再依据 `lib->decoder->buf_bytes` 把真实有效字节数返回给 Python

因此“上游负责解码与 EOF 语义”，而“本仓库负责把上游结果整理成 Python 可消费的字节流”。

### 3.4 `decode_to_wav_file()` / `decode_to_wav_bytes()` 的原理

这两个 API 没有走任何上游 WAV 导出接口，而是：

1. 先调用 `open_stream()`
2. 循环调用 `read_pcm16(4096)`
3. 用 Python 标准库 `wave` 写入 WAV 头和 PCM 数据
4. 最后返回字节或写入文件

因此：

- 上游只负责“打开流 + 解码 PCM”
- WAV 封装完全由 Python 层完成

这也是为什么当前导出能力仅限于 WAV，而不是上游支持什么封装就自动暴露什么封装。

## 4. 当前设计的边界

### 4.1 已经保持住的边界

当前设计已经做到以下几点：

- 没有包含上游内部头 `vgmstream.h`
- 没有直接访问上游私有 `priv` 数据
- Python API 没有暴露上游复杂配置结构
- Python 层没有承接格式兼容策略，只消费当前上游已能打开的流

这符合项目的“薄封装 + 公共 API 优先”方向。

### 4.2 当前仍然存在的耦合点

当前耦合主要有三类：

### A. 公开 ABI / 数据结构耦合

虽然依赖的是公开头，但当前代码会直接读取公开结构字段，例如：

- `lib->format->sample_rate`
- `lib->format->channels`
- `lib->decoder->done`
- `lib->decoder->buf_bytes`

如果将来上游保留函数 API，但调整公开结构布局、字段命名或字段含义，这里仍然可能需要改。

### B. 打开路径与 IO 适配耦合

当前只使用 `libstreamfile_open_from_stdio(...)` 这条路径。

这意味着：

- 当前只直接支持基于本地路径的文件打开
- 内存流、自定义文件系统、非磁盘来源都还没有隔离成独立适配层

### C. 仓库布局 / CMake 目标耦合

这是目前最明显的耦合点。

当前构建过程依赖：

- 上游仓库作为 submodule 存在
- vendored 仓库的目录结构稳定
- CMake 模块名稳定
- 目标名 `libvgmstream` 稳定
- Windows 额外依赖文件布局稳定

所以当前最脆弱的不是 Python API 名字，而是“上游仓库怎么组织源码和构建”。

## 5. 维护入口

这一节不是面向“第一次读完整个仓库”的人，而是面向“接手维护时，想先知道从哪下手”的人。

建议维护者先按问题所在的层级定位，而不是一上来同时看 Python、C++、CMake 和上游源码。

### 5.1 四个本地入口

1. 构建接入层：先看 `cmake/resolve_vgmstream.cmake`
   这里集中维护 vendored 上游的仓库路径、CMake helper、目标名、Windows 运行时文件打包等逻辑。
2. 原生桥接层：先看 `src/native/module.cpp`
   这里集中维护默认解码策略、上游公开结构快照、Python 绑定导出。
3. Python 壳层：先看 `src/pyvgmstream/api.py` / `src/pyvgmstream/stream.py` / `src/pyvgmstream/models.py`
   这里负责对象模型、上下文管理和 WAV 导出，不负责上游解码细节。
4. 结构与约束校验：先看 `tests/test_package_layout.py`
   这里不是业务测试，而是仓库结构、溯源锚点和本地适配分层的守门测试。

### 5.2 常见变更场景

| 场景 | 先看哪个本地文件 | 再看哪个上游文件 | 验证方式 |
| --- | --- | --- | --- |
| 上游仓库目录布局变了，导致构建失败 | `cmake/resolve_vgmstream.cmake` | `vendor/vgmstream/CMakeLists.txt`、`vendor/vgmstream/cmake/vgmstream.cmake`、`vendor/vgmstream/src/CMakeLists.txt` | `uv run pytest -q tests/test_package_layout.py`，必要时再跑 `uv run pytest -q tests` |
| 上游目标名、include 或 Windows 运行时文件路径变了 | `cmake/resolve_vgmstream.cmake` | 同上，再加 `vendor/vgmstream/ext_libs` 相关路径 | `uv run pytest -q tests/test_package_layout.py`，再做一次实际构建链验证 |
| 想调整默认解码策略，例如 loop 或输出 sample format | `src/native/module.cpp` 中的 `DecodePolicy` / `build_default_decode_policy()` / `apply_decode_policy(...)` | `vendor/vgmstream/src/libvgmstream.h` | `uv run pytest -q tests` |
| 上游公开结构字段变化，导致 metadata 或 `done`/`buf_bytes` 语义变化 | `src/native/module.cpp` 中的 `snapshot_format()` / `snapshot_decoder()` | `vendor/vgmstream/src/libvgmstream.h` | `uv run pytest -q tests` |
| 想新增 Python 公开能力，但不想直接暴露上游复杂结构 | `src/pyvgmstream/api.py`、`src/pyvgmstream/models.py`、`src/pyvgmstream/stream.py` | 必要时回看 `src/native/module.cpp` 与 `vendor/vgmstream/src/libvgmstream.h` | 先补对应测试，再跑 `uv run pytest -q tests` |
| 文档和溯源信息过期，需要更新 handoff 说明 | `docs/developer-upstream-binding.md`、`tests/test_package_layout.py` | 视更新内容决定是否回看对应上游文件 | `uv run pytest -q tests/test_package_layout.py` |

### 5.3 一个推荐的重入顺序

如果维护者对仓库还不熟，推荐按下面顺序重入：

1. 先看 `docs/developer-upstream-binding.md` 的溯源表和本节维护入口。
2. 再看 `tests/test_package_layout.py`，确认仓库当前把哪些结构约束当成不变量。
3. 如果问题发生在构建阶段，再看 `cmake/resolve_vgmstream.cmake`。
4. 如果问题发生在解码、metadata、seek、done 语义，再看 `src/native/module.cpp`。
5. 只有在本地适配层确定需要追上游事实时，再去打开对应的 vendored 上游文件。

这样做的目的是先理解“本仓库自己的边界和责任”，再去理解“上游当前长什么样”。

## 6. 开发者应如何理解当前实现

可以把当前仓库理解成：

- 不是 `vgmstream` 的重新实现
- 不是 `vgmstream` 所有能力的完整 Python 映射
- 也不是一个播放器

它更像是：

- 一个针对 `.wem` 主路径的 Python 包装层
- 一个把上游公开解码能力投影成 Python 可用 API 的适配器
- 一个在 Python 层补齐对象模型、上下文管理和 WAV 封装的壳层

换句话说，当前 API 的职责是“把上游公开解码接口变成 Python 友好的使用方式”，而不是“吸收上游所有复杂性并重新定义一套音频框架”。

## 7. 如果要降低耦合，优先改哪些地方

下面按收益和性价比排序。

### 6.1 第一优先级：降低构建层对上游仓库布局的耦合

这是当前最值得改的部分。

可以考虑的方向：

- 引入独立的 `Findlibvgmstream.cmake` 或 imported target 方案
- 支持“链接预构建 `libvgmstream`”与“使用 vendored source 构建”两种模式
- 把上游 source layout 相关假设集中到一个 CMake 适配层，而不是散落在主 `CMakeLists.txt`
- 把 Windows 下 `libvorbis` 处理也局部封装到适配脚本

这样做的好处是：

- 上游目录结构变化时，主要只改适配层
- 包装层源码不必跟着一起动
- 后续也更容易切换到系统安装版或 CI 预构建产物

### 6.2 第二优先级：减少对公开结构字段的直接读取

如果要继续降低 ABI 层耦合，可以在本地绑定层再加一道“数据投影”：

- 在 C++ 层立即把 `lib->format` / `lib->decoder` 读取到本地 plain struct
- Python 层只接收本地稳定字段，不直接依赖上游结构组织方式

这一步不能完全消除上游 API 变化的影响，但可以把变化集中在少数 helper 内。

如果未来上游新增 getter 函数并建议以 getter 为主，也可以逐步从“读字段”迁移成“调 getter”。

### 6.3 第三优先级：把输入源适配从 `stdio` 路径抽象出来

当前 `libstreamfile_open_from_stdio(...)` 直接把“输入一定来自本地路径”编码进了绑定层。

如果后续要降低这部分耦合，可以：

- 先在本地定义自己的输入抽象，例如 `PathInput` / `BinaryInput`
- 为 `libstreamfile_t` 增加本地适配层
- 让“如何把 Python 输入映射到 `libstreamfile_t`”成为单独模块

这样做后：

- 当前路径输入仍可复用
- 未来若要加内存流或自定义文件系统，不需要重写整个解码 API

### 6.4 第四优先级：把固定配置做成本地策略层

当前 `open_stream()` 会固定：

- `ignore_loop = true`
- `force_sfmt = LIBVGMSTREAM_SFMT_PCM16`

这本身不是坏事，但它让 Python API 语义直接绑定了当前上游配置方式。

如果未来要进一步降耦合，可以把这些默认配置收敛到本地策略层，例如：

- `DecodePolicy`
- `build_default_decode_policy()`
- `apply_decode_policy(...)`
- `build_default_decode_config()`

这样未来即使上游配置结构发生局部调整，改动也能收束在少量桥接代码里。

## 8. 不建议当前就做的事

下面这些方向短期内不一定值得：

- 为了“绝对低耦合”去复制上游逻辑或重写解码流程
- 在 Python 层引入大量格式特判，替代上游本来的能力边界
- 过早把全部上游公共 API 一次性映射出来

原因很简单：

- 会显著扩大维护面
- 会让 `pyvgmstream` 从“薄封装”变成“半个重新实现”
- 不符合当前仓库的 WEM-first 和最小可维护边界

## 9. 一句话总结

当前 `pyvgmstream` 是建立在上游公开 `libvgmstream` / `libstreamfile` API 之上的薄封装；真正需要优先降低的，不是 Python API 对上游函数名的依赖，而是构建系统对 vendored 上游仓库布局和目标组织方式的依赖。
