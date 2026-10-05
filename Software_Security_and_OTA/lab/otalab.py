"""Independent teaching implementation of the supplied Secure OTA slides.

Cryptography and file I/O are real; protected storage, ECU execution and
health results are simulated. Never use this as a production updater.
"""

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import tempfile
import zlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

TOY = b'OTA-DEMO: led=0\n'
TOY_BAD = b'OTA-DEMO: led=1\n'
SLOT_LEN = 512 * 1024
CHUNK_SIZE = 64 * 1024
MAX_MANIFEST = 64 * 1024
MAX_IMAGE = 8 * 1024 * 1024
TARGET = 'ECU-BODY-01'
HW = 'rev2'
MAGIC = 'OTA-LAB-1'


class Reject(Exception):
    """Stable diagnostic code; the caller must stop the operation."""


def require(condition, code):
    if not condition:
        raise Reject(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    # Lab serialization convention, not a general JSON canonicalization standard.
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def public_bytes(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def parse(raw):
    try:
        return json.loads(raw, object_pairs_hook=no_duplicates)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Reject('JSON_INVALID') from exc


def verify_signature(raw, signature, public):
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(signature, raw)
    except (InvalidSignature, ValueError) as exc:
        raise Reject('SIGNATURE_INVALID') from exc


def build_package(key, image, **overrides):
    manifest = dict(target=TARGET, hardware_revision=HW, version='2.4.0',
                    security_version=6, size=len(image), chunk_size=CHUNK_SIZE,
                    payload_hash=digest(image),
                    chunk_hashes=[digest(image[i:i + CHUNK_SIZE])
                                  for i in range(0, len(image), CHUNK_SIZE)])
    manifest.update(overrides)
    raw = encode(manifest)
    return raw, key.sign(raw), public_bytes(key)


def verify_manifest(raw, signature, public, authorized, floor, target=TARGET, hardware=HW):
    require(len(raw) <= MAX_MANIFEST, 'MANIFEST_TOO_LARGE')
    verify_signature(raw, signature, public)
    require(public in authorized, 'SIGNER_NOT_AUTHORIZED')
    m = parse(raw)
    require(isinstance(m, dict), 'SCHEMA_INVALID')
    strings = ('target', 'hardware_revision', 'version', 'payload_hash')
    integers = ('size', 'chunk_size', 'security_version')
    require(all(type(m.get(k)) is str for k in strings), 'SCHEMA_INVALID')
    require(all(type(m.get(k)) is int for k in integers), 'SCHEMA_INVALID')
    require(0 < m['size'] <= MAX_IMAGE, 'SIZE_LIMIT')
    require(0 < m['chunk_size'] <= CHUNK_SIZE, 'CHUNK_SIZE_INVALID')
    require(m['security_version'] >= 0, 'SCHEMA_INVALID')
    hashes = m.get('chunk_hashes')
    count = (m['size'] + m['chunk_size'] - 1) // m['chunk_size']
    require(type(hashes) is list and len(hashes) == count and count <= 4096,
            'CHUNK_COUNT_INVALID')
    require(all(type(h) is str and re.fullmatch('[0-9a-f]{64}', h)
                for h in hashes + [m['payload_hash']]), 'HASH_FORMAT_INVALID')
    require(m['target'] == target, 'TARGET_MISMATCH')
    require(m['hardware_revision'] == hardware, 'HARDWARE_MISMATCH')
    require(m['security_version'] >= floor, 'SECURITY_VERSION_TOO_LOW')
    return m


def validate_payload(image, m):
    require(len(image) == m['size'], 'SIZE_MISMATCH')
    require(digest(image) == m['payload_hash'], 'PAYLOAD_HASH_REJECTED')


def atomic_json(path, value):
    """One-file OS replacement only; not a flash power-loss guarantee."""
    path = Path(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        f.write(encode(value))
        f.flush()
        os.fsync(f.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def chunk_range(m, index):
    require(type(index) is int and 0 <= index < len(m['chunk_hashes']), 'CHUNK_INDEX_INVALID')
    start = index * m['chunk_size']
    return start, min(start + m['chunk_size'], m['size']) - 1


def receive_chunks(work, raw, m, fetch):
    """Caller supplies an already authenticated manifest and bounded fetch."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    state_path = work / 'download_state.json'
    if state_path.exists():
        state = parse(state_path.read_bytes())
        require(isinstance(state, dict) and state.get('manifest_id') == digest(raw),
                'RESUME_MANIFEST_MISMATCH')
    else:
        state = dict(manifest_id=digest(raw), received=[])
    requested = []
    chunks = []
    for index, expected_hash in enumerate(m['chunk_hashes']):
        path = work / f'chunk_{index}.bin'
        start, end = chunk_range(m, index)
        length = end - start + 1
        # Do not read an oversized local file just because a state flag says complete.
        data = path.read_bytes() if path.exists() and path.stat().st_size == length else b''
        if len(data) != length or digest(data) != expected_hash:
            requested.append(index)
            data = fetch(start, end)
            require(len(data) == length, 'CHUNK_LENGTH_REJECTED')
            require(digest(data) == expected_hash, 'CHUNK_HASH_REJECTED')
            with path.open('wb') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        chunks.append(data)
        state['received'] = list(range(index + 1))
        atomic_json(state_path, state)
    image = b''.join(chunks)
    validate_payload(image, m)
    return image, requested


def make_meta(seq, candidate=None, attempts=0):
    body = dict(magic=MAGIC, seq=seq, candidate_slot=candidate, attempts_left=attempts)
    return dict(body, crc32=zlib.crc32(encode(body)))


def meta_valid(m):
    if not isinstance(m, dict) or set(m) != {'magic', 'seq', 'candidate_slot', 'attempts_left', 'crc32'}:
        return False
    if not (m['magic'] == MAGIC and type(m['seq']) is int and m['seq'] >= 0
            and m['candidate_slot'] in (None, 'A', 'B')
            and type(m['attempts_left']) is int and 0 <= m['attempts_left'] <= 3
            and type(m['crc32']) is int):
        return False
    if m['candidate_slot'] is None and m['attempts_left'] != 0:
        return False
    body = {k: v for k, v in m.items() if k != 'crc32'}
    return m['crc32'] == zlib.crc32(encode(body))


def load_meta(work):
    valid = []
    for index in range(2):
        try:
            m = parse((Path(work) / f'meta{index}.json').read_bytes())
            if meta_valid(m):
                valid.append((index, m))
        except (OSError, Reject):
            pass
    require(valid, 'BOOT_METADATA_INVALID')
    if len(valid) == 2 and valid[0][1]['seq'] == valid[1][1]['seq']:
        require(valid[0][1] == valid[1][1], 'BOOT_METADATA_CONFLICT')
    return max(valid, key=lambda pair: pair[1]['seq'])


def save_meta(work, candidate=None, attempts=0):
    index, old = load_meta(work)
    new = make_meta(old['seq'] + 1, candidate, attempts)
    atomic_json(Path(work) / f'meta{1 - index}.json', new)
    return new


def initialize(work):
    """Initialize a NEW directory; never silently reset existing lab state."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    require(not any(work.iterdir()), 'WORK_DIRECTORY_NOT_EMPTY')
    key = Ed25519PrivateKey.generate()
    (work / 'authorized.pub').write_bytes(public_bytes(key))
    # Publisher key remains in a separate fixture directory, not device state.
    publisher = work / 'publisher'
    publisher.mkdir()
    (publisher / 'signer.key').write_bytes(key.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
        serialization.NoEncryption()))
    for slot, value, security in [('A', b'A', 5), ('B', b'B', 6)]:
        image = value * SLOT_LEN
        raw, sig, pub = build_package(key, image, security_version=security)
        (work / f'{slot}.bin').write_bytes(image)
        (work / f'{slot}.manifest').write_bytes(raw)
        (work / f'{slot}.sig').write_bytes(sig)
        (work / f'{slot}.pub').write_bytes(pub)
    atomic_json(work / 'confirmed.json', dict(confirmed_slot='A', security_floor=5))
    atomic_json(work / 'meta0.json', make_meta(0))
    atomic_json(work / 'meta1.json', make_meta(0))


def confirmed(work):
    # Simulated protected storage. JSON access does not implement authorization.
    c = parse((Path(work) / 'confirmed.json').read_bytes())
    require(isinstance(c, dict) and c.get('confirmed_slot') in ('A', 'B')
            and type(c.get('security_floor')) is int and c['security_floor'] >= 0,
            'CONFIRMED_STATE_INVALID')
    return c


def slot_check(work, slot, floor):
    work = Path(work)
    raw = (work / f'{slot}.manifest').read_bytes()
    m = verify_manifest(raw, (work / f'{slot}.sig').read_bytes(),
                        (work / f'{slot}.pub').read_bytes(),
                        [(work / 'authorized.pub').read_bytes()], floor)
    require((work / f'{slot}.bin').stat().st_size == m['size'], 'SIZE_MISMATCH')
    validate_payload((work / f'{slot}.bin').read_bytes(), m)
    return m


def install(work, arch='ab', cut=False):
    work = Path(work)
    c = confirmed(work)
    _, meta = load_meta(work)
    require(meta['candidate_slot'] is None, 'CANDIDATE_ALREADY_PENDING')
    target = ('B' if c['confirmed_slot'] == 'A' else 'A') if arch == 'ab' else c['confirmed_slot']
    key = Ed25519PrivateKey.from_private_bytes((work / 'publisher' / 'signer.key').read_bytes())
    image = b'N' * SLOT_LEN
    raw, sig, pub = build_package(key, image)
    m = verify_manifest(raw, sig, pub, [(work / 'authorized.pub').read_bytes()], c['security_floor'])
    validate_payload(image, m)
    old = (work / f"{c['confirmed_slot']}.bin").read_bytes()
    # Approval metadata describes the NEW image even when its write is interrupted.
    (work / f'{target}.manifest').write_bytes(raw)
    (work / f'{target}.sig').write_bytes(sig)
    (work / f'{target}.pub').write_bytes(pub)
    with (work / f'{target}.bin').open('r+b') as f:
        f.write(image[:SLOT_LEN // 2] if cut else image)
        f.flush()
        os.fsync(f.fileno())
    preserved = old == (work / f"{c['confirmed_slot']}.bin").read_bytes()
    if cut:
        return dict(update='INTERRUPTED', old_preserved=preserved, written=SLOT_LEN // 2)
    slot_check(work, target, c['security_floor'])
    save_meta(work, target, 3)
    return dict(update='INSTALLED', candidate_slot=target, old_preserved=preserved)


def recover(work, c):
    try:
        slot_check(work, c['confirmed_slot'], c['security_floor'])
    except Reject as exc:
        return dict(update='FAILED', recovery='FORBIDDEN', booted_slot=None,
                    code='RECOVERY_FORBIDDEN', reason=str(exc), mode='RECOVERY')
    return dict(update='FAILED', recovery='SUCCESS', booted_slot=c['confirmed_slot'])


def boot(work, healthy=True):
    work = Path(work)
    c = confirmed(work)
    _, m = load_meta(work)
    candidate = m['candidate_slot']
    # A commit may persist before the candidate-clearing write. Never retry it as new.
    if candidate == c['confirmed_slot']:
        save_meta(work)
        candidate = None
    if candidate is None:
        result = recover(work, c)
        if result['recovery'] == 'SUCCESS':
            result.update(update='IDLE', boot_validation='PASS')
        return result
    if m['attempts_left'] <= 0:
        result = recover(work, c)
        save_meta(work)
        return result
    try:
        approved = slot_check(work, candidate, c['security_floor'])
    except Reject as exc:
        save_meta(work)
        return dict(recover(work, c), candidate_rejection=str(exc))
    left = m['attempts_left'] - 1
    save_meta(work, candidate, left)  # Persist BEFORE simulated transfer of control.
    if healthy:
        atomic_json(work / 'confirmed.json', dict(confirmed_slot=candidate,
                    security_floor=max(c['security_floor'], approved['security_version'])))
        save_meta(work)
        return dict(update='COMMITTED', booted_slot=candidate,
                    security_floor=confirmed(work)['security_floor'], attempts_left=left)
    if left == 0:
        result = recover(work, c)
        save_meta(work)
        return result
    return dict(update='TESTING_FAILED', booted_slot=candidate,
                confirmed_slot=c['confirmed_slot'], attempts_left=left)


def apply_trust(state, raw, signature, public, recovery_public=None):
    """In-memory protected-state model, NOT certificate path validation."""
    verify_signature(raw, signature, public)
    update = parse(raw)
    require(isinstance(update, dict), 'TRUST_SCHEMA_INVALID')
    mode = update.get('op')
    if mode == 'recover-trust-set':
        require(recovery_public is not None and public == recovery_public, 'RECOVERY_AUTHORITY_REQUIRED')
    else:
        require(mode == 'replace-trust-set' and public.hex() in state['accepted'],
                'TRUST_SIGNER_NOT_AUTHORIZED')
    require(type(update.get('from_epoch')) is int and update['from_epoch'] == state['epoch'],
            'TRUST_STATE_ROLLBACK')
    require(type(update.get('to_epoch')) is int and update['to_epoch'] > state['epoch'],
            'TRUST_STATE_ROLLBACK')
    keys = update.get('accepted')
    revoked = update.get('revoked', [])
    require(type(keys) is list and keys and type(revoked) is list, 'TRUST_SCHEMA_INVALID')
    require(all(type(k) is str and re.fullmatch('[0-9a-f]{64}', k)
                for k in keys + revoked), 'TRUST_SCHEMA_INVALID')
    require(len(set(keys)) == len(keys), 'TRUST_SCHEMA_INVALID')
    retired = set(state['revoked']) | set(revoked)
    require(not set(keys) & retired, 'REVOKED_KEY_REINTRODUCED')
    return dict(epoch=update['to_epoch'], accepted=keys, revoked=sorted(retired))


APPROVED = {(1, 3, 1), (1, 4, 1), (2, 4, 1), (2, 4, 2)}


def check_configuration(config):
    require(len(config) == 3 and all(type(v) is int for v in config), 'CONFIG_INVALID')
    require(not (config[0] >= 2 and config[1] < 4), 'DEPENDENCY_REJECTED')
    require(tuple(config) in APPROVED, 'CONFIG_NOT_APPROVED')


def vehicle(initial=(1, 3, 1), goal=(2, 4, 2), order='BAC', fail_c=False):
    check_configuration(initial)
    check_configuration(goal)
    require(sorted(order) == ['A', 'B', 'C'], 'ORDER_INVALID')
    planned = list(initial)
    path = [list(initial)]
    for name in order:
        i = 'ABC'.index(name)
        planned[i] = goal[i]
        check_configuration(planned)  # Preflight checks every intermediate state.
        path.append(planned.copy())
    actual = list(initial)
    for name in order:
        if name == 'C' and fail_c:
            continue
        i = 'ABC'.index(name)
        actual[i] = goal[i]
        check_configuration(actual)
    complete = actual == list(goal)
    return dict(path=path, actual=actual, configuration='ALLOWED',
                campaign='COMPLETE' if complete else 'INCOMPLETE',
                commit='PASS' if complete else 'BLOCKED')


def attempt(call):
    try:
        call()
        return 'PASS'
    except Reject as exc:
        return str(exc)


def crypto_demo(kind, attack=False):
    if kind == 'hash':
        h1, h2 = digest(TOY), digest(TOY_BAD)
        return dict(original=h1, changed=h2,
                    changed_bits=(int(h1, 16) ^ int(h2, 16)).bit_count(),
                    comparison=(h2 == (h2 if attack else h1)))
    if kind == 'mac':
        key = b'shared-key-2026'  # Public teaching constant, not a real secret.
        tag = hmac.digest(key, TOY, 'sha256')
        check = lambda msg, t: hmac.compare_digest(hmac.digest(key, msg, 'sha256'), t)
        return dict(original=check(TOY, tag), changed=check(TOY_BAD, tag),
                    zero_tag=check(TOY, bytes(32)),
                    leaked_key_forgery=check(TOY_BAD, hmac.digest(key, TOY_BAD, 'sha256')))
    key, evil = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    return dict(original=attempt(lambda: verify_signature(TOY, key.sign(TOY), public_bytes(key))),
                changed=attempt(lambda: verify_signature(TOY_BAD, key.sign(TOY), public_bytes(key))),
                wrong_signer=attempt(lambda: verify_signature(TOY, evil.sign(TOY), public_bytes(key))),
                replaced_key=attempt(lambda: verify_signature(TOY_BAD, evil.sign(TOY_BAD), public_bytes(evil))))


def package_demo(case='normal', work=None):
    key, evil = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    image = b'N' * SLOT_LEN
    overrides = {}
    if case == 'wrong_target':
        overrides['target'] = 'ECU-CHASSIS-07'
    if case == 'wrong_hardware':
        overrides['hardware_revision'] = 'rev1'
    if case == 'rollback':
        overrides['security_version'] = 5
    raw, signature, public = build_package(evil if case == 'wrong_signer' else key, image, **overrides)
    if case == 'bad_signature':
        signature = bytes(64)
    if case == 'whitespace':
        raw = json.dumps(json.loads(raw), indent=2).encode()
    m = verify_manifest(raw, signature, public, [public_bytes(key)], 6)
    if work is None:
        with tempfile.TemporaryDirectory() as folder:
            return package_demo_in_folder(folder, raw, m, image, case)
    return package_demo_in_folder(work, raw, m, image, case)


def package_demo_in_folder(folder, raw, m, image, case):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    require(not any(folder.iterdir()), 'WORK_DIRECTORY_NOT_EMPTY')
    (folder / 'manifest.json').write_bytes(raw)
    if case == 'chunk_corrupt':
        for i in range(5):
            data = image[i * CHUNK_SIZE:(i + 1) * CHUNK_SIZE]
            (folder / f'chunk_{i}.bin').write_bytes(b'X' + data[1:] if i == 2 else data)
        atomic_json(folder / 'download_state.json', dict(manifest_id=digest(raw), received=list(range(5))))
    joined, requests = receive_chunks(folder, raw, m, lambda start, end: image[start:end + 1])
    if case == 'tamper_after_join':
        joined = b'X' + joined[1:]
    validate_payload(joined, m)
    (folder / 'firmware.bin').write_bytes(joined)
    return dict(signature='PASS', signer='PASS', policy='PASS', requested=requests,
                image='PASS', payload_hash=digest(joined))


def trust_demo():
    a, b, recovery = [Ed25519PrivateKey.generate() for _ in range(3)]
    pa, pb, pr = [public_bytes(k) for k in (a, b, recovery)]
    initial = dict(epoch=1, accepted=[pa.hex()], revoked=[])
    raw = encode(dict(op='replace-trust-set', from_epoch=1, to_epoch=2, accepted=[pb.hex()], revoked=[pa.hex()]))
    updated = apply_trust(initial, raw, a.sign(raw), pa)
    old_replay = attempt(lambda: apply_trust(updated, raw, b.sign(raw), pb))
    # A compromised operating key can sign BOTH genuine and malicious transitions.
    forged = encode(dict(op='replace-trust-set', from_epoch=1, to_epoch=2, accepted=[pr.hex()]))
    compromise = attempt(lambda: apply_trust(initial, forged, a.sign(forged), pa))
    restoration = encode(dict(op='recover-trust-set', from_epoch=1, to_epoch=2,
                             accepted=[pb.hex()], revoked=[pa.hex()]))
    restored = apply_trust(initial, restoration, recovery.sign(restoration), pr, pr)
    return dict(epoch=updated['epoch'], revoked_old_key=True, replay=old_replay,
                compromised_operating_key=compromise, independent_recovery_epoch=restored['epoch'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for kind in ('hash', 'mac', 'sign'):
        p = sub.add_parser(kind)
        p.add_argument('--attack', action='store_true')
    sub.add_parser('trust')
    p = sub.add_parser('package')
    p.add_argument('--case', default='normal', choices=('normal', 'bad_signature', 'wrong_signer',
                   'whitespace', 'wrong_target', 'wrong_hardware', 'rollback', 'chunk_corrupt', 'tamper_after_join'))
    p.add_argument('--work')
    p = sub.add_parser('init')
    p.add_argument('--work', required=True)
    p = sub.add_parser('install')
    p.add_argument('--work', required=True)
    p.add_argument('--arch', choices=('ab', 'inplace'), default='ab')
    p.add_argument('--cut', choices=('WRITING',))
    p = sub.add_parser('boot')
    p.add_argument('--work', required=True)
    p.add_argument('--health', choices=('pass', 'fail'), default='pass')
    p = sub.add_parser('inject-floor')
    p.add_argument('--work', required=True)
    p.add_argument('--value', type=int, default=6)
    p = sub.add_parser('vehicle')
    p.add_argument('--initial', default='1/3/1')
    p.add_argument('--goal', default='2/4/2')
    p.add_argument('--order', default='BAC')
    p.add_argument('--fail-c', action='store_true')
    args = parser.parse_args()
    try:
        if args.command in ('hash', 'mac', 'sign'):
            result = crypto_demo(args.command, args.attack)
        elif args.command == 'trust':
            result = trust_demo()
        elif args.command == 'package':
            result = package_demo(args.case, args.work)
        elif args.command == 'init':
            initialize(args.work)
            result = dict(initialized=args.work)
        elif args.command == 'install':
            result = install(args.work, args.arch, args.cut is not None)
        elif args.command == 'boot':
            result = boot(args.work, args.health == 'pass')
        elif args.command == 'inject-floor':
            c = confirmed(args.work)
            require(args.value >= c['security_floor'], 'FLOOR_DECREASE_FORBIDDEN')
            c['security_floor'] = args.value
            atomic_json(Path(args.work) / 'confirmed.json', c)
            result = dict(fault_injection='EARLY_FLOOR_RAISE', security_floor=args.value)
        else:
            try:
                initial = tuple(int(v) for v in args.initial.split('/'))
                goal = tuple(int(v) for v in args.goal.split('/'))
            except ValueError as exc:
                raise Reject('CONFIG_INVALID') from exc
            result = vehicle(initial, goal, args.order, args.fail_c)
        print(json.dumps(result, indent=2))
        return 0
    except (Reject, OSError) as exc:
        print(json.dumps(dict(result='REJECTED', code=str(exc))))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
