import requests
import json
from typing import List, Dict, Optional, Union, Any
import io
import os
from pathlib import Path


class AIFClientError(Exception):
    """Base exception for AI-f SDK errors."""
    pass


class AuthenticationError(AIFClientError):
    """Raised when authentication fails."""
    pass


class APIError(AIFClientError):
    """Raised when API returns an error."""
    def __init__(self, message: str, status_code: int, response: Dict[str, Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class AIFClient:
    """
    Official Python SDK for AI-f Enterprise Face Recognition.
    
    Provides a simple interface for face recognition, enrollment, and
    management operations.
    
    Example:
        >>> from ai_f_sdk.client import AIFClient
        >>> client = AIFClient(base_url="http://localhost:8000", api_key="your-api-key")
        >>> result = client.recognize(image_path="person.jpg")
        >>> print(f"Recognized: {result['faces'][0]['matches'][0]['name']}")
    """
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        """
        Initialize the AI-f client.
        
        Args:
            base_url: Base URL of the AI-f server (e.g., http://localhost:8000)
            api_key: API key for authentication
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self._session = None

    @property
    def session(self) -> requests.Session:
        """Get or create a requests session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(self.headers)
        return self._session

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response and raise appropriate errors.
        
        Args:
            response: The response object from requests
            
        Returns:
            Parsed JSON response data
            
        Raises:
            AuthenticationError: If authentication fails (401/403)
            APIError: For other API errors
        """
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key or token expired")
        elif response.status_code == 403:
            raise AuthenticationError("Insufficient permissions")
        elif response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get('detail', error_data.get('message', response.text))
            except:
                message = response.text
            raise APIError(
                message=f"API Error ({response.status_code}): {message}",
                status_code=response.status_code,
                response=error_data if 'error_data' in locals() else None
            )
        
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"raw_response": response.text}

    def recognize(self, image_path: Union[str, Path], top_k: int = 1, 
                  threshold: float = 0.4, camera_id: Optional[str] = None,
                  enable_spoof_check: bool = True) -> Dict[str, Any]:
        """
        Perform face recognition on an image file.
        
        Args:
            image_path: Path to the image file
            top_k: Number of top matches to return (default: 1)
            threshold: Recognition threshold (0-1, default: 0.4)
            camera_id: Optional camera ID for filtering
            enable_spoof_check: Whether to enable liveness detection (default: True)
            
        Returns:
            Recognition result with faces and matches
            
        Example:
            >>> result = client.recognize("person.jpg", top_k=3)
            >>> for face in result['faces']:
            ...     for match in face['matches']:
            ...         print(f"  {match['name']}: {match['score']:.2%}")
        """
        url = f"{self.base_url}/api/recognize"
        
        with open(image_path, 'rb') as f:
            files = {'image': (os.path.basename(image_path), f, 'image/jpeg')}
            data = {
                'top_k': top_k,
                'threshold': threshold,
                'enable_spoof_check': enable_spoof_check
            }
            if camera_id:
                data['camera_id'] = camera_id
            
            response = self.session.post(
                url, 
                files=files, 
                data=data,
                timeout=self.timeout
            )
        
        return self._handle_response(response)

    def recognize_bytes(self, image_data: bytes, filename: str = "image.jpg",
                       top_k: int = 1, threshold: float = 0.4,
                       camera_id: Optional[str] = None,
                       enable_spoof_check: bool = True) -> Dict[str, Any]:
        """
        Perform face recognition on image bytes.
        
        Args:
            image_data: Raw image bytes
            filename: Filename for the upload (default: "image.jpg")
            top_k: Number of top matches to return
            threshold: Recognition threshold (0-1)
            camera_id: Optional camera ID for filtering
            enable_spoof_check: Whether to enable liveness detection
            
        Returns:
            Recognition result with faces and matches
        """
        url = f"{self.base_url}/api/recognize"
        
        files = {'image': (filename, image_data, 'image/jpeg')}
        data = {
            'top_k': top_k,
            'threshold': threshold,
            'enable_spoof_check': enable_spoof_check
        }
        if camera_id:
            data['camera_id'] = camera_id
        
        response = self.session.post(
            url,
            files=files,
            data=data,
            timeout=self.timeout
        )
        
        return self._handle_response(response)

    def enroll(self, name: str, images: List[Union[str, Path]],
               consent: bool = True, camera_id: Optional[str] = None,
               metadata: Optional[str] = None, age: Optional[int] = None,
               gender: Optional[str] = None) -> Dict[str, Any]:
        """
        Enroll a new person with multiple face images.
        
        Args:
            name: Person's name
            images: List of image file paths
            consent: Whether consent was obtained (default: True)
            camera_id: Optional camera ID
            metadata: Optional metadata JSON string
            age: Optional age
            gender: Optional gender
            
        Returns:
            Enrollment result with person_id
            
        Example:
            >>> result = client.enroll(
            ...     name="John Doe",
            ...     images=["photo1.jpg", "photo2.jpg"],
            ...     consent=True
            ... )
            >>> print(f"Enrolled: {result['person_id']}")
        """
        url = f"{self.base_url}/api/enroll"
        
        # Prepare files
        files = []
        for img in images:
            img_path = Path(img)
            files.append((
                'images',
                (img_path.name, open(img_path, 'rb'), 'image/jpeg')
            ))
        
        data = {
            'name': name,
            'consent': str(consent).lower()
        }
        if camera_id:
            data['camera_id'] = camera_id
        if metadata:
            data['metadata'] = metadata
        if age is not None:
            data['age'] = str(age)
        if gender:
            data['gender'] = gender
        
        try:
            response = self.session.post(
                url,
                files=files,
                data=data,
                timeout=self.timeout
            )
        finally:
            # Close all file handles
            for _, file_tuple in files:
                file_tuple[1].close()
        
        return self._handle_response(response)

    def enroll_bytes(self, name: str, image_data_list: List[bytes],
                    filenames: Optional[List[str]] = None,
                    consent: bool = True, camera_id: Optional[str] = None,
                    metadata: Optional[str] = None,
                    age: Optional[int] = None,
                    gender: Optional[str] = None) -> Dict[str, Any]:
        """
        Enroll a new person with image bytes.
        
        Args:
            name: Person's name
            image_data_list: List of image byte data
            filenames: Optional filenames for each image (default: "image_0.jpg", etc.)
            consent: Whether consent was obtained
            camera_id: Optional camera ID
            metadata: Optional metadata JSON string
            age: Optional age
            gender: Optional gender
            
        Returns:
            Enrollment result with person_id
        """
        url = f"{self.base_url}/api/enroll"
        
        if filenames is None:
            filenames = [f"image_{i}.jpg" for i in range(len(image_data_list))]
        
        files = [
            ('images', (fn, data, 'image/jpeg'))
            for fn, data in zip(filenames, image_data_list)
        ]
        
        data = {
            'name': name,
            'consent': str(consent).lower()
        }
        if camera_id:
            data['camera_id'] = camera_id
        if metadata:
            data['metadata'] = metadata
        if age is not None:
            data['age'] = str(age)
        if gender:
            data['gender'] = gender
        
        response = self.session.post(
            url,
            files=files,
            data=data,
            timeout=self.timeout
        )
        
        return self._handle_response(response)

    def get_person(self, person_id: str) -> Dict[str, Any]:
        """
        Get person details.
        
        Args:
            person_id: Unique person identifier
            
        Returns:
            Person details including embeddings
        """
        url = f"{self.base_url}/api/persons/{person_id}"
        
        response = self.session.get(url, timeout=self.timeout)
        return self._handle_response(response)

    def update_person(self, person_id: str, name: Optional[str] = None,
                     age: Optional[int] = None,
                     gender: Optional[str] = None) -> Dict[str, Any]:
        """
        Update person details.
        
        Args:
            person_id: Unique person identifier
            name: New name (optional)
            age: New age (optional)
            gender: New gender (optional)
            
        Returns:
            Updated person details
        """
        url = f"{self.base_url}/api/persons/{person_id}"
        
        data = {}
        if name is not None:
            data['name'] = name
        if age is not None:
            data['age'] = age
        if gender is not None:
            data['gender'] = gender
        
        response = self.session.put(url, json=data, timeout=self.timeout)
        return self._handle_response(response)

    def delete_person(self, person_id: str) -> Dict[str, Any]:
        """
        Delete a person and all associated data.
        
        Args:
            person_id: Unique person identifier
            
        Returns:
            Deletion confirmation
            
        Note:
            This operation is irreversible and deletes all associated
            embeddings, audit logs, and related data.
        """
        url = f"{self.base_url}/api/persons/{person_id}"
        
        response = self.session.delete(url, timeout=self.timeout)
        return self._handle_response(response)

    def search_persons(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search for persons by name or metadata.
        
        Args:
            query: Search query string
            limit: Maximum number of results (default: 10)
            
        Returns:
            List of matching persons
        """
        url = f"{self.base_url}/api/persons/search"
        
        params = {
            'query': query,
            'limit': limit
        }
        
        response = self.session.get(url, params=params, timeout=self.timeout)
        return self._handle_response(response)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get system metrics and statistics.
        
        Returns:
            System metrics including recognition counts, latency, etc.
        """
        url = f"{self.base_url}/api/metrics"
        
        response = self.session.get(url, timeout=self.timeout)
        return self._handle_response(response)

    def get_health(self) -> Dict[str, Any]:
        """
        Check system health status.
        
        Returns:
            Health status of all system components
            
        Example:
            >>> health = client.get_health()
            >>> if health['status'] == 'ok':
            ...     print("System is healthy")
        """
        url = f"{self.base_url}/api/health"
        
        response = self.session.get(url, timeout=self.timeout)
        return self._handle_response(response)

    def get_audit_logs(self, limit: int = 100, start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      action: Optional[str] = None,
                      person_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get audit logs for compliance and forensics.
        
        Args:
            limit: Maximum number of log entries (default: 100)
            start_date: Filter logs from this date (ISO format)
            end_date: Filter logs until this date (ISO format)
            action: Filter by specific action type
            person_id: Filter by specific person
            
        Returns:
            List of audit log entries
            
        Example:
            >>> logs = client.get_audit_logs(
            ...     limit=50,
            ...     action='enroll',
            ...     start_date='2024-01-01T00:00:00Z'
            ... )
        """
        url = f"{self.base_url}/api/audit"
        
        params = {
            'limit': limit
        }
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if action:
            params['action'] = action
        if person_id:
            params['person_id'] = person_id
        
        response = self.session.get(
            url,
            params=params,
            timeout=self.timeout
        )
        return self._handle_response(response)

    def get_usage(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get usage statistics and quotas.
        
        Args:
            user_id: Optional user ID (defaults to authenticated user)
            
        Returns:
            Usage statistics including limits and current usage
        """
        if user_id:
            url = f"{self.base_url}/api/usage/{user_id}"
        else:
            url = f"{self.base_url}/api/usage"
        
        response = self.session.get(url, timeout=self.timeout)
        return self._handle_response(response)

    def close(self):
        """Close the client session."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Backward compatibility alias
FaceRecognitionSDK = AIFClient