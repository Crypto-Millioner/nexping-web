## 🚀 Quick Install (Termux)

```bash
# Install dependencies
pkg update && pkg install python python-pip -y
pip install cryptography aiohttp aiosqlite zeroconf

# Download and run NexPing
curl -O https://raw.githubusercontent.com/Crypto-Millioner/nexping-web/main/app.py
curl -O https://raw.githubusercontent.com/Crypto-Millioner/nexping-web/main/server.py
curl -O https://raw.githubusercontent.com/Crypto-Millioner/nexping-web/main/database.py
curl -O https://raw.githubusercontent.com/Crypto-Millioner/nexping-web/main/index.html
curl -O https://raw.githubusercontent.com/Crypto-Millioner/nexping-web/main/style.css
curl -O https://raw.githubusercontent.com/Crypto-Millioner/nexping-web/main/script.js

# Start server
python app.py start
