FROM public.ecr.aws/lambda/python:3.8

# Install necessary packages
RUN pip install numpy==1.24.3 scipy==1.10.1 onnxruntime==1.15.0 opencv-python==4.8.0.76 pillow==10.0.1 torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cpu
RUN pip install speechbrain==0.5.11 librosa==0.10.0

# Copy application code
COPY app.py /app.py
COPY decision_engine.py /decision_engine.py
# Copy known embeddings (in production, this would be encrypted and decrypted at runtime)
COPY known_face_embeddings.npy /known_face_embeddings.npy
COPY known_voice_embeddings.npy /known_voice_embeddings.npy

# Set the command to run the app
CMD ["python", "/app.py"]