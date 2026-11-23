"""English song titles and artists: every title and artist of song_params.plist written in
Japanese or Chinese replaced by its official English or romanised name, so an English player
can read it and search for it; for the English language only.

Sources, in this order (researched 2026-10-27): the English part Konami already gave the
title (-The Great Artist-, -Feel the Love-, -Flowers-, Jolin Tsai, Show Lo); the release's
own English name as English Wikipedia gives it (the licensed singles and their artists);
RemyWiki's romanised page name, the BEMANI reference, for Konami's originals; for the
artists with neither, the name their own releases use (Apple Music: HINATABI BITTER SWEETS♪
BEST, BENIIRO LITMUS's channel, Nana Mitani's videos; COCONATSU, the pop'n wiki).
"(かんたん振り付け)" and "(9回裏振付ver)" are choreography labels, not part of a song's
name: translated.

The plist is rewritten by APPENDING: each new string goes at the end of the string table and
field 13 (title) or 14 (artist) points at it, and field 27, the NAME tab's sort key, gets the English title in
plain capitals (`name_key`); every other byte stays (unlock_songs.add_yest
does the same).

    python _tools/mods/content/titles.py      lists Konami's text -> ours, and self-checks
"""
import io
import os
import struct
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")))  # _tools: paths, and the packages
from formats import song_params as spt
from paths import ROOT

EASY = "(Easy Choreography)"
TITLES = {   # song code -> English title; '\n' splits the lines as Konami's do
    "sakr": "Sakura",
    "hvro": "Heavy Rotation",
    "hvrt": "Heavy Rotation\n" + EASY,
    "irny": "irony\n" + EASY,
    "tuto": "Tutorial",
    "howt": "Tutorial",                       # 外周チュートリアル: the hidden attract demo
    "rena": "Love Revolution 21",
    "reni": "Love Revolution 21\n" + EASY,
    "maru": "Maru Maru Mori Mori!",
    "meme": "Memeshikute",
    "luka": "Luka Luka★Night Fever",
    "maji": "Maji LOVE1000%",
    "ikuz": "Ikuze! Kaito Shojo -Zver.-",
    "hana": "Hana Ranman -Flowers-\n(2nd EDITION)",
    "zenr": "Zenryaku, Michi no Ue yori",
    "name": "Nameko no Uta",
    "circ": "Renai Circulation",
    "odop": "Odoru Pompokolin",
    "cybe": "Cyber Thunder Cider",
    "megu": "Megu Megu☆Fire Endless Night",
    "akbb": "Koi Suru Fortune Cookie",
    "malo": "Maji LOVE2000%",
    "mika": "Mikakunin Chugakusei X",
    "inva": "Invader Invader",
    "obor": "Oboro",
    "loma": "LOVE Machine",
    "ckpp": "Chikuwa Parfait da yo☆CKP",
    "mawa": "Maware! Setsugetsuka",
    "joli": "The Great Artist",
    "show": "Feel the Love",
    "fuji": "FUJIMORI -Matsuri- FESTIVAL",
    "pura": "Kokoro no Placard",
    "funa": "Funa Funa Funassyi♪\n~Funassyi Official Theme Song~",
    "rint": "Rin to Shite Saku Hana no Gotoku",
    "todo": "Todoroke! Koi no Beanball!!",
    "todm": "Todoroke! Koi no Beanball!!\n(Bottom of the 9th ver)",
    "tsum": "Tsumi to Batsu",
    "choc": "Chocolate Smile",
    "haps": "Happy Synthesizer",
    "alst": "Alstroemeria\n(walk with you remix)",
    "msou": "Musou",
    "akat": "Aka to Ao no Rampage",
}
ARTISTS = {   # song code -> artist, where Konami's is in kana or kanji (a styled name, TЁЯRA, √5, stays: the user)
    "maru": "Kaoru to Tomoki, Tamani Mook",
    "brav": "Naoto Inti Raymi",
    "simw": "SUPER STAR MITSURU",
    "meme": "Golden Bomber",
    "ponp": "Kyary Pamyu Pamyu",
    "inva": "Kyary Pamyu Pamyu",
    "luka": "Nana Mitani",
    "megu": "Nana Mitani",
    "ikuz": "Momoiro Clover Z",
    "zenr": "Issei Fubi Sepia",
    "lanj": "Yuki Kimura",
    "name": "Haruka Fukuhara",
    "circ": "Nadeko Sengoku (CV. Kana Hanazawa)",
    "cowo": "Rib",
    "mika": "Shiritsu Ebisu Chugaku",
    "ckpp": "Hinatabi Bitter Sweets♪",
    "choc": "Hinatabi Bitter Sweets♪ & Coconatsu",
    "mawa": "Utagumi Setsugetsuka",
    "joli": "Jolin Tsai",
    "show": "Show Lo",
    "funa": "Funassyi",
    "rint": "Beniiro Litmus",
    "todo": "Dynamic Yakyu Kyodai v.s. Crossfire Prim",
    "todm": "Dynamic Yakyu Kyodai v.s. Crossfire Prim",
}
FIELDS = ((spt.TITLE, TITLES), (spt.ARTIST, ARTISTS))
FONT = os.path.join(ROOT, "data", "font", "2d_font_ui.kbf")   # the one font holding every glyph of Konami's titles


FONT_ENTRY = "data/font/2d_font_ui.kbf"   # in data/arc/2d_font_ui.arc, the copy the game loads
ROOT_SIGN, ROOT_ADVANCE = 0x221A, (28, 12)


def font_fix(kbf: bytes) -> bytes:
    """√ advances 12 px instead of the whole 28 px cell: its hook is 12 px wide and its bar runs over
    the rest, so the next glyph (the 5 of √5, the only √ the song list has) sits under the bar."""
    out = bytearray(kbf)
    for i in range(struct.unpack_from("<I", out, 0x14)[0]):
        if struct.unpack_from("<I", out, 0x20 + 16 * i)[0] == ROOT_SIGN:
            assert out[0x20 + 16 * i + 10] == ROOT_ADVANCE[0], "√'s advance is not Konami's 28"
            out[0x20 + 16 * i + 10] = ROOT_ADVANCE[1]
            return bytes(out)
    raise AssertionError("no √ in the font")


def foreign(ch: str) -> bool:
    """A letter an English player cannot read or type: kana, kanji, full-width letters. Symbols
    and styled letters (☆ ★ ♥ ♪ ・ √ the Ё and Я of TЁЯRA) are the artists' own styling and stay."""
    o = ord(ch)
    return (0x3040 <= o <= 0x30ff and o != 0x30fb) or 0x3400 <= o <= 0x9fff or 0xff10 <= o <= 0xff5a


def font_codes() -> set[int]:
    b = Path(FONT).read_bytes()
    return {struct.unpack_from("<I", b, 0x20 + 16 * i)[0] for i in range(struct.unpack_from("<I", b, 0x14)[0])}


def name_key(title: str) -> str:
    """The NAME tab's key for an English title: upper case, accents dropped, Latin letters, digits and spaces only. The game
    compares the keys byte by byte (an inline strcmp in the song list's sort), so these sort A to Z (the user, 2026-11-12)."""
    plain = unicodedata.normalize("NFKD", title.replace("\n", " ")).encode("ascii", "ignore").decode().upper()
    return " ".join("".join(ch for ch in plain if ch.isalnum() or ch == " ").split())


def sort_key(konami: str, title: str) -> str:
    """Field 27 for a song: its title's name_key; but Konami gave the dance lesson (tuto) and the attract tutorial a key in
    Latin letters ("tutorial", "demo") where every song has katakana, which puts the lesson FIRST in NAME (Latin bytes come
    before kana). That stays: a space first sorts it before every title, digits included (the user, 2026-11-12)."""
    return " " + name_key(konami) if konami.isascii() else name_key(title)


def retitle(plist: bytes) -> bytes:
    """The plist with every song of TITLES / ARTISTS renamed, and every song's NAME key (field 27) from its English title:
    with English titles the NAME tab runs A to Z; without them it keeps Konami's kana order."""
    out = bytearray(plist)
    n = struct.unpack(">I", out[8:12])[0]
    for r in range(n):
        code = spt.cstr(out, struct.unpack_from(">I", out, 16 + r * 128)[0])
        for field, table in FIELDS:
            if code in table:
                struct.pack_into(">I", out, 16 + r * 128 + field * 4, len(out))
                out += table[code].encode("utf-8") + b"\x00"
        title = spt.cstr(out, struct.unpack_from(">I", out, 16 + r * 128 + spt.TITLE * 4)[0])
        key = sort_key(spt.cstr(out, struct.unpack_from(">I", out, 16 + r * 128 + spt.NAME_KEY * 4)[0]), title)
        struct.pack_into(">I", out, 16 + r * 128 + spt.NAME_KEY * 4, len(out))
        out += key.encode("ascii") + b"\x00"
    struct.pack_into(">I", out, 12, len(out))
    return bytes(out)


def check(orig: bytes, new: bytes) -> None:
    """Only fields 13/14 of the songs in the tables changed, each to its string; the original
    string table is intact; no title or artist is left in kana or kanji; every new
    character is a glyph of the title font."""
    sb = 16 + struct.unpack(">I", orig[8:12])[0] * 128
    assert new[:12] == orig[:12] and new[sb:len(orig)] == orig[sb:], "the original string table changed"
    _, a = spt.parse(orig)
    d1, b = spt.parse(new)
    assert list(a) == list(b)
    for c in a:
        diff = [i for i in range(32) if a[c][i] != b[c][i]]
        assert diff == [f for f, t in FIELDS if c in t] + [spt.NAME_KEY], (c, diff)
        for f, t in FIELDS:
            if c in t:
                assert spt.cstr(d1, b[c][f]) == t[c]
        key = spt.cstr(d1, b[c][spt.NAME_KEY])
        assert key.strip() and key == sort_key(spt.cstr(orig, a[c][spt.NAME_KEY]), spt.cstr(d1, b[c][spt.TITLE])), (c, key)
        assert all(ch == " " or "0" <= ch <= "9" or "A" <= ch <= "Z" for ch in key), (c, key)
    assert name_key("L'amour et la liberté\n(Darwin)") == "LAMOUR ET LA LIBERTE DARWIN" and name_key("TA・DA ☆ YO・SHI") == "TADA YOSHI"
    left = [(c, spt.cstr(d1, b[c][f])) for c in b for f, _ in FIELDS if any(foreign(ch) for ch in spt.cstr(d1, b[c][f]))]
    assert not left, "still not in Latin letters: %s" % left
    codes = font_codes()
    missing = {ch for _, t in FIELDS for s in t.values() for ch in s if ch != "\n" and ord(ch) not in codes}
    assert not missing, "not in 2d_font_ui: %s" % "".join(sorted(missing))


if __name__ == "__main__":
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    d, rows = spt.load()
    new = retitle(d)
    check(d, new)
    kbf = Path(FONT).read_bytes()
    fixed = font_fix(kbf)
    assert sum(a != b for a, b in zip(kbf, fixed, strict=True)) == 1
    for c, f in rows.items():
        for field, t in FIELDS:
            if c in t:
                print("%s  %-40s %s" % (c, spt.cstr(d, f[field]).replace("\n", " / "), t[c].replace("\n", " / ")))
    print("%d titles, %d artists; check passed" % (len(TITLES), len(ARTISTS)))
