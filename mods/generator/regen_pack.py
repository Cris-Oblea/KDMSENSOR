r"""
The players' pack, split in two: what a PC makes from its own Konami base, and what ships fixed (T116, MOD_AUDIT.md §9c).

    python _tools/mods/regen_pack.py --fixed DIR     writes the FIXED part (what no Konami base can make) from mods/ into DIR
    python _tools/mods/regen_pack.py --check DIR [--scratch S]
                                                     makes the GENERATED part into S (default _tools/out/regen) from Konami's
                                                     files + the fixed part in DIR, and compares every file of mods/data and
                                                     mods/conf with the shipped one by SHA-256; exit 1 on any difference
    python _tools/mods/regen_pack.py --expect OUT.json DIR     writes the release's generated.json (the SHA-256 of every generated file)
    python regen_pack.py --make generated.json                 on a PLAYER's PC (the release's mods/generator, its own Python): the fixed
                                                     part already extracted into mods/, makes the rest from the game's files into mods/
                                                     only if every file equals generated.json (T113, MOD_AUDIT.md section 9d)

The base is the game folder (ROOT): Konami's, proven by verify_build.py part 1. Generated, in Python with the standard library only:
stealth (the master chart copied over each stealth chart), the song list (22 unlocks, the rena typo, YESTERDAY's record from its seed),
pani_yest.arc (two animations of the base's own song_yest arcs), the English titles, the shaders of each resolution, the two configs,
and the three preview banks (waves of the base's own preview banks and of the seed, laid out by the shipped header).
"""
import hashlib
import json
import os
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))  # _tools
from formats import song_params
from formats.arc_lz import build_arc, read_arc, read_arc_filtered
from mods import build_mods
from mods.content.songs import unlock_songs
from paths import ROOT

MODS = os.path.join(ROOT, "mods")
BANKS = ("bgm_thumb", "bgm_thumb2", "bgm_thumb3")
# shipped files no Konami base can make: relative to mods/ (the folder tree is kept, so the archive extracts into mods/)
FIXED_COPY = [f"data/banks_restored/sound/{c}.xwb" for c in (
              "brav", "circ", "cowo", "cybe", "grre", "iron", "joli", "kind", "lanj", "loma",
              "maru", "merr", "mick", "noff", "odop", "ponp", "rena", "show", "swet", "zenr")] + [
    "data/yesterday/sound/yest.xsb", "data/yesterday/sound/yest.xwb", "data/yesterday/bm2d/jk_yest_v0.ifs"] + [
    f"data/previews/sound/{b}.xsb" for b in BANKS]
PLIST = "data/songlist_yesterday/arc/resource_lists_arc/data/song/song_params.plist"
SEED_AT = "fixed/previews_seed.bin"


def parse_xwb(d: bytes):
    """formats.adpcm.parse_xwb, copied: that module imports numpy at the top and the player's PC needs only the standard library."""
    segs = [struct.unpack("<2I", d[12 + i * 8:20 + i * 8]) for i in range(5)]
    cnt, = struct.unpack("<I", d[segs[0][0] + 4:segs[0][0] + 8])
    return d, segs, [list(struct.unpack("<6I", d[segs[1][0] + i * 24:segs[1][0] + (i + 1) * 24])) for i in range(cnt)]


def wave_bytes(d: bytes, segs, ent) -> bytes:
    return d[segs[4][0] + ent[2]:segs[4][0] + ent[2] + ent[3]]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def put(root: str, rel: str, data: bytes) -> None:
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    Path(p).write_bytes(data)


def base_waves() -> dict[str, list[bytes]]:
    """Konami's own preview waves, per bank, in the bank's order."""
    out = {}
    for b in BANKS:
        d, segs, ents = parse_xwb(Path(ROOT, "data", "sound", b + ".xwb").read_bytes())
        out[b] = [bytes(wave_bytes(d, segs, e)) for e in ents]
    return out


# ------------------------------------------------------------------------------------ the fixed part
def make_fixed(dst: str) -> None:
    for rel in FIXED_COPY:
        put(dst, rel, Path(MODS, rel).read_bytes())
    put(dst, "fixed/yest_seed.json", json.dumps(unlock_songs.yest_seed(Path(MODS, PLIST).read_bytes()), indent=1).encode())
    have = {sha(w): (b, i) for b, ws in base_waves().items() for i, w in enumerate(ws)}
    seed, recipe = bytearray(), {}
    for b in BANKS:
        d, segs, ents = parse_xwb(Path(MODS, "data/previews/sound", b + ".xwb").read_bytes())
        steps = []
        for e in ents:
            w = bytes(wave_bytes(d, segs, e))
            if sha(w) in have:
                steps.append(["base", *have[sha(w)]])
            else:
                steps.append(["seed", len(seed), len(w)])
                seed += w
        put(dst, f"fixed/{b}.header", d[:segs[4][0]])
        recipe[b] = steps
    put(dst, "fixed/previews_recipe.json", json.dumps(recipe).encode())
    put(dst, SEED_AT, bytes(seed))


# ------------------------------------------------------------------------------- the generated part
def gen_stealth(out: str) -> None:
    """Every stealth chart becomes a copy of the master's (stealth.py): one loose file per song container."""
    for p in sorted(Path(ROOT, "data", "arc").glob("song_*.arc")):
        base = p.name[5:-4]
        if base[:4] in ("howt", "tuto"):
            continue
        ents = {os.path.basename(e["name"])[:-4]: e for e in read_arc_filtered(str(p), lambda n: n.endswith(("_sl.dsq", "_m.dsq")))}
        sl, m = ents.get(base + "_sl"), ents.get(base + "_m")
        if sl and m and sl["data"] != m["data"]:
            put(out, f"data/stealth/arc/song_{base}_arc/{sl['name']}", m["data"])


def gen_songlist(out: str, fixed: str) -> bytes:
    base = next(e for e in read_arc(os.path.join(ROOT, "data/arc/resource_lists.arc")) if e["name"].endswith("song_params.plist"))["data"]
    p = bytearray(base)
    n = struct.unpack(">I", p[8:12])[0]
    for r in range(n):
        f = struct.unpack(">32I", p[16 + r * 128:16 + (r + 1) * 128])
        if f[9] == unlock_songs.LOCKED:
            struct.pack_into(">I", p, 16 + r * 128 + 36, song_params.unlocked_phase(p[f[0]:p.index(b"\0", f[0])].decode()))
    assert p.count(b"rana021") == 1
    k = p.find(b"rana021")
    p[k:k + 7] = b"rena021"
    seed = json.loads(Path(fixed, "fixed/yest_seed.json").read_bytes())
    new, _ = unlock_songs.add_yest(bytes(p), seed)
    assert new
    put(out, PLIST, new)
    return new


def gen_pani(out: str) -> None:
    """pani_yest.arc: the two dancers' YESTERDAY animations, which the base keeps inside its song arcs, stored raw."""
    names = [("song_yest011", "data/chara/pl_galf000/pl_galf000_yest011_exec.anm"), ("song_yest021", "data/chara/pl_galm000/pl_galm000_yest011_exec.anm")]
    ents = [{"name": nm, "data": next(e["data"] for e in read_arc(os.path.join(ROOT, "data/arc", a + ".arc")) if e["name"] == nm)} for a, nm in names]
    put(out, "data/yesterday/arc/pani_yest.arc", build_arc(ents, compress=False))


def gen_previews(out: str, fixed: str) -> None:
    """Each bank: the shipped header, then every wave from the base's own bank or from the seed, at the offsets the header gives."""
    recipe = json.loads(Path(fixed, "fixed/previews_recipe.json").read_bytes())
    seed = Path(fixed, SEED_AT).read_bytes()
    base = base_waves()
    for b in BANKS:
        head = Path(fixed, f"fixed/{b}.header").read_bytes()
        _, segs, ents = parse_xwb(head + b"\0" * 16)
        data = bytearray(segs[4][1])
        assert len(ents) == len(recipe[b])
        for e, step in zip(ents, recipe[b], strict=True):
            w = base[step[1]][step[2]] if step[0] == "base" else seed[step[1]:step[1] + step[2]]
            assert len(w) == e[3], (b, step)
            data[e[2]:e[2] + len(w)] = w
        put(out, f"data/previews/sound/{b}.xwb", head + bytes(data))


def generate(scratch: str, fixed: str) -> None:
    shutil.rmtree(scratch, ignore_errors=True)
    mods = os.path.join(scratch, "mods")
    out = mods
    gen_stealth(out)
    gen_songlist(out, fixed)
    gen_pani(out)
    gen_previews(out, fixed)
    build_mods.MODS = mods   # build_mods writes under MODS: the scratch tree
    build_mods.eng_titles()
    for width, folder in ((1920, "shaders_1080"), (2560, "shaders_1440"), (3840, "shaders_2160")):
        build_mods.shaders(width, folder)
    build_mods.conf()


def compare(scratch: str, fixed: str) -> int:
    """Generated + fixed against the shipped mods/data and mods/conf (the two configs), file by file."""
    mods = os.path.join(scratch, "mods")
    for rel in FIXED_COPY:
        put(mods, rel, Path(fixed, rel).read_bytes())
    shipped = {}
    for top in ("data", "conf"):
        for p, _, fs in os.walk(os.path.join(MODS, top)):
            for f in fs:
                rel = os.path.relpath(os.path.join(p, f), MODS).replace("\\", "/")
                if rel.startswith("data/_cache") or (top == "conf" and f not in ("avs-config.xml", "eamuse-config.xml")):
                    continue
                shipped[rel] = os.path.join(p, f)
    made = {os.path.relpath(os.path.join(p, f), mods).replace("\\", "/"): os.path.join(p, f)
            for p, _, fs in os.walk(mods) for f in fs}
    bad = [r for r in sorted(shipped.keys() | made.keys())
           if r not in shipped or r not in made or sha(Path(shipped[r]).read_bytes()) != sha(Path(made[r]).read_bytes())]
    print(f"{len(shipped)} shipped files, {len(made)} made; {len(shipped) - len(bad)} equal by SHA-256")
    for r in bad[:20]:
        print("  DIFFERENT:", r, "(not made)" if r not in made else "(not shipped)" if r not in shipped else "")
    return 1 if bad else 0


def made_hashes(mods: str) -> dict[str, str]:
    """SHA-256 of every file generate() left under `mods` (data/ and the two configs), keyed by path relative to mods/."""
    return {os.path.relpath(os.path.join(p, f), mods).replace("\\", "/"): sha(Path(p, f).read_bytes())
            for p, _, fs in os.walk(mods) for f in fs}


def expect(dst: str, scratch: str, fixed: str) -> None:
    """Writes the release's generated.json: what a player's PC must make, file by file (the launcher's check on a foreign base)."""
    generate(scratch, fixed)
    Path(dst).write_text(json.dumps(made_hashes(os.path.join(scratch, "mods")), indent=0, sort_keys=True))


def make(fixed: str, expected: str) -> int:
    """The player's step: fixed part already in `fixed` (the player's mods/), makes the rest from the game's files, checks every
    file against generated.json, and only then puts them in mods/ (a different file means the base is not Konami's: nothing is written)."""
    want = json.loads(Path(expected).read_text())
    scratch = os.path.join(fixed, "_gen")
    try:
        generate(scratch, fixed)
        made = made_hashes(os.path.join(scratch, "mods"))
        bad = [r for r in sorted(want.keys() | made.keys()) if want.get(r) != made.get(r)]
        if bad:
            print(f"your game files are not Konami's unmodified August 2016 build (KDM-001-2016080100): {len(bad)} of {len(want)} mod files came out different, e.g. {bad[:2]}. Nothing was written.")
            return 1
        state = Path(fixed, "generated.state")
        old = json.loads(state.read_text()) if state.exists() else []
        for r in old:
            if r not in made and os.path.isfile(os.path.join(fixed, r)):
                os.remove(os.path.join(fixed, r))   # a file an earlier version made and this one does not
        for r in made:
            dst = os.path.join(fixed, r)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(scratch, "mods", r), dst + ".new")
            os.replace(dst + ".new", dst)
        print(f"made {len(made)} files, every one equal to the shipped SHA-256")
        state.write_text(json.dumps(sorted(made)))
        return 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main(argv: list[str]) -> int:
    if "--expect" in argv:   # --expect OUT.json FIXED_DIR
        expect(argv[argv.index("--expect") + 1], os.path.join(ROOT, "_tools", "out", "regen"), argv[argv.index("--expect") + 2])
        return 0
    if "--make" in argv:   # --make EXPECTED.json (fixed part and output: ROOT/mods)
        return make(MODS, argv[argv.index("--make") + 1])
    if "--fixed" in argv:
        dst = argv[argv.index("--fixed") + 1]
        shutil.rmtree(dst, ignore_errors=True)
        make_fixed(dst)
        n = sum(len(fs) for _, _, fs in os.walk(dst))
        print(f"fixed part: {n} files, {sum(os.path.getsize(os.path.join(p, f)) for p, _, fs in os.walk(dst) for f in fs) / 2**20:.1f} MB in {dst}")
        return 0
    if "--check" in argv:
        fixed = argv[argv.index("--check") + 1]
        scratch = argv[argv.index("--scratch") + 1] if "--scratch" in argv else os.path.join(ROOT, "_tools", "out", "regen")
        generate(scratch, fixed)
        return compare(scratch, fixed)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
