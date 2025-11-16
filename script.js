class RealTimeMessenger {
    constructor() {
        this.contacts = [];
        this.serverName = '';
        this.nodeId = '';
        this.activeContact = null;
        this.messageQueue = [];
        this.isConnected = false;
        this.init();
    }

    async init() {
        await this.loadContacts();
        this.setupEventListeners();
        this.updateUI();
        this.startRealtimeUpdates();
    }

    async loadContacts() {
        try {
            const response = await fetch('/contacts');
            const data = await response.json();
            this.contacts = data.contacts;
            this.serverName = data.server_name;
            this.nodeId = data.node_id;
            this.renderContacts();
            this.updateServerInfo();
        } catch (error) {
            console.error('Failed to load contacts:', error);
            this.showError('Failed to load contacts');
        }
    }

    renderContacts() {
        const contactsList = document.getElementById('contactsList');
        
        if (this.contacts.length === 0) {
            contactsList.innerHTML = '<div class="loading">No contacts found</div>';
            return;
        }

        contactsList.innerHTML = this.contacts.map(contact => `
            <div class="contact-item" data-contact="${contact.name}" data-node-id="${contact.node_id}">
                <div class="contact-info">
                    <div class="contact-status ${contact.status === 'online' ? 'status-online' : 'status-offline'}"></div>
                    <span>${contact.name}</span>
                </div>
                <div class="contact-last-seen">${contact.last_seen}</div>
            </div>
        `).join('');

        // Add click listeners to contacts
        contactsList.querySelectorAll('.contact-item').forEach(item => {
            item.addEventListener('click', () => this.selectContact(
                item.dataset.contact,
                item.dataset.nodeId
            ));
        });
    }

    async selectContact(contactName, contactNodeId) {
        this.activeContact = this.contacts.find(c => c.name === contactName);
        if (this.activeContact) {
            this.activeContact.node_id = contactNodeId;
            await this.loadChatHistory();
            this.updateChatInterface();
            
            // Enable input
            document.getElementById('messageInput').disabled = false;
            document.getElementById('sendButton').disabled = false;
        }
    }

    async loadChatHistory() {
        if (!this.activeContact) return;
        this.displayWelcomeMessage();
    }

    updateChatInterface() {
        if (this.activeContact) {
            document.getElementById('activeContact').textContent = this.activeContact.name;
        }
    }

    updateServerInfo() {
        document.getElementById('serverName').textContent = this.serverName;
    }

    updateUI() {
        const statusElement = document.getElementById('status');
        statusElement.innerHTML = '<i class="fas fa-circle online"></i><span>Connected to P2P Network</span>';
    }

    setupEventListeners() {
        const sendButton = document.getElementById('sendButton');
        const messageInput = document.getElementById('messageInput');

        // Исправляем привязку контекста
        this.sendMessage = this.sendMessage.bind(this);
        this.handleKeyPress = this.handleKeyPress.bind(this);

        sendButton.addEventListener('click', this.sendMessage);
        messageInput.addEventListener('keypress', this.handleKeyPress);
    }

    handleKeyPress(e) {
        if (e.key === 'Enter') {
            this.sendMessage();
        }
    }

    async sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();

        if (!message || !this.activeContact) return;

        // Add message to UI immediately
        this.addMessageToChat('outgoing', message);
        
        // Clear input
        messageInput.value = '';
        
        try {
            // Send to server
            const response = await fetch('/send_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    contact_node_id: this.activeContact.node_id,
                    message: message
                })
            });
            
            const result = await response.json();
            
            if (!result.success) {
                this.showError('Failed to send message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Network error');
        }
    }

    addMessageToChat(type, message) {
        const chatMessages = document.getElementById('chatMessages');
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}`;
        messageElement.innerHTML = `
            <div class="message-bubble ${type}">
                <div class="message-text">${this.escapeHtml(message)}</div>
                <div class="message-time">${new Date().toLocaleTimeString()}</div>
            </div>
        `;
        
        // Remove welcome message if present
        const welcomeMessage = chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    displayWelcomeMessage() {
        const chatMessages = document.getElementById('chatMessages');
        if (this.activeContact) {
            chatMessages.innerHTML = `
                <div class="welcome-message">
                    <i class="fas fa-lock"></i>
                    <p>Secure chat with ${this.activeContact.name}</p>
                    <small>All messages are end-to-end encrypted</small>
                    <small>Status: ${this.activeContact.status}</small>
                </div>
            `;
        }
    }

    startRealtimeUpdates() {
        // Poll for new contacts and messages
        setInterval(async () => {
            await this.loadContacts();
        }, 5000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showError(message) {
        // Simple error display
        console.error('NexPing Error:', message);
        alert('Error: ' + message);
    }
}

// XSS Protection
(function() {
    const originalInnerHTML = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML').set;
    
    Object.defineProperty(Element.prototype, 'innerHTML', {
        set: function(value) {
            const div = document.createElement('div');
            div.textContent = value;
            originalInnerHTML.call(this, div.innerHTML);
        }
    });
})();

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.messenger = new RealTimeMessenger();
});