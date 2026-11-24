# ruff: noqa: C408   (the option catalogue is data: dict(id=..., help=...) reads as a table)
r"""
Builds `mods/`: every mod of the project as a selectable option, apart from the game.

The installed game is never written (the user's rule, MOD_AUDIT.md). This script reads
Konami's originals from the game itself (modules/, data/: verify_build.py proves them equal to
the arcade dump) and writes:

    mods/catalog.json     every option: what it does for the player, what it needs, its
                          code edits as spice2x "memory" patches (file offsets, dllName,
                          original bytes checked on apply) and its data folders
    mods/data/shaders_1080/, shaders_1440/, shaders_2160/  each resolution's shader entries (shaders.py --out), rebuilt

The other folders of mods/data are SOURCE here, not output (regen_pack.py makes every one of them again from Konami's files
plus a fixed part and proves it by SHA-256, MOD_AUDIT.md 9c): the project's content as it was cut
on 2026-10-25 from the build it had installed (proven: Konami's original + these folders
reproduced all 91 modded files byte for byte), before the game was restored. They are never
deleted or rebuilt here, only required and checked; a copy is in
_tools/mods/sources/mods_content_20261112.7z (after the previews and phases of 2026-11-12;
the cut of 2026-10-25 beside it). check_songlist() proves songlist_yesterday without its appended `yest` record
(unlock_songs.drop_yest, the inverse of add_yest) against Konami's table.

Code options are measured, not hand-written: each one is built by its own patcher on a copy
of the original file, and the edit list is the byte difference. Then the check that makes
them combinable: no two options that can be on together touch the same byte, and applying
every option's edits at once gives the same MD5 as running the patchers one after another.

USAGE
    python _tools/mods/build_mods.py         rebuild what mods/ derives (catalogue, shaders,
                                            binaries); check the content folders
    python _tools/mods/build_mods.py --check  only the code checks, writes nothing
"""
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))  # _tools: paths, and the packages
from formats import song_params
from formats.arc_lz import read_arc
from mods.content import titles
from mods.content.songs.unlock_songs import drop_yest
from paths import ROOT, TOOLS

ORIG = ROOT   # the game is Konami's original (verify_build.py part 1)
MODS = os.path.join(ROOT, "mods")
# Konami's files (the manifest does not cover modules/; these equal the August archive).
SOURCES = {
    "gamekdm.dll": (os.path.join(ORIG, "modules", "gamekdm.dll"), "ed4040df5924c448de11868db3a1e242"),
    "arkkdm.dll": (os.path.join(ORIG, "modules", "arkkdm.dll"), "7baf823d12f8adbe32c7cf61a4972b70"),
    "libafputils-win32.dll": (os.path.join(ORIG, "modules", "libafputils-win32.dll"), None),
}
# spice.exe ships in mods/bin: the pack never uses the player's spice2x. The launcher sets
# LARGE_ADDRESS_AWARE on its copy from the PE header, not by offset.
RES = "mods/picture/resolution/resolution.py"   # every part of the option, in order
TEST_MODE = "mods/picture/resolution/test_mode.py"   # test mode's pictures (the Screen Check card) scaled with the screen
RES_1080 = [("gamekdm.dll", RES, ["--apply", "1920", "1080"]), ("gamekdm.dll", TEST_MODE, ["--apply", "1920", "1080"])]
RES_1440 = [("gamekdm.dll", RES, ["--apply", "2560", "1440"]), ("gamekdm.dll", TEST_MODE, ["--apply", "2560", "1440"])]
RES_2160 = [("gamekdm.dll", RES, ["--apply", "3840", "2160"]), ("gamekdm.dll", TEST_MODE, ["--apply", "3840", "2160"])]
USER_TOOLS = os.path.join(os.path.expanduser("~"), "Tools")
BINS = {"d3d9.dll": os.path.join(TOOLS, "d3d9probe", "out", "player", "d3d9.dll"),   # our proxy, KDM_PLAYER
        "ifs_hook.dll": os.path.join(USER_TOOLS, "ifs_hook_omni", "ifs_hook.dll"),   # mon's LayeredFS 4.1
        "spice.exe": os.path.join(ROOT, "spice.exe")}
# spice2x refuses a config with no <soft> block (F:avs-ea3: datecode missing), and Konami's has none.
SOFT = (b'  <soft>\r\n    <model __type="str">KDM</model>\r\n    <dest __type="str">J</dest>\r\n    <spec __type="str">B</spec>\r\n'
        b'    <rev __type="str">A</rev>\r\n    <ext __type="str">2016080100</ext>\r\n  </soft>\r\n')
CONTENT = {"banks_restored": 20, "songlist_yesterday": 1, "yesterday": 4,
           "previews": 6, "stealth": 60}   # folder: files (MOD_AUDIT.md 1.1)


def txt(*lines: str) -> str:
    return " ".join(lines)


# Every option is a choice; a toggle is a choice between "off" (the original) and "on".
# A value's `needs` lists other values ("option.value") that are switched on with it.
OPTIONS = [
    dict(id="language", title="Language",
         help=txt("The language of every text and menu picture the game draws. The machine picks one",
                  "at the factory. A fourth code in the game (kan, Simplified Chinese, from the Mainland China version) is not offered:",
                  "Konami never shipped its pictures, and the game crashes looking for them."),
         values=[
             dict(id="jpn", label="Japanese (original)", help="As Konami set the machine."),
             dict(id="eng", label="English", code=[("gamekdm.dll", "mods/content/language.py", ["eng", "--apply"])],
                  help="The game's own English assets (*_lang_eng)."),
             dict(id="han", label="Chinese (Traditional)", code=[("gamekdm.dll", "mods/content/language.py", ["han", "--apply"])],
                  help="The game's own Traditional Chinese assets (*_lang_han)."),
         ]),
    dict(id="songs", title="Song list",
         help=txt("Konami's August 2016 offline build locked 22 songs and emptied the audio of 20 of",
                "them (licences expiring). This brings them back."),
         values=[
             dict(id="original", label="Original (80 songs)", help="The song list as Konami shipped it."),
             # one value since 2026-10-27, previews included (the user: unlocking is everything, each song whole,
             # nothing separate); check_songlist() proves the shipped list, yest taken out, against Konami's
             dict(id="all", label="Every song unlocked (102 songs)",
                  data=["banks_restored", "songlist_yesterday", "yesterday", "previews"],
                  needs=["soundpath.on", "soundheap.on"],
                  help=txt("The 22 locked songs unlocked; the 20 emptied audio banks restored (14 are Konami's own audio,",
                         "as in its October 2015 build; 6 are found only in a 2017 copy of the February 2016",
                         "build, who put them there is not known: brav iron maru merr noff rena);",
                         "Konami's typo in rena's second chart fixed; YESTERDAY, its chart from the Dance Masters",
                         "disc, its audio and jacket from that same 2017 copy;",
                         "and the song-select preview of every song that had none, cut at the instant",
                         "Konami chose for the others.")),
         ]),
    # {songs}: the launcher names the folder after the song list chosen, since each one holds a whole
    # song_params.plist; eng_ sorts before songlist_, so LayeredFS serves it first (mods.md trap 8)
    dict(id="titles", title="Song titles in English",
         help=txt("In English the song list still shows Japanese titles and artists. This writes them",
                  "with their official English or romanised names (from the releases and the BEMANI",
                  "references), so a player can read them and look them up."),
         values=[dict(id="off", label="Original"),
                 # seen in music select by the user, 2026-10-27 (MOD_AUDIT.md §0)
                 dict(id="on", label="English and romanised", data=["eng_titles_{songs}"], needs=["language.eng"])]),
    dict(id="soundheap", title="Sound memory",
         help=txt("Raises the game's sound memory from 76 to 128 MB. Needed by the unlocked songs' previews",
                "(they do not fit in 76 MB and then no sound plays at all)."),
         values=[dict(id="off", label="Original (76 MB)"),
                 dict(id="on", label="128 MB", code=[("gamekdm.dll", "mods/support/soundheap.py", ["128", "--apply"])])]),
    dict(id="soundpath", title="Sound files",
         help=txt("The game reads its music and sound banks straight from data/sound, where mods cannot",
                  "reach. Mods that bring audio (restored songs, previews, YESTERDAY) make it read",
                  "mods/snd instead, where the launcher links every original bank plus theirs."),
         values=[dict(id="off", label="Original folder"),
                 dict(id="on", label="Through the mods (mods/snd)", sound=True,
                      code=[("gamekdm.dll", "mods/support/soundpath.py", ["--apply"])])]),
    dict(id="stealth", title="Stealth difficulty", lock_online=True,   # lock_online: changes the score, Konami's value on a server (MOD_AUDIT.md 0)
         help=txt("Stealth is the hardest chart played with no step markers. For the 30 songs that",
                "came from the Dance Masters disc it copies EXTREME, because the disc had no master",
                "chart; this makes it copy MASTER, as the arcade's own songs do."),
         values=[dict(id="off", label="Original"),
                 dict(id="on", label="Stealth = master everywhere", data=["stealth"])]),
    # one value, so always on (T152, the user 2026-11-23): only the server decides, nothing is drawn without an event and no
    # score changes (T129, ARCHITECTURE.md 16.7), so no lock_online and no menu entry
    dict(id="rankicon", title="Ranking event icon",
         help=txt("When a server runs a ranking event (two songs everyone competes on), the game was meant to mark",
                  "those songs' difficulties with a RANKING! icon in the difficulty select, but never did: Konami's",
                  "build does not load the file that holds the picture. This loads it. Nothing is drawn without an event."),
         values=[dict(id="on", label="RANKING! icon on the event's songs", data=["rank_icon"],
                      code=[("gamekdm.dll", "mods/content/rank_icon.py", ["--apply"])])]),
    # no lock_online (T149, the user 2026-11-23): it changes no score, and it is set the way an operator sets it: FREE PLAY is
    # written into the player's saved settings as the service menu writes it (`nvram`, play_mods.ps1 GameSettings; nvram.py),
    # and event mode, which the game never saves, is the byte the menu's EVENT MODE sets (the one reader patch)
    dict(id="eventmode", title="Game mode",
         help=txt("How a game is paid and timed, set as the arcade's operator sets it in the service menu (free play",
                "in COIN OPTIONS, then EVENT MODE): the same state, written for you. Original: your game's settings",
                "stay as they are. Credits: coins, as the arcade. Free play: the same game without credits. Event",
                "mode, the operator setting for shows and parties: free play with the clocks frozen (no time limit,",
                "no game over between songs); the arcade switches it off at every boot, this keeps it on. Credits",
                "and Free play are saved in your game's settings, so Original afterwards keeps the last one."),
         values=[dict(id="off", label="Original (your game's settings)"),
                 dict(id="credits", label="Credits", nvram=dict(freeplay=False)),
                 dict(id="freeplay", label="Free play", nvram=dict(freeplay=True)),
                 dict(id="on", label="Event mode (free play, clocks frozen)", nvram=dict(freeplay=True),
                      code=[("arkkdm.dll", "mods/game_rules/eventmode.py", ["--apply"])])]),
    dict(id="stages", title="Songs per game", lock_online=True,
         help=txt("How many songs a game gives before the title, whatever the service menu's STAGE",
                "setting holds. Original: the service menu's (Konami's is 2, 3 when the e-amusement",
                "extra stage applies). At most 4: the game keeps 4 stage records per player."),
         values=[dict(id="off", label="Original (the service menu's setting)")] +
                [dict(id=str(n), label="%d song%s" % (n, "" if n == 1 else "s"),
                      code=[("gamekdm.dll", "mods/game_rules/stages.py", ["--apply", str(n)])]) for n in range(1, 5)]),
    dict(id="resolution", title="Resolution",
         help=txt("The game renders at 1280x720. The others render natively: 3D, effects and 2D, the camera picture",
                "included; not an upscale of the 720p image. Only the modes your main screen offers are listed, since the game",
                "always runs in exclusive full screen (a higher one needs that monitor, or AMD VSR / NVIDIA DSR switched on)."),
         values=[dict(id="720", label="1280x720 (original)"),
                 # a mode like the others (2026-11-12): a 1366x768 notebook screen has no 1080p to open exclusive full screen in
                 dict(id="1080", label="1920x1080 native", code=RES_1080, data=["shaders_1080"], mode=[1920, 1080]),
                 # shown since 2026-10-26: composes every screen (run 2 of 2026-10-25, 95 captures, windowed + window_fit;
                 # run N), the fonts right at 1440p (seen by the user); a real 1440p display taken as working in theory
                 dict(id="1440", label="2560x1440 native", code=RES_1440, data=["shaders_1440"], mode=[2560, 1440]),
                 # no 2160p screen here: in the menu by the user's decision, 2026-11-02 (the same route as 1080p and 1440p)
                 dict(id="2160", label="3840x2160 native", code=RES_2160, data=["shaders_2160"], mode=[3840, 2160])]),
    # one value, so always on: with 2 GB the game ran out of address space on this PC with every option at
    # Konami's (log.txt of 2026-10-29: 1998 of 2048 MB used, an allocation returned NULL in libavs; MOD_AUDIT §0)
    dict(id="laa", title="Memory limit",
         help=txt("Lets the 32-bit game use 4 GB of address space instead of 2: with 2 GB it runs out",
                "of memory on a modern PC and crashes. Set on the launcher's copy of spice.exe, never on yours."),
         values=[dict(id="on", label="4 GB", laa=True)]),
    dict(id="refresh", title="Frame rate",
         help=txt("Vsync is always on: the game never draws more frames than your monitor can show, and the songs run on real",
                  "time, so they stay in sync at any frame rate. What each PC does depends on its monitor and on Windows, so if one",
                  "choice does not give you what it says, try another. Before playing, close Task Manager and anything set to stay",
                  "on top, on any screen: Windows then has to compose the screen, and frames get lost. You never need to change your",
                  "monitor's Hz."),
         values=[dict(id="original", label="Original: what Konami's game asks for", help=txt(
                     "Nothing changed: the game asks for 60 Hz. It may run at 60 fps or faster, depending on the PC; above 60 the song select runs fast.",
                     "If you want more frames and stay at 60, choose Unlimited.")),
                 # menu_speed: played by the user 2026-11-10 (trace-20261110-232334, ~94-138 fps): "everything perfect"
                 dict(id="max", label="Unlimited: up to your monitor's maximum", env={"KDM_REFRESH": "max"},
                      code=[("gamekdm.dll", "mods/picture/menu_speed.py", ["--apply"])], help=txt(
                     "Asks for your monitor's highest refresh rate: as many frames as the PC can draw, up to that.",
                     "The song and difficulty select keep the cabinet's speed (Konami's step once per frame, so above 60",
                     "they run faster). If the picture jumps because the PC cannot keep up, or the PC gets hot, choose Limit to 60.")),
                 dict(id="cap60", label="Limit to 60 fps", env={"KDM_FPSCAP": "60"}, help=txt(
                     "Never more than 60, whatever the PC could do: less heat and more power left over.",
                     "Stability over frames: for when Unlimited and the webcam sensor together give you trouble, and for notebooks."))]),
    dict(id="smaa", title="Anti-aliasing",
         help="Smooths the jagged edges of the 3D (SMAA, about 1.4 ms per frame).",
         values=[dict(id="off", label="Off (original)"), dict(id="on", label="SMAA", env={"KDM_SMAA": "1"})]),
    dict(id="aniso", title="Texture filtering",
         help="Keeps floors and walls sharp at a glancing angle (anisotropic x16, about 0.4 ms).",
         values=[dict(id="off", label="Original"), dict(id="on", label="Anisotropic x16", env={"KDM_ANISO": "16"})]),
    dict(id="workers", title="Render threads",
         help=txt("The PC build prepares each frame on ONE worker thread. This sizes the pool for",
                "your CPU at boot (CPUs - 2, between 1 and 4): smoother songs on a fast monitor."),
         values=[dict(id="off", label="Original (1 thread)"),
                 dict(id="auto", label="Sized to the CPU", code=[("gamekdm.dll", "mods/support/workers.py", ["--apply", "auto"])])]),
    dict(id="demo_master", title="Attract demo: difficulty",
         help="The demo the cabinet plays while idle. Original: standard charts.",
         values=[dict(id="off", label="Original"),
                 dict(id="on", label="Master charts", code=[("gamekdm.dll", "mods/attract_demo/demo.py", ["--apply", "--part", "master"])])]),
    dict(id="demo_songs", title="Attract demo: length",
         help="Original: each demo song stops after 30 seconds.",
         values=[dict(id="off", label="Original (30 s)"),
                 dict(id="on", label="Whole songs", code=[("gamekdm.dll", "mods/attract_demo/demo.py", ["--apply", "--part", "songs"])])]),
    dict(id="demo_shuffle", title="Attract demo: song order",
         help="Original: two hand-picked playlists (50 songs).",
         values=[dict(id="off", label="Original"),
                 dict(id="on", label="Every song, shuffled, none twice per round",
                      code=[("gamekdm.dll", "mods/attract_demo/demo.py", ["--apply", "--part", "shuffle"])])]),
    # no performance option: the original demo never misses on master when nothing stalls the game (the user,
    # 2026-10-30); the misses came from the probe's capture stutter (MOD_AUDIT §0)
    dict(id="demo_hud", title="Attract demo: score display",
         help="Shows the SCORE bar and the COMBO during the demo, as in real play.",
         values=[dict(id="off", label="Original"),
                 # verified 2026-10-31 with the webcam sensor (trace-20261031-161931) and approved by the user
                 dict(id="on", label="Score and combo",
                      help="No camera picture in the demo (verified with a sensor connected).",
                      code=[("gamekdm.dll", "mods/attract_demo/demo.py", ["--apply", "--part", "hud"])])]),
    # in the menu for the user's first game on it (the user, 2026-10-31: the launcher plays with the Kinect or any
    # camera); verified so far without the game: the selftest in its wait loop and AIST++ (WEBCAM_SENSOR.md)
    dict(id="sensor", title="Body sensor",
         help=txt("What sees the dancer. The game was made for the Kinect v1. With a webcam (or any camera",
                  "Windows sees) the project's own sensor turns the picture into a Kinect skeleton: no app to",
                  "install or open, everything ships in mods/webcam. Calibrate camera... sets it up; Sensor preview... shows what the game will see."),
         values=[dict(id="kinect", label="Kinect (original)", help="Microsoft's Kinect runtime, as the game ships."),
                 dict(id="webcam", label="Webcam or any camera", sensor="webcam",
                      help=txt("The whole body must be in the picture, feet included, as with the Kinect. Calibrate camera... once",
                               "where you play (about a minute, nothing typed). Windows Studio Effects are turned off for the session",
                               "where the camera allows it."))]),
    dict(id="sensorload", title="Webcam sensor runs on",
         help=txt("Only with the webcam as Body sensor. Where its main network runs. The GPU ran the sensor better in every",
                  "test (faster, lower latency, and the CPU left to the game); on a PC where the GPU cannot run it, the sensor",
                  "falls back to the CPU by itself. The CPU by hand only to compare."),
         values=[dict(id="gpu", label="GPU (DirectML; the CPU if the GPU cannot run it)"), dict(id="cpu", label="CPU")]),
    dict(id="verbose", title="Diagnostic log",
         help=txt("To report a crash, a problem or how the webcam sensor did: the game, spice2x and every mod log what they do,",
                  "and when the game closes a report is saved in mods\\reports (your Windows user and PC names removed).",
                  "Send that zip back. Slower to start; leave it off to play."),
         values=[dict(id="off", label="Off"),
                 dict(id="on", label="Full log and report", args=["-avsverbose", "-loglevel", "all"],
                      env={"KDM_DIAG": "{mods}\\active\\d3d9diag.log"})]),
]


# The menu's order: every option in exactly one sector (checked in build()).
AUTO = "Support (switched on by the options that need it)"
SECTORS = [("Sensor", ["sensor", "sensorload"]),
           ("Content", ["language", "songs", "titles", "stealth"]),
           ("Game rules", ["eventmode", "stages"]),
           ("Picture", ["resolution", "refresh", "smaa", "aniso"]),
           # part of the options that need them, never a choice of their own (the user, 2026-10-27): not in the menu
           (AUTO, ["soundheap", "soundpath", "laa", "rankicon"]),
           ("Attract demo", ["demo_master", "demo_songs", "demo_shuffle", "demo_hud"]),
           ("Advanced", ["workers", "verbose"])]


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def run(tool: str, args: list[str]) -> None:
    r = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, tool), *args],
                       capture_output=True, text=True, check=False)
    if r.returncode:
        raise SystemExit("%s %s failed (exit %d):\n%s%s" % (tool, " ".join(args), r.returncode, r.stdout, r.stderr))


def originals() -> dict[str, bytes]:
    out = {}
    for name, (path, want) in SOURCES.items():
        b = Path(path).read_bytes()
        if want and not md5(b).startswith(want):
            raise SystemExit("%s is not the original (%s)" % (path, md5(b)))
        out[name] = b
    return out


def guarded() -> dict[str, str]:
    """MD5 of every game file a session could reach, for the launcher to check before and after
    each game: modules/ (copied), data/sound/ (hard-linked into mods/snd) and every data/ file a
    mods/data folder overlays (`arc/<name>_arc/...` overlays data/arc/<name>.arc)."""
    rels = {"modules/" + n for n in os.listdir(os.path.join(ROOT, "modules"))}
    rels |= {"data/sound/" + n for n in os.listdir(os.path.join(ROOT, "data", "sound"))}
    for d in os.listdir(os.path.join(MODS, "data")):
        if d.startswith("_"):   # _cache: LayeredFS's own merged copies
            continue
        for p, _, fs in os.walk(os.path.join(MODS, "data", d)):
            parts = Path(p).relative_to(Path(MODS, "data", d)).parts
            if len(parts) >= 2 and parts[1].endswith("_arc"):
                rels.add("data/%s/%s.arc" % (parts[0], parts[1][:-4]))
            elif "_arc" not in "".join(parts):
                rels |= {"data/" + "/".join((*parts, f)) for f in fs}
    rels = {r for r in rels if os.path.isfile(os.path.join(ROOT, r))}
    assert all(r.startswith(("modules/", "data/")) for r in rels) and len(rels) > 300, len(rels)
    return {r: md5(Path(ROOT, r).read_bytes()) for r in sorted(rels)}


def build(steps: list[tuple[str, str, list[str]]], orig: dict[str, bytes]) -> dict[str, bytes]:
    """Runs the patchers in order on copies of the originals; returns the files they changed."""
    with tempfile.TemporaryDirectory() as tmp:
        for name, b in orig.items():
            Path(tmp, name).write_bytes(b)
        for name, tool, args in steps:
            run(tool, [*args, "--dll", os.path.join(tmp, name)])
        files = {n: Path(tmp, n).read_bytes() for n in orig}
    return {n: b for n, b in files.items() if b != orig[n]}


def edits(orig: bytes, new: bytes) -> list[tuple[int, bytes, bytes]]:
    """Runs of changed bytes; runs closer than 8 bytes are merged (fewer, still exact, edits)."""
    assert len(orig) == len(new), "a patcher changed the file size; not expressible as edits"
    runs: list[list[int]] = []
    for i in (i for i in range(len(orig)) if orig[i] != new[i]):
        if runs and i - runs[-1][1] <= 8:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1])
    return [(a, orig[a:b], new[a:b]) for a, b in runs]


def apply_edits(orig: dict[str, bytes], patches: list[dict]) -> dict[str, bytes]:
    """What the launcher does: check every edit's original bytes, then write them all."""
    out = {n: bytearray(b) for n, b in orig.items()}
    for p in patches:
        f, off = out[p["dllName"]], p["offset"]
        old, new = bytes.fromhex(p["dataDisabled"]), bytes.fromhex(p["dataEnabled"])
        assert bytes(f[off:off + len(old)]) == old, "edit at %s+0x%x: original bytes differ" % (p["dllName"], off)
        f[off:off + len(new)] = new
    return {n: bytes(b) for n, b in out.items()}


def code_patches(orig: dict[str, bytes]) -> dict[str, list[dict]]:
    """value key -> its edits; with the two checks that make any combination safe."""
    found, spans = {}, {}
    for o in OPTIONS:
        for v in o["values"]:
            if not v.get("code"):
                continue
            key = "%s.%s" % (o["id"], v["id"])
            changed = build(v["code"], orig)
            found[key] = [dict(dllName=n, offset=a, dataDisabled=x.hex(), dataEnabled=y.hex())
                          for n, b in sorted(changed.items()) for a, x, y in edits(orig[n], b)]
            spans[key] = {(p["dllName"], p["offset"] + i) for p in found[key] for i in range(len(p["dataDisabled"]) // 2)}
            print("  %-24s %4d edits  %s" % (key, len(found[key]), ", ".join(sorted(changed))))
    keys = sorted(found)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if a.split(".")[0] != b.split(".")[0] and spans[a] & spans[b]:
                raise SystemExit("%s and %s edit the same bytes; they cannot be combined" % (a, b))
    # every option at once (the first code value of each), against the patchers run in sequence
    full = [(o["id"], v) for o in OPTIONS for v in o["values"][1:2] if v.get("code")]
    seq = build([s for _, v in full for s in v["code"]], orig)
    composed = apply_edits(orig, [p for oid, v in full for p in found["%s.%s" % (oid, v["id"])]])
    for n, b in seq.items():
        if md5(composed[n]) != md5(b):
            raise SystemExit("composition check failed on %s: edits %s, patchers in sequence %s" % (n, md5(composed[n]), md5(b)))
    print("  composition: every option at once == the patchers in sequence (%s)" %
          ", ".join("%s %s" % (n, md5(b)[:8]) for n, b in sorted(seq.items())))
    return found


def entry(arc: str, name: str) -> bytes:
    return next(e["data"] for e in read_arc(arc) if e["name"] == name)


def put(folder: str, rel: str, data: bytes) -> None:
    p = os.path.join(MODS, "data", folder, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    Path(p).write_bytes(data)


def rank_icon() -> None:
    """rank_icon: difficulty_menu_v0.ifs with Konami's icon_ranking added (content/rank_icon.py)."""
    shutil.rmtree(os.path.join(MODS, "data", "rank_icon"), ignore_errors=True)
    run("mods/content/rank_icon.py", ["--ifs", os.path.join(MODS, "data", "rank_icon")])


def shaders(width: int, folder: str) -> None:
    out = os.path.join(MODS, "data", folder)
    shutil.rmtree(out, ignore_errors=True)
    with tempfile.TemporaryDirectory() as tmp:
        run("mods/picture/resolution/shaders.py", ["--apply", "--out", tmp, "--width", str(width)])
        for f in sorted(os.listdir(tmp)):
            a = {e["name"]: e["data"] for e in read_arc(os.path.join(ROOT, "data", "arc", f))}
            for e in read_arc(os.path.join(tmp, f)):
                if a[e["name"]] != e["data"]:
                    put(folder, "arc/%s_arc/%s" % (f[:-4], e["name"]), e["data"])


def eng_titles() -> None:
    """eng_titles_<song list>: that list's song_params with the English titles (titles.py)."""
    sp = "data/song/song_params.plist"
    lists = {"original": entry(os.path.join(ORIG, "data/arc/resource_lists.arc"), sp)}
    lists["all"] = Path(MODS, "data", "songlist_yesterday", "arc", "resource_lists_arc", sp).read_bytes()
    kbf = titles.font_fix(entry(os.path.join(ROOT, "data/arc/2d_font_ui.arc"), titles.FONT_ENTRY))
    for name, plist in lists.items():
        new = titles.retitle(plist)
        titles.check(plist, new)
        shutil.rmtree(os.path.join(MODS, "data", "eng_titles_" + name), ignore_errors=True)
        put("eng_titles_" + name, "arc/resource_lists_arc/" + sp, new)
        put("eng_titles_" + name, "arc/2d_font_ui_arc/" + titles.FONT_ENTRY, kbf)


def conf() -> None:
    """mods/conf: Konami's two configs with what the pack needs apart (spice2x -v, -e): saves here, the soft id."""
    d = os.path.join(MODS, "conf")
    os.makedirs(d, exist_ok=True)
    avs = Path(ROOT, "prop", "avs-config.xml").read_bytes()
    for name in (b"nvram", b"raw"):
        old = b".\\conf\\" + name
        assert avs.count(old) == 1, old
        avs = avs.replace(old, b".\\mods\\conf\\" + name)
    Path(d, "avs-config.xml").write_bytes(avs)
    ea3 = Path(ROOT, "prop", "eamuse-config.xml").read_bytes()
    assert b"<soft>" not in ea3, "prop/eamuse-config.xml is not Konami's"
    root_end = ea3.index(b">\r\n", ea3.index(b"<ea3")) + 3
    Path(d, "eamuse-config.xml").write_bytes(ea3[:root_end] + SOFT + ea3[root_end:])


def check_content() -> None:
    for f, n in CONTENT.items():
        got = sum(len(fs) for _, _, fs in os.walk(os.path.join(MODS, "data", f)))
        assert got == n, "mods/data/%s: %d files, %d expected (it is source: restore it from the backup)" % (f, got, n)
    sp = "data/song/song_params.plist"
    # the list players get, without yest: a stored reference went stale on the other PC (2026-11-16, phases of 11-12)
    shipped = Path(MODS, "data", "songlist_yesterday", "arc", "resource_lists_arc", sp).read_bytes()
    check_songlist(entry(os.path.join(ROOT, "data/arc/resource_lists.arc"), sp), drop_yest(shipped))


def check_songlist(orig: bytes, mod: bytes) -> None:
    """Restored = Konami's table with ONLY field 9 of the 22 locked songs and rena's chart name changed: each takes the
    phase of its song-select tab (unlock_songs.target: 1 POPULAR, 0 KONAMI SONGS)."""
    assert len(orig) == len(mod), "song_params without yest is not the original's size"
    n = struct.unpack(">I", orig[8:12])[0]
    unlocked = 0
    for r in range(n):
        a = struct.unpack(">32I", orig[16 + r * 128:16 + (r + 1) * 128])
        b = struct.unpack(">32I", mod[16 + r * 128:16 + (r + 1) * 128])
        diff = [i for i in range(32) if a[i] != b[i]]
        assert diff in ([], [9]), "record %d: fields %s changed" % (r, diff)
        code = mod[b[0]:mod.index(b"\x00", b[0])].decode()
        unlocked += diff == [9] and a[9] == 999 and b[9] == song_params.unlocked_phase(code)
    assert unlocked == 22, unlocked
    sb = 16 + n * 128
    tail = [i for i in range(sb, len(orig)) if orig[i] != mod[i]]
    assert len(tail) == 1 and orig[tail[0] - 1:tail[0] + 6] == b"rana021" \
        and mod[tail[0] - 1:tail[0] + 6] == b"rena021", "string table: more than the rena typo changed"


def main(argv: list[str]) -> int:
    orig = originals()
    print("code options, measured on Konami's originals:")
    patches = code_patches(orig)
    if "--check" in argv:
        return 0
    check_content()
    eng_titles()
    rank_icon()
    shaders(1920, "shaders_1080")
    shaders(2560, "shaders_1440")
    shaders(3840, "shaders_2160")
    for dst, src in BINS.items():
        shutil.copy2(src, os.path.join(MODS, "bin", dst))
    for f in (os.path.join(TOOLS, "mods", "play_mods.ps1"), os.path.join(TOOLS, "mods", "update.ps1"), os.path.join(ROOT, "1 - Play.bat")):   # PowerShell 5.1 and cmd read them in each PC's code page
        assert Path(f).read_bytes().isascii(), f"{f} must be ASCII: players run it on Windows in any language"
    shutil.copy2(os.path.join(TOOLS, "mods", "play_mods.ps1"), MODS)
    shutil.copy2(os.path.join(TOOLS, "mods", "update.ps1"), MODS)
    shutil.copy2(os.path.join(TOOLS, "mods", "support", "pack_readme.txt"), os.path.join(ROOT, "1 - Play (README).txt"))   # beside the launcher (the user, 2026-11-11)
    conf()
    sector = {oid: name for name, ids in SECTORS for oid in ids}
    assert sorted(sector) == sorted(o["id"] for o in OPTIONS) and len(sector) == sum(len(i) for _, i in SECTORS), "SECTORS"
    order = [oid for _, ids in SECTORS for oid in ids]
    originals_md5 = guarded()
    assert all(originals_md5["modules/" + n] == md5(b) for n, b in orig.items()), "modules/ is not Konami's"
    cat = dict(originals=originals_md5,
               options=[dict(o, sector=sector[o["id"]], auto=sector[o["id"]] == AUTO,
                             values=[dict({k: x for k, x in v.items() if k != "code"},
                                          patches=patches.get("%s.%s" % (o["id"], v["id"]), []))
                                     for v in o["values"]])
                        for o in sorted(OPTIONS, key=lambda o: order.index(o["id"]))])
    with open(os.path.join(MODS, "catalog.json"), "w", encoding="utf-8") as f:
        json.dump(cat, f, indent=1)
    for d in sorted(os.listdir(os.path.join(MODS, "data"))):
        files = [os.path.join(p, x) for p, _, fs in os.walk(os.path.join(MODS, "data", d)) for x in fs]
        print("  data/%-20s %5d files %8.1f MB" % (d, len(files), sum(map(os.path.getsize, files)) / 2 ** 20))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
