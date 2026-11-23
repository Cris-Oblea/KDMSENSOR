"""Unlocks DanceEvolution's event songs (build 2016080100).

WHAT IT DOES
  data/arc/resource_lists.arc holds data/song/song_params.plist (magic MS02BE):
  101 records of 128 bytes. Field 9 (offset +0x24 of the record) is the AVAILABILITY
  PHASE. The August offline kit set 999 on 22 event songs; the other 79 have 0,1,2,3,5
  and all of them show in song select. The February build (online) only used 0, 1 and
  100 - nobody had 999.

  This script sets those 22 to an always-available phase of their song-select tab's parity
  (1 licensed, 0 Konami's: `target()`) and rebuilds the .arc container.

  --fix-rena also fixes a Konami typo that exists in BOTH builds: song_params points
  'rena''s second chart at the resource "rana021", but the real resource and the file on
  disk are "rena021". It was never noticed because 'rena' was event-locked; unlocked, it
  matters.

USAGE
  python _tools/mods/content/songs/unlock_songs.py                        # dry run, writes nothing
  python _tools/mods/content/songs/unlock_songs.py --apply --fix-rena     # applies (automatic backup)
  python _tools/mods/content/songs/unlock_songs.py --revert               # restores the most recent backup

NOTE: data/arc/resource_lists.arc is NOT in crclist.bin, so this change adds no failure to
the ROM CHECK.
"""
import glob
import os
import shutil
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../..")))  # _tools: paths, and the packages
from formats import song_params
from formats.arc_lz import build_arc_preserving, read_arc
from paths import ROOT, TOOLS

GAME = ROOT   # the installed game, Konami's original: read only
# The installed game is never written (MOD_AUDIT.md): writes go to a staging copy, --root DIR.
if '--root' in sys.argv:
    ROOT = os.path.abspath(sys.argv[sys.argv.index('--root') + 1])
elif '--apply' in sys.argv or '--revert' in sys.argv:
    raise SystemExit('this writes game files: add --root <a staging copy>; the installed game is never written (MOD_AUDIT.md)')
os.chdir(ROOT)

ARC = 'data/arc/resource_lists.arc'
# the ORIGINAL container, intact: the 21 blocks we do not touch are copied from it
ORIG_ARC = os.path.join(GAME, 'data', 'arc', 'resource_lists.arc')
BACKUP_DIR = '_backup/data'
LOCKED = 999
FIELD = 9                       # +0x24 in the 128-byte record
# the phase also files the song under POPULAR or KONAMI SONGS (formats/song_params.py, unlocked_phase)
target = song_params.unlocked_phase


FEB_ARC = os.path.join(TOOLS, 'mods', 'sources', 'feb2016', 'resource_lists.arc')   # = the February 2016 dump's
# the only 9 fields of the record that are pointers into the string table
PTR_FIELDS = [0, 1, 2, 6, 13, 14, 18, 19, 27]


def yest_seed(plist: bytes) -> dict:
    """The appended 'yest' record of a table (the shipped one) as plain data: its 32 fields and its 9 strings."""
    n = struct.unpack('>I', plist[8:12])[0]
    f = list(struct.unpack('>32I', plist[16 + (n - 1) * 128:16 + n * 128]))
    return {'fields': f, 'strings': {str(i): plist[f[i]:plist.index(b'\x00', f[i])].decode('utf-8') for i in PTR_FIELDS}}


def add_yest(plist, seed=None):
    """Puts back the record of 'yest' (YESTERDAY / CHERRY) from the February build (or from `seed`, yest_seed's).
    The field-9 phase is always the song-select tab's (`target`); every other field is the source's.

    August keeps ALL of the song's files (charts, audio, jacket, animations) and its
    entries in song_resources.rlist and song_character_params.plist: the only thing the
    offline kit deleted was this 128-byte record of song_params. In February it had phase
    0, i.e. it was a base song, always available.

    It is done by APPENDING: the original string table stays byte for byte intact and only
    the existing records' pointers move by 128 bytes.
    """
    n = struct.unpack('>I', plist[8:12])[0]
    sb = 16 + n * 128

    def cstr_at(buf, off):
        return buf[off:buf.index(b'\x00', off)]

    for r in range(n):
        o = struct.unpack('>I', plist[16 + r * 128:20 + r * 128])[0]
        if cstr_at(plist, o) == b'yest':
            return None, 'it was already there'

    if seed:   # the record as shipped (yest_seed), for a PC that has no February dump
        src, text = list(seed['fields']), {i: seed['strings'][str(i)].encode('utf-8') for i in PTR_FIELDS}
    else:
        feb = next(e for e in read_arc(FEB_ARC) if e['name'].endswith('song_params.plist'))['data']
        fn = struct.unpack('>I', feb[8:12])[0]
        src = None
        for r in range(fn):
            f = list(struct.unpack('>32I', feb[16 + r * 128:16 + r * 128 + 128]))
            if cstr_at(feb, f[0]) == b'yest':
                src = f
                break
        if src is None:
            return None, 'February does not have the record'
        text = {i: cstr_at(feb, src[i]) for i in PTR_FIELDS}

    strings = bytearray()
    rel = {}
    for i in PTR_FIELDS:
        rel[i] = len(strings)
        strings += text[i] + b'\x00'

    out = bytearray(plist[:16])
    for r in range(n):
        f = list(struct.unpack('>32I', plist[16 + r * 128:16 + r * 128 + 128]))
        for i in PTR_FIELDS:
            f[i] += 128
        out += struct.pack('>32I', *f)
    new = list(src)
    new[FIELD] = target('yest')   # February had 0: KONAMI SONGS in August's song select
    base = len(plist) + 128
    for i in PTR_FIELDS:
        new[i] = base + rel[i]
    out += struct.pack('>32I', *new)
    out += plist[sb:]
    out += strings
    struct.pack_into('>I', out, 8, n + 1)
    struct.pack_into('>I', out, 12, len(out))

    # check: the 9 pointers of the 102 records have to resolve
    o2 = bytes(out)
    n_sb = 16 + (n + 1) * 128
    for r in range(n + 1):
        f = struct.unpack('>32I', o2[16 + r * 128:16 + r * 128 + 128])
        for i in PTR_FIELDS:
            v = f[i]
            assert n_sb <= v < len(o2) and (v == n_sb or o2[v - 1] == 0), \
                'invalid pointer: record %d field %d' % (r, i)
    return o2, '%s / %s (phase %d, order %d)' % (
        cstr_at(o2, new[13]).decode('utf-8', 'replace'),
        cstr_at(o2, new[14]).decode('utf-8', 'replace'), new[9], new[22])


def drop_yest(plist: bytes) -> bytes:
    """The inverse of add_yest: the table without its appended 'yest' record, its strings, and the 128-byte pointer shift."""
    n1 = struct.unpack('>I', plist[8:12])[0]
    last = struct.unpack('>32I', plist[16 + (n1 - 1) * 128:16 + n1 * 128])
    assert plist[last[0]:plist.index(b'\x00', last[0])] == b'yest', "the last record is not 'yest'"
    size = min(last[i] for i in PTR_FIELDS) - 128   # its strings start where the table without it ended
    out = bytearray(plist[:16])
    for r in range(n1 - 1):
        f = list(struct.unpack('>32I', plist[16 + r * 128:16 + (r + 1) * 128]))
        for i in PTR_FIELDS:
            f[i] -= 128
        out += struct.pack('>32I', *f)
    out += plist[16 + n1 * 128:size + 128]
    struct.pack_into('>I', out, 8, n1 - 1)
    struct.pack_into('>I', out, 12, len(out))
    return bytes(out)


def parse(plist):
    n = struct.unpack('>I', plist[8:12])[0]

    def s(o):
        return plist[o:plist.index(b'\x00', o)].decode('utf-8', 'replace')

    return [(16 + r * 128,
             s(struct.unpack('>I', plist[16 + r * 128:20 + r * 128])[0]),
             s(struct.unpack('>I', plist[16 + r * 128 + 52:16 + r * 128 + 56])[0]),
             list(struct.unpack('>32I', plist[16 + r * 128:16 + r * 128 + 128])))
            for r in range(n)]


def main():
    apply_ = '--apply' in sys.argv
    fix_rena = '--fix-rena' in sys.argv

    if '--revert' in sys.argv:
        b = sorted(glob.glob(os.path.join(BACKUP_DIR, 'resource_lists.arc.*')))
        if not b:
            print('There is no backup in %s' % BACKUP_DIR)
            return 1
        shutil.copy2(b[-1], ARC)
        print('Restored from %s' % b[-1])
        return 0

    ents = read_arc(ARC)
    idx = next(i for i, e in enumerate(ents) if e['name'].endswith('song_params.plist'))
    plist = bytearray(ents[idx]['data'])

    hits = [(o, c, t) for o, c, t, f in parse(bytes(plist)) if f[FIELD] == LOCKED]
    print('Songs in phase %d (locked): %d\n' % (LOCKED, len(hits)))
    for o, c, t in hits:
        print('   %-6s %s' % (c, t.replace('\n', ' / ')))
        if apply_:
            struct.pack_into('>I', plist, o + FIELD * 4, target(c))

    if fix_rena:
        tok = b'rana021'
        n_tok = plist.count(tok)
        if n_tok != 1:
            print('\n(--fix-rena) "rana021" appears %d times: nothing touched.' % n_tok)
        elif apply_:
            k = plist.find(tok)
            plist[k:k + len(tok)] = b'rena021'
            print('\n(--fix-rena) fixed "rana021" -> "rena021" at offset %d' % k)
        else:
            print('\n(--fix-rena) "rana021" -> "rena021" would be fixed')

    if '--add-yest' in sys.argv:
        new, msg = add_yest(bytes(plist))
        if new is None:
            print('\n(--add-yest) nothing done: %s' % msg)
        else:
            print('\n(--add-yest) YESTERDAY restored: %s' % msg)
            print('             song_params goes from %d to %d songs' %
                  (struct.unpack('>I', bytes(plist)[8:12])[0],
                   struct.unpack('>I', new[8:12])[0]))
            if apply_:
                plist = bytearray(new)

    if not apply_:
        print('\n(dry run) Nothing written. Use --apply to apply.')
        return 0

    # CAREFUL: do NOT use build_arc() here. Recompressing the 22 blocks with our encoder
    # leaves the game with no songs at all: song select builds its vectors empty
    # (begin=NULL) and crashes at gamekdm+0x689b5. Confirmed by reading the minidump on
    # 2026-08-21. build_arc_preserving() copies the original blocks byte for byte and puts
    # only the modified song_params in UNCOMPRESSED, a mode Konami already uses in this file.
    ents[idx]['data'] = bytes(plist)
    new = build_arc_preserving(ORIG_ARC, {'song_params.plist': bytes(plist)})

    os.makedirs(BACKUP_DIR, exist_ok=True)
    bak = os.path.join(BACKUP_DIR, 'resource_lists.arc.%s' % time.strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(ARC, bak)
    Path(ARC).write_bytes(new)

    # check: read back from disk and verify it came out as intended
    chk = read_arc(ARC)
    pl = next(e for e in chk if e['name'].endswith('song_params.plist'))['data']
    left = [c for o, c, t, f in parse(pl) if f[FIELD] == LOCKED]
    print('\nBackup : %s' % bak)
    print('Written: %s (%d bytes)' % (ARC, len(new)))
    print('Check after reading back: %d songs left at %d %s' % (len(left), LOCKED, left))
    print('Container blocks intact: %d/%d' %
          (sum(1 for a, b2 in zip(ents, chk, strict=False) if a['data'] == b2['data']), len(ents)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
