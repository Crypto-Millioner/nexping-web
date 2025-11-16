from setuptools import setup, find_packages
import os

def read_requirements():
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="nexping",
    version="2.0.0",
    packages=find_packages(),
    install_requires=read_requirements(),
    entry_points={
        'console_scripts': [
            'nexping=app:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['*.html', '*.css', '*.js', '*.ico', '*.bat', '*.sh'],
    },
    python_requires='>=3.7',
    author="NexPing Team",
    author_email="contact@example.com",
    description="Private P2P Messenger with E2EE Encryption",
    keywords="p2p messenger encryption privacy",
    url="https://github.com/Crypto-Millioner/nexping",
)