import sys
import os
import asyncio
import subprocess
import threading
from server import start_server, P2PServer
import signal

class NexPingDaemon:
    def __init__(self):
        self.server = None
        self.is_running = False

    def start(self):
        """Start the NexPing server"""
        if self.is_running:
            print("Server is already running")
            return
        
        print("Starting NexPing P2P Messenger...")
        print("Initializing database...")
        print("Starting P2P network...")
        print("Web interface: http://localhost:2947")
        
        self.is_running = True
        self.server = start_server()

    def stop(self):
        """Stop the NexPing server"""
        if not self.is_running:
            print("Server is not running")
            return
        
        print("Stopping NexPing server...")
        self.is_running = False
        
        os._exit(0)

def print_help():
    print("NexPing P2P Messenger - Private Network")
    print("Commands:")
    print("  nex start    - Start the P2P server")
    print("  nex stop     - Stop the server")
    print("  nex version  - Show version")
    print("  nex status   - Show network status")
    print("  nex contacts - List discovered contacts")

def show_version():
    print("NexPing v2.0.0")
    print("Private P2P Messenger with SQLite")
    print("Network: NexPing Private P2P Network")
    print("Features: E2EE, SQLite, Real P2P, UDP Discovery")

async def check_status():
    """Check server status"""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:2947/contacts') as resp:
                if resp.status == 200:
                    print("Status: Server is running")
                    data = await resp.json()
                    print(f"Node ID: {data.get('node_id', 'Unknown')}")
                    print(f"Contacts: {len(data.get('contacts', []))} discovered")
                    return
    except:
        print("Status: Server is not running")

def main():
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1]
    daemon = NexPingDaemon()

    if command == "start":
        daemon.start()
    elif command == "stop":
        daemon.stop()
    elif command == "version":
        show_version()
    elif command == "status":
        asyncio.run(check_status())
    elif command == "contacts":
        print("Use web interface at http://localhost:2947 to view contacts")
    else:
        print(f"Unknown command: {command}")
        print_help()

if __name__ == "__main__":

    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    main()