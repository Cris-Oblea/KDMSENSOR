# Third-party notices

What ships in a release beside this project's own code, where it comes from, and under which terms. The exact files and their SHA-256 are in each release's `manifest.json`.

## Konami's game

DanceEvolution ARCADE is Konami's. This project contains none of its files and is not affiliated with or endorsed by Konami. You need your own copy.

## Programs the launcher runs

| Component | File | Version | Licence | Source |
|---|---|---|---|---|
| spice2x | `mods/bin/spice.exe` | release 26-10-03, as published, unmodified | GNU GPL v3 | https://github.com/spice2x/spice2x.github.io (the source of this release is there, tag `26-10-03`) |
| LayeredFS | `mods/bin/ifs_hook.dll` | as published, unmodified | Apache-2.0 with the author's modifications (below) | https://github.com/mon/ifs_layeredfs |
| ONNX Runtime (DirectML build) | `mods/webcam/onnxruntime.dll` | 1.24.4 | MIT | https://github.com/microsoft/onnxruntime |
| DirectML | `mods/webcam/DirectML.dll` | as redistributed in the NuGet package Microsoft.AI.DirectML | Microsoft Software License Terms (redistributable) | https://www.nuget.org/packages/Microsoft.AI.DirectML |
| Visual C++ runtime | `mods/webcam/msvcp140.dll`, `msvcp140_1.dll`, `vcruntime140.dll`, `vcruntime140_1.dll` | Visual Studio redistributable | Microsoft Software License Terms (redistributable) | https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files |
| Python (embeddable) | `mods/bin/python/` | 3.14.10, from python.org, unmodified except its `._pth` file | Python Software Foundation License (`mods/bin/python/LICENSE.txt`) | https://www.python.org |
| 7-Zip (7zr.exe) | `mods/bin/7zr.exe` | 26.04, from 7-zip.org, unmodified | GNU LGPL, 7-Zip's licence: https://www.7-zip.org/license.txt | https://www.7-zip.org |

spice2x is distributed here unmodified, as a GPL-3.0 program; its complete source is at the repository above. LayeredFS's licence file reads: "Treat the license for this code as though it were the Apache-2.0 license, WITH THE FOLLOWING MODIFICATIONS: If you integrate LayeredFS into your launcher of choice, you MUST NOT modify the existing commandline argument names. If you add any commandline arguments, they MUST begin with `--layered-`." This launcher passes only LayeredFS's own `-k ifs_hook.dll` arguments through spice2x and adds none.

## Models (webcam sensor)

| Model | File | Licence | Source |
|---|---|---|---|
| RTMDet-nano (person detection), RTMPose-s (body7, Halpe-26) | `mods/webcam/models/rtmdet_nano.onnx`, `rtmpose_s_halpe26.onnx` | Apache-2.0 | OpenMMLab MMPose, https://github.com/open-mmlab/mmpose |
| BlazePose GHUM lite | `mods/webcam/models/blazepose_lite.onnx` | Apache-2.0 | Google MediaPipe Pose Landmarker, https://github.com/google-ai-edge/mediapipe (converted from TFLite to ONNX with tf2onnx) |
| 2D-to-depth lifter for dance | `mods/webcam/models/lifter.onnx` | this project's own (MIT), trained on the AIST++ dataset's 3D keypoints | Li, Yang, Ross, Kanazawa, "AI Choreographer: Music Conditioned 3D Dance Generation with AIST++", ICCV 2021; annotations under CC BY 4.0, https://google.github.io/aistplusplus_dataset |

## Code inside this project's own binaries

`mods/bin/d3d9.dll` (the Direct3D 9 proxy: native resolutions, frame rate, filters) contains the reference SMAA shader:

> SMAA: Copyright (C) 2013 Jorge Jimenez (jorge@iryoku.com), Jose I. Echevarria (joseignacioechevarria@gmail.com), Belen Masia (bmasia@unizar.es), Fernando Navarro (fernandn@microsoft.com), Diego Gutierrez (diegog@unizar.es). MIT licence, https://github.com/iryoku/smaa

## This project

The launcher (`1 - Play.bat`, `mods/play_mods.ps1`, `mods/update.ps1`), the options' catalogue (`mods/catalog.json`), the generator (`mods/generator`), the webcam sensor (`mods/webcam/kdmsensor.exe`), the Kinect shim (`mods/webcam/Kinect10.dll`) and the Direct3D 9 proxy (`mods/bin/d3d9.dll`): MIT, see `LICENSE`.

## The fixed archive

`KDMSENSOR-restored-audio.7z` (one file, never versioned) holds audio and art that no Konami base can give: the audio of the 20 banks Konami emptied in its last offline build (14 are Konami's own audio from its October 2015 build, 6 are found only in a 2017 copy of the February 2016 build that circulates, whose author is unknown), YESTERDAY's audio and jacket (from that copy), and the song-select preview seed (Konami's own preview waves from its February 2016 build). It is Konami's and other rights holders' material, not this project's, and is not part of this repository: the player puts it in `mods`, and the launcher unpacks it only if its SHA-256 matches `mods/fixed.json`.
