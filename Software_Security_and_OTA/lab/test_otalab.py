"""Checks security rejection paths and persisted recovery, not just happy output."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import otalab as ota
import tls_lab


class SecureOTATest(unittest.TestCase):
    def rejected(self, code, call):
        with self.assertRaises(ota.Reject) as caught:
            call()
        self.assertEqual(str(caught.exception), code)

    def test_crypto(self):
        self.assertEqual(ota.crypto_demo('hash')['changed_bits'], 120)
        self.assertFalse(ota.crypto_demo('hash')['comparison'])
        self.assertTrue(ota.crypto_demo('hash', True)['comparison'])
        self.assertEqual(ota.crypto_demo('mac'), dict(original=True, changed=False,
                         zero_tag=False, leaked_key_forgery=True))
        self.assertEqual(ota.crypto_demo('sign'), dict(original='PASS', changed='SIGNATURE_INVALID',
                         wrong_signer='SIGNATURE_INVALID', replaced_key='PASS'))

    def test_package_failures(self):
        cases = {'bad_signature': 'SIGNATURE_INVALID', 'whitespace': 'SIGNATURE_INVALID',
                 'wrong_signer': 'SIGNER_NOT_AUTHORIZED', 'wrong_target': 'TARGET_MISMATCH',
                 'wrong_hardware': 'HARDWARE_MISMATCH', 'rollback': 'SECURITY_VERSION_TOO_LOW',
                 'tamper_after_join': 'PAYLOAD_HASH_REJECTED'}
        for case, code in cases.items():
            with self.subTest(case=case):
                self.rejected(code, lambda: ota.package_demo(case))
        self.assertEqual(ota.package_demo()['image'], 'PASS')

    def test_input_and_last_chunk(self):
        key = Ed25519PrivateKey.generate()
        pub = ota.public_bytes(key)
        raw, _, _ = ota.build_package(key, b'x' * 65537)
        def check(data):
            return ota.verify_manifest(data, key.sign(data), pub, [pub], 6)
        m = check(raw)
        self.assertEqual(ota.chunk_range(m, 1), (65536, 65536))
        with tempfile.TemporaryDirectory() as folder:
            image, requests = ota.receive_chunks(folder, raw, m, lambda s, e: (b'x' * 65537)[s:e + 1])
            self.assertEqual(len(image), 65537)
            self.assertEqual(requests, [0, 1])
        self.rejected('DUPLICATE_JSON_KEY', lambda: check(b'{"size":1,"size":2}'))
        changed = json.loads(raw)
        changed['size'] = True
        self.rejected('SCHEMA_INVALID', lambda: check(ota.encode(changed)))
        changed['size'] = ota.MAX_IMAGE + 1
        self.rejected('SIZE_LIMIT', lambda: check(ota.encode(changed)))
        changed['size'] = 65537
        changed['chunk_hashes'] = []
        self.rejected('CHUNK_COUNT_INVALID', lambda: check(ota.encode(changed)))

    def test_resume_revalidates_local_bytes(self):
        result = ota.package_demo('chunk_corrupt')
        self.assertEqual(result['requested'], [2, 5, 6, 7])
        key = Ed25519PrivateKey.generate()
        raw, sig, pub = ota.build_package(key, b'x' * 100)
        m = ota.verify_manifest(raw, sig, pub, [pub], 6)
        with tempfile.TemporaryDirectory() as folder:
            ota.atomic_json(Path(folder) / 'download_state.json', dict(manifest_id='other', received=[]))
            self.rejected('RESUME_MANIFEST_MISMATCH', lambda: ota.receive_chunks(folder, raw, m, lambda s, e: b'x'))
        with tempfile.TemporaryDirectory() as folder:
            self.rejected('CHUNK_HASH_REJECTED', lambda: ota.receive_chunks(folder, raw, m, lambda s, e: b'y' * 100))

    def test_interrupted_install_in_new_process(self):
        for arch in ('ab', 'inplace'):
            with self.subTest(arch=arch), tempfile.TemporaryDirectory() as folder:
                ota.initialize(folder)
                result = ota.install(folder, arch, cut=True)
                self.assertEqual(result['old_preserved'], arch == 'ab')
                self.assertEqual((Path(folder) / 'A.bin').stat().st_size, ota.SLOT_LEN)
                p = subprocess.run([sys.executable, str(Path(ota.__file__)), 'boot', '--work', folder],
                                   capture_output=True, text=True, check=True)
                after = json.loads(p.stdout)
                self.assertEqual(after['booted_slot'], 'A' if arch == 'ab' else None)
                self.assertEqual(after['recovery'], 'SUCCESS' if arch == 'ab' else 'FORBIDDEN')
                self.assertEqual(ota.confirmed(folder)['security_floor'], 5)

    def test_commit_and_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            ota.initialize(folder)
            ota.install(folder)
            self.assertEqual(ota.confirmed(folder)['confirmed_slot'], 'A')
            result = ota.boot(folder, healthy=True)
            self.assertEqual(result['update'], 'COMMITTED')
            self.assertEqual(ota.confirmed(folder), dict(confirmed_slot='B', security_floor=6))
            self.assertEqual(ota.boot(folder)['booted_slot'], 'B')
        with tempfile.TemporaryDirectory() as folder:
            ota.initialize(folder)
            ota.install(folder)
            self.assertEqual(ota.boot(folder, False)['attempts_left'], 2)
            self.assertEqual(ota.load_meta(folder)[1]['attempts_left'], 2)
            self.assertEqual(ota.boot(folder, False)['attempts_left'], 1)
            self.assertEqual(ota.boot(folder, False)['booted_slot'], 'A')
            self.assertEqual(ota.confirmed(folder)['security_floor'], 5)
        with tempfile.TemporaryDirectory() as folder:
            ota.initialize(folder)
            ota.install(folder)
            ota.atomic_json(Path(folder) / 'confirmed.json', dict(confirmed_slot='A', security_floor=6))
            for _ in range(3):
                result = ota.boot(folder, False)
            self.assertEqual(result['code'], 'RECOVERY_FORBIDDEN')
            self.assertEqual(result['mode'], 'RECOVERY')

    def test_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            ota.initialize(folder)
            ota.save_meta(folder, 'B', 3)
            latest_index, _ = ota.load_meta(folder)
            (Path(folder) / f'meta{latest_index}.json').write_bytes(b'{partial')
            self.assertEqual(ota.load_meta(folder)[1]['seq'], 0)
            (Path(folder) / f'meta{1-latest_index}.json').write_bytes(b'{partial')
            self.rejected('BOOT_METADATA_INVALID', lambda: ota.load_meta(folder))
        invalid = ota.make_meta(1, 'B', 4)
        self.assertFalse(ota.meta_valid(invalid))
        with tempfile.TemporaryDirectory() as folder:
            ota.initialize(folder)
            ota.atomic_json(Path(folder) / 'meta0.json', ota.make_meta(1, 'B', 3))
            ota.atomic_json(Path(folder) / 'meta1.json', ota.make_meta(1, 'B', 2))
            self.rejected('BOOT_METADATA_CONFLICT', lambda: ota.load_meta(folder))
        with tempfile.TemporaryDirectory() as folder:
            ota.initialize(folder)
            ota.install(folder)
            # Simulate a durable commit with stale, not-yet-cleared candidate metadata.
            ota.atomic_json(Path(folder) / 'confirmed.json', dict(confirmed_slot='B', security_floor=6))
            self.assertEqual(ota.boot(folder)['update'], 'IDLE')
            self.assertIsNone(ota.load_meta(folder)[1]['candidate_slot'])

    def test_trust(self):
        a, b, r = [Ed25519PrivateKey.generate() for _ in range(3)]
        pa, pb, pr = [ota.public_bytes(k) for k in (a, b, r)]
        initial = dict(epoch=1, accepted=[pa.hex()], revoked=[])
        raw = ota.encode(dict(op='replace-trust-set', from_epoch=1, to_epoch=2, accepted=[pb.hex()], revoked=[pa.hex()]))
        state = ota.apply_trust(initial, raw, a.sign(raw), pa)
        old = ota.encode(dict(op='replace-trust-set', from_epoch=1, to_epoch=2, accepted=[pb.hex()]))
        self.rejected('TRUST_STATE_ROLLBACK', lambda: ota.apply_trust(state, old, b.sign(old), pb))
        resurrect = ota.encode(dict(op='replace-trust-set', from_epoch=2, to_epoch=3, accepted=[pa.hex()]))
        self.rejected('REVOKED_KEY_REINTRODUCED', lambda: ota.apply_trust(state, resurrect, b.sign(resurrect), pb))
        recover = ota.encode(dict(op='recover-trust-set', from_epoch=1, to_epoch=2, accepted=[pb.hex()], revoked=[pa.hex()]))
        self.rejected('RECOVERY_AUTHORITY_REQUIRED', lambda: ota.apply_trust(initial, recover, a.sign(recover), pa, pr))
        self.assertEqual(ota.apply_trust(initial, recover, r.sign(recover), pr, pr)['epoch'], 2)

    def test_vehicle(self):
        self.assertEqual(ota.vehicle()['campaign'], 'COMPLETE')
        result = ota.vehicle(fail_c=True)
        self.assertEqual(result['actual'], [2, 4, 1])
        self.assertEqual((result['configuration'], result['campaign'], result['commit']),
                         ('ALLOWED', 'INCOMPLETE', 'BLOCKED'))
        self.rejected('DEPENDENCY_REJECTED', lambda: ota.vehicle(goal=(2, 3, 1)))
        self.rejected('CONFIG_NOT_APPROVED', lambda: ota.vehicle(goal=(2, 5, 1)))
        self.rejected('DEPENDENCY_REJECTED', lambda: ota.vehicle(order='ABC'))

    def test_pki(self):
        self.assertEqual(tls_lab.pki_demo(), dict(trusted_chain='PASS', expired_leaf='CERT_EXPIRED',
                         wrong_usage='WRONG_USAGE', attacker_chain='UNTRUSTED_ROOT'))

    def test_local_tls_and_ranges(self):
        result = tls_lab.tls_demo()
        self.assertEqual(result['tls'], 'TLSv1.3')
        self.assertEqual(result['name_mismatch'], 'HOSTNAME_REJECTED')
        self.assertEqual(result['requested'], list(range(8)))
        self.assertEqual(result['image'], 'PASS')

    def test_bad_range_responses(self):
        class Response:
            status = 206
            headers = {'Content-Range': 'bytes 0-3/4', 'Content-Length': '4'}
            data = b'abcd'

            def getheader(self, name):
                return self.headers.get(name)

            def read(self, limit):
                return self.data[:limit]

        cases = [(200, Response.headers, b'abcd', 'RANGE_STATUS_REJECTED'),
                 (206, {'Content-Range': 'bytes 1-3/4', 'Content-Length': '4'}, b'abcd', 'CONTENT_RANGE_REJECTED'),
                 (206, {'Content-Range': 'bytes 0-3/4', 'Content-Length': '5'}, b'abcd', 'RANGE_LENGTH_REJECTED'),
                 (206, Response.headers, b'ab', 'RANGE_LENGTH_REJECTED')]
        for status, headers, data, code in cases:
            with self.subTest(code=code), patch('tls_lab.http.client.HTTPSConnection') as connection:
                response = Response()
                response.status, response.headers, response.data = status, headers, data
                connection.return_value.getresponse.return_value = response
                self.rejected(code, lambda: tls_lab.fetch_range(None, 1, 0, 3, 4))


if __name__ == '__main__':
    unittest.main()
