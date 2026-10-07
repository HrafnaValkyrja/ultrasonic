#!/usr/bin/env python3
"""fw/tools/imgcrc.py: patch the FWSIM-R21 image header CRC into fw.bin (objcopy -O binary of the app ELF, base 0x08002000).

Header at offset 0x300: magic "PODA" (0x41444F50), version 1, length (linker _app_size), crc32. The CRC is zlib CRC-32 over [0, length)
with the crc word read as 0; the boot stub (fw/port_u575/boot/boot.c boot_image_crc) recomputes it before every jump to the app.
    python3 fw/tools/imgcrc.py fw.bin            # patch in place, print the header as JSON
    python3 fw/tools/imgcrc.py --check fw.bin    # exit 1 unless the header and CRC are valid
"""
import argparse
import json
import struct
import sys
import zlib
from pathlib import Path

OFF, MAGIC = 0x300, 0x41444F50


def crc_of(img, length):
    b = bytearray(img[:length])
    b[OFF + 12:OFF + 16] = b"\0\0\0\0"
    return zlib.crc32(bytes(b)) & 0xFFFFFFFF


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("bin", type=Path)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    img = bytearray(a.bin.read_bytes())
    magic, ver, length, crc = struct.unpack_from("<4I", img, OFF)
    ok = magic == MAGIC and ver == 1 and OFF + 16 <= length == len(img)
    if not ok:
        print(json.dumps({"ok": False, "magic": hex(magic), "version": ver, "length": length, "bin_len": len(img)}))
        return 1
    want = crc_of(img, length)
    if a.check:
        print(json.dumps({"ok": crc == want, "length": length, "crc32": hex(crc)}))
        return 0 if crc == want else 1
    struct.pack_into("<I", img, OFF + 12, want)
    a.bin.write_bytes(bytes(img))
    print(json.dumps({"ok": True, "length": length, "crc32": hex(want)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
