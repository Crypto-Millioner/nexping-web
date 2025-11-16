# NexPing - Private P2P Messenger

Secure messenger with end-to-end encryption and P2P network. Works on Termux and Linux.

![NexPing](https://img.shields.io/badge/Version-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.7%2B-green)
![Termux](https://img.shields.io/badge/Termux-Supported-brightgreen)

## Quick Install (Termux)

```bash
# Update and install Python
pkg update && pkg upgrade
pkg install python python-pip

# Install dependencies
pip install cryptography aiohttp aiosqlite zeroconf

# Download NexPing files
curl -O https://raw.githubusercontent.com/Crypto-Millioner/nexping-web/main/app.py
curl -O https://raw.githubusercontent.com/Crypto-Millioner/nexping-web/main/server.py
curl -O https://raw.githubusercontent.com/Crypto-Millioner/nexping-web/main/database.py
curl -O https://raw.githubusercontent.com/Crypto-Millioner/nexping-web/main/index.html
curl -O https://raw.githubusercontent.com/Crypto-Millioner/nexping-web/main/style.css
curl -O https://raw.githubusercontent.com/Crypto-Millioner/nexping-web/main/script.js

# Start server
python app.py start

The open: http://localhost:2947/

# Start server
python app.py start

# Stop server  
python app.py stop

# Check version
python app.py version

# Network status
python app.py status

ZIP:
curl -LO https://github.com/Crypto-Millioner/nexping-web/releases/download/v1.0.0/nexping-termux.zip
unzip nexping-termux.zip
cd nexping
pip install cryptography aiohttp aiosqlite zeroconf
python app.py start

MIT License - feel free to use and modify!

