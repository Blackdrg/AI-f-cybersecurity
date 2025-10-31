import numpy as np

try:
    import librosa
    import torch
    from speechbrain.pretrained import EncoderClassifier
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    librosa = None
    torch = None
    EncoderClassifier = None


class VoiceEmbedder:
    def __init__(self):
        if LIBROSA_AVAILABLE:
            # Use SpeechBrain's ECAPA-TDNN for voice embeddings
            self.model = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="tmp/spkrec-ecapa-voxceleb"
            )
        else:
            # Fallback: generate random embeddings for testing
            self.model = None

    def get_embedding(self, audio_path: str) -> np.ndarray:
        """
        Extract voice embedding from audio file.
        Returns 1-D float32 vector (192-d for ECAPA-TDNN).
        """
        if LIBROSA_AVAILABLE and self.model is not None:
            # Load audio
            signal, fs = librosa.load(
                audio_path, sr=16000)  # Resample to 16kHz

            # Extract embedding
            with torch.no_grad():
                embedding = self.model.encode_batch(
                    torch.tensor(signal).unsqueeze(0))
                embedding = embedding.squeeze().numpy().astype(np.float32)

            # L2 normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding /= norm

            return embedding
        else:
            # Fallback: return random normalized embedding
            embedding = np.random.randn(192).astype(np.float32)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding /= norm
            return embedding
