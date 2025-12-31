import sys
import os
import platform
import subprocess
import shutil

def main():
    if len(sys.argv) < 2:
        print("Usage: ./ohos-configure <OHOS_NATIVE_SDK_PATH> [ARCH]")
        print("Example: ./ohos-configure /Users/xxx/Library/OpenHarmony/Sdk/10/native arm64")
        sys.exit(1)

    ohos_sdk_path = os.path.abspath(sys.argv[1])
    arch = sys.argv[2] if len(sys.argv) > 2 else 'arm64'

    print(f"Configuring for HarmonyOS ({arch}) using SDK at {ohos_sdk_path}")

    if not os.path.exists(ohos_sdk_path):
        print(f"Error: SDK path {ohos_sdk_path} does not exist.")
        sys.exit(1)

    # Detect LLVM path
    # Usually <sdk>/llvm
    llvm_path = os.path.join(ohos_sdk_path, 'llvm')
    if not os.path.exists(llvm_path):
        # Try finding it in 'toolchains'
        # <sdk>/toolchains/llvm...
        # But OpenHarmony SDK structure usually puts llvm directly in native/llvm or native/toolchains/llvm
        print(f"Warning: {llvm_path} not found. Searching for llvm...")
        found = False
        for root, dirs, files in os.walk(ohos_sdk_path):
            if 'llvm' in dirs:
                llvm_path = os.path.join(root, 'llvm')
                if os.path.exists(os.path.join(llvm_path, 'bin', 'clang')) or os.path.exists(os.path.join(llvm_path, 'bin', 'clang-15')):
                    found = True
                    break
        if not found:
             print(f"Error: Could not find valid llvm toolchain in {ohos_sdk_path}")
             sys.exit(1)
    
    print(f"Using Toolchain: {llvm_path}")

    # Set up tools
    # Host OS for toolchain binaries
    host_system = platform.system().lower()
    
    # Try to find clang executable
    cc = os.path.join(llvm_path, 'bin', 'clang')
    if not os.path.exists(cc):
        cc = os.path.join(llvm_path, 'bin', 'clang-15')
    
    cxx = os.path.join(llvm_path, 'bin', 'clang++')
    if not os.path.exists(cxx):
        # clang++ might be a link to clang, or clang-15
        if os.path.exists(os.path.join(llvm_path, 'bin', 'clang++')):
             cxx = os.path.join(llvm_path, 'bin', 'clang++')
        else:
             # Fallback to clang-15 if clang++ doesn't exist? usually clang++ is just clang check argv[0]
             # But let's check for target specific ones or just assume clang behaves as ++
             # Actually, let's look for any clang++ variant
             import glob
             candidates = glob.glob(os.path.join(llvm_path, 'bin', 'clang++*'))
             if not candidates:
                 # Try using clang as cxx
                 cxx = cc
             else:
                 cxx = candidates[0]
                 
    # If we still rely on clang-15, make sure we use it
    if not os.path.exists(cc):
         # Search for clang-*
         import glob
         candidates = glob.glob(os.path.join(llvm_path, 'bin', 'clang-[0-9]*'))
         if candidates:
             cc = candidates[0]
         else:
             print(f"Error: clang not found in {os.path.join(llvm_path, 'bin')}")
             sys.exit(1)

    # Re-check CXX if it was defaulted
    if not os.path.exists(cxx) or cxx == os.path.join(llvm_path, 'bin', 'clang++'):
         # If we didn't find specific clang++, try to find one matching cc version or just use cc
         # Actually, for OHOS, usually there is no clang++ binary sometimes? 
         # But LS output showed aarch64-unknown-linux-ohos-clang++
         # Let's try to use the target-specific compiler if available, as it handles sysroot better
         target_cc = os.path.join(llvm_path, 'bin', f"{arch.replace('arm64', 'aarch64')}-unknown-linux-ohos-clang")
         target_cxx = os.path.join(llvm_path, 'bin', f"{arch.replace('arm64', 'aarch64')}-unknown-linux-ohos-clang++")
         
         if os.path.exists(target_cc):
             print(f"Found target-specific compiler: {target_cc}")
             cc = target_cc
             cxx = target_cxx
    
    ar = os.path.join(llvm_path, 'bin', 'llvm-ar')
    nm = os.path.join(llvm_path, 'bin', 'llvm-nm')
    
    # Check if tools exist
    if not os.path.exists(cc):
        print(f"Error: clang not found at {cc}")
        sys.exit(1)

    # Set environment variables
    env = os.environ.copy()
    env['CC'] = cc
    env['CXX'] = cxx
    env['AR'] = ar
    env['NM'] = nm
    
    # Need to set sysroot?
    # Clang in OHOS SDK usually knows its sysroot if invoked correctly, 
    # but providing --sysroot is safer.
    sysroot = os.path.join(ohos_sdk_path, 'sysroot')
    cflags = ""
    ldflags = env.get('LDFLAGS', '')

    if os.path.exists(sysroot):
        print(f"Using Sysroot: {sysroot}")
        # We pass sysroot via CFLAGS/LDFLAGS or let configure handle it?
        # node-gyp/configure doesn't have a direct --sysroot flag that propagates easily everywhere 
        # except via CFLAGS.
        cflags = f"--sysroot={sysroot}"
        ldflags = f"--sysroot={sysroot}"
    else:
        print("Warning: sysroot not found, assuming compiler defaults.")

    # Set compiler flags
    env['CFLAGS'] = f"{cflags} -fPIC"
    env['CXXFLAGS'] = f"{cflags} -fPIC"
    env['LDFLAGS'] = ldflags

    # Set host compiler to system compiler (for building build tools)
    env['CC_host'] = 'clang' 
    env['CXX_host'] = 'clang++'

    # GYP Definitions
    # We use OS=linux to enable generic POSIX build, but target_arch must match.
    # We explicitly set v8_target_arch.
    # We can add 'is_ohos=1' if we want custom logic in gyp files.
    # IMPORTANT: Must set host_os explicitly, otherwise gyp might think host is also linux (due to OS=linux)
    if host_system == 'darwin':
        host_os_def = 'mac'
    else:
        host_os_def = host_system
        
    # Add ANDROID_NDK_ROOT and ANDROID_NDK_SYSROOT to GYP_DEFINES
    # Ensure -fPIC is used for static libraries so they can be linked into shared libraries
    gyp_defines = f"target_arch={arch} v8_target_arch={arch} OS=linux host_os={host_os_def} is_ohos=1 standalone_static_library=1 v8_enable_private_mapping_fork_optimization=0 ANDROID_NDK_ROOT={ohos_sdk_path} ANDROID_NDK_SYSROOT={sysroot} cflags='-fPIC' cxxflags='-fPIC'"
    env['GYP_DEFINES'] = gyp_defines

    # Run configure
    # --dest-os=linux: treats it as Linux (closest relative)
    # --cross-compiling: skips running compiled binaries
    # --shared: builds libnode.so
    # --without-intl: reduces size/complexity (optional, but good for mobile)
    # --without-inspector: optional
    
    cmd = [
        './configure',
        '--dest-cpu=' + arch,
        '--dest-os=linux', 
        '--cross-compiling',
        '--enable-static',
        '--without-npm',
        '--without-intl',
        '--without-inspector',
        '--without-node-snapshot',
        '--without-dtrace',
        '--without-etw',
        '--verbose'
    ]

    print("Running configure command:")
    print(" ".join(cmd))
    print(f"GYP_DEFINES={gyp_defines}")

    try:
        # Hack for Mac Host: Create dummy librt.a because gyp insists on linking -lrt for OS=linux
        if host_system == 'darwin':
             out_dir = os.path.abspath('out/Release')
             os.makedirs(out_dir, exist_ok=True)
             
             dummy_c = os.path.join(out_dir, 'dummy_rt.c')
             dummy_o = os.path.join(out_dir, 'dummy_rt.o')
             librt = os.path.join(out_dir, 'librt.a')
             
             with open(dummy_c, 'w') as f:
                 f.write('void __dummy_librt() {}')
                 
             # Use host compiler (cc should be available)
             subprocess.check_call(['cc', '-c', dummy_c, '-o', dummy_o])
             if os.path.exists(librt):
                 os.remove(librt)
             subprocess.check_call(['ar', 'crs', librt, dummy_o])
             
             os.remove(dummy_c)
             os.remove(dummy_o)
             print(f"Created dummy {librt} for Mac host build")

        subprocess.check_call(cmd, env=env)
        print("\nConfiguration successful!")
        print("To build, run: make -j$(nproc)")
        if host_system == 'darwin':
            print(f"NOTE: On Mac, you might need: make -j$(sysctl -n hw.ncpu) LDFLAGS_host='-L{out_dir}'")
        else:
            print("Or if you are on mac: make -j$(sysctl -n hw.ncpu)")
            
        print("\nThe compiled library will be in: out/Release/lib.target/libnode.so")
    except subprocess.CalledProcessError as e:
        print("Error running configure.")
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
