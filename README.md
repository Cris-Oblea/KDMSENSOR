# KDMSENSOR

A launcher for **DanceEvolution ARCADE** (Konami, game build `KDM-001-2016080100`, August 2016) with every mod as an option, and a body sensor that works with a **Kinect v1 or any webcam**. The game is never changed: with every option on its first value it is Konami's game exactly as it shipped.

> [!IMPORTANT]
> This repository holds no file of Konami's and none made from a decompile of it. You need your own, unmodified copy of the game. The mods are made on your PC from your own files (see [How it works](#how-it-works)).

## Features

| Sector | Options |
|---|---|
| Content | Language (English, Traditional Chinese, Japanese), every song unlocked (101 songs, previews and fade-outs for all), English song titles, Stealth played as Master |
| Game rules | Game mode (credits, free play, event mode), 1 to 4 songs per game |
| Picture | Native 1080p, 1440p and 2160p (3D, effects, 2D and the camera picture), unlimited frame rate, SMAA, anisotropic filtering, render threads |
| Attract demo | Master charts, whole songs, every song shuffled, score and combo shown |
| Body sensor | Kinect v1, or the project's webcam sensor (GPU, real time, with an automatic calibrator) |

Each option explains itself in the launcher, and the players' guide (`1 - Play (README).txt`, extracted beside the launcher) describes every one.

Online, the game obeys the server: with an e-amusement server set, every option that changes judging or score stays at Konami's value. For running a server, the game's plugin for Asphyxia CORE is [asphyxia-deac](https://github.com/Cris-Oblea/asphyxia-deac): it keeps the records, runs the weekly Progress events and shows each score's sensor from this launcher.

## Requirements

- Your own copy of the game, **DanceEvolution ARCADE KDM-001-2016080100**, extracted and unmodified. The launcher checks every file against Konami's own manifest before and after each game and refuses to play on a changed one.
- Windows 10 or 11 (64-bit), in any language, and an administrator account.
- Microsoft's *DirectX End-User Runtimes (June 2010)*, which the game needs.
- A Kinect v1, or a camera (a graphics card with DirectX 12 for the webcam sensor).
- `KDMSENSOR-restored-audio.7z` (about 95 MB, the songs' restored audio), once, and the internet whenever you update.

## Installation

1. Download `KDMSENSOR-x.y.z.zip` from the [latest release](https://github.com/Cris-Oblea/KDMSENSOR/releases/latest).
2. Extract it into the game's folder, the one that holds `data`, `modules` and `prop`. It adds `1 - Play.bat`, `1 - Play (README).txt` and `mods\` and touches nothing else.
3. Open `1 - Play.bat` and say yes to the administrator prompt.
4. Put `KDMSENSOR-restored-audio.7z` in the `mods` folder (keep its name; the launcher says so when it is missing). The first time, the launcher checks its SHA-256, unpacks it, and makes the mods from your game files (about a minute). If your files are not Konami's August 2016 build it says so and writes nothing.
5. Press *spice2x settings...* and bind your buttons (the cabinet has no keyboard), choose your options, and press *Play*.

## Updating

The launcher's title shows the version you have; below its buttons, the link to this repository and the **Changelog** link, which opens every version's changes. Each time it opens, and whenever you press **Check for updates** beside Play (it answers in a window: the latest version, no internet, or no release yet), the launcher looks at the latest release. If it is newer, it shows what changed, with **Update** and **Not now**. An update downloads only the parts that changed, checks the size and SHA-256 of every file, and replaces nothing until all of them are right: a failed or partial download leaves the version you have. It never writes `modules\`, `data\` or your own settings, saves and options.

## How it works

The release carries everything that does not come from Konami's files: the launcher, the options' catalogue (`mods/catalog.json`, every edit as bytes with the original bytes it expects), spice2x and the other tools, the webcam sensor, and `mods/generator`, a small Python program (with its own embedded Python, nothing to install) that makes the rest **on your PC from your own game files**: the stealth charts, the song list with its 22 unlocks, the English titles, the shaders of each resolution, the configuration and the song previews. It checks each file it makes against `mods/generated.json` (SHA-256) before writing any, so a base that is not Konami's gives an error, never a half-made mod.

The audio of the 20 songs whose banks Konami emptied in its last offline build, and YESTERDAY's audio and jacket, can not be made from any base. They are one archive (`KDMSENSOR-restored-audio.7z`, never changing, no version), not part of this repository; `mods/fixed.json` holds its name, size and SHA-256, and the launcher unpacks it once and refuses any other file.

## What this repository never contains

- Konami's files, in any form: no game data, no module, no manifest, no audio, no art.
- Decompiles or disassemblies of Konami's code.
- Your game, your saves or your settings.

## Credits

- **[spice2x](https://github.com/spice2x/spice2x.github.io)**, the loader the launcher runs (GPL-3.0).
- **[JoeKoh27](https://github.com/JoeKoh27/danevo-patches)**, whose omnimix and Kinect-bypass patches showed what the offline build could do, and which the launcher runs beside without touching.
- **[LayeredFS](https://github.com/mon/ifs_layeredfs)** (mon), the file overlay that serves the mods' data without writing the game's.
- SMAA by Jorge Jimenez et al., ONNX Runtime and DirectML (Microsoft), MMPose and RTMPose (OpenMMLab), MediaPipe BlazePose (Google), the AIST++ dataset, Python, 7-Zip. Their licences are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Not affiliated with or endorsed by Konami.

## License

Each part has its own licence, listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The launcher, the updater, the generator, the catalogue and this project's own programs (the sensor, the Kinect shim, the Direct3D 9 proxy) are under the [MIT License](LICENSE). Konami's game is Konami's.
