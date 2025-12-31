# Node.js Mobile HarmonyOS Integration Summary & Build Guide

## 1. Project Summary

### Issue
The application crashed on startup with `TypeError: Cannot read property startNodeProject of undefined` and `dlopen` errors. This was caused by the HarmonyOS dynamic linker failing to load `libnode.so` or its dependencies correctly, leading to incomplete initialization of the NAPI module. Subsequent attempts to link statically failed with `recompile with -fPIC` errors and `undefined symbol` linker errors.

### Solution
We switched from Shared Library (`.so`) integration to **Static Library (`.a`)** integration. This eliminates runtime dependency loading issues by embedding Node.js directly into the application's native module.

### Key Fixes
1.  **Force -fPIC**: Modified `common.gypi` to enforce Position Independent Code (`-fPIC`) for the `ohos` platform. This is mandatory when linking static libraries (like `libnode.a`) into a shared NAPI module (`libentry.so`).
2.  **Full Static Linking**: Updated `CMakeLists.txt` to explicitly link `libnode.a` and all its internal dependencies (V8, libuv, OpenSSL, Zlib, etc.), including specific ARM64 optimization libraries and snapshot stubs.

---

## 2. Compilation Guide

### Prerequisites
*   **HarmonyOS SDK (Native)**: Ensure the SDK is installed (e.g., `/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native`).
*   **Python 3**: Required for the configure script.
*   **Make**: Required for building.

### Step 1: Configure Build Settings

Modify `entry/src/main/cpp/deps/nodejs-mobile/common.gypi` to ensure static libraries are compatible with shared module linking.

**File**: `deps/nodejs-mobile/common.gypi`
**Change**:
```python
# Find the 'OS == "ohos"' section and change it to:
['OS == "ohos" or is_ohos==1', {
  'cflags': [ '-fPIC' ],
  'ldflags': [ '-fPIC' ]
}],
```

### Step 2: Configure and Build Node.js

Run the configuration script and build command in the terminal.

```bash
cd entry/src/main/cpp/deps/nodejs-mobile

# 1. Clean previous build
rm -rf out

# 2. Configure for ARM64 (Static Build)
# The script internally calls ./configure --enable-static ...
./ohos_configure.py /Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native arm64

# 3. Build
make -j8
```

### Step 3: CMake Integration

In your module's `CMakeLists.txt`, link `libnode.a` and its dependencies. This is the most critical step to avoid undefined symbols.

**File**: `entry/src/main/cpp/CMakeLists.txt`

```cmake
# Define Node.js Static Library
add_library(node STATIC IMPORTED)
set_target_properties(node PROPERTIES IMPORTED_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/libnode.a")

# Link libraries to your NAPI module
target_link_libraries(entry PUBLIC node
    # Core Dependencies
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/uv/libuv.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/openssl/libopenssl.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/zlib/libzlib.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/llhttp/libllhttp.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/cares/libcares.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/nghttp2/libnghttp2.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/brotli/libbrotli.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/ngtcp2/libngtcp2.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/ngtcp2/libnghttp3.a"
    
    # V8 JavaScript Engine
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_snapshot.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_libplatform.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_base_without_compiler.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_libbase.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_zlib.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_compiler.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/tools/v8_gypfiles/libv8_initializers.a"

    # Utils & Helpers
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/histogram/libhistogram.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/uvwasi/libuvwasi.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/ada/libada.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/base64/libbase64.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/simdutf/libsimdutf.a"

    # ARM64 Specific Optimizations (Critical for linking)
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/base64/libbase64_neon64.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/zlib/libzlib_inflate_chunk_simd.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/zlib/libzlib_adler32_simd.a"
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/deps/zlib/libzlib_arm_crc32.a"

    # Node Snapshot Stub (Critical for initialization)
    "${CMAKE_CURRENT_SOURCE_DIR}/deps/nodejs-mobile/out/Release/obj.target/node/src/node_snapshot_stub.o"
)
```
