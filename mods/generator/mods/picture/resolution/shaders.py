r"""
Rescales the screen sizes BAKED INTO compiled shaders from 1280x720 to the target screen.

THE PROBLEM (history/STATUS_TO_2026-10-26.md 6 A5). Some pixel shaders turn the screen pixel into a texture
coordinate with literals written into the bytecode, not uploaded as constants:

    def c0, 0.000781250012, 0.00138888892, 0.03125, 0.5     ; 1/1280, 1/720
    mul r1, c0.xyzz, vPos.xyxy                               ; uv = pixel * (1/1280, 1/720)
    texld r0, r0, s10                                        ; the scene copy

At 1080p vPos reaches 1920, the uv 1.5, the sampler wraps: the hit ring and the distortion
at the feet show a displaced copy of the scene (the "echo"). Disassembled with the Windows
SDK's `fxc /dumpbin`.

TWO KINDS OF USE, both rescaled (read shader by shader before listing it here):
  * screen uv from vPos: mdl_ch_distortion, mdl_bg_distortion, mdl_*_spot_light_beam,
    pkt_smoke;
  * texel offsets of surfaces that already scale (full screen, or Gesture's quarter):
    filter_depth_down_scale, filter_depth_of_field (x3), filter_gesture.
NOT touched: gs_screencommand_natal (1/320, 1/240: the Kinect camera, not the screen) and
app_gradate_velocitymap (multiples of 1/320 and 1/180 on a surface not identified yet).

WHAT IS REWRITTEN: only the four floats of `def` instructions (token 0x05000051) inside
those shaders, and only a value that is n/1280, n/720, n/640, n/360, n/320 or n/180 with
n a multiple of 0.5 up to 16; it becomes n over the same base times target/1280, computed
exactly. 0.5, 1, 2, 20 and the 0.03125 noise tiling are left as they are.

The containers are rebuilt with arc_lz.build_arc_preserving: every untouched block byte for
byte, the changed ones stored uncompressed (the game rejects our recompression).

USAGE
    python _tools/mods/picture/resolution/shaders.py --show                 every change it would make
    python _tools/mods/picture/resolution/shaders.py --apply --out DIR [--width 1920]
                                    the rebuilt .arc files into DIR (build_mods.py takes their
                                    changed entries); the game's own containers are never written
    python _tools/mods/picture/resolution/shaders.py --selftest
"""
import os
import struct
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../..")))  # _tools: paths, and the packages
from formats.arc_lz import build_arc_preserving, read_arc_filtered
from paths import ROOT

ARCS = ["model_shader", "model_shader_release", "shader", "system_shader", "filter"]
SHADERS = ["mdl_ch_distortion", "mdl_bg_distortion", "mdl_ch_spot_light_beam",
           "mdl_bg_spot_light_beam", "pkt_smoke", "filter_depth_down_scale",
           "filter_depth_of_field", "filter_depth_of_field_ATI",
           "filter_depth_of_field_nVidia", "filter_gesture"]
DEF = 0x05000051
BASES = (1280, 720, 640, 360, 320, 180)
NATIVE_W = 1280


def arc_path(name: str) -> str:
    return os.path.join(ROOT, "data", "arc", name + ".arc")


def rescale(v: float, ratio: float) -> float | None:
    """The 1080p value of a 720p screen-size literal, or None if v is not one."""
    if v == 0 or abs(v) >= 0.05 or abs(abs(v) - 0.03125) < 1e-9:
        return None
    def f32(x: float) -> float:
        return struct.unpack("<f", struct.pack("<f", x))[0]
    for base in BASES:
        n = round(v * base * 2) / 2
        # exact float32 equality: a near miss (DoF's 0.0104160551 ~ 7.5/720) is not a size
        if 0 < abs(n) <= 16 and f32(n / base) == v:
            return f32(n / (base * ratio))
    return None


def patch_blob(d: bytes, ratio: float) -> tuple[bytes, list[str]]:
    """Every DEF in every bytecode stream of one .gsp; returns (new bytes, changes)."""
    out = bytearray(d)
    changes = list[str]()
    for i in range(0, len(d) - 24, 4):
        if struct.unpack_from("<I", d, i)[0] != DEF:
            continue
        reg = struct.unpack_from("<I", d, i + 4)[0] & 0x7FF
        for k in range(4):
            v = struct.unpack_from("<f", d, i + 8 + 4 * k)[0]
            nv = rescale(v, ratio)
            if nv is not None:
                struct.pack_into("<f", out, i + 8 + 4 * k, nv)
                changes.append("c%d.%s %.9g -> %.9g" % (reg, "xyzw"[k], v, nv))
    return bytes(out), changes


def source(a: str) -> str:
    """The ORIGINAL container: the installed one, which nothing writes any more (MOD_AUDIT.md)."""
    return arc_path(a)


def plan(ratio: float) -> dict[str, dict[str, tuple[bytes, list[str]]]]:
    """{arc: {shader file: (new bytes, changes)}}, always from the original containers."""
    res: dict[str, dict[str, tuple[bytes, list[str]]]] = {}
    for a in ARCS:
        ents = read_arc_filtered(source(a), lambda n: n.split("/")[-1][:-4] in SHADERS)
        res[a] = {}
        for e in ents:
            new, ch = patch_blob(e["data"], ratio)
            if ch:
                res[a][e["name"].split("/")[-1]] = (new, ch)
    return res


def show(ratio: float) -> int:
    total = 0
    for a, files in plan(ratio).items():
        for f, (_, ch) in files.items():
            total += len(ch)
            print("%-22s %-34s %3d  %s" % (a, f, len(ch), sorted(set(ch))[:4]))
    print("total literals: %d" % total)
    return total


def apply_patch(width: int, out: str) -> int:
    ratio = width / NATIVE_W
    os.makedirs(out, exist_ok=True)
    bad = 0
    for a, files in plan(ratio).items():
        if not files:
            continue
        data = build_arc_preserving(source(a), {f: nb for f, (nb, _) in files.items()})
        dest = os.path.join(out, a + ".arc")
        with open(dest, "wb") as fh:
            fh.write(data)
        got = {e["name"].split("/")[-1]: e["data"]
               for e in read_arc_filtered(dest, lambda n, fs=files: n.split("/")[-1] in fs)}
        bad += sum(got.get(f) != nb for f, (nb, _) in files.items())
        print("%s: %d shaders rewritten" % (a, len(files)))
    print("read back: %s" % ("every rewritten shader is what was planned" if not bad
                             else "%d MISMATCHES" % bad))
    return 1 if bad else 0


def selftest() -> int:
    def f32(x: float) -> float:
        return struct.unpack("<f", struct.pack("<f", x))[0]
    for old, new in ((1 / 1280, 1 / 1920), (1 / 720, 1 / 1080), (0.5 / 1280, 0.5 / 1920),
                     (-2 / 720, -2 / 1080), (7 / 180, 7 / 270)):
        assert rescale(f32(old), 1.5) == f32(new), old
    for keep in (0.0, 0.5, 1.0, 2.0, 20.0, 0.03125, -0.707106769, 8191.875,
                 0.0104160551, 0.00585903134):      # DoF constants that only look like sizes
        assert rescale(keep, 1.5) is None, keep
    print("selftest OK")
    return 0


def main(argv: list[str]) -> int:
    width = int(argv[argv.index("--width") + 1]) if "--width" in argv else 1920
    if "--selftest" in argv:
        return selftest()
    if "--apply" in argv:
        if "--out" not in argv:
            print("--apply needs --out DIR: the game's shader containers are never written (MOD_AUDIT.md)")
            return 1
        return apply_patch(width, argv[argv.index("--out") + 1])
    show(width / NATIVE_W)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
