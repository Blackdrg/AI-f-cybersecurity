"""
gRPC Client for Face Recognition Service
Used by edge devices, mobile apps, and external systems
"""
import grpc
from typing import Optional, List, Tuple
import asyncio
import numpy as np
import cv2
import os

# Import generated protobuf classes
try:
    from .face_recognition_pb2_grpc import FaceRecognitionServiceStub
    from .face_recognition_pb2 import (
        EnrollRequest, EnrollResponse,
        RecognizeRequest, RecognizeResponse,
        GetPersonRequest, GetPersonResponse,
        DeletePersonRequest, DeleteResponse,
        AuditLogsRequest, AuditLogsResponse
    )
    PROTO_AVAILABLE = True
except ImportError:
    PROTO_AVAILABLE = False
    raise ImportError("Protobuf files not generated. Run: python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. face_recognition.proto")


class FaceRecognitionClient:
    """Client for gRPC Face Recognition Service"""
    
    def __init__(self, host: str = "localhost:50051", token: str = None, secure: bool = True):
        self.host = host
        self.token = token
        self.secure = secure
        self._channel = None
        self._stub = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def connect(self):
        """Establish gRPC channel"""
        if self.secure:
            # Load TLS certificates from environment or default paths
            cert_path = os.getenv("SSL_CERT_FILE", "/app/certs/client.crt")
            key_path = os.getenv("SSL_KEY_FILE", "/app/certs/client.key")
            ca_path = os.getenv("SSL_CA_FILE", "/app/certs/ca.crt")
            
            with open(key_path, 'rb') as f:
                private_key = f.read()
            with open(cert_path, 'rb') as f:
                certificate_chain = f.read()
            with open(ca_path, 'rb') as f:
                root_certificates = f.read()
            
            credentials = grpc.ssl_channel_credentials(
                root_certificates=root_certificates,
                private_key=private_key,
                certificate_chain=certificate_chain
            )
            self._channel = grpc.aio.secure_channel(self.host, credentials)
        else:
            self._channel = grpc.aio.insecure_channel(self.host)
        
        self._stub = FaceRecognitionServiceStub(self._channel)
    
    async def close(self):
        """Close channel"""
        if self._channel:
            await self._channel.close()
    
    def _metadata(self):
        """Build auth metadata"""
        if self.token:
            return (('authorization', f'Bearer {self.token}'),)
        return ()
    
    async def enroll(self, name: str, images: List[np.ndarray], consent: bool = True,
                     camera_id: str = None, voice_files: List[bytes] = None,
                     gait_video: bytes = None, metadata: dict = None) -> str:
        """
        Enroll a new identity.
        
        Args:
            name: Person's name
            images: List of face images (numpy arrays)
            consent: GDPR consent obtained
            camera_id: Source camera identifier
            voice_files: Optional voice recordings
            gait_video: Optional gait analysis video
            metadata: Additional enrollment data
        
        Returns:
            person_id: Unique identifier for enrolled person
        """
        if not PROTO_AVAILABLE:
            raise RuntimeError("Protobuf not available")
        
        # Convert images to bytes
        image_bytes = []
        for img in images:
            _, buf = cv2.imencode('.jpg', img)
            image_bytes.append(buf.tobytes())
        
        request = EnrollRequest(
            name=name,
            images=image_bytes,
            consent=consent,
            camera_id=camera_id or "",
            voice_files=voice_files or [],
            gait_video=gait_video or b'',
            physiological_data=json.dumps(metadata or {}),
        )
        
        response = await self._stub.Enroll(request, metadata=self._metadata())
        return response.person_id
    
    async def recognize(self, image: np.ndarray, top_k: int = 5, threshold: float = 0.7,
                        camera_id: str = None, enable_spoof_check: bool = True,
                        enable_emotion: bool = False, enable_age_gender: bool = False,
                        enable_behavior: bool = False, voice_file: bytes = None,
                        gait_video: bytes = None, physiological_data: str = "") -> Dict:
        """
        Recognize face in image.
        
        Returns:
            Dict with detected faces and matches
        """
        if not PROTO_AVAILABLE:
            raise RuntimeError("Protobuf not available")
        
        _, img_bytes = cv2.imencode('.jpg', image)
        
        request = RecognizeRequest(
            image=img_bytes.tobytes(),
            top_k=top_k,
            threshold=threshold,
            camera_id=camera_id or "",
            enable_spoof_check=enable_spoof_check,
            enable_emotion=enable_emotion,
            enable_age_gender=enable_age_gender,
            enable_behavior=enable_behavior,
            voice_file=voice_file or b'',
            gait_video=gait_video or b'',
            physiological_data=physiological_data,
        )
        
        response = await self._stub.Recognize(request, metadata=self._metadata())
        
        # Convert response to dict
        faces = []
        for face in response.faces:
            face_dict = {
                "face_box": list(face.face_box),
                "inference_ms": face.inference_ms,
                "is_unknown": face.is_unknown,
                "matches": [
                    {
                        "person_id": m.person_id,
                        "name": m.name if m.HasField('name') else None,
                        "score": m.score,
                        "distance": m.distance
                    } for m in face.matches
                ]
            }
            if face.HasField('spoof_score'):
                face_dict["spoof_score"] = face.spoof_score
            if face.HasField('reconstruction_confidence'):
                face_dict["reconstruction_confidence"] = face.reconstruction_confidence
            if face.HasField('emotion'):
                face_dict["emotion"] = {"emotion": face.emotion.emotion, "confidence": face.emotion.confidence}
            if face.HasField('age'):
                face_dict["age"] = face.age
            if face.HasField('gender'):
                face_dict["gender"] = face.gender
            if face.HasField('behavior'):
                face_dict["behavior"] = {"behavior": face.behavior.behavior, "confidence": face.behavior.confidence}
            
            faces.append(face_dict)
        
        return {"faces": faces}
    
    async def get_person(self, person_id: str) -> Optional[Dict]:
        """Get person details by ID"""
        if not PROTO_AVAILABLE:
            raise RuntimeError("Protobuf not available")
        
        request = GetPersonRequest(person_id=person_id)
        response = await self._stub.GetPerson(request, metadata=self._metadata())
        return {
            "person_id": response.person_id,
            "name": response.name if response.HasField('name') else None,
            "embeddings": list(response.embeddings),
            "consent_record": {
                "consent_record_id": response.consent_record.consent_record_id,
                "timestamp": response.consent_record.timestamp,
                "client_id": response.consent_record.client_id,
                "consent_text_version": response.consent_record.consent_text_version,
                "captured_ip": response.consent_record.captured_ip,
            }
        }
    
    async def delete_person(self, person_id: str) -> bool:
        """Delete person and all associated data"""
        if not PROTO_AVAILABLE:
            raise RuntimeError("Protobuf not available")
        
        request = DeletePersonRequest(person_id=person_id)
        response = await self._stub.DeletePerson(request, metadata=self._metadata())
        return response.deleted


# Convenience wrapper for synchronous usage (blocking)
class SyncFaceRecognitionClient:
    """Synchronous wrapper for the async gRPC client"""
    
    def __init__(self, host: str = "localhost:50051", token: str = None, secure: bool = True):
        self.host = host
        self.token = token
        self.secure = secure
        self._loop = None
    
    def _get_loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop
    
    def enroll(self, *args, **kwargs) -> str:
        loop = self._get_loop()
        async_client = FaceRecognitionClient(self.host, self.token, self.secure)
        try:
            return loop.run_until_complete(async_client.enroll(*args, **kwargs))
        finally:
            loop.run_until_complete(async_client.close())
    
    def recognize(self, *args, **kwargs) -> Dict:
        loop = self._get_loop()
        async_client = FaceRecognitionClient(self.host, self.token, self.secure)
        try:
            return loop.run_until_complete(async_client.recognize(*args, **kwargs))
        finally:
            loop.run_until_complete(async_client.close())
    
    def get_person(self, person_id: str) -> Optional[Dict]:
        loop = self._get_loop()
        async_client = FaceRecognitionClient(self.host, self.token, self.secure)
        try:
            return loop.run_until_complete(async_client.get_person(person_id))
        finally:
            loop.run_until_complete(async_client.close())
    
    def delete_person(self, person_id: str) -> bool:
        loop = self._get_loop()
        async_client = FaceRecognitionClient(self.host, self.token, self.secure)
        try:
            return loop.run_until_complete(async_client.delete_person(person_id))
        finally:
            loop.run_until_complete(async_client.close())
