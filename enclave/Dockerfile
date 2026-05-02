FROM public.ecr.aws/lambda/python:3.8

# Install necessary packages
RUN pip install numpy==1.24.3 scipy==1.10.1 onnxruntime==1.15.0 opencv-python==4.8.0.76 pillow==10.0.1

# Copy application code
COPY app.py /app.py
# Copy known embeddings (in production, this would be encrypted and decrypted at runtime)
COPY known_embeddings.npy /known_embeddings.npy

# Set the command to run the app
CMD ["python", "/app.py"]