"""Fetch only the CAXTON images adapt_caxton kept, without downloading whole print zips (T-0065 Part 2).

    python scripts/fetch_caxton_subset.py --needed data/needed.txt --root D:/caxton [--workers 16]

needed.txt comes from `adapt_caxton.py --list-needed`. Each printK.zip on the Apollo record is opened remotely
(HTTP Range reads of its central directory), and only the listed members are fetched, one ranged request each,
CRC-checked, and written to <root>/<img_path>, the layout build_crops expects. Existing files are skipped, so a
re-run resumes. ~4–5 GB for 500 images/print instead of 55.8 GB. Exit 1 if any image failed (re-run to retry).
"""
import argparse
import io
import re
import struct
import sys
import threading
import time
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

BUNDLE = "https://api.repository.cam.ac.uk/server/api/core/bundles/f08ca36b-4413-4525-82ec-2cb712947a79/bitstreams"
PATH = re.compile(r"caxton_dataset/(print\d+)/([^/\\]+\.jpg)")
_local = threading.local()


def plan(lines) -> dict[str, list[tuple[str, str]]]:
    """needed.txt lines → {"printK.zip": [(zip member, img_path), ...]}; rejects anything else (no path tricks)."""
    out: dict[str, list[tuple[str, str]]] = {}
    for line in lines:
        p = line.strip()
        if not p:
            continue
        m = PATH.fullmatch(p)
        if not m:
            raise ValueError(f"unexpected img_path: {p!r}")
        out.setdefault(f"{m[1]}.zip", []).append((f"{m[1]}/{m[2]}", p))
    return out


def member_bytes(get, info: zipfile.ZipInfo) -> bytes:
    """One member's bytes via get(start, end_inclusive); usually a single ranged request."""
    off = info.header_offset
    b = get(off, off + 30 + len(info.filename.encode()) + len(info.extra) + info.compress_size + 255)
    sig, n_name, n_extra = struct.unpack_from("<4s22xHH", b)
    if sig != b"PK\x03\x04":
        raise ValueError(f"{info.filename}: no local header at {off}")
    start = 30 + n_name + n_extra
    end = start + info.compress_size
    if end > len(b):
        b += get(off + len(b), off + end - 1)
    data = b[start:end]
    if info.compress_type == zipfile.ZIP_DEFLATED:
        data = zlib.decompress(data, -15)
    elif info.compress_type != zipfile.ZIP_STORED:
        raise ValueError(f"{info.filename}: compression {info.compress_type} not supported")
    if zlib.crc32(data) != info.CRC:
        raise ValueError(f"{info.filename}: CRC mismatch")
    return data


def _session() -> requests.Session:
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
    return _local.s


def _ranged(url):
    def get(start, end):
        r = _session().get(url, headers={"Range": f"bytes={start}-{end}"}, timeout=120)
        if r.status_code != 206:  # a 200 would be the whole archive
            raise OSError(f"HTTP {r.status_code} for a range request")
        return r.content
    return get


class _RangeFile(io.RawIOBase):
    """Seekable read-only view of a remote file, enough for zipfile to read the central directory."""

    def __init__(self, url):
        self.get, self.pos = _ranged(url), 0
        r = _session().get(url, headers={"Range": "bytes=0-0"}, timeout=120)
        self.size = int(r.headers["Content-Range"].rsplit("/", 1)[1])

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        return self.pos

    def readinto(self, b):
        if self.pos >= self.size:
            return 0
        d = self.get(self.pos, min(self.size, self.pos + len(b)) - 1)
        b[:len(d)] = d
        self.pos += len(d)
        return len(d)


def _retry(fn, *args, tries=4):
    for k in range(tries):
        try:
            return fn(*args)
        except (OSError, ValueError, requests.RequestException, zlib.error):
            if k == tries - 1:
                raise
            time.sleep(2 ** k)


def bitstreams() -> dict[str, str]:
    """{file name: content URL} for every file on the Apollo record."""
    urls, page = {}, 0
    while True:
        d = _session().get(BUNDLE, params={"size": 100, "page": page}, timeout=120).json()
        for b in d["_embedded"]["bitstreams"]:
            urls[b["name"]] = b["_links"]["content"]["href"]
        page += 1
        if page >= d["page"]["totalPages"]:
            return urls


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--needed", default="data/needed.txt", help="from adapt_caxton.py --list-needed")
    ap.add_argument("--root", required=True, help="writes <root>/caxton_dataset/printK/image-N.jpg")
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args(argv)
    root = Path(a.root)
    todo = {z: [(m, p) for m, p in pairs if not (root / p).is_file()]
            for z, pairs in plan(Path(a.needed).read_text(encoding="utf-8").splitlines()).items()}
    todo = {z: pairs for z, pairs in todo.items() if pairs}
    n = sum(map(len, todo.values()))
    print(f"{n} images to fetch from {len(todo)} print zips")
    if not n:
        return 0
    urls = bitstreams()
    absent = [z for z in todo if z not in urls]
    if absent:
        print(f"not on the record: {', '.join(absent)}", file=sys.stderr)
        return 2

    def listing(z):
        return z, {i.filename: i for i in zipfile.ZipFile(io.BufferedReader(_RangeFile(urls[z]), 1 << 16)).infolist()}

    jobs, failed, done = [], [], [0]
    lock = threading.Lock()
    with ThreadPoolExecutor(a.workers) as ex:
        for z, infos in ex.map(lambda z: _retry(listing, z), todo):
            for member, path in todo[z]:
                if member in infos:
                    jobs.append((urls[z], infos[member], path))
                else:
                    failed.append(f"{path}: not in {z}")

        def one(job):
            url, info, path = job
            try:
                data = _retry(member_bytes, _ranged(url), info)
            except Exception as e:  # noqa: BLE001 - reported below, re-run retries
                with lock:
                    failed.append(f"{path}: {e}")
                return
            dst = root / path
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.replace(dst)
            with lock:
                done[0] += 1
                if done[0] % 1000 == 0:
                    print(f"  {done[0]} / {len(jobs)}", flush=True)

        list(ex.map(one, jobs))
    print(f"fetched {done[0]}, failed {len(failed)}")
    for f in failed[:20]:
        print(f"  {f}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
