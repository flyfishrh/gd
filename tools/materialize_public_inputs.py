"""Restore immutable public research inputs from verified text transport only."""
from pathlib import Path, PurePosixPath
import base64
import gzip
import hashlib
import io
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'transport/TRANSPORT_MANIFEST.json').read_text())
    pieces = []
    for entry in manifest['parts']:
        path = PurePosixPath(entry['path'])
        if path.is_absolute() or '..' in path.parts or path.parts[0] != 'transport':
            raise ValueError('UNSAFE_PART_PATH')
        data = (ROOT / path).read_bytes()
        assert len(data) == entry['bytes']
        assert hashlib.sha256(data).hexdigest() == entry['SHA256']
        pieces.append(data)
    compressed = base64.b64decode(b''.join(pieces), validate=True)
    assert len(compressed) == manifest['compressedBytes']
    assert hashlib.sha256(compressed).hexdigest() == manifest['compressedSHA256']
    raw = gzip.decompress(compressed)
    if len(raw) > 16_000_000:
        raise ValueError('PUBLIC_INPUT_ARCHIVE_TOO_LARGE')
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if (not member.isfile() or name.is_absolute() or '..' in name.parts
                    or len(name.parts) != 2 or name.parts[0] != 'rc11'
                    or member.name not in manifest['files'] or member.name in seen):
                raise ValueError('UNEXPECTED_INPUT_MEMBER')
            seen.add(member.name)
            data = archive.extractfile(member).read()
            expected = manifest['files'][member.name]
            assert len(data) == expected['bytes']
            assert hashlib.sha256(data).hexdigest() == expected['SHA256']
            target = ROOT / 'inputs' / name
            if target.is_symlink() or target.parent.is_symlink():
                raise ValueError('INPUT_SYMLINK_FORBIDDEN')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.read_bytes() == data, 'REFUSE_OVERWRITE_DIFFERENT_INPUT'
            else:
                target.write_bytes(data)
    assert seen == set(manifest['files'])
    print(json.dumps({'status': 'PASS', 'originalPublicFiles': len(seen),
                      'modelImportedOrLoaded': False}))


if __name__ == '__main__':
    main()
