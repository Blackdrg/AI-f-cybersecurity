"""
Voice embedding extractor using speechbrain's ECAPA-TDNN model.
Provides speaker embeddings for voice-based recognition.
"""

import logging
from typing import Optional, Dict, Any

import numpy as np

# Optional dependency: librosa (used for signal analysis/resampling)
# Pylance may report missing imports in some environments; runtime import is tolerated.
try:
    import librosa  # type: ignore
    LIBROSA_AVAILABLE = True
except ImportError:
    librosa = None  # type: ignore
    LIBROSA_AVAILABLE = False


try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# --- SpeechBrain / torchaudio compatibility ---
# Some SpeechBrain versions call torchaudio.set_audio_backend(),
# but newer torchaudio releases removed it.
# Monkeypatch a no-op before importing SpeechBrain.
try:
    import torchaudio  # type: ignore

    if not hasattr(torchaudio, "set_audio_backend"):
        def _noop_set_audio_backend(*args, **kwargs):
            return None

        torchaudio.set_audio_backend = _noop_set_audio_backend  # type: ignore[attr-defined]
except Exception:
    # If torchaudio isn't importable, SpeechBrain will also likely fail.
    pass

# NOTE: Pylance may not resolve `speechbrain` in this repo/environment.
# We intentionally keep the import dynamic and tolerant.
try:
    from speechbrain.inference.speaker import EncoderClassifier  # type: ignore
    SPEECHBRAIN_AVAILABLE = True
except Exception:
    SPEECHBRAIN_AVAILABLE = False




logger = logging.getLogger(__name__)

import scipy.signal as sig


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
        if not LIBROSA_AVAILABLE:
            return {"liveness_score": 0.5, "is_live": True, "warning": "librosa not available"}

        try:
            # 1. Spectral analysis for replay detection (artifacts from loudspeakers)
            replay_indicator = self._detect_replay_spectral(audio_signal, sample_rate)
            
            # 2. Analyze noise consistency (natural recordings have background noise variance)
            noise_score = self._analyze_noise_consistency(audio_signal, sample_rate)
            
            # 3. Detect micro-tremors (natural human speech has jitter/shimmer absent in replay)
            tremor_ratio = self._detect_tremor(audio_signal, sample_rate)
            
            # Weighted combination
            # Lower replay_indicator is better (1.0 - x)
            # Higher noise_score is better (suggests non-static noise)
            # Higher tremor_ratio is better (suggests human jitter)
            liveness_score = (
                (1.0 - replay_indicator) * 0.4 +
                noise_score * 0.3 +
                tremor_ratio * 0.3
            )
            liveness_score = max(0.0, min(1.0, liveness_score))
            
            return {
                "liveness_score": float(liveness_score),
                "is_live": liveness_score > 0.55,
                "details": {
                    "replay_indicator": float(replay_indicator),
                    "noise_consistency": float(noise_score),
                    "tremor_ratio": float(tremor_ratio)
                },
                "method": "advanced_spectral_analysis"
            }
        except Exception as e:
            logger.warning(f"Voice liveness detection failed: {e}")
            return {
                "liveness_score": 0.5,
                "is_live": False,
                "error": str(e)
            }
    
    def _detect_replay_spectral(self, signal: np.ndarray, sr: int) -> float:
        """Detect spectral artifacts from replay devices (e.g., high-freq roll-off)."""
        try:
            # Compute Power Spectral Density (PSD)
            freqs, psd = sig.welch(signal, sr, nperseg=1024)
            
            # Replay devices often have a sharp cut-off above 15-18kHz
            # or significant resonance peaks at specific device frequencies
            high_freq_mask = freqs > 15000
            if np.any(high_freq_mask):
                high_freq_energy = np.mean(psd[high_freq_mask])
                low_freq_energy = np.mean(psd[freqs < 5000])
                ratio = high_freq_energy / (low_freq_energy + 1e-10)
                # If ratio is extremely low, it might be a low-quality speaker replay
                return 1.0 if ratio < 1e-6 else 0.0
            return 0.0
        except Exception:
            return 0.5
    
    def _analyze_noise_consistency(self, signal: np.ndarray, sr: int) -> float:
        """Analyze noise floor for synthetic consistency."""
        # Genuine speech has environmental noise with variance
        # Divide into small segments
        segments = np.array_split(signal, 8)
        segment_vars = [np.var(seg) for seg in segments if len(seg) > 0]
        if len(segment_vars) < 2:
            return 0.5
        
        # Variation coefficient
        var_coef = np.std(segment_vars) / (np.mean(segment_vars) + 1e-10)
        # Higher variation suggests live recording; very low suggests static noise (replay)
        return min(1.0, var_coef * 2)
    
    def _detect_tremor(self, signal: np.ndarray, sr: int) -> float:
        """Detect micro-tremors in fundamental frequency (Pitch Jitter)."""
        try:
            # Simple zero-crossing rate variation as proxy for jitter
            if LIBROSA_AVAILABLE:
                zcr = librosa.feature.zero_crossing_rate(signal)[0]
                
                zcr_var = np.std(zcr) / (np.mean(zcr) + 1e-10)
                # Live speech has natural jitter
                return min(1.0, zcr_var * 3)
            else:
                return 0.3
        except Exception:
            return 0.3


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
            if LIBROSA_AVAILABLE:
                signal, fs = librosa.load(audio_path, sr=16000)
            else:
                raise ImportError("librosa is not available")
            
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
            if LIBROSA_AVAILABLE:
                signal, sr = librosa.load(audio_path, sr=16000)
                return self.liveness_detector.detect_liveness(signal, sr)
            else:
                logger.warning("librosa not available, returning default liveness result")
                return {"liveness_score": 0.5, "is_live": True, "warning": "librosa not available"}
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
            if sample_rate != 16000 and LIBROSA_AVAILABLE:
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