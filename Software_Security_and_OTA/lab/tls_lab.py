"""Local-only PKI/TLS/HTTP Range lab. No external server is contacted."""

from datetime import datetime, timedelta, timezone
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
import tempfile
import threading

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from otalab import Reject, require, SLOT_LEN, digest, build_package, public_bytes, verify_manifest, receive_chunks
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def new_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def certificate(name, key, issuer_cert=None, issuer_key=None, ca=False, usage=None, expired=False):
    now = datetime.now(timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    issuer = issuer_cert.subject if issuer_cert else subject
    start = now - timedelta(days=5)
    end = now - timedelta(days=1) if expired else now + timedelta(days=30)
    b = (x509.CertificateBuilder().subject_name(subject).issuer_name(issuer)
         .public_key(key.public_key()).serial_number(x509.random_serial_number())
         .not_valid_before(start).not_valid_after(end)
         .add_extension(x509.BasicConstraints(ca=ca, path_length=1 if ca and issuer_cert is None else 0 if ca else None), True)
         .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                        key_encipherment=not ca, data_encipherment=False, key_agreement=False,
                        key_cert_sign=ca, crl_sign=ca, encipher_only=False, decipher_only=False), True))
    if usage is not None:
        b = b.add_extension(x509.ExtendedKeyUsage([usage]), False)
    if usage == ExtendedKeyUsageOID.SERVER_AUTH:
        b = b.add_extension(x509.SubjectAlternativeName([
            x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), False)
    return b.sign(issuer_key or key, hashes.SHA256())


def verify_fixed_chain(chain, trusted_root, expected_usage, now=None):
    """Restricted generated RSA Root->Intermediate->Leaf exercise.

    This is NOT a general X.509 path builder: it omits CRL/OCSP, policy and
    name constraints, alternate paths and arbitrary critical extensions.
    TLS verification below is delegated to Python/OpenSSL.
    """
    require(len(chain) == 3, 'PATH_INVALID')
    root, intermediate, leaf = chain
    require(root.fingerprint(hashes.SHA256()) == trusted_root.fingerprint(hashes.SHA256()), 'UNTRUSTED_ROOT')
    now = now or datetime.now(timezone.utc)
    for cert in chain:
        require(cert.not_valid_before_utc <= now <= cert.not_valid_after_utc, 'CERT_EXPIRED')
    for child, issuer in ((root, root), (intermediate, root), (leaf, intermediate)):
        require(child.issuer == issuer.subject, 'ISSUER_MISMATCH')
        try:
            issuer.public_key().verify(child.signature, child.tbs_certificate_bytes,
                                       padding.PKCS1v15(), child.signature_hash_algorithm)
        except InvalidSignature as exc:
            raise Reject('CERT_SIGNATURE_INVALID') from exc
    for cert in (root, intermediate):
        require(cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca, 'CA_REQUIRED')
        require(cert.extensions.get_extension_for_class(x509.KeyUsage).value.key_cert_sign, 'CA_USAGE_INVALID')
    require(root.extensions.get_extension_for_class(x509.BasicConstraints).value.path_length >= 1,
            'PATH_LENGTH_INVALID')
    require(not leaf.extensions.get_extension_for_class(x509.BasicConstraints).value.ca, 'LEAF_INVALID')
    require(leaf.extensions.get_extension_for_class(x509.KeyUsage).value.digital_signature, 'LEAF_USAGE_INVALID')
    require(expected_usage in leaf.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value,
            'WRONG_USAGE')
    return True


def fixtures():
    root_key, intermediate_key, leaf_key = [new_key() for _ in range(3)]
    root = certificate('LAB Root', root_key, ca=True)
    intermediate = certificate('LAB Intermediate', intermediate_key, root, root_key, ca=True)
    signer = certificate('LAB Signer', leaf_key, intermediate, intermediate_key,
                         usage=ExtendedKeyUsageOID.CODE_SIGNING)
    server = certificate('localhost', leaf_key, intermediate, intermediate_key,
                         usage=ExtendedKeyUsageOID.SERVER_AUTH)
    expired = certificate('LAB Expired', leaf_key, intermediate, intermediate_key,
                          usage=ExtendedKeyUsageOID.CODE_SIGNING, expired=True)
    attacker_key = new_key()
    attacker_root = certificate('OTHER Root', attacker_key, ca=True)
    return root, intermediate, signer, server, expired, attacker_root, leaf_key


def pki_demo():
    root, intermediate, signer, server, expired, attacker_root, _ = fixtures()
    out = {}
    for name, chain, trust in [('trusted_chain', [root, intermediate, signer], root),
                               ('expired_leaf', [root, intermediate, expired], root),
                               ('wrong_usage', [root, intermediate, server], root),
                               ('attacker_chain', [root, intermediate, signer], attacker_root)]:
        try:
            verify_fixed_chain(chain, trust, ExtendedKeyUsageOID.CODE_SIGNING)
            out[name] = 'PASS'
        except Reject as exc:
            out[name] = str(exc)
    return out


def fetch_range(context, port, start, end, total):
    require(type(start) is int and type(end) is int and 0 <= start <= end < total, 'RANGE_INVALID')
    conn = http.client.HTTPSConnection('localhost', port, context=context, timeout=5)
    try:
        conn.request('GET', '/firmware.bin', headers={'Range': f'bytes={start}-{end}'})
        response = conn.getresponse()
        require(response.status == 206, 'RANGE_STATUS_REJECTED')
        require(response.getheader('Content-Range') == f'bytes {start}-{end}/{total}', 'CONTENT_RANGE_REJECTED')
        expected = end - start + 1
        require(response.getheader('Content-Length') == str(expected), 'RANGE_LENGTH_REJECTED')
        data = response.read(expected + 1)
        require(len(data) == expected, 'RANGE_LENGTH_REJECTED')
        return data
    finally:
        conn.close()


def tls_demo():
    root, intermediate, _, server_cert, _, _, server_key = fixtures()
    image = b'N' * SLOT_LEN

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            match = re.fullmatch(r'bytes=(\d+)-(\d+)', self.headers.get('Range', ''))
            if self.path != '/firmware.bin' or not match:
                self.send_error(400)
                return
            start, end = map(int, match.groups())
            if not 0 <= start <= end < len(image):
                self.send_error(416)
                return
            data = image[start:end + 1]
            self.send_response(206)
            self.send_header('Content-Range', f'bytes {start}-{end}/{len(image)}')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        (folder / 'root.pem').write_bytes(root.public_bytes(serialization.Encoding.PEM))
        (folder / 'server.pem').write_bytes(server_cert.public_bytes(serialization.Encoding.PEM)
                                          + intermediate.public_bytes(serialization.Encoding.PEM))
        (folder / 'server.key').write_bytes(server_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.minimum_version = ssl.TLSVersion.TLSv1_3
        server_context.load_cert_chain(folder / 'server.pem', folder / 'server.key')
        client_context = ssl.create_default_context(cafile=str(folder / 'root.pem'))
        client_context.minimum_version = ssl.TLSVersion.TLSv1_3
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        httpd.socket = server_context.wrap_socket(httpd.socket, server_side=True)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        port = httpd.server_address[1]
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=5) as sock:
                with client_context.wrap_socket(sock, server_hostname='localhost') as conn:
                    version = conn.version()
            mismatch = 'UNEXPECTED_PASS'
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=5) as sock:
                    with client_context.wrap_socket(sock, server_hostname='other.invalid'):
                        pass
            except ssl.SSLCertVerificationError:
                mismatch = 'HOSTNAME_REJECTED'
            key = Ed25519PrivateKey.generate()
            raw, sig, public = build_package(key, image)
            m = verify_manifest(raw, sig, public, [public_bytes(key)], 6)
            assembled, requested = receive_chunks(folder / 'download', raw, m,
                lambda start, end: fetch_range(client_context, port, start, end, len(image)))
            return dict(tls=version, name_match='PASS', name_mismatch=mismatch,
                        requested=requested, payload_hash=digest(assembled), image='PASS')
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=5)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('pki', 'tls'))
    args = parser.parse_args()
    print(json.dumps(pki_demo() if args.mode == 'pki' else tls_demo(), indent=2))
