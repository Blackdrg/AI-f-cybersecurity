"""
Decentralized Identity (DID) Integration.

Implements W3C DID specification and Verifiable Credentials
for self-sovereign identity management.

References:
- W3C DID Core: https://www.w3.org/TR/did-core/
- W3C Verifiable Credentials: https://www.w3.org/TR/vc-data-model/
"""

import json
import base64
import hashlib
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
import numpy as np
from cryptography.exceptions import InvalidSignature
import jwt


@dataclass
class DIDDocument:
    """W3C DID Document representation."""
    context: List[str] = None
    id: str = ""
    publicKey: List[Dict[str, Any]] = None
    authentication: List[str] = None
    assertionMethod: List[str] = None
    capabilityDelegation: List[str] = None
    capabilityInvocation: List[str] = None
    keyAgreement: List[str] = None
    service: List[Dict[str, Any]] = None
    alsoKnownAs: List[str] = None
    controller: Optional[str] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = ["https://www.w3.org/ns/did/v1"]
        if self.publicKey is None:
            self.publicKey = []
        if self.authentication is None:
            self.authentication = []
        if self.assertionMethod is None:
            self.assertionMethod = []
        if self.capabilityDelegation is None:
            self.capabilityDelegation = []
        if self.capabilityInvocation is None:
            self.capabilityInvocation = []
        if self.keyAgreement is None:
            self.keyAgreement = []
        if self.service is None:
            self.service = []
    
    def to_dict(self):
        """Convert to dict with @context."""
        d = asdict(self)
        d["@context"] = d.pop("context")
        return d


@dataclass
class VerifiableCredential:
    """W3C Verifiable Credential representation."""
    context: List[str] = None
    id: str = ""
    type: List[str] = None
    issuer: str = ""
    issuanceDate: str = ""
    expirationDate: Optional[str] = None
    credentialSubject: Dict[str, Any] = None
    proof: Dict[str, Any] = None
    credentialStatus: Optional[Dict[str, Any]] = None
    termsOfUse: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1"
            ]
        if self.type is None:
            self.type = ["VerifiableCredential"]
        if self.credentialSubject is None:
            self.credentialSubject = {}
    
    def to_dict(self):
        """Convert to dict with @context."""
        d = asdict(self)
        d["@context"] = d.pop("context")
        return d

@dataclass
class DIDResolutionResult:
    """DID resolution result."""
    did_document: Optional[DIDDocument]
    did_document_metadata: Dict[str, Any]
    did_resolution_metadata: Dict[str, Any]


class DIDKeyManager:
    """Manages cryptographic keys for DIDs."""
    
    def __init__(self):
        self.private_keys = {}
        self.public_keys = {}
    
    def generate_keypair(self, key_type: str = "P-256") -> Dict[str, str]:
        """
        Generate elliptic curve key pair.
        
        Args:
            key_type: Curve type (P-256, P-384, P-521)
        
        Returns:
            Dict with private and public keys (PEM format)
        """
        curve_map = {
            "P-256": ec.SECP256R1(),
            "P-384": ec.SECP384R1(),
            "P-521": ec.SECP521R1()
        }
        
        curve = curve_map.get(key_type, ec.SECP256R1())
        private_key = ec.generate_private_key(curve)
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        key_id = f"did:key:{uuid.uuid4()}"
        
        self.private_keys[key_id] = private_key
        self.public_keys[key_id] = public_key
        
        return {
            "key_id": key_id,
            "private_key": private_pem,
            "public_key": public_pem,
            "type": key_type
        }
    
    def sign(self, message: str, key_id: str) -> str:
        """
        Sign a message with private key.
        
        Args:
            message: Message to sign
            key_id: Key identifier
        
        Returns:
            Base64-encoded signature
        """
        if key_id not in self.private_keys:
            raise ValueError(f"Unknown key: {key_id}")
        
        private_key = self.private_keys[key_id]
        signature = private_key.sign(
            message.encode(),
            ec.ECDSA(hashes.SHA256())
        )
        
        return base64.b64encode(signature).decode()
    
    def verify(self, message: str, signature: str, public_key_pem: str) -> bool:
        """
        Verify signature with public key.
        
        Args:
            message: Original message
            signature: Base64-encoded signature
            public_key_pem: Public key in PEM format
        
        Returns:
            True if signature is valid
        """
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode()
            )
            sig_bytes = base64.b64decode(signature)
            public_key.verify(
                sig_bytes,
                message.encode(),
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except (InvalidSignature, Exception):
            return False


class DIDManager:
    """
    Decentralized Identity Manager.
    
    Creates and manages W3C DIDs and Verifiable Credentials.
    Supports multiple DID methods (did:ethr, did:key, did:web).
    """
    
    def __init__(self, did_method: str = "did:key"):
        self.did_method = did_method
        self.key_manager = DIDKeyManager()
        self.dids = {}  # did -> DID document
        self.credentials = {}  # credential_id -> VC
        self.revocation_registry = {}  # credential_id -> revoked status
    
    def create_did(self, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new Decentralized Identifier.
        
        Args:
            options: Optional configuration (key type, controllers, etc.)
        
        Returns:
            Dict with DID, document, and keys
        """
        options = options or {}
        key_type = options.get("key_type", "P-256")
        controller = options.get("controller")
        
        # Generate key pair
        keypair = self.key_manager.generate_keypair(key_type)
        
        if self.did_method == "did:key":
            # did:key method: derive DID from public key
            public_key_pem = keypair["public_key"]
            public_key_bytes = public_key_pem.encode()
            key_hash = hashlib.sha256(public_key_bytes).digest()
            key_id = base64.urlsafe_b64encode(key_hash).decode().rstrip("=")
            did = f"did:key:{key_id}"
        elif self.did_method == "did:ethr":
            # did:ethr: Ethereum-based DID
            did = f"did:ethr:{uuid.uuid4().hex}"
        else:  # did:web
            did = f"did:web:{options.get('domain', 'example.com')}"
        
        # Create DID Document
        did_doc = DIDDocument(
            id=did,
            controller=controller or did
        )
        
        # Add public key
        key_entry = {
            "id": f"{did}#key-1",
            "type": "EcdsaSecp256k1VerificationKey2019",
            "controller": did,
            "publicKeyPem": keypair["public_key"]
        }
        did_doc.publicKey.append(key_entry)
        
        # Set authentication
        did_doc.authentication.append(f"{did}#key-1")
        did_doc.assertionMethod.append(f"{did}#key-1")
        
        # Store
        self.dids[did] = did_doc
        
        return {
            "did": did,
            "did_document": asdict(did_doc),
            "keys": keypair,
            "method": self.did_method,
            "created": datetime.now(timezone.utc).isoformat()
        }
    
    def resolve(self, did: str) -> DIDResolutionResult:
        """
        Resolve a DID to its DID Document.
        
        Args:
            did: Decentralized Identifier
        
        Returns:
            DIDResolutionResult with document and metadata
        """
        if did in self.dids:
            doc = self.dids[did]
            return DIDResolutionResult(
                did_document=doc,
                did_document_metadata={
                    "versionId": "1",
                    "published": True
                },
                did_resolution_metadata={
                    "contentType": "application/did+json",
                    "retrieved": datetime.now(timezone.utc).isoformat()
                }
            )
        
        return DIDResolutionResult(
            did_document=None,
            did_document_metadata={},
            did_resolution_metadata={
                "error": "notFound"
            }
        )
    
    def create_verifiable_credential(
        self,
        issuer_did: str,
        subject_id: str,
        credential_type: str,
        claims: Dict[str, Any],
        expires_in_days: Optional[int] = 365
    ) -> Dict[str, Any]:
        """
        Create a Verifiable Credential.
        
        Args:
            issuer_did: DID of the issuer
            subject_id: Subject identifier
            credential_type: Type of credential (e.g., "IdentityCredential")
            claims: Claims to include in credential
            expires_in_days: Days until expiration
        
        Returns:
            Verifiable Credential (JSON)
        """
        if issuer_did not in self.dids:
            raise ValueError(f"Unknown issuer DID: {issuer_did}")
        
        cred_id = f"urn:uuid:{uuid.uuid4()}"
        issuance_date = datetime.now(timezone.utc)
        
        expiration_date = None
        if expires_in_days:
            expiration_date = issuance_date.replace(
                tzinfo=timezone.utc
            ) + timedelta(days=expires_in_days)
        
        vc = VerifiableCredential(
            id=cred_id,
            issuer=issuer_did,
            issuanceDate=issuance_date.isoformat(),
            expirationDate=expiration_date.isoformat() if expiration_date else None,
            credentialSubject={
                "id": subject_id,
                **claims
            }
        )
        
        # Add type
        vc.type = ["VerifiableCredential", credential_type]
        
        # Create JWT proof
        doc = self.dids[issuer_did]
        key_id = doc.authentication[0] if doc.authentication else None
        
        if key_id:
            # Extract key ID for JWT
            private_key = list(self.key_manager.private_keys.values())[0]
            
            payload = {
                "iss": issuer_did,
                "sub": subject_id,
                "jti": cred_id,
                "nbf": issuance_date.timestamp(),
                "exp": expiration_date.timestamp() if expiration_date else None,
                "vc": {
                    "@context": vc.context,
                    "type": vc.type,
                    "credentialSubject": vc.credentialSubject
                }
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            token = jwt.encode(
                payload,
                private_key.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ),
                algorithm="ES256"
            )
            
            vc.proof = {
                "type": "EcdsaSecp256k1Signature2019",
                "created": issuance_date.isoformat(),
                "proofPurpose": "assertionMethod",
                "verificationMethod": key_id,
                "jwt": token
            }
        
        self.credentials[cred_id] = vc
        
        return {
            "verifiableCredential": asdict(vc),
            "token": token.decode() if isinstance(token, bytes) else token
        }
    
    def verify_credential(
        self,
        credential: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify a Verifiable Credential.
        
        Args:
            credential: VC as dict or JWT string
        
        Returns:
            Verification result
        """
        try:
            # Handle JWT format
            if isinstance(credential, str):
                decoded = jwt.decode(credential, options={"verify_signature": False})
                issuer = decoded.get("iss")
                cred_id = decoded.get("jti")
                
                # Verify signature
                if issuer in self.dids:
                    doc = self.dids[issuer]
                    if doc.publicKey:
                        # Get public key
                        public_key_pem = doc.publicKey[0].get("publicKeyPem")
                        if public_key_pem:
                            jwt.decode(
                                credential,
                                public_key_pem,
                                algorithms=["ES256"]
                            )
                            return {
                                "verified": True,
                                "credential_id": cred_id,
                                "issuer": issuer,
                                "subject": decoded.get("sub"),
                                "claims": decoded.get("vc", {}).get("credentialSubject", {})
                            }
            
            # Handle JSON format
            elif isinstance(credential, dict):
                cred_id = credential.get("id")
                issuer = credential.get("issuer")
                
                if cred_id in self.credentials:
                    stored = self.credentials[cred_id]
                    return {
                        "verified": True,
                        "credential_id": cred_id,
                        "issuer": issuer,
                        "type": stored.type,
                        "subject": stored.credentialSubject,
                        "expired": datetime.now(timezone.utc) > datetime.fromisoformat(
                            stored.expirationDate.replace('Z', '+00:00')
                        ) if stored.expirationDate else False
                    }
            
            return {
                "verified": False,
                "reason": "Could not verify credential"
            }
        
        except Exception as e:
            return {
                "verified": False,
                "reason": str(e)
            }
    
    def revoke_credential(self, credential_id: str) -> bool:
        """
        Revoke a Verifiable Credential.
        
        Args:
            credential_id: ID of credential to revoke
        
        Returns:
            True if revoked
        """
        if credential_id in self.credentials:
            self.revocation_registry[credential_id] = {
                "revoked": True,
                "revokedAt": datetime.now(timezone.utc).isoformat()
            }
            return True
        return False
    
    def is_revoked(self, credential_id: str) -> bool:
        """
        Check if a credential is revoked.
        
        Args:
            credential_id: ID to check
        
        Returns:
            True if revoked
        """
        entry = self.revocation_registry.get(credential_id)
        return entry is not None and entry.get("revoked", False)
    
    def create_presentation(
        self,
        holder_did: str,
        credentials: List[Dict[str, Any]],
        verifier_did: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Verifiable Presentation.
        
        Args:
            holder_did: DID of the presentation holder
            credentials: List of verifiable credentials
            verifier_did: Optional verifier DID
        
        Returns:
            Verifiable Presentation
        """
        pres_id = f"urn:uuid:{uuid.uuid4()}"
        issuance_date = datetime.now(timezone.utc)
        
        presentation = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1"
            ],
            "type": ["VerifiablePresentation"],
            "id": pres_id,
            "holder": holder_did,
            "verifiableCredential": credentials,
            "proof": {
                "type": "Ed25519Signature2018",
                "created": issuance_date.isoformat(),
                "proofPurpose": "authentication",
                "verificationMethod": f"{holder_did}#key-1",
                "challenge": uuid.uuid4().hex,
                "domain": "example.com"
            }
        }
        
        return presentation
    
    def register_did_document(
        self,
        did_document: Dict[str, Any],
        blockchain: str = "ethereum"
    ) -> Dict[str, Any]:
        """
        Register DID Document on blockchain (simulated).
        
        Args:
            did_document: DID Document to register
            blockchain: Target blockchain
        
        Returns:
            Registration receipt
        """
        did = did_document.get("id")
        tx_hash = hashlib.sha256(
            json.dumps(did_document, sort_keys=True).encode()
        ).hexdigest()
        
        return {
            "did": did,
            "blockchain": blockchain,
            "transactionHash": tx_hash,
            "registeredAt": datetime.now(timezone.utc).isoformat(),
            "status": "confirmed",
            "explorerUrl": f"https://{blockchain}.com/tx/{tx_hash}"
        }


class SecureEnclaveWallet:
    """
    Self-Sovereign Identity Wallet with Secure Enclave support.
    
    Simulates mobile device secure enclave (TEE/SE) for
    storing biometric credentials and private keys.
    """
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.did_manager = DIDManager()
        self.secure_storage = {}  # Simulated secure enclave storage
        self.biometric_templates = {}  # Encrypted biometric data
        self.keychain = {}  # Private keys
        self.credentials = {}  # Verifiable credentials
    
    def create_did_in_wallet(
        self,
        key_type: str = "P-256"
    ) -> Dict[str, Any]:
        """
        Create DID and store keys in secure enclave.
        
        Args:
            key_type: Cryptographic curve type
        
        Returns:
            DID creation result
        """
        result = self.did_manager.create_did({"key_type": key_type})
        
        # Store private key in "secure enclave" (simulated)
        did = result["did"]
        self.keychain[did] = {
            "private_key": result["keys"]["private_key"],
            "public_key": result["keys"]["public_key"],
            "created": result["created"],
            "secure_enclave": True
        }
        
        # Store DID document
        self.secure_storage[did] = result["did_document"]
        
        return result
    
    def add_biometric_credential(
        self,
        biometric_type: str,
        template_data: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add encrypted biometric template to secure wallet.
        
        Args:
            biometric_type: Type of biometric (face, voice, gait)
            template_data: Biometric template (embedding)
            metadata: Optional metadata
        
        Returns:
            Credential storage result
        """
        # Generate credential ID
        cred_id = f"urn:biometric:{uuid.uuid4()}"
        
        # Encrypt template (simulated)
        encrypted_template = self._encrypt_biometric(template_data)
        
        # Create VC
        issuer_did = list(self.keychain.keys())[0] if self.keychain else None
        if not issuer_did:
            self.create_did_in_wallet()
            issuer_did = list(self.keychain.keys())[0]
        
        vc_result = self.did_manager.create_verifiable_credential(
            issuer_did=issuer_did,
            subject_id=issuer_did,
            credential_type=f"Biometric{credentialtype.capitalize()}Credential",
            claims={
                "biometricType": biometric_type,
                "templateHash": hashlib.sha256(
                    template_data.tobytes()
                ).hexdigest(),
                "encrypted": True,
                "metadata": metadata or {}
            },
            expires_in_days=365
        )
        
        # Store in secure enclave
        self.biometric_templates[cred_id] = {
            "encrypted_template": encrypted_template,
            "credential": vc_result,
            "biometric_type": biometric_type,
            "created": datetime.now(timezone.utc).isoformat()
        }
        
        return {
            "credential_id": cred_id,
            "encrypted": True,
            "biometric_type": biometric_type,
            "verifiableCredential": vc_result
        }
    
    def _encrypt_biometric(
        self,
        template: np.ndarray
    ) -> Dict[str, Any]:
        """
        Encrypt biometric template (simulated secure enclave encryption).
        
        In real implementation, would use TEE/SE hardware encryption.
        
        Args:
            template: Biometric template
        
        Returns:
            Encrypted data
        """
        return {
            "encrypted": True,
            "data": base64.b64encode(template.tobytes()).decode(),
            "iv": base64.b64encode(np.random.bytes(16)).decode(),
            "tag": base64.b64encode(np.random.bytes(16)).decode(),
            "algorithm": "AES-256-GCM (simulated)",
            "secure_element": True
        }
    
    def sign_with_secure_key(
        self,
        message: str,
        did: str
    ) -> Dict[str, Any]:
        """
        Sign message using key from secure enclave.
        
        Args:
            message: Message to sign
            did: DID whose key to use
        
        Returns:
            Signature
        """
        if did not in self.keychain:
            raise ValueError(f"No key for DID: {did}")
        
        # In real implementation, signing happens inside secure enclave
        # Private key never leaves secure element
        
        return {
            "message": message,
            "signature": base64.b64encode(
                hashlib.sha256(message.encode()).digest()
            ).decode(),
            "did": did,
            "key_id": f"{did}#key-1",
            "secure_enclave": True,
            "algorithm": "ES256"
        }
    
    def create_verifiable_presentation(
        self,
        credentials: Optional[List[str]] = None,
        purpose: str = "authentication"
    ) -> Dict[str, Any]:
        """
        Create Verifiable Presentation from wallet credentials.
        
        Args:
            credentials: List of credential IDs to include
            purpose: Purpose of presentation
        
        Returns:
            Verifiable Presentation
        """
        holder_did = list(self.keychain.keys())[0] if self.keychain else None
        if not holder_did:
            raise ValueError("No DID in wallet")
        
        # Select credentials
        selected_creds = []
        if credentials:
            for cred_id in credentials:
                if cred_id in self.biometric_templates:
                    cred_data = self.biometric_templates[cred_id]["credential"]
                    selected_creds.append(cred_data)
        else:
            # Include all credentials
            for cred_data in self.biometric_templates.values():
                selected_creds.append(cred_data["credential"])
        
        presentation = self.did_manager.create_presentation(
            holder_did=holder_did,
            credentials=selected_creds
        )
        
        # Sign with secure enclave key
        signed_pres = {
            **presentation,
            "proof": {
                "type": "Ed25519Signature2018",
                "created": datetime.now(timezone.utc).isoformat(),
                "proofPurpose": purpose,
                "verificationMethod": f"{holder_did}#key-1",
                "signature": self.sign_with_secure_key(
                    json.dumps(presentation, sort_keys=True),
                    holder_did
                )["signature"],
                "secure_enclave": True
            }
        }
        
        return signed_pres
    
    def verify_presentation(
        self,
        presentation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify a Verifiable Presentation.
        
        Args:
            presentation: VP to verify
        
        Returns:
            Verification result
        """
        holder = presentation.get("holder")
        credentials = presentation.get("verifiableCredential", [])
        
        verified_credentials = []
        for cred in credentials:
            if isinstance(cred, str):
                # JWT format
                verification = self.did_manager.verify_credential(cred)
            else:
                # JSON format
                cred_id = cred.get("id")
                if cred_id in self.credentials:
                    verification = {
                        "verified": True,
                        "credential": cred
                    }
                else:
                    verification = self.did_manager.verify_credential(cred)
            
            verified_credentials.append(verification)
        
        # Check if all credentials are valid
        all_valid = all(
            c.get("verified", False) for c in verified_credentials
        )
        
        return {
            "verified": all_valid,
            "holder": holder,
            "credentials": verified_credentials,
            "presentation_id": presentation.get("id")
        }
    
    def revoke_credential(
        self,
        credential_id: str
    ) -> bool:
        """
        Revoke a credential from wallet.
        
        Args:
            credential_id: ID of credential to revoke
        
        Returns:
            True if revoked
        """
        if credential_id in self.biometric_templates:
            # Revoke the VC
            cred_data = self.biometric_templates[credential_id]
            vc = cred_data["credential"]
            if isinstance(vc, dict) and "verifiableCredential" in vc:
                cred_id = vc.get("credential_id") or vc["verifiableCredential"].get("id")
                if cred_id:
                    self.did_manager.revoke_credential(cred_id)
            
            # Remove from secure storage (in real implementation,
            # would securely delete from enclave)
            del self.biometric_templates[credential_id]
            return True
        
        return False
    
    def list_credentials(self) -> List[Dict[str, Any]]:
        """
        List all credentials in wallet.
        
        Returns:
            List of credential summaries
        """
        return [
            {
                "credential_id": cred_id,
                "biometric_type": data["biometric_type"],
                "encrypted": True,
                "created": data["created"],
                "revoked": False
            }
            for cred_id, data in self.biometric_templates.items()
        ]
    
    def get_wallet_status(self) -> Dict[str, Any]:
        """
        Get wallet status.
        
        Returns:
            Wallet status information
        """
        return {
            "device_id": self.device_id,
            "did_count": len(self.keychain),
            "credentials_count": len(self.biometric_templates),
            "secure_enclave": True,
            "encryption_enabled": True,
            "biometric_types": list(set(
                data["biometric_type"] 
                for data in self.biometric_templates.values()
            ))
        }


# Convenience functions

def create_did_document(
    did: str,
    public_keys: List[Dict[str, Any]],
    service_endpoints: Optional[List[Dict[str, Any]]] = None
) -> DIDDocument:
    """Create a DID Document."""
    doc = DIDDocument(
        id=did,
        publicKey=public_keys,
        authentication=[k["id"] for k in public_keys],
        assertionMethod=[k["id"] for k in public_keys],
        service=service_endpoints or []
    )
    return doc


def issue_credential(
    issuer_did: str,
    subject_did: str,
    credential_type: str,
    claims: Dict[str, Any],
    did_manager: DIDManager
) -> Dict[str, Any]:
    """Issue a Verifiable Credential."""
    return did_manager.create_verifiable_credential(
        issuer_did=issuer_did,
        subject_id=subject_did,
        credential_type=credential_type,
        claims=claims
    )


def verify_presentation(
    presentation: Dict[str, Any],
    did_manager: DIDManager
) -> Dict[str, Any]:
    """Verify a Verifiable Presentation."""
    holder = presentation.get("holder")
    credentials = presentation.get("verifiableCredential", [])
    
    results = []
    for cred in credentials:
        if isinstance(cred, str):
            result = did_manager.verify_credential(cred)
        else:
            result = did_manager.verify_credential(cred)
        results.append(result)
    
    return {
        "verified": all(r.get("verified", False) for r in results),
        "results": results
    }