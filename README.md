# Chromium 42 для Android 4.0 ICS — Build Kit

Сборочный комплект для Chromium 42.0.2311.107 (последняя версия Chrome для Android 4.0).

## Что это

Полностью автоматизированный процесс сборки `chrome_shell_apk` — development
shell с рабочим движком Chromium 42 (rendering, V8, networking, codecs).
Без расширений и Google-сервисов.

## Быстрый старт

```bash
# 1. Установка окружения (~20 минут, один раз)
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

## Что внутри

```
chromium42-build/
├── BUILD.md           # Подробное описание процесса
├── README.md          # Этот файл
├── bin/
│   ├── setup_env.sh
│   ├── chromium42_env.sh
│   ├── fetch_source.sh
│   └── build.sh
└── patches/
    ├── apply_patches.py              # Мета-патчер (запускает все ниже)
    ├── fix_grd_android_excludes.py
    ├── fix_gcc_warnings.py
    ├── fix_stlport_vector_data.py
    ├── fix_libusb_android.py
    ├── fix_gms_javalib.py
    ├── stub_google_play_services.sh
    ├── run_hooks.sh
    ├── fix_gyp_components.py
    ├── fix_dead_target_refs.py
    ├── fix_copresence_sources.py
    ├── fix_copresence_api_sources.py
    ├── fix_manual_patches.py
    └── chrome_shell_stubs.cc
```

## Подробности

См. [BUILD.md](./BUILD.md) — полное описание каждого шага, всех патчей,
переменных окружения, и решение типичных проблем.

## Что получилось в итоге

- Chrome Shell APK для Android 4.0+ (armv7)
- Рабочий движок: rendering, JavaScript, HTML5, media
- Proprietary codecs: H.264, AAC, MP3
- Widevine DRM
- minSdkVersion: 14 (ICS)
- Размер APK: ~25-35 MB

## Что НЕ включено

- Расширения (не работают на ICS)
- Sync (требует Google account)
- Multi-tab UI, bookmark manager, history UI, settings UI
- SafeBrowsing, component updater

## Лицензия

Chromium — BSD-style license. Патчи — свободны для использования.
