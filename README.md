# JRETS-NotchBridge

`JRETS-NotchBridge` is a Windows controller bridge for **JR East Train Simulator**. It reads a USB joystick or throttle axis, maps that input to train notches, and sends the corresponding keyboard commands to the game.

The app is built with Python and Pygame and is packaged for end users with PyInstaller.

## Features

- Maps a joystick axis to brake, neutral, and power notches
- Supports per-train notch layouts from `vehicles.json`
- Supports both linear mapping and calibrated segmented mapping
- Optional axis-end emergency brake trigger
- Button mapping for neutral, emergency brake, resync, horn, cruise, departure music, and announcements
- Focus-aware input sending so controls pause when the game is not the active window
- Stores runtime configuration under `%APPDATA%`

## Project Files

- `main.py`: main UI and input loop
- `notch.py`: notch definitions and mapping helpers
- `key_sender.py`: keyboard injection helpers and key queue
- `focus_checker.py`: foreground-window/game focus detection
- `vehicles.json`: train notch presets
- `build.ps1`: PyInstaller build script

## Runtime Requirements

- Windows 10 or Windows 11
- Python 3.x for source builds
- A USB joystick, throttle, or other compatible game controller
- JR East Train Simulator

## Configuration

At runtime the app writes its working files under:

```text
%APPDATA%\JRETS-NotchBrige
```

Files used there:

- `config.json`: saved controller and mapping settings
- `vehicles.json`: train definitions copied from the bundled default on first run

## Local Development

Install the Python dependencies you use for development, then run:

```powershell
python main.py
```

Build a Windows package with:

```powershell
.\build.ps1
```

The packaged output is generated under `dist\JRETS_Controller`.

## Release Artifact

Version `0.1.0` is published as a zipped PyInstaller package containing:

- `JRETS_Controller.exe`
- bundled runtime dependencies
- bundled `vehicles.json`

Extract the archive and run `JRETS_Controller.exe`.

## Notes

- The current repository ignores `config.json`, `build/`, and `dist/` so local machine state and generated artifacts do not pollute source control.
- The packaged application name and AppData folder currently use `JRETS-NotchBrige`, matching the existing code.
