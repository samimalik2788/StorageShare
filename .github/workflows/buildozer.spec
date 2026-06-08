[app]

# (str) Title of your application
title = StorageShare

# (str) Package name
package.name = storageshare

# (str) Package domain (needed for android/ios packaging)
package.domain = com.storageshare

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,txt,json

# (list) List of inclusions using pattern matching
source.include_patterns = assets/kv/*.kv

# (list) Source files to exclude (let empty to not exclude anything)
#source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
#source.exclude_dirs = tests, bin

# (list) List of exclusions using pattern matching
#source.exclude_patterns = license,readme

# (str) Application versioning (method 1)
version = 1.0.0

# (str) Application versioning (method 2)
# version.regex = __version__ = ['"](.*)['"]
# version.filename = %(source.dir)s/main.py

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,kivymd,pyjnius,requests,Pillow

# (str) Custom source folders for requirements
#requirements.custom_source_dirs =

# (list) Preseeded requirements
#preseed_packages =

# (str) Android application theme
android.api = 33

# (int) Android SDK version to use
#android.sdk = 20

# (str) Android NDK version to use
android.ndk = 25b

# (int) Android minimum API
android.minapi = 21

# (int) Android target API
android.targetapi = 33

# (list) Android additional libraries to add
#android.add_libs = 

# (str) Android extra packages
#android.extra_packages = 

# (bool) If True, then we automatically download the sdk, ndk, etc.
android.accept_sdk_license = True

# (bool) If True, then we download the latest Android build tools
android.install_build_tools = True

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
#android.ndk_path =

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
#android.sdk_path =

# (str) Android Ant directory (if empty, it will be automatically downloaded.)
#android.ant_path =

# (bool) If True, then we will try to download Java if needed
android.install_java = True

# (str) Android package name (you can change it to something else)
#android.arch = armeabi-v7a

# (list) Android architecture list to build for
android.archs = arm64-v8a, armeabi-v7a

# (str) Android entry point, default is 'org.kivy.android.PythonActivity'
#android.entrypoint = org.kivy.android.PythonActivity

# (str) Presplash background color (in '#rrggbb' format)
presplash.color = #4CAF50

# (str) Presplash image
presplash.filename = %(source.dir)s/assets/icons/icon.png

# (str) Icon of the application
icon.filename = %(source.dir)s/assets/icons/icon.png

# (str) Loading spinner color (in '#rrggbb' format)
#android.loadingspinner.color = #4CAF50

# (list) Android permissions
android.permissions = INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, CHANGE_WIFI_STATE, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, FOREGROUND_SERVICE

# (int) Android service to start at boot
#android.service = 

# (str) Android app class
#android.appclass = 

# (str) Android package name
#android.package_name =

# (bool) If True, then use the android private storage
#android.use_private_storage = True

# (str) Android log handler
#android.log_handler = 

# (bool) If True, then the app will not be restarted when the device orientation changes
#android.allow_backup = False

# (str) Android window size
#android.window_size = 

# (bool) If True, then we don't build the APK in debug mode
#android.release = False

# (str) Android keystore alias
#android.keyalias =

# (str) Android keystore password
#android.keystore_password = 

# (str) Android keystore name
#android.keystore = 

# (str) Android private key password
#android.key_password = 

# (bool) If True, then the app will be built in debug mode
android.debug = True

# (str) Android logcat filter
android.logcat_filters = *:S python:D

# (bool) Copy application APK to the current directory
android.copy_apk = True

# (str) Source code to execute on the first available run
#android.first_run = 

# (str) Additional Java dependencies
#android.add_src =

# (list) Java files to add to the java project
#android.add_java_src =

# (list) AAR files to add to the java project
#android.add_aar =

# (list) JAR files to add to the java project
#android.add_jar =

# (list) Gradle dependencies repositories
#android.gradle_repositories =

# (list) Gradle dependencies
#android.gradle_dependencies =

# (str) The Android app theme to use
#android.apptheme = @android:style/Theme.Material.Light

# (str) The Android app theme for the splash screen
#android.apptheme_splash = @android:style/Theme.Material.Light

# (list) Add extra command line arguments for the build
#android.build_cmdline_args =

# (str) Buildozer command line arguments
#buildozer_cmd_args =

# (str) Log level for the build (info, debug, error)
buildozer_loglevel = 2

[buildozer]

# (int) Log level (0 = error, 1 = info, 2 = debug)
log_level = 2

# (str) Path to the build directory
#build_dir = ./.buildozer

# (str) Path to the bin directory
#bin_dir = ./bin

# (str) Path to the Android SDK
#android_sdk =

# (str) Path to the Android NDK
#android_ndk =

# (str) Path to the Android Ant
#android_ant =

# (str) Path to the Java
#java_path =

# (str) Path to Python
#python_path =

# (str) Operating System (android, ios, windows, linux, osx)
#os = android

# (str) Build platform (ubuntu, osx, windows)
#build_platform =

# (str) Target Platform (android, ios)
#target = android

# (int) Timeout for the build process
#timeout = 3600

# (str) Path to the build log
#log_filename = build.log

# (str) Path to the build error log
#error_filename = build.err

# (str) Path to the build output
#output_filename =

# (bool) If True, then we will use the system's Java
#use_system_java = False

# (bool) If True, then we will use the system's Python
#use_system_python = False

# (str) Android API
#android_api = 30

# (int) Android minimum API
#android_minapi = 21

# (str) Android NDK version
#android_ndk = 21

# (str) Android SDK
#android_sdk = 30

# (str) Android platform
#android_platform =

# (str) Android architecture
#android_arch = armeabi-v7a

# (list) Android architectures
#android_archs = armeabi-v7a, arm64-v8a