"""
Voice embedding extractor using speechbrain's ECAPA-TDNN model.
Provides speaker embeddings for voice-based recognition.
"""

import logging
from typing import Optional, Dict, Any

import numpy as np

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from speechbrain.inference.speaker import EncoderClassifier
    SPEECHBRAIN_AVAILABLE = True
except ImportError:
    SPEECHBRAIN_AVAILABLE = False

logger = logging.getLogger(__name__)


class VoiceLivenessDetector:
    """Detects voice liveness to prevent replay attacks."""
    
    def detect_liveness(self, audio_signal: np.ndarray, sample_rate: int = 16000) -> Dict[str, Any]:
        """
        Analyze audio for signs of replay attacks.
        
        Args:
            audio_signal: Audio samples as numpy array
            sample_rate: Sample rate in Hz
            
        Returns:
            Dictionary with liveness detection results
        """
        try:
            # Spectral analysis for replay detection
            replay_indicator = self._detect_replay_spectral(audio_signal, sample_rate)
            noise_score = self._analyze_noise_consistency(audio_signal, sample_rate)
            tremor_ratio = self._detect_tremor(audio_signal, sample_rate)
            
            # Combine indicators
            liveness_score = (
                (1.0 - replay_indicator) * 0.5 +
                noise_score * 0.3 +
                (1.0 - tremor_ratio) * 0.2
            )
            liveness_score = max(0.0, min(1.0, liveness_score))
            
            return {
                "liveness_score": float(liveness_score),
                "is_live": liveness_score > 0.6,
                "replay_indicator": float(replay_indicator),
                "noise_consistency": float(noise_score),
                "tremor_ratio": float(tremor_ratio),
                "method": "spectral_analysis"
            }
        except Exception as e:
            logger.warning(f"Voice liveness detection failed: {e}")
            return {
                "liveness_score": 0.5,
                "is_live": False,
                "error": str(e)
            }
    
    def _detect_replay_spectral(self, signal: np.ndarray, sr: int) -> float:
        """Detect spectral artifacts from replay devices."""
        try:
            from scipy import signal as sig
            # Analyze frequency response for device-specific patterns
            # Simplified: check for unusual spectral flatness
            fft = np.fft.rfft(signal)
            magnitude = np.abs(fft)
            spectral_flatness = np.exp(np.mean(np.log(magnitude + 1e-10))) / (np.mean(magnitude) + 1e-10)
            # Lower flatness suggests more tonal (potentially replayed) content
            return min(1.0, max(0.0, 1.0 - spectral_flatness * 10))
        except:
            return 0.5
    
    def _analyze_noise_consistency(self, signal: np.ndarray, sr: int) -> float:
        """Analyze noise patterns for consistency."""
        # Real recordings have variable noise; replayed may have consistent noise
        frames = np.array_split(signal, 10)
        frame_energies = [np.var(f) for f in frames if len(f) > 0]
        if len(frame_energies) < 2:
            return 0.5
        energy_variation = np.std(frame_energies) / (np.mean(frame_energies) + 1e-10)
        # Low variation suggests replay
        return min(1.0, energy_variation * 5)
    
    def _detect_tremor(self, signal: np.ndarray, sr: int) -> float:
        """Detect tremor in audio (natural in speech, absent in replay)."""
        try:
            # Envelope analysis
            analytic_signal = np.abs(sig.hilbert(signal))
            env_fft = np.abs(np.fft.rfft(analytic_signal))
            freqs = np.fft.rfftfreq(len(analytic_signal), 1/sr)
            
            # Look for tremor frequency band (4-8 Hz)
            tremor_band = (freqs >= 4) & (freqs <= 8)
            if np.any(tremor_band):
                tremor_energy = np.sum(env_fft[1:][tremor_band[1:]])
                total_energy = np.sum(env_fft[1:])
                tremor_ratio = tremor_energy / (total_energy + 1e-10)
            else:
                tremor_ratio = 0.0
        except:
            tremor_ratio = 0.0
        return tremor_ratio


class VoiceEmbedder:
    """Extracts voice embeddings for speaker recognition."""
    
    def __init__(self):
        """Initialize voice embedder with ECAPA-TDNN model."""
        self.model = None
        self.liveness_detector = VoiceLivenessDetector()
        
        if SPEECHBRAIN_AVAILABLE and TORCH_AVAILABLE:
            try:
                self.model = EncoderClassifier.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb",
                    savedir="tmp/spkrec-ecapa-voxceleb"
                )
                logger.info("Voice embedder initialized with ECAPA-TDNN")
            except Exception as e:
                logger.warning(f"Failed to load ECAPA-TDNN model: {e}")
                self.model = None
        else:
            logger.warning("SpeechBrain or PyTorch not available, voice embedding disabled")
    
    def get_embedding(self, audio_path: str) -> np.ndarray:
        """
        Extract voice embedding from audio file.
        
        Args:
            audio_path: Path to audio file (WAV format recommended)
            
        Returns:
            192-dimensional embedding vector (ECAPA-TDNN output)
        """
        if self.model is None:
            # Return random embedding if model not available
            return np.random.randn(192).astype(np.float32)
        
        try:
            # Load audio
            signal, fs = librosa.load(audio_path, sr=16000)
            
            # Extract embedding
            with torch.no_grad():
                embedding = self.model.encode_batch(torch.tensor(signal).unsqueeze(0))
                embedding = embedding.squeeze().numpy().astype(np.float32)
            
            # L2 normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding
        except Exception as e:
            logger.error(f"Voice embedding extraction failed: {e}")
            return np.random.randn(192).astype(np.float32)
    
    def verify_liveness(self, audio_path: str) -> Dict[str, Any]:
        """
        Verify voice liveness to prevent replay attacks.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Liveness detection results
        """
        try:
            signal, sr = librosa.load(audio_path, sr=16000)
            return self.liveness_detector.detect_liveness(signal, sr)
        except Exception as e:
            logger.error(f"Liveness verification failed: {e}")
            return {"liveness_score": 0.0, "is_live": False, "error": str(e)}
    
    def get_embedding_from_signal(self, signal: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        Extract embedding directly from audio signal.
        
        Args:
            signal: Audio samples as numpy array
            sample_rate: Sample rate in Hz
            
        Returns:
            192-dimensional embedding vector
        """
        if self.model is None:
            return np.random.randn(192).astype(np.float32)
        
        try:
            # Resample if needed
            if sample_rate != 16000:
                import librosa
                signal = librosa.resample(signal, orig_sr=sample_rate, target_sr=16000)
            
            # Extract embedding
            with torch.no_grad():
                embedding = self.model.encode_batch(torch.tensor(signal).unsqueeze(0).float())
                embedding = embedding.squeeze().numpy().astype(np.float32)
            
            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding
        except Exception as e:
            logger.error(f"Embedding extraction from signal failed: {e}")
            return np.random.randn(192).astype(np.float32)