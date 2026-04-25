#!/usr/bin/env python3
"""
Generate self-signed certificates for gRPC TLS/mTLS development.
Production should use real certificates from a CA (Let's Encrypt, HashiCorp Vault, etc.).
"""

import os
import ssl
import datetime
from pathlib import Path

CERTS_DIR = Path("certs")
CERTS_DIR.mkdir(exist_ok=True)

# Certificate validity (1 year for dev)
NOT_BEFORE = datetime.datetime.utcnow()
NOT_AFTER = NOT_BEFORE + datetime.timedelta(days=365)

# Subject info
COUNTRY = "US"
STATE = "California"
LOCALITY = "San Francisco"
ORG_NAME = "FaceRecognition Dev"
COMMON_NAME = "localhost"  # For dev; use actual domain in prod

def generate_ca():
    """Generate a self-signed CA certificate."""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    # Generate CA private key
    ca_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )

    # Build CA subject
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, COUNTRY),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, STATE),
        x509.NameAttribute(NameOID.LOCALITY_NAME, LOCALITY),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, ORG_NAME),
        x509.NameAttribute(NameOID.COMMON_NAME, "FaceRecognition CA"),
    ])

    # Build CA certificate
    ca_cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        subject
    ).public_key(
        ca_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        NOT_BEFORE
    ).not_valid_after(
        NOT_AFTER
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=0), critical=True
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=True,
            crl_sign=True,
            encipher_only=False,
            decipher_only=False,
        ), critical=True
    ).sign(ca_key, hashes.SHA256())

    # Write CA cert
    ca_cert_path = CERTS_DIR / "ca.crt"
    with open(ca_cert_path, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
    print(f"[OK] Generated CA certificate: {ca_cert_path}")

    # Write CA key (keep secure)
    ca_key_path = CERTS_DIR / "ca.key"
    with open(ca_key_path, "wb") as f:
        f.write(ca_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    print(f"✓ Generated CA private key: {ca_key_path}")

    return ca_cert, ca_key

def generate_server_cert(ca_cert, ca_key):
    """Generate server certificate signed by the CA."""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    # Server private key
    server_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Server subject
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, COUNTRY),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, STATE),
        x509.NameAttribute(NameOID.LOCALITY_NAME, LOCALITY),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, ORG_NAME),
        x509.NameAttribute(NameOID.COMMON_NAME, COMMON_NAME),
    ])

    # Server certificate
    server_cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        ca_cert.subject
    ).public_key(
        server_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        NOT_BEFORE
    ).not_valid_after(
        NOT_AFTER
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=True,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ), critical=True
    ).add_extension(
        x509.ExtendedKeyUsage([
            x509.ExtendedKeyUsageOID.SERVER_AUTH,
            x509.ExtendedKeyUsageOID.CLIENT_AUTH,  # For mTLS
        ]), critical=False
    ).sign(ca_key, hashes.SHA256())

    # Write server cert
    server_cert_path = CERTS_DIR / "server.crt"
    with open(server_cert_path, "wb") as f:
        f.write(server_cert.public_bytes(serialization.Encoding.PEM))
    print(f"✓ Generated server certificate: {server_cert_path}")

    # Write server key
    server_key_path = CERTS_DIR / "server.key"
    with open(server_key_path, "wb") as f:
        f.write(server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    print(f"✓ Generated server private key: {server_key_path}")

    return server_cert, server_key

def generate_client_cert(ca_cert, ca_key):
    """Generate a client certificate for mTLS testing."""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    # Client private key
    client_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Client subject
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, COUNTRY),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, STATE),
        x509.NameAttribute(NameOID.LOCALITY_NAME, LOCALITY),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, ORG_NAME),
        x509.NameAttribute(NameOID.COMMON_NAME, "test-client"),
    ])

    # Client certificate
    client_cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        ca_cert.subject
    ).public_key(
        client_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        NOT_BEFORE
    ).not_valid_after(
        NOT_AFTER
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=True,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ), critical=True
    ).add_extension(
        x509.ExtendedKeyUsage([
            x509.ExtendedKeyUsageOID.CLIENT_AUTH,
        ]), critical=False
    ).sign(ca_key, hashes.SHA256())

    # Write client cert
    client_cert_path = CERTS_DIR / "client.crt"
    with open(client_cert_path, "wb") as f:
        f.write(client_cert.public_bytes(serialization.Encoding.PEM))
    print(f"✓ Generated client certificate: {client_cert_path}")

    # Write client key
    client_key_path = CERTS_DIR / "client.key"
    with open(client_key_path, "wb") as f:
        f.write(client_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    print(f"✓ Generated client private key: {client_key_path}")

    return client_cert, client_key

if __name__ == "__main__":
    print("Generating development certificates for gRPC TLS/mTLS...")
    print(f"Certificates will be saved to: {CERTS_DIR.absolute()}")
    print()

    try:
        ca_cert, ca_key = generate_ca()
        server_cert, server_key = generate_server_cert(ca_cert, ca_key)
        client_cert, client_key = generate_client_cert(ca_cert, ca_key)

        print()
        print("✅ All certificates generated successfully!")
        print()
        print("To use with gRPC server:")
        print("  export SSL_CERT_FILE=certs/server.crt")
        print("  export SSL_KEY_FILE=certs/server.key")
        print("  export SSL_CA_FILE=certs/ca.crt")
        print("  export MTLS_ENABLED=true")
        print()
        print("To use with gRPC client (mTLS):")
        print("  Provide client.crt and client.key to client credentials")
        print()
        print("NOTE: These are self-signed certificates for development ONLY.")
        print("      For production, use certificates from a trusted CA.")
    except ImportError as e:
        print(f"Error: Missing cryptography library. Install with: pip install cryptography")
        print(f"Details: {e}")
        exit(1)
    except Exception as e:
        print(f"Error generating certificates: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
