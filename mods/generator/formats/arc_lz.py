"""Reader and writer of Konami/AVS's .arc container (magic 0x19751120, compression=2).

FORMAT SOLVED 2026-08-21.

Container:
    0x00 u32 LE magic       = 0x19751120
    0x04 u32 LE version     = 1
    0x08 u32 LE n_entries
    0x0C u32 LE compression = 2
    0x10 a table of n 16-byte entries:  (name_off, data_off, usize, csize) u32 LE
    Data aligned to 16 bytes.  csize == usize  =>  an UNCOMPRESSED block.

Compression (LZSS-style LZ77):
    a flag byte, LSB first, 8 items per flag
      bit = 1 -> literal (1 byte)
      bit = 0 -> reference (2 bytes b0,b1):
                    distance = (b0 << 4) | (b1 >> 4)      12 bits, backwards
                    length   = (b1 & 0x0F) + 3            3..18
    Copied byte by byte (overlapping copies are legitimate).

    KEY: the encoder emits references that point BEFORE the start of the output. The real
    decoder has a 4096-byte circular window initialised to ZERO, so those reads return
    zeros. Here that is emulated by returning 0 on underflow. This is what broke every
    earlier attempt: the FIRST reference of the file already underflows, and treating it as
    an error cuts the output at 6 bytes.
"""
import struct
from pathlib import Path
from typing import Any

MAGIC = 0x19751120


def lz_decompress(src, usize):
    out = bytearray()
    p = 0
    flags = 0
    cnt = 0
    ns = len(src)
    while len(out) < usize and p < ns:
        if cnt == 0:
            flags = src[p]
            p += 1
            cnt = 8
        bit = flags & 1
        flags >>= 1
        cnt -= 1
        if bit:
            out.append(src[p])
            p += 1
        else:
            if p + 1 >= ns:
                break
            b0, b1 = src[p], src[p + 1]
            p += 2
            dist = (b0 << 4) | (b1 >> 4)
            ln = (b1 & 0x0F) + 3
            if dist == 0:
                break
            for _ in range(ln):
                out.append(out[-dist] if dist <= len(out) else 0)
    return bytes(out)


def read_arc(path: str) -> list[dict[str, Any]]:
    d = Path(path).read_bytes()
    magic, _ver, n, _comp = struct.unpack('<4I', d[:16])
    assert magic == MAGIC, 'unexpected magic %08X' % magic
    ents = []
    for i in range(n):
        o = 16 + i * 16
        no, do, us, cs = struct.unpack('<4I', d[o:o + 16])
        name = d[no:d.index(b'\0', no)].decode('ascii', 'replace')
        blob = d[do:do + cs]
        data = blob if us == cs else lz_decompress(blob, us)
        ents.append({'i': i, 'name': name, 'usize': us, 'csize': cs, 'data': data})
    return ents


# ---------------------------------------------------------------- compression
def _longest_match(src, i, window, maxlen, minlen):
    """(length, distance) of the longest match ending before i, or (0, 0).
    Searched in minlen-byte probes with rfind, backwards."""
    best_len, best_dist = 0, 0
    n = len(src)
    probe = src[i:i + minlen]
    if i < 1 or len(probe) != minlen:
        return best_len, best_dist
    lo = max(0, i - window)
    j = src.rfind(probe, lo, i)
    while j != -1:
        ln = minlen
        while ln < maxlen and i + ln < n and src[j + ln] == src[i + ln]:
            ln += 1
        if ln > best_len:
            best_len, best_dist = ln, i - j
            if ln == maxlen:
                break
        j = src.rfind(probe, lo, j)
    return best_len, best_dist


def lz_compress(src, window=4095, maxlen=18, minlen=3):
    """LZ77 compressor compatible with lz_decompress. It never emits underflowing
    distances nor distance 0, so any implementation can decode the result, not only
    the one above."""
    out = bytearray()
    n = len(src)
    i = 0
    while i < n:
        flagpos = len(out)
        out.append(0)
        flags = 0
        for b in range(8):
            if i >= n:
                break
            best_len, best_dist = _longest_match(src, i, window, maxlen, minlen)
            if best_len >= minlen:
                out.append((best_dist >> 4) & 0xFF)
                out.append(((best_dist & 0x0F) << 4) | (best_len - 3))
                i += best_len
            else:
                flags |= (1 << b)
                out.append(src[i])
                i += 1
        out[flagpos] = flags
    return bytes(out)


def build_arc(entries, compress=True):
    """entries: a list of dicts with 'name' and 'data'. Rebuilds the container."""
    n = len(entries)
    blobs = []
    for e in entries:
        raw = e['data']
        c = lz_compress(raw) if compress else raw
        if len(c) >= len(raw):
            c = raw                      # uncompressed: csize == usize
        # the order matters: an uncompressed block must not go through the decompressor
        assert c == raw or lz_decompress(c, len(raw)) == raw, 'round trip failed: ' + e['name']
        blobs.append(c)
    # the names right after the table, then the data aligned to 16
    names = bytearray()
    noffs = []
    nbase = 16 + n * 16
    for e in entries:
        noffs.append(nbase + len(names))
        names += e['name'].encode('ascii') + b'\0'
    cur = nbase + len(names)
    cur = (cur + 15) & ~15
    doffs = []
    for c in blobs:
        doffs.append(cur)
        cur = (cur + len(c) + 15) & ~15
    out = bytearray(cur)
    out[0:16] = struct.pack('<4I', MAGIC, 1, n, 2)
    for i, e in enumerate(entries):
        out[16 + i * 16:32 + i * 16] = struct.pack('<4I', noffs[i], doffs[i],
                                                   len(e['data']), len(blobs[i]))
    out[nbase:nbase + len(names)] = names
    for i, c in enumerate(blobs):
        out[doffs[i]:doffs[i] + len(c)] = c
    return bytes(out)


def build_arc_preserving(orig_path, replacements):
    """Rebuilds a .arc keeping EVERY original block byte for byte, and putting the
    replacements in UNCOMPRESSED (csize == usize).

    Why this way and not with build_arc(): the game's decoder is stricter than ours.
    Recompressing the 22 blocks with our encoder left the game with no songs at all (the
    song select vectors all came out NULL -> crash). Konami already stores 8 blocks
    uncompressed in this very file, so the raw mode is proven.

    replacements: {block_name: new_bytes}
    """
    d = Path(orig_path).read_bytes()
    magic, ver, n, comp = struct.unpack('<4I', d[:16])
    assert magic == MAGIC
    ents = []
    for i in range(n):
        o = 16 + i * 16
        no, do, us, cs = struct.unpack('<4I', d[o:o + 16])
        name = d[no:d.index(b'\0', no)].decode('ascii')
        blob = d[do:do + cs]
        for k, v in replacements.items():
            if name.endswith(k):
                blob, us = v, len(v)        # raw: csize == usize
                break
        ents.append((name, blob, us))

    nbase = 16 + n * 16
    names = bytearray()
    noffs = []
    for name, _, _ in ents:
        noffs.append(nbase + len(names))
        names += name.encode('ascii') + b'\0'
    cur = (nbase + len(names) + 15) & ~15
    doffs = []
    for _, blob, _ in ents:
        doffs.append(cur)
        cur = (cur + len(blob) + 15) & ~15

    out = bytearray(cur)
    out[0:16] = struct.pack('<4I', MAGIC, ver, n, comp)
    for i, (_name, blob, us) in enumerate(ents):
        out[16 + i * 16:32 + i * 16] = struct.pack('<4I', noffs[i], doffs[i], us, len(blob))
        out[doffs[i]:doffs[i] + len(blob)] = blob
    out[nbase:nbase + len(names)] = names
    return bytes(out)


# ---------------------------------------------------------------- lazy reading
def list_arc(path):
    """Only the entry table, decompressing nothing."""
    with open(path, 'rb') as fh:
        d = fh.read(1 << 20)
    magic, _ver, n, _comp = struct.unpack('<4I', d[:16])
    assert magic == MAGIC, 'unexpected magic %08X in %s' % (magic, path)
    ents = []
    for i in range(n):
        o = 16 + i * 16
        no, do, us, cs = struct.unpack('<4I', d[o:o + 16])
        name = d[no:d.index(b'\0', no)].decode('ascii', 'replace')
        ents.append({'i': i, 'name': name, 'off': do, 'usize': us, 'csize': cs})
    return ents


def read_arc_filtered(path, pred):
    """Decompresses ONLY the entries whose name satisfies pred(name).

    The song_*.arc files are around 5 MB and nearly all animation; decompressing the
    whole container with the Python LZ77 costs minutes per file. The .dsq files are
    3-21 KB, so filtering before decompressing brings it down to milliseconds.
    """
    ents = list_arc(path)
    wanted = [e for e in ents if pred(e['name'])]
    if not wanted:
        return []
    end = max(e['off'] + e['csize'] for e in wanted)
    with open(path, 'rb') as fh:
        d = fh.read(end)
    out = []
    for q in wanted:
        blob = d[q['off']:q['off'] + q['csize']]
        e = dict(q)
        e['data'] = blob if e['usize'] == e['csize'] else lz_decompress(blob, e['usize'])
        out.append(e)
    return out


# ---------------------------------------------------------------- big-endian variant
def read_arc_be(path_or_data):
    """The .arc container of the CONSOLE versions: the same layout but BIG-ENDIAN, with
    standard zlib instead of the arcade's own LZ77 (comp=1, header 78 9c)."""
    import zlib
    d = path_or_data if isinstance(path_or_data, (bytes, bytearray)) else Path(path_or_data).read_bytes()
    magic, _ver, n, _comp = struct.unpack('>4I', d[:16])
    assert magic == MAGIC, 'unexpected magic %08X' % magic
    out = []
    for i in range(n):
        o = 16 + i * 16
        no, do, us, cs = struct.unpack('>4I', d[o:o + 16])
        name = d[no:d.index(b'\0', no)].decode('ascii', 'replace')
        blob = d[do:do + cs]
        data = blob if us == cs else zlib.decompress(blob)
        out.append({'i': i, 'name': name, 'usize': us, 'csize': cs, 'data': data})
    return out


if __name__ == '__main__':
    import sys
    ok = True
    for e in read_arc(sys.argv[1] if len(sys.argv) > 1 else 'data/arc/resource_lists.arc'):
        good = len(e['data']) == e['usize']
        ok &= good
        print('%2d %-42s %-7d -> %-7d %s %s' % (e['i'], e['name'], e['csize'],
              len(e['data']), 'OK  ' if good else 'FAIL', e['data'][:8]))
    print('\nALL OK' if ok else '\nTHERE ARE FAILURES')
