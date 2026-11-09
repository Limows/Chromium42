# Сборка Chromium 42 для Android 4.0 (ICS)

Последняя версия Chromium, официально поддерживавшая Android 4.0 ICS.
Собираем `chrome_shell_apk` — development shell с рабочим движком
(rendering, V8, networking, codecs), без расширений и Google-сервисов.

## Что получится в итоге

- `ChromeShell.apk` — рабочий браузер для Android 4.0+
- `libchromeshell.so` — native ARMv7 библиотека
- Включено: H.264/AAC/Widevine через `proprietary_codecs=1`
- Выключено: extensions, SafeBrowsing, component updater, Google Now
- minSdkVersion: 14 (Android 4.0 ICS)
- targetSdkVersion: 21 (Android 5.0 Lollipop)

## Требования к системе

- Ubuntu 18.04 x86_64 (или новее)
- 50 GB свободного места (исходники + сборка)
- 8 GB RAM (16 GB рекомендуется)
- Интернет ~12 GB (gclient sync)

## Быстрый старт (4 команды)

```bash
# 1. Установка окружения (один раз, ~20 минут)
bash bin/setup_env.sh

# 2. Скачать исходники (~30-60 минут, ~12 GB)
bash bin/fetch_source.sh

# 3. Применить патчи (~30 секунд)
cd ~/chromium42/src
python3 ~/build_env/patches/apply_patches.py

# 4. Собрать APK (~1-4 часа)
bash bin/build.sh
```

Результат: `~/chromium42/src/out/Release/apks/ChromeShell.apk`

## Структура проекта

```
chromium42-build/
├── BUILD.md                  # этот файл
├── README.md                 # краткое описание
├── bin/
│   ├── setup_env.sh          # 1. Установка окружения (один раз)
│   ├── chromium42_env.sh     # source-файл переменных окружения
│   ├── fetch_source.sh       # 2. gclient sync (~12 GB)
│   └── build.sh              # 4. gyp_chromium + ninja
└── patches/
    ├── apply_patches.py      # 3. Мета-патчер (запускает все ниже)
    ├── fix_grd_android_excludes.py  # .grd: not is_android → False
    ├── fix_gcc_warnings.py          # GCC warnings для host g++
    ├── fix_stlport_vector_data.py   # STLport vector::data()
    ├── fix_libusb_android.py        # libusb POSIX threads
    ├── fix_gms_javalib.py           # GMS has_java_resources=0
    ├── stub_google_play_services.sh # stub GMS
    ├── run_hooks.sh                 # LASTCHANGE, LASTCHANGE.blink
    ├── fix_gyp_components.py        # exclude dead components (audio_modem, etc.)
    ├── fix_dead_target_refs.py      # remove dead target references
    ├── fix_copresence_sources.py    # exclude copresence .cc files
    ├── fix_copresence_api_sources.py # exclude copresence IDL + headers
    ├── fix_manual_patches.py        # 7 C++ source patches
    └── chrome_shell_stubs.cc        # stubs for 9 link-time undefined refs
```

## Что делают патчи

### Шаг 1: `fix_grd_android_excludes.py`
Заменяет `<if expr="not is_android">` на `<if expr="False">` в .grd файлах,
чтобы GRIT генерировал только Android-специфичные IDS_ константы.

### Шаг 2: `fix_gcc_warnings.py`
Добавляет `-Wno-*` флаги для host g++ (GCC 7+), не затрагивая NDK gcc 4.9.
Решает проблему deprecated warnings в современном GCC.

### Шаг 3: `fix_stlport_vector_data.py`
Патчит STLport `_vector.h` (оба варианта) для добавления `vector::data()`,
которая нужна для C++11 кода, но отсутствует в старом STLport.

### Шаг 4: `fix_libusb_android.py`
Патчит libusb для Android: POSIX threads, OS_LINUX condition
(без linux_netlink, SOCK_RAW undefined на Android).

### Шаг 5: `fix_gms_javalib.py`
Ставит `has_java_resources=0` в android_tools.gyp для GMS — stub'ный jar
не должен обрабатываться как настоящий.

### Шаг 6: `stub_google_play_services.sh`
Создаёт stub Google Play Services: пустой .jar, R.java, GmsStub.java.
Реальный GMS не доступен на Android 4.0 и не нужен для chrome_shell.

### Шаг 7: `run_hooks.sh`
Генерирует `build/util/LASTCHANGE` и `build/util/LASTCHANGE.blink` —
нужны для version info в Chrome.

### Шаг 8: `fix_gyp_components.py`
Исключает из сборки мёртвые Google API:
- `audio_modem` (ультразвуковая передача — эксперимент 2015)
- `copresence` (Bluetooth presence — эксперимент)
- `cryptauth` (device-to-device crypto)
- `proximity_auth` (Easy Unlock backend)
- `storage_monitor`, `user_manager`, `feedback`, `browser_watcher`, `wifi`

### Шаг 9: `fix_dead_target_refs.py`
Удаляет ссылки на `_test_support` targets (audio_modem_test_support, etc.)
из всех .gypi файлов — они ссылаются на удалённые в шаге 8 targets.

### Шаг 10: `fix_copresence_sources.py`
Исключает .cc файлы copresence из source lists.

### Шаг 11: `fix_copresence_api_sources.py`
Удаляет `copresence.idl`, `copresence_private.idl`, `audio_modem.idl` из
`schemas.gypi`. Удаляет `copresence_api.h` из `chrome_browser_extensions.gypi`
(чтобы `generated_api_registration.cc` не инклудил его).

### Шаг 12: `fix_manual_patches.py`
Применяет 7 ручных C++ патчей:
- `compiler_version.py`: `-dumpversion` → `-dumpfullversion` (GCC 7+)
- `hid_service.cc`: `#elif defined(OS_WIN)` → добавить `|| defined(OS_ANDROID)`
- `chrome_content_rules_registry.cc`: `::iterator` → `::const_iterator`
- `windows_event_router.cc`: добавить OS_ANDROID handling
- `pepper_plugin_info.h`: закомментировать `#error "Plugins should be enabled"`
- `native_process_launcher_posix.cc`: stub для `chrome::DIR_NATIVE_MESSAGING`
- `tts_extension_api.cc`: `::iterator` → `::const_iterator`

### Шаг 13: копирование `chrome_shell_stubs.cc`
Stub-файл с пустыми реализациями для 9 undefined references:
- `chrome_pdf::PPP_GetInterface`, `PPP_InitializeModule`, `PPP_ShutdownModule`
- `SafeBrowsingService::OnResourceRequest`, `ui_manager`, `CreatePreferenceValidationDelegate`
- `SafeBrowsingUIManager::UnsafeResource` constructor/destructor
- `SafeBrowsingBlockingPage::CreateBlockingPage`

Эти символы ссылаются на desktop-only код, который не компилируется на Android.
Stubs никогда не вызываются в runtime.

## Переменные окружения

`chromium42_env.sh` определяет:
- `CHROMIUM_ROOT` — где лежит исходник (default: `~/chromium42`)
- `DEPOT_TOOLS_ROOT` — где depot_tools (default: `~/build_env/depot_tools`)
- `GYP_DEFINES` — все ключи сборки (target_arch=arm, OS=android, clang=0, etc.)
- Функции `gyp_chromium` и `ninja_run` — wrappers с python2.7 в PATH

### Ключи GYP_DEFINES

```
target_arch=arm
arm_version=7
arm_float_abi=softfp
OS=android
chromeos=0
branding=Chromium
buildtype=Official

proprietary_codecs=1          # H.264, AAC, MP3
ffmpeg_branding="Chrome"
enable_widevine=1              # DRM для Netflix-подобных сервисов
enable_widevine_cdm_host_verification=0

disable_component_updater=1    # нет авто-обновления
safe_browsing=0               # нет Google SafeBrowsing
enable_google_now=0           # нет Google Now
enable_extensions=0           # нет расширений (не работают на ICS)
enable_plugins=1               # Pepper plugins (PDF)

clang=0                        # использовать системный gcc
host_clang=0                   # тоже для host binaries
werror=''                     # не превращать warnings в errors

v8_use_snapshot=0              # отключить mksnapshot (segfault на GCC 7)
v8_use_external_startup_data=0

GYP_GENERATORS=ninja
android_sdk_root=...
```

## Команды-обёртки

### `gyp_chromium`
Запускает `python2.7 build/gyp_chromium` с python2.7 в PATH.
GYP скрипты Chromium 42 написаны на Python 2.

### `ninja_run`
Запускает `/usr/bin/ninja` (system ninja, не depot_tools wrapper) с
python2.7 в PATH для subprocess вызовов.

Использование:
```bash
ninja_run -C out/Release chrome_shell_apk
```

## Что НЕ работает в Chrome Shell

- **Расширения** — выключены (`enable_extensions=0`)
- **Multi-tab UI** — только одно окно
- **Bookmark UI** — нет встроенного
- **History UI** — нет встроенного
- **Settings UI** — минимальный
- **Sync** — нет (требует Google account)
- **Sign-in** — нет

## Что РАБОТАЕТ

- Полный веб-рендеринг (Blink)
- JavaScript (V8)
- HTML5, CSS3, WebGL
- Media: H.264, AAC, MP3, WebM
- Widevine DRM (для видео-сервисов)
- Networking (HTTP/1, HTTP/2, WebSocket)
- Cookies, localStorage, IndexedDB
- Service Workers
- Omnibox с URL navigation

## Установка APK на устройство

```bash
# Включить USB debugging на Android устройстве
adb devices
adb install -r ~/chromium42/src/out/Release/apks/ChromeShell.apk

# Запустить
adb shell am start -n org.chromium.chrome.shell/.ChromeShellActivity
```

## Решение проблем

### gclient sync висит
- Это нормально. gclient печатает "Still working on: src" каждые ~10s
- Проверяй прогресс: `du -sh ~/chromium42/src`
- Если реально завис (>1 час без роста размера): убей и перезапусти с `--reset`

### gyp_chromium: Dependency 'X' not found
- Запусти `fix_dead_target_refs.py` заново
- Если новый target: добавь его имя в `_BASE_TARGETS` в скрипте

### ninja: undefined reference to 'X'
- Запусти `fix_link_stubs.py` с лог-файлом ошибки
- Или добавь stub вручную в `chrome/browser/chrome_shell_stubs.cc`

### ninja: SyntaxError (Python)
- Это Python 2 скрипт запущен под Python 3
- Используй `ninja_run` (не `ninja` напрямую) — он ставит python2.7 в PATH

### ninja: clang++ not found
- GYP_DEFINES должен содержать `clang=0` и `host_clang=0`
- После изменения: `gyp_chromium` для перегенерации

### Build failed: object incomplete type
- Обычно `scoped_ptr<T>` где T не полностью определён
- Найди правильный #include для T (grep -rln "class T")
- Поставь его ПЕРЕД использованием (важен порядок include)

## Дальнейшие шаги

После успешной сборки:
1. **Запустить APK** на Android 4.0 устройстве — проверить что работает
2. **Выпилить Google-код** (URLs в strings, telemetry)
3. **Обновить CA bundle** (текущий от 2015)
4. **Обновить cipher suites** для современного TLS 1.3 (если возможно)
5. **Развить UI** — добавить tabs, bookmarks, history, settings

## Ссылки

- Chromium 42 release notes: https://blog.chromium.org/2015/04/chrome-42-stable-update.html
- Last ICS support announcement: https://chrome.googleblog.com/2015/04/chrome-42-update-ics-deprecation.html
- Source: https://chromium.googlesource.com/chromium/src/+/42.0.2311.107
