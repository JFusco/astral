"""Versioned lossless encoding for new bulky evidence; legacy rows stay intact."""
import struct
import zlib
import hashlib

NAMESPACE = b'\x89ASTRAL'
MAGIC = NAMESPACE+b'Z1\0'
REFERENCE = NAMESPACE+b'R1\0'
MAX_BYTES = 32*1024*1024


def pack_bytes(raw):
    if not isinstance(raw, bytes):
        raise ValueError('Evidence bytes required')
    reserved = raw.startswith(NAMESPACE)
    if reserved and len(raw) > MAX_BYTES:
        raise ValueError('Reserved evidence exceeds encoder budget')
    if not reserved and not 512 <= len(raw) <= MAX_BYTES:
        return raw
    encoded = MAGIC+struct.pack('>I', len(raw))+zlib.compress(raw, 6)
    return encoded if reserved or len(encoded) < len(raw) else raw


def unpack_bytes(value, db=None):
    if not isinstance(value, bytes):
        raise ValueError('Evidence bytes required')
    if not value.startswith(NAMESPACE):
        return value
    if value.startswith(REFERENCE):
        if db is None or len(value) != len(REFERENCE)+32:
            raise ValueError('Evidence reference requires its ledger')
        key = value[len(REFERENCE):]
        row = db.execute('SELECT payload FROM evidence_blobs WHERE sha256=?', (key,)).fetchone()
        if row is None:
            raise ValueError('Referenced evidence unavailable')
        raw = unpack_bytes(row[0])
        if hashlib.sha256(raw).digest() != key:
            raise ValueError('Referenced evidence hash mismatch')
        return raw
    if not value.startswith(MAGIC) or len(value) < len(MAGIC)+4:
        raise ValueError('Unsupported evidence encoding')
    size = struct.unpack('>I', value[len(MAGIC):len(MAGIC)+4])[0]
    if not 0 < size <= MAX_BYTES:
        raise ValueError('Evidence size exceeds decoder budget')
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(value[len(MAGIC)+4:], max_length=size+1)
    except zlib.error as exc:
        raise ValueError('Corrupt evidence encoding') from exc
    if len(raw) != size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('Incomplete or changed evidence encoding')
    return raw


def pack_text(value):
    if not isinstance(value, str):
        raise ValueError('Evidence text required')
    raw = value.encode('utf-8')
    packed = pack_bytes(raw)
    return packed if packed.startswith(MAGIC) else value


def unpack_text(value, db=None):
    if isinstance(value, str):
        return value
    if not isinstance(value, bytes) or not value.startswith(NAMESPACE):
        raise ValueError('Unsupported evidence text encoding')
    return unpack_bytes(value, db).decode('utf-8')


def reference_bytes(db, raw):
    key = hashlib.sha256(raw).digest()
    db.execute('INSERT OR IGNORE INTO evidence_blobs VALUES(?,?)', (key, pack_bytes(raw)))
    reference = REFERENCE+key
    if unpack_bytes(reference, db) != raw:
        raise ValueError('Existing evidence content differs')
    return reference


def reference_text(db, value):
    return reference_bytes(db, value.encode('utf-8'))


def unpack_row(row, db=None):
    value = dict(row)
    for column in ('payload', 'context', 'packet'):
        if isinstance(value.get(column), bytes):
            value[column] = unpack_text(value[column], db)
    if isinstance(value.get('frame'), bytes):
        value['frame'] = unpack_bytes(value['frame'], db)
    return value
