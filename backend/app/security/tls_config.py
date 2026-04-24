import ssl
import os
import logging

logger = logging.getLogger(__name__)

def get_ssl_context(server_side: bool = True):
    """
    Returns an SSL context configured for TLS 1.3 and mTLS if enabled.
    """
    cert_file = os.getenv("SSL_CERT_FILE", "certs/server.crt")
    key_file = os.getenv("SSL_KEY_FILE", "certs/server.key")
    ca_file = os.getenv("SSL_CA_FILE", "certs/ca.crt")
    mtls_enabled = os.getenv("MTLS_ENABLED", "false").lower() == "true"

    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        logger.warning(f"SSL certificates not found at {cert_file}. Returning None.")
        return None

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH if server_side else ssl.Purpose.SERVER_AUTH)
    
    # Enforce TLS 1.3
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    
    if mtls_enabled and ca_file and os.path.exists(ca_file):
        context.load_verify_locations(cafile=ca_file)
        context.verify_mode = ssl.CERT_REQUIRED
        logger.info("mTLS enabled and CA loaded.")
    
    return context
