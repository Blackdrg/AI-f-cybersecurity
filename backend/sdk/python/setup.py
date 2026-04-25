from setuptools import setup, find_packages
import os

# Read README for long description
with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open(os.path.join(os.path.dirname(__file__), 'requirements.txt'), encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="ai-f-sdk",
    version="2.0.0",
    packages=find_packages(),
    install_requires=requirements,
    author="AI-f Security Team",
    author_email="security@ai-f.io",
    maintainer="AI-f Security Team",
    maintainer_email="security@ai-f.io",
    description="Enterprise Python SDK for AI-f Biometric Recognition Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ai-f/ai-f-python-sdk",
    download_url="https://github.com/ai-f/ai-f-python-sdk/releases",
    project_urls={
        "Bug Tracker": "https://github.com/ai-f/ai-f-python-sdk/issues",
        "Documentation": "https://docs.ai-f.io/sdk/python",
        "Source Code": "https://github.com/ai-f/ai-f-python-sdk",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "Topic :: Security :: Biometrics",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    keywords="biometrics, face recognition, security, authentication, enterprise",
    license="Apache-2.0",
    include_package_data=True,
    zip_safe=False,
)
