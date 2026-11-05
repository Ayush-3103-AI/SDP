import io
import zipfile

import pytest
from caxton_fixture import load_script

fetch = load_script("fetch_caxton_subset")


def test_plan_groups_needed_paths_by_print_zip():
    lines = ["caxton_dataset/print7/image-544.jpg\n", "caxton_dataset/print7/image-9.jpg", "", "caxton_dataset/print12/image-1.jpg"]
    assert fetch.plan(lines) == {
        "print7.zip": [("print7/image-544.jpg", "caxton_dataset/print7/image-544.jpg"),
                       ("print7/image-9.jpg", "caxton_dataset/print7/image-9.jpg")],
        "print12.zip": [("print12/image-1.jpg", "caxton_dataset/print12/image-1.jpg")],
    }


def test_plan_rejects_unexpected_paths():
    with pytest.raises(ValueError):
        fetch.plan(["print7/image-1.jpg"])


@pytest.mark.parametrize("method", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
def test_member_bytes_match_from_ranged_reads(method):
    payload = {f"print7/image-{i}.jpg": bytes(range(256)) * (i + 3) for i in range(4)}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", method) as z:
        z.writestr("print7/print_log.csv", "a,b\n1,2\n")
        for name, data in payload.items():
            z.writestr(name, data)
    blob = buf.getvalue()
    calls = []

    def get(start, end):  # inclusive, like an HTTP Range header
        calls.append((start, end))
        return blob[start:end + 1]

    infos = {i.filename: i for i in zipfile.ZipFile(io.BytesIO(blob)).infolist()}
    for name, data in payload.items():
        assert fetch.member_bytes(get, infos[name]) == data
    assert len(calls) == len(payload)  # one ranged request per image


def test_member_bytes_rejects_corrupt_data():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        z.writestr("print7/image-1.jpg", b"x" * 100)
    blob = bytearray(buf.getvalue())
    info = zipfile.ZipFile(io.BytesIO(bytes(blob))).infolist()[0]
    blob[info.header_offset + 30 + len(info.filename) + 5] ^= 0xFF
    with pytest.raises(ValueError, match="CRC"):
        fetch.member_bytes(lambda s, e: bytes(blob[s:e + 1]), info)
