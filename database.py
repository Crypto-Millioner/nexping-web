import aiosqlite
import asyncio
import json
from datetime import datetime
import os

class Database:
    def __init__(self, db_path="nexping.db"):
        self.db_path = db_path
        self.init_done = False

    async def init_db(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Contacts table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    ip_address TEXT,
                    port INTEGER,
                    public_key TEXT,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_online BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Messages table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_id INTEGER,
                    message_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    encrypted_content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_delivered BOOLEAN DEFAULT FALSE,
                    is_read BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (contact_id) REFERENCES contacts (id)
                )
            ''')
            
            # Server settings table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            await db.commit()
            self.init_done = True

    async def add_contact(self, node_id, name, ip_address=None, port=None, public_key=None):
        """Add or update a contact"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO contacts 
                (node_id, name, ip_address, port, public_key, last_seen, is_online)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (node_id, name, ip_address, port, public_key, datetime.now(), True))
            await db.commit()

    async def get_contacts(self):
        """Get all contacts"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM contacts ORDER BY is_online DESC, name ASC
            ''')
            contacts = await cursor.fetchall()
            return [dict(contact) for contact in contacts]

    async def update_contact_status(self, node_id, is_online):
        """Update contact online status"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE contacts 
                SET is_online = ?, last_seen = ?
                WHERE node_id = ?
            ''', (is_online, datetime.now(), node_id))
            await db.commit()

    async def add_message(self, contact_id, content, message_type="text", encrypted_content=None):
        """Add a new message"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO messages (contact_id, message_type, content, encrypted_content)
                VALUES (?, ?, ?, ?)
            ''', (contact_id, message_type, content, encrypted_content))
            await db.commit()
            return cursor.lastrowid

    async def get_messages(self, contact_id, limit=100):
        """Get messages for a contact"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT m.*, c.name as contact_name 
                FROM messages m 
                JOIN contacts c ON m.contact_id = c.id 
                WHERE m.contact_id = ? 
                ORDER BY m.timestamp ASC 
                LIMIT ?
            ''', (contact_id, limit))
            messages = await cursor.fetchall()
            return [dict(message) for message in messages]

    async def get_contact_by_node_id(self, node_id):
        """Get contact by node ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM contacts WHERE node_id = ?', (node_id,))
            contact = await cursor.fetchone()
            return dict(contact) if contact else None

    async def save_setting(self, key, value):
        """Save server setting"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
            ''', (key, value))
            await db.commit()

    async def get_setting(self, key, default=None):
        """Get server setting"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT value FROM settings WHERE key = ?', (key,))
            result = await cursor.fetchone()
            return result[0] if result else default