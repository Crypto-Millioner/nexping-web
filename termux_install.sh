#!/bin/bash 
echo "Installing NexPing for Termux..." 
pkg update && pkg install python python-pip -y 
pip install cryptography aiohttp aiosqlite zeroconf 
echo "Installation complete!" 
echo "Run: python app.py start" 
