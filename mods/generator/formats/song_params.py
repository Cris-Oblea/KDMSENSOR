"""The song table: data/song/song_params.plist, inside data/arc/resource_lists.arc.

    from formats.song_params import load, cstr, as_float, TITLE

Layout (big-endian): u32 record count at 8, records from 16, 128 bytes each =
32 u32 fields. A field that holds text is an offset to a NUL-terminated string
in the same plist. The fields this project knows, named once here: until
2026-10-19 five scripts each parsed the table on their own and named different
fields, so a meaning learned in one never reached the others.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))  # _tools: paths, and the packages
from paths import ROOT

ARC = os.path.join(ROOT, "data", "arc", "resource_lists.arc")

CODE = 0        # str: the 4-letter song code
CHART_A = 1     # str: chart names
CHART_B = 2
FLAGS = 8       # four bytes the loader reads one by one (GAMEPLAY.md 6): the last, 0 1 2, doubles the note visuals' unit when above 0
PHASE = 9     # unlock phase: 0, 1, 2, 3, 5; 100 = the hidden attract demo (howt); 999 = locked
DUR_MS = 10     # declared duration, ms
TITLE = 13      # str: the title, lines separated by '\n'
ARTIST = 14     # str: the artist
START = 20      # f32 bits: preview start
NAME_KEY = 27   # str: what the NAME tab sorts by, byte by byte (Konami's: the title's reading in katakana; ARCHITECTURE.md 10.1)
VARIANT = 21
ORDER = 22

# The PHASE also files the song in song select's tabs (the song select's list builder; MOD_AUDIT.md section 9): 1 3 7 9 under
# POPULAR, any other under KONAMI SONGS; by row, 0x46 (ckpp) under both, 0x50 (rint) and 0x64 (hall) under KONAMI SONGS. The
# tabs are ALL, NEWEST, NAME, LEVEL, POPULAR, KONAMI SONGS, two tabs nothing files songs under, UNPLAYED, CHALLENGE, KAC (data/bm2d/sort_lang_*).
POPULAR_PHASES = (1, 3, 7, 9)
# The songs Konami's August build locks (phase 999) that are licensed (RemyWiki AC_DanEvo), and YESTERDAY ("license YESTERDAY").
LICENSED_LOCKED = {"iron", "irny", "rena", "reni", "maru", "brav", "ponp", "merr", "noff", "zenr", "lanj", "mick", "circ", "odop",
                   "cybe", "swet", "cowo", "grre", "loma", "joli", "show", "yest"}


def unlocked_phase(code: str) -> int:
    """An always-shown phase of the song's own tab: 1 for a licensed song (as Konami's October 2015 build had them), 0 for Konami's."""
    return 1 if code in LICENSED_LOCKED else 0


def tab(row: int, phase: int) -> str:
    """POPULAR, KONAMI SONGS or both, by the game's rule above."""
    if row == 0x46:
        return "both"
    if row in (0x50, 0x64):
        return "KONAMI SONGS"
    return "POPULAR" if phase in POPULAR_PHASES else "KONAMI SONGS"


def cstr(d: bytes | bytearray, off: int) -> str:
    return d[off:d.index(b"\x00", off)].decode("utf-8", "replace")


def as_float(u32: int) -> float:
    return struct.unpack(">f", struct.pack(">I", u32))[0]


def entry(arc: str, suffix: str) -> bytes:
    """One file out of a .arc, through the container reader every script already uses."""
    from formats.arc_lz import read_arc
    return bytes(next(e["data"] for e in read_arc(arc) if str(e["name"]).endswith(suffix)))


def resources(arc: str = ARC) -> dict[str, list[str]]:
    """data/song/song_resources.rlist: {song: the resource names it loads}. Records of
    (name offset, count, size) followed by `count` string offsets, all relative to the record."""
    return parse_resources(entry(arc, "song_resources.rlist"))


def parse_resources(d: bytes) -> dict[str, list[str]]:
    """The same, from the rlist's bytes."""
    n = struct.unpack(">I", d[8:12])[0]
    off = 16
    out: dict[str, list[str]] = {}
    for _ in range(n):
        no, cnt, size = struct.unpack(">3I", d[off:off + 12])
        out[cstr(d, off + no)] = [cstr(d, off + o) for o in
                                  struct.unpack(">%dI" % cnt, d[off + 12:off + 12 + cnt * 4])]
        off += size
    return out


def load(arc: str = ARC) -> tuple[bytes, dict[str, list[int]]]:
    """(the plist's bytes, {song code: its 32 fields}) in table order."""
    return parse(entry(arc, "song_params.plist"))


def parse(d: bytes) -> tuple[bytes, dict[str, list[int]]]:
    """The same, from the plist's bytes (e.g. a mod's copy of the entry)."""
    n = struct.unpack(">I", d[8:12])[0]
    rows: dict[str, list[int]] = {}
    for r in range(n):
        f = list(struct.unpack(">32I", d[16 + r * 128:16 + r * 128 + 128]))
        rows[cstr(d, f[CODE])] = f
    return d, rows
