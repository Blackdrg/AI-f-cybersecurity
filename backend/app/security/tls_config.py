import ssl
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def get_ssl_context(server_side: bool = True) -> Optional[ssl.SSLContext]:
    """
    Returns an SSL context configured for TLS 1.3 and mTLS if enabled.
    In production, this enforces strict certificate validation and TLS 1.3.
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    cert_file = os.getenv("SSL_CERT_FILE", "certs/server.crt")
    key_file = os.getenv("SSL_KEY_FILE", "certs/server.key")
    ca_file = os.getenv("SSL_CA_FILE", "certs/ca.crt")
    mtls_enabled = os.getenv("MTLS_ENABLED", "false").lower() == "true"

    # Production requirement check
    if env == "production":
        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            logger.error(f"CRITICAL: SSL certificates missing in production environment ({cert_file}).")
            raise FileNotFoundError(f"SSL certificates required for production at {cert_file}")
    
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        logger.warning(f"SSL certificates not found at {cert_file}. Running without TLS (Degraded Mode).")
        return None

    try:
        context = ssl.create_default_context(
            ssl.Purpose.CLIENT_AUTH if server_side else ssl.Purpose.SERVER_AUTH
        )
        
        # Enforce TLS 1.3 as the minimum (and only) version for enterprise security
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.options |= ssl.OP_NO_TLSv1_2
        
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        
        if mtls_enabled:
            if ca_file and os.path.exists(ca_file):
                context.load_verify_locations(cafile=ca_file)
                context.verify_mode = ssl.CERT_REQUIRED
                logger.info("mTLS enabled and CA certificate successfully loaded.")
            else:
                logger.error("mTLS enabled but CA_FILE is missing or invalid. Security risk!")
                if env == "production":
                    raise ValueError("mTLS enabled but CA_FILE missing in production")
        
        return context
    except Exception as e:
        logger.error(f"Failed to initialize SSL context: {e}")
        if env == "production":
            raise
        return None
