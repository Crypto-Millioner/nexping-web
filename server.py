import asyncio
import socket
import json
import random
import time
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import aiohttp
from aiohttp import web
import threading
from database import Database
import hashlib
import os
import struct

class STUNClient:
    """Клиент для получения внешнего IP и проброса NAT"""
    STUN_SERVERS = [
        ('stun.l.google.com', 19302),
        ('stun1.l.google.com', 19302),
        ('stun2.l.google.com', 19302),
        ('stun3.l.google.com', 19302),
        ('stun4.l.google.com', 19302)
    ]
    
    async def get_public_info(self):
        """Получить публичный IP и порт через STUN"""
        for server, port in self.STUN_SERVERS:
            try:
                result = await self.stun_request(server, port)
                if result:
                    print(f"STUN: Got public IP {result['public_ip']}:{result['public_port']} from {server}")
                    return result
            except Exception as e:
                print(f"STUN: Failed to get info from {server}: {e}")
                continue
        print("STUN: All servers failed, using local IP")
        return self.get_local_info()
    
    def get_local_info(self):
        """Получить локальную информацию когда STUN недоступен"""
        try:
    
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            return {'public_ip': local_ip, 'public_port': 2948}
        except:
            return {'public_ip': '127.0.0.1', 'public_port': 2948}
    
    async def stun_request(self, host, port):
        """Выполнить STUN запрос"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3)
        
            header = struct.pack('>HHLL', 0x0001, 0x0000, 0x2112A442, 0)
            transaction_id = os.urandom(12)
            message = header + transaction_id
            
            sock.sendto(message, (host, port))
            data, addr = sock.recvfrom(1024)
            sock.close()
            
            # Parse STUN response
            if len(data) > 0:
                # Simplified parsing - in real implementation would parse attributes
                return {
                    'public_ip': addr[0],
                    'public_port': addr[1]
                }
        except Exception as e:
            raise e
        return None

class RelayClient:
    """Клиент для ретрансляции через публичные сервера (заглушка)"""
    def __init__(self):
        self.relay_servers = [
         
        ]
    
    async def send_via_relay(self, target_node, message):
        """Отправить сообщение через ретранслятор"""
        if not self.relay_servers:
            return False
            
        for relay in self.relay_servers:
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(relay, json={
                        'target': target_node,
                        'message': message,
                        'timestamp': datetime.now().isoformat()
                    }, timeout=5)
                print(f"Relay: Message sent via {relay}")
                return True
            except Exception as e:
                print(f"Relay: Failed to send via {relay}: {e}")
                continue
        return False

class P2PNetwork:
    def __init__(self, node_id, port=2948):
        self.node_id = node_id
        self.port = port
        self.peers = {}
        self.is_running = False
        self.db = Database()
        self.stun_client = STUNClient()
        self.relay_client = RelayClient()
        self.public_ip = None
        self.public_port = None
        self.udp_socket = None

    async def start(self):
        """Start P2P network services"""
        self.is_running = True
        await self.db.init_db()
    
        print("Getting public IP information...")
        public_info = await self.stun_client.get_public_info()
        if public_info:
            self.public_ip = public_info['public_ip']
            self.public_port = public_info['public_port']
            print(f"Public IP: {self.public_ip}:{self.public_port}")
        
        # Start UDP listener
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(('0.0.0.0', self.port))
        self.udp_socket.setblocking(False)
        
        print(f"P2P Network started on port {self.port}")
        print(f"Node ID: {self.node_id}")
        
        # Start network tasks
        asyncio.create_task(self.udp_listener())
        asyncio.create_task(self.peer_discovery())
        asyncio.create_task(self.keep_alive())
        asyncio.create_task(self.network_maintenance())

    async def udp_listener(self):
        """Listen for incoming UDP messages"""
        loop = asyncio.get_event_loop()
        
        while self.is_running:
            try:
                # Use asyncio to handle UDP socket
                data, addr = await loop.sock_recvfrom(self.udp_socket, 1024)
                await self.handle_message(data, addr)
            except BlockingIOError:
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"UDP listener error: {e}")
                await asyncio.sleep(1)

    async def handle_message(self, data, addr):
        """Handle incoming P2P messages"""
        try:
            message = json.loads(data.decode('utf-8', errors='ignore'))
            msg_type = message.get('type')
            
            if msg_type == 'discovery':
                await self.handle_discovery(message, addr)
            elif msg_type == 'message':
                await self.handle_p2p_message(message, addr)
            elif msg_type == 'keep_alive':
                await self.handle_keep_alive(message, addr)
            elif msg_type == 'connect_request':
                await self.handle_connect_request(message, addr)
            elif msg_type == 'connect_ack':
                await self.handle_connect_ack(message, addr)
            elif msg_type == 'peer_info':
                await self.handle_peer_info(message, addr)
                
        except json.JSONDecodeError:
            print(f"Invalid JSON received from {addr}")
        except Exception as e:
            print(f"Error handling message from {addr}: {e}")

    async def handle_discovery(self, message, addr):
        """Handle peer discovery messages"""
        peer_id = message.get('node_id')
        if peer_id and peer_id != self.node_id:
            peer_info = {
                'ip': addr[0],
                'port': addr[1],
                'public_ip': message.get('public_ip'),
                'public_port': message.get('public_port', self.port),
                'last_seen': datetime.now(),
                'name': message.get('name', f"Node_{peer_id[:8]}"),
                'local_addr': addr
            }
            
            self.peers[peer_id] = peer_info
            
            # Save to database
            await self.db.add_contact(
                node_id=peer_id,
                name=peer_info['name'],
                ip_address=addr[0],
                port=addr[1],
                public_key=None 
            )
            
            print(f"Discovered peer: {peer_info['name']} at {addr}")
            
            # Send peer info to establish better connection
            await self.send_peer_info(peer_id)

    async def handle_peer_info(self, message, addr):
        """Handle peer information exchange"""
        peer_id = message.get('node_id')
        if peer_id in self.peers:
            self.peers[peer_id].update({
                'public_ip': message.get('public_ip'),
                'public_port': message.get('public_port'),
                'last_seen': datetime.now()
            })

    async def handle_connect_request(self, message, addr):
        """Handle connection requests from remote peers"""
        peer_id = message.get('node_id')
        peer_public_ip = message.get('public_ip')
        peer_public_port = message.get('public_port')
        
        print(f"Connection request from {peer_id} at {peer_public_ip}:{peer_public_port}")
        
        # Add to peers if not already
        if peer_id not in self.peers:
            self.peers[peer_id] = {
                'ip': addr[0],
                'port': addr[1],
                'public_ip': peer_public_ip,
                'public_port': peer_public_port,
                'last_seen': datetime.now(),
                'name': f"Node_{peer_id[:8]}"
            }
        
        # Send acknowledgment
        connect_ack = {
            'type': 'connect_ack',
            'node_id': self.node_id,
            'public_ip': self.public_ip,
            'public_port': self.public_port,
            'timestamp': datetime.now().isoformat()
        }
        
        # Try to send ack via public IP if available
        if peer_public_ip and peer_public_port:
            try:
                await self.send_to_address(connect_ack, (peer_public_ip, peer_public_port))
                print(f"Sent connect ack to {peer_public_ip}:{peer_public_port}")
            except Exception as e:
                print(f"Failed to send ack to public IP: {e}")
        
        # Also send via local address
        try:
            await self.send_to_address(connect_ack, (addr[0], addr[1]))
        except Exception as e:
            print(f"Failed to send ack to local IP: {e}")

    async def handle_connect_ack(self, message, addr):
        """Handle connection acknowledgment"""
        peer_id = message.get('node_id')
        print(f"Connection established with {peer_id}")

    async def handle_p2p_message(self, message, addr):
        """Handle actual P2P messages"""
        from_node = message.get('from')
        content = message.get('content')
        
        print(f"Received message from {from_node}: {content[:50] if content else 'empty'}...")
        
        # Store message in database
        contact = await self.db.get_contact_by_node_id(from_node)
        if contact:
            await self.db.add_message(
                contact_id=contact['id'],
                content=content,
                encrypted_content=None 
            )
            await self.db.update_contact_status(from_node, True)
        else:
            # Auto-add contact if not exists
            await self.db.add_contact(
                node_id=from_node,
                name=f"Node_{from_node[:8]}",
                ip_address=addr[0],
                port=addr[1]
            )

    async def handle_keep_alive(self, message, addr):
        """Handle keep-alive messages"""
        peer_id = message.get('node_id')
        if peer_id in self.peers:
            self.peers[peer_id]['last_seen'] = datetime.now()
            await self.db.update_contact_status(peer_id, True)

    async def send_to_address(self, message, addr):
        """Send message to specific address"""
        try:
            data = json.dumps(message).encode('utf-8')
            self.udp_socket.sendto(data, addr)
            return True
        except Exception as e:
            print(f"Failed to send to {addr}: {e}")
            return False

    async def send_peer_info(self, peer_id):
        """Send our information to peer"""
        if peer_id not in self.peers:
            return
            
        peer_info = {
            'type': 'peer_info',
            'node_id': self.node_id,
            'public_ip': self.public_ip,
            'public_port': self.public_port,
            'timestamp': datetime.now().isoformat()
        }
        
        peer = self.peers[peer_id]
        
        # Try all possible addresses
        addresses_to_try = []
        
        if peer.get('public_ip') and peer.get('public_port'):
            addresses_to_try.append((peer['public_ip'], peer['public_port']))
        
        if peer.get('local_addr'):
            addresses_to_try.append(peer['local_addr'])
        
        if peer.get('ip') and peer.get('port'):
            addresses_to_try.append((peer['ip'], peer['port']))
        
        # Send to all addresses
        for addr in addresses_to_try:
            if await self.send_to_address(peer_info, addr):
                print(f"Sent peer info to {addr}")
                break

    async def peer_discovery(self):
        """Broadcast discovery messages to find peers"""
        discovery_msg = {
            'type': 'discovery',
            'node_id': self.node_id,
            'name': f"Node_{self.node_id[:8]}",
            'public_ip': self.public_ip,
            'public_port': self.public_port,
            'timestamp': datetime.now().isoformat()
        }
        
        while self.is_running:
            try:
                # Local network broadcast
                broadcast_addr = ('255.255.255.255', self.port)
                await self.send_to_address(discovery_msg, broadcast_addr)
                
                # Also try specific subnet broadcast (common in local networks)
                local_broadcasts = [
                    ('192.168.1.255', self.port),
                    ('192.168.0.255', self.port),
                    ('10.0.0.255', self.port),
                    ('172.16.0.255', self.port),
                ]
                
                for broadcast in local_broadcasts:
                    await self.send_to_address(discovery_msg, broadcast)
                
            except Exception as e:
                print(f"Discovery broadcast error: {e}")
            
            # Random delay to reduce network noise
            await asyncio.sleep(random.uniform(15, 25))

    async def connect_to_peer(self, peer_info):
        """Connect to specific peer"""
        connect_msg = {
            'type': 'connect_request',
            'node_id': self.node_id,
            'public_ip': self.public_ip,
            'public_port': self.public_port,
            'timestamp': datetime.now().isoformat()
        }
        
        # Try all possible connection methods
        success = False
        
        # Try public IP first
        if peer_info.get('public_ip') and peer_info.get('public_port'):
            success = await self.send_to_address(
                connect_msg, 
                (peer_info['public_ip'], peer_info['public_port'])
            )
            if success:
                print(f"Connected via public IP to {peer_info['public_ip']}")
        
        # Try local IP
        if not success and peer_info.get('ip') and peer_info.get('port'):
            success = await self.send_to_address(
                connect_msg,
                (peer_info['ip'], peer_info['port'])
            )
            if success:
                print(f"Connected via local IP to {peer_info['ip']}")
        
        # Fallback to relay
        if not success:
            success = await self.relay_client.send_via_relay(peer_info['node_id'], connect_msg)
            if success:
                print(f"Connected via relay to {peer_info['node_id']}")
        
        return success

    async def send_message(self, peer_id, message_content):
        """Send message to specific peer"""
        if peer_id not in self.peers:
            print(f"Peer {peer_id} not found in network")
            return False
        
        peer = self.peers[peer_id]
        message = {
            'type': 'message',
            'from': self.node_id,
            'to': peer_id,
            'content': message_content,
            'timestamp': datetime.now().isoformat()
        }
        
        # Try all possible connection methods in order of reliability
        success = False
        
        # 1. Try local network first (fastest)
        if peer.get('ip') and peer.get('port'):
            success = await self.send_to_address(message, (peer['ip'], peer['port']))
            if success:
                print(f"Message sent to {peer_id} via local network")
        
        # 2. Try public IP
        if not success and peer.get('public_ip') and peer.get('public_port'):
            success = await self.send_to_address(
                message, 
                (peer['public_ip'], peer['public_port'])
            )
            if success:
                print(f"Message sent to {peer_id} via public IP")
        
        # 3. Fallback to relay
        if not success:
            success = await self.relay_client.send_via_relay(peer_id, message)
            if success:
                print(f"Message sent to {peer_id} via relay")
        
        if not success:
            print(f"Failed to send message to {peer_id}")
        
        return success

    async def keep_alive(self):
        """Send keep-alive messages to peers"""
        while self.is_running:
            keep_alive_msg = {
                'type': 'keep_alive',
                'node_id': self.node_id,
                'timestamp': datetime.now().isoformat()
            }
            
            for peer_id, peer_info in self.peers.items():
                try:
                    # Send to last known address
                    if peer_info.get('ip') and peer_info.get('port'):
                        await self.send_to_address(
                            keep_alive_msg, 
                            (peer_info['ip'], peer_info['port'])
                        )
                except Exception as e:
                    print(f"Error sending keep-alive to {peer_id}: {e}")
            
            await asyncio.sleep(20)  # Send keep-alive every 20 seconds

    async def network_maintenance(self):
        """Clean up dead peers and maintain network health"""
        while self.is_running:
            current_time = datetime.now()
            dead_peers = []
            
            for peer_id, peer_info in self.peers.items():
                time_diff = (current_time - peer_info['last_seen']).total_seconds()
                if time_diff > 60:  # 60 seconds timeout
                    dead_peers.append(peer_id)
                    await self.db.update_contact_status(peer_id, False)
                    print(f"Peer {peer_id} timed out")
            
            for peer_id in dead_peers:
                del self.peers[peer_id]
            
            # Print network status
            online_peers = len([p for p in self.peers.values() 
                              if (current_time - p['last_seen']).total_seconds() < 30])
            print(f"Network status: {online_peers} peers online, {len(self.peers)} total known")
            
            await asyncio.sleep(30)  # Check every 30 seconds

    def stop(self):
        """Stop the network"""
        self.is_running = False
        if self.udp_socket:
            self.udp_socket.close()
        print("P2P Network stopped")

class P2PServer:
    def __init__(self, host='0.0.0.0', web_port=2947, p2p_port=2948):
        self.host = host
        self.web_port = web_port
        self.p2p_port = p2p_port
        self.node_id = self.generate_node_id()
        self.server_name = f"Node_{self.node_id[:8]}"
        
        self.db = Database()
        self.network = P2PNetwork(self.node_id, p2p_port)
        self.web_app = None
        self.runner = None
        self.site = None

    def generate_node_id(self):
        """Generate unique node ID"""
        unique_string = f"{random.getrandbits(256)}-{time.time()}-{os.urandom(16).hex()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]

    async def start(self):
        """Start all server components"""
        print("Initializing database...")
        await self.db.init_db()
        
        print("Starting P2P network...")
        await self.network.start()
        
        # Add self to contacts
        await self.db.add_contact(
            node_id=self.node_id,
            name=self.server_name,
            ip_address="127.0.0.1",
            port=self.p2p_port
        )
        
        print(f"Server started: {self.server_name} ({self.node_id})")

    async def start_web_interface(self):
        """Start HTTP server for web interface"""
        app = web.Application()
        
        # Add routes
        app.router.add_get('/', self.serve_index)
        app.router.add_get('/contacts', self.handle_contacts)
        app.router.add_post('/send_message', self.handle_send_message)
        app.router.add_get('/messages', self.handle_get_messages)
        app.router.add_get('/favicon.ico', self.serve_favicon)
        app.router.add_static('/', path=os.path.dirname(__file__))
        
        self.web_app = app
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, self.host, self.web_port)
        await self.site.start()
        
        print(f"Web interface: http://{self.host}:{self.web_port}")
        print("NexPing server is ready!")

    async def serve_favicon(self, request):
        """Serve favicon - return empty for now"""
        return web.Response(status=404)

    async def serve_index(self, request):
        """Serve main page"""
        return web.FileResponse('./index.html')

    async def handle_contacts(self, request):
        """API endpoint for contacts"""
        contacts = await self.db.get_contacts()
        
        # Format contacts for frontend
        formatted_contacts = []
        for contact in contacts:
            # Skip self
            if contact['node_id'] == self.node_id:
                continue
                
            formatted_contacts.append({
                'name': contact['name'],
                'status': 'online' if contact['is_online'] else 'offline',
                'last_seen': self.format_last_seen(contact['last_seen']),
                'node_id': contact['node_id'],
                'id': contact['id']
            })
        
        return web.json_response({
            'contacts': formatted_contacts,
            'server_name': self.server_name,
            'node_id': self.node_id
        })

    async def handle_get_messages(self, request):
        """API endpoint to get messages for a contact"""
        contact_node_id = request.query.get('contact_node_id')
        if not contact_node_id:
            return web.json_response({'error': 'contact_node_id required'}, status=400)
        
        contact = await self.db.get_contact_by_node_id(contact_node_id)
        if not contact:
            return web.json_response({'error': 'Contact not found'}, status=404)
        
        messages = await self.db.get_messages(contact['id'])
        return web.json_response({'messages': messages})

    async def handle_send_message(self, request):
        """API endpoint for sending messages"""
        try:
            data = await request.json()
            contact_node_id = data.get('contact_node_id')
            message_content = data.get('message')
            
            if not contact_node_id or not message_content:
                return web.json_response({'success': False, 'error': 'Missing parameters'})
            
            # Get contact info
            contact = await self.db.get_contact_by_node_id(contact_node_id)
            if not contact:
                return web.json_response({'success': False, 'error': 'Contact not found'})
            
            # Store message locally
            message_id = await self.db.add_message(
                contact_id=contact['id'],
                content=message_content
            )
            
            # Send via P2P network
            success = await self.network.send_message(contact_node_id, message_content)
            
            return web.json_response({
                'success': success,
                'message_id': message_id
            })
        
        except Exception as e:
            print(f"Error sending message: {e}")
            return web.json_response({'success': False, 'error': str(e)})

    def format_last_seen(self, timestamp):
        """Format timestamp for display"""
        if not timestamp:
            return 'unknown'
        
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                return timestamp
        
        now = datetime.now()
        diff = now - timestamp
        
        if diff.total_seconds() < 60:
            return 'now'
        elif diff.total_seconds() < 3600:
            return f"{int(diff.total_seconds() / 60)}min ago"
        elif diff.total_seconds() < 86400:
            return f"{int(diff.total_seconds() / 3600)}h ago"
        else:
            return timestamp.strftime('%Y-%m-%d %H:%M')

    async def stop(self):
        """Stop the server"""
        print("Stopping NexPing server...")
        self.network.stop()
        
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        
        print("Server stopped")

async def start_server_async():
    """Start server asynchronously"""
    server = P2PServer()
    await server.start()
    await server.start_web_interface()
    return server

def start_server():
    """Start the P2P server (blocking)"""
    server = P2PServer()
    
    # Run in asyncio event loop
    async def run():
        await server.start()
        await server.start_web_interface()
        
        # Keep running
        while True:
            await asyncio.sleep(1)
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nShutting down...")
        asyncio.run(server.stop())

if __name__ == "__main__":
    start_server()