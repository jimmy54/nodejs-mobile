# Node.js Mobile 鸿蒙系统集成总结报告与编译指南

## 1. 项目总结

### 问题描述
应用在启动时崩溃，报错 `TypeError: Cannot read property startNodeProject of undefined`。经排查，原因是鸿蒙系统的动态链接器无法正确加载 `libnode.so` 或其依赖项，导致 NAPI 模块初始化不完整。随后尝试静态链接时，遇到了 `-fPIC` 编译错误和大量 `undefined symbol` 链接错误。

### 解决方案
我们从动态库（`.so`）集成方案切换到了 **静态库（`.a`）** 集成方案。通过将 Node.js 直接编译进应用的 Native 模块中，彻底解决了运行时依赖加载的问题。

### 关键修复
1.  **强制开启 -fPIC**：修改了 `common.gypi`，强制在 `ohos` 平台启用位置无关代码（`-fPIC`）。这是将静态库（如 `libnode.a`）链接到共享 NAPI 模块（`libentry.so`）所必须的。
2.  **完整静态链接**：更新了 `CMakeLists.txt`，显式链接 `libnode.a` 及其所有内部依赖（V8, libuv, OpenSSL, Zlib 等），包括特定的 ARM64 优化库和快照桩文件。

---

## 2. 编译指南

### 前置条件
*   **HarmonyOS SDK (Native)**: 确保已安装 SDK (例如 `/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native`).
*   **Python 3**: 运行配置脚本需要.
*   **Make**: 编译构建需要.

### 第一步：配置构建设置

修改 `entry/src/main/cpp/deps/nodejs-mobile/common.gypi` 文件以确保静态库兼容共享模块链接。

**文件**: `deps/nodejs-mobile/common.gypi`
**修改内容**:
```python
# 找到 'OS == "ohos"' 部分并修改为：
['OS == "ohos" or is_ohos==1', {
  'cflags': [ '-fPIC' ],
  'ldflags': [ '-fPIC' ]
}],
```

### 第二步：配置并编译 Node.js

在终端运行配置脚本和编译命令。

```bash
cd entry/src/main/cpp/deps/nodejs-mobile

# 1. 清理旧构建
rm -rf out

# 2. 配置 ARM64 (静态编译)
# 脚本内部会调用 ./configure --enable-static ...
./ohos_configure.py /Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native arm64

# 3. 编译
make -j8
```

### 第三步：CMake 集成

在模块的 `CMakeLists.txt` 中链接 `libnode.a` 及其依赖。这是避免未定义符号错误的最关键步骤。

**文件**: `entry/src/main/cpp/CMakeLists.txt`

```cmake
# 定义 Node.js 静态库
add_library(node STATIC IMPORTED)
set_target_properties(node PROPERTIES IMPORTED_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/libnode.a")

# 将库链接到你的 NAPI 模块
target_link_libraries(entry PUBLIC node
    # 核心依赖
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/uv/libuv.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/openssl/libopenssl.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/zlib/libzlib.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/llhttp/libllhttp.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/cares/libcares.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/nghttp2/libnghttp2.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/brotli/libbrotli.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/ngtcp2/libngtcp2.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/ngtcp2/libnghttp3.a"
    
    # V8 JavaScript 引擎
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_snapshot.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_libplatform.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_base_without_compiler.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_libbase.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_zlib.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_compiler.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_initializers.a"

    # 工具与辅助库
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/histogram/libhistogram.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/uvwasi/libuvwasi.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/ada/libada.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/base64/libbase64.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/simdutf/libsimdutf.a"

    # ARM64 特定优化（链接必须）
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/base64/libbase64_neon64.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/zlib/libzlib_inflate_chunk_simd.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/zlib/libzlib_adler32_simd.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/zlib/libzlib_arm_crc32.a"

    # Node 快照桩（初始化必须）
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/node/src/node_snapshot_stub.o"
)
```
