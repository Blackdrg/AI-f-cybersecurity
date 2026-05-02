import os
try:
    import boto3
    BOTO3 = True
except:
    BOTO3 = False
try:
    from cryptography.hazmat.primitives import serialization
    CRYPTO = True
except:
    CRYPTO = False
