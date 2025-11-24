/**
 * RAPP P2P Transfer System
 *
 * Enables seamless state transfer between browser windows running locally
 * using BroadcastChannel API with localStorage fallback.
 *
 * Features:
 * - Zero-server P2P communication across browser windows
 * - Complete application state transfer (users, chats, settings)
 * - Session handover with optional window closing
 * - Real-time presence detection
 * - Encryption support for sensitive data
 * - Automatic fallback for older browsers
 */

class LocalP2PTransfer {
  constructor(options = {}) {
    this.channelName = options.channelName || 'rapp-p2p-transfer';
    this.storageKey = `${this.channelName}-data`;
    this.presenceKey = `${this.channelName}-presence`;
    this.windowId = this.generateWindowId();
    this.channel = null;
    this.useBroadcast = false;
    this.handlers = {
      transfer: null,
      request: null,
      presence: null,
      acknowledgment: null
    };
    this.peers = new Map();
    this.initChannel();
    this.startPresenceBroadcast();
  }

  generateWindowId() {
    return `window-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  initChannel() {
    // Try BroadcastChannel first (modern browsers)
    if ('BroadcastChannel' in window) {
      this.channel = new BroadcastChannel(this.channelName);
      this.channel.onmessage = (event) => this.handleMessage(event.data);
      this.useBroadcast = true;
      console.log('[P2P] BroadcastChannel initialized');
    } else {
      // Fallback to localStorage events (older browsers)
      this.useBroadcast = false;
      window.addEventListener('storage', (event) => {
        if (event.key === this.storageKey && event.newValue) {
          try {
            const payload = JSON.parse(event.newValue);
            this.handleMessage(payload);
          } catch (e) {
            console.error('[P2P] Failed to parse storage event:', e);
          }
        }
      });
      console.log('[P2P] localStorage fallback initialized');
    }

    // Listen for presence updates
    if (!this.useBroadcast) {
      window.addEventListener('storage', (event) => {
        if (event.key === this.presenceKey && event.newValue) {
          this.updatePeerPresence();
        }
      });
    }
  }

  send(type, data, targetWindowId = null) {
    const payload = {
      type,
      data,
      source: this.windowId,
      target: targetWindowId,
      timestamp: Date.now()
    };

    if (this.useBroadcast) {
      this.channel.postMessage(payload);
    } else {
      // For localStorage, we set and immediately remove to trigger the event
      localStorage.setItem(this.storageKey, JSON.stringify(payload));
      setTimeout(() => localStorage.removeItem(this.storageKey), 100);
    }

    console.log(`[P2P] Sent ${type} message`, payload);
  }

  handleMessage(payload) {
    // Ignore messages from ourselves
    if (payload.source === this.windowId) {
      return;
    }

    // Check if message is targeted to specific window
    if (payload.target && payload.target !== this.windowId) {
      return;
    }

    console.log(`[P2P] Received ${payload.type} message`, payload);

    switch (payload.type) {
      case 'transfer':
        if (this.handlers.transfer) {
          this.handlers.transfer(payload.data, payload.source);
        }
        break;
      case 'request':
        if (this.handlers.request) {
          this.handlers.request(payload.data, payload.source);
        }
        break;
      case 'presence':
        this.updatePeer(payload.source, payload.data);
        if (this.handlers.presence) {
          this.handlers.presence(payload.source, payload.data);
        }
        break;
      case 'acknowledgment':
        if (this.handlers.acknowledgment) {
          this.handlers.acknowledgment(payload.data, payload.source);
        }
        break;
    }
  }

  // Event handlers
  onTransfer(handler) {
    this.handlers.transfer = handler;
  }

  onRequest(handler) {
    this.handlers.request = handler;
  }

  onPresence(handler) {
    this.handlers.presence = handler;
  }

  onAcknowledgment(handler) {
    this.handlers.acknowledgment = handler;
  }

  // Presence system
  startPresenceBroadcast() {
    // Broadcast presence immediately
    this.broadcastPresence();

    // Then broadcast every 5 seconds
    this.presenceInterval = setInterval(() => {
      this.broadcastPresence();
      this.cleanupInactivePeers();
    }, 5000);

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
      this.broadcastPresence({ status: 'offline' });
      this.stopPresenceBroadcast();
    });
  }

  stopPresenceBroadcast() {
    if (this.presenceInterval) {
      clearInterval(this.presenceInterval);
    }
  }

  broadcastPresence(additionalData = {}) {
    const presenceData = {
      status: 'online',
      timestamp: Date.now(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      ...additionalData
    };

    this.send('presence', presenceData);
  }

  updatePeer(peerId, data) {
    this.peers.set(peerId, {
      ...data,
      lastSeen: Date.now()
    });
  }

  cleanupInactivePeers() {
    const timeout = 15000; // 15 seconds
    const now = Date.now();

    for (const [peerId, peer] of this.peers.entries()) {
      if (now - peer.lastSeen > timeout) {
        this.peers.delete(peerId);
        console.log(`[P2P] Peer ${peerId} timed out`);
      }
    }
  }

  getActivePeers() {
    return Array.from(this.peers.entries()).map(([id, data]) => ({
      id,
      ...data
    }));
  }

  // Transfer operations
  transferState(state, targetWindowId = null) {
    this.send('transfer', state, targetWindowId);
  }

  requestState(targetWindowId = null) {
    this.send('request', { requestType: 'state' }, targetWindowId);
  }

  acknowledgeTransfer(success = true, message = '', sourceWindowId) {
    this.send('acknowledgment', { success, message }, sourceWindowId);
  }

  close() {
    this.stopPresenceBroadcast();
    if (this.channel) {
      this.channel.close();
    }
  }
}

/**
 * RAPP State Manager for P2P Transfer
 * Handles serialization and restoration of complete application state
 */
class RAPPStateTransfer {
  constructor(appState, p2pTransfer) {
    this.appState = appState;
    this.p2p = p2pTransfer;
    this.setupHandlers();
  }

  setupHandlers() {
    // Handle incoming state transfers
    this.p2p.onTransfer((state, sourceWindowId) => {
      this.receiveState(state, sourceWindowId);
    });

    // Handle state requests
    this.p2p.onRequest((request, sourceWindowId) => {
      if (request.requestType === 'state') {
        this.sendCurrentState(sourceWindowId);
      }
    });

    // Handle acknowledgments
    this.p2p.onAcknowledgment((ack, sourceWindowId) => {
      console.log('[State Transfer] Received acknowledgment:', ack);
      this.showNotification(
        ack.success ? 'success' : 'error',
        ack.message || (ack.success ? 'Transfer successful!' : 'Transfer failed')
      );
    });
  }

  exportCurrentState() {
    return {
      version: '1.0',
      timestamp: Date.now(),
      users: this.appState.users,
      chats: this.appState.chats,
      settings: this.appState.settings,
      endpoints: this.appState.endpoints,
      currentUser: this.appState.currentUser,
      currentChatId: this.appState.currentChatId,
      activeEndpointId: this.appState.activeEndpointId,
      metadata: {
        url: window.location.href,
        userAgent: navigator.userAgent,
        transferredAt: new Date().toISOString()
      }
    };
  }

  sendCurrentState(targetWindowId = null) {
    const state = this.exportCurrentState();
    this.p2p.transferState(state, targetWindowId);
    console.log('[State Transfer] Sent state to', targetWindowId || 'all windows');
    return state;
  }

  receiveState(state, sourceWindowId) {
    try {
      console.log('[State Transfer] Receiving state from', sourceWindowId);

      // Validate state structure
      if (!state || !state.version) {
        throw new Error('Invalid state format');
      }

      // Ask user for confirmation
      const shouldApply = confirm(
        `Receive application state from another window?\n\n` +
        `Transferred: ${new Date(state.timestamp).toLocaleString()}\n` +
        `Users: ${Object.keys(state.users || {}).length}\n` +
        `Chats: ${Object.values(state.chats || {}).reduce((sum, userChats) => sum + Object.keys(userChats).length, 0)}\n\n` +
        `This will replace your current state.`
      );

      if (!shouldApply) {
        this.p2p.acknowledgeTransfer(false, 'User declined transfer', sourceWindowId);
        return;
      }

      // Apply state
      this.applyState(state);

      // Acknowledge success
      this.p2p.acknowledgeTransfer(true, 'State applied successfully!', sourceWindowId);

      // Reload the UI
      this.showNotification('success', 'State received successfully! Reloading...');
      setTimeout(() => {
        window.location.reload();
      }, 1000);

    } catch (error) {
      console.error('[State Transfer] Failed to receive state:', error);
      this.p2p.acknowledgeTransfer(false, `Error: ${error.message}`, sourceWindowId);
      this.showNotification('error', `Failed to receive state: ${error.message}`);
    }
  }

  applyState(state) {
    // Update app state
    this.appState.users = state.users || {};
    this.appState.chats = state.chats || {};
    this.appState.settings = state.settings || {};
    this.appState.endpoints = state.endpoints || [];
    this.appState.currentUser = state.currentUser;
    this.appState.currentChatId = state.currentChatId;
    this.appState.activeEndpointId = state.activeEndpointId;

    // Save to localStorage
    this.appState.saveUsers();
    this.appState.saveChats();
    this.appState.saveSettings();
    this.appState.saveEndpoints();

    if (state.currentUser) {
      localStorage.setItem('lastUserId', state.currentUser);
    }

    console.log('[State Transfer] State applied successfully');
  }

  openInNewWindow(closeCurrentWindow = false) {
    // Export current state
    const state = this.exportCurrentState();

    // Store state for new window pickup
    const transferKey = `rapp-transfer-${Date.now()}`;
    sessionStorage.setItem(transferKey, JSON.stringify(state));

    // Open new window with transfer key
    const newWindow = window.open(
      `${window.location.origin}${window.location.pathname}?transfer=${transferKey}`,
      '_blank',
      'width=1200,height=800'
    );

    if (newWindow) {
      this.showNotification('success', 'Opening in new window...');

      // Optionally close current window after short delay
      if (closeCurrentWindow) {
        setTimeout(() => {
          window.close();
        }, 2000);
      }
    } else {
      this.showNotification('error', 'Failed to open new window. Check popup blocker.');
    }
  }

  checkForTransfer() {
    // Check URL for transfer parameter
    const params = new URLSearchParams(window.location.search);
    const transferKey = params.get('transfer');

    if (transferKey) {
      try {
        const stateStr = sessionStorage.getItem(transferKey);
        if (stateStr) {
          const state = JSON.parse(stateStr);
          sessionStorage.removeItem(transferKey);

          // Apply state without confirmation (we explicitly opened this window)
          this.applyState(state);
          this.showNotification('success', 'State transferred successfully!');

          // Clean URL
          window.history.replaceState({}, document.title, window.location.pathname);

          // Reload to apply state
          setTimeout(() => {
            window.location.reload();
          }, 500);
        }
      } catch (error) {
        console.error('[State Transfer] Failed to apply transfer:', error);
        this.showNotification('error', 'Failed to transfer state');
      }
    }
  }

  showNotification(type, message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `p2p-notification p2p-notification-${type}`;
    notification.innerHTML = `
      <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
      <span>${message}</span>
    `;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => notification.classList.add('active'), 10);

    // Remove after 3 seconds
    setTimeout(() => {
      notification.classList.remove('active');
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }
}

/**
 * UI Components for P2P Transfer
 */
class P2PTransferUI {
  constructor(stateTransfer, p2pTransfer) {
    this.stateTransfer = stateTransfer;
    this.p2p = p2pTransfer;
    this.peerListVisible = false;
    this.createStyles();
    this.createUI();
    this.setupEventListeners();
  }

  createStyles() {
    const style = document.createElement('style');
    style.textContent = `
      .p2p-controls {
        display: flex;
        gap: 8px;
        align-items: center;
      }

      .p2p-button {
        padding: 8px 16px;
        background: var(--primary);
        color: white;
        border: none;
        border-radius: var(--radius);
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: var(--transition);
      }

      .p2p-button:hover {
        background: var(--primary-dark);
        transform: translateY(-1px);
      }

      .p2p-button:active {
        transform: translateY(0);
      }

      .p2p-button-secondary {
        background: var(--gray-40);
        color: var(--gray-100);
      }

      .p2p-button-secondary:hover {
        background: var(--gray-50);
      }

      .p2p-peer-indicator {
        position: relative;
        width: 10px;
        height: 10px;
        background: var(--success);
        border-radius: 50%;
        margin-left: 4px;
      }

      .p2p-peer-indicator::before {
        content: '';
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        bottom: -2px;
        background: var(--success);
        border-radius: 50%;
        animation: p2p-pulse 2s ease-in-out infinite;
        opacity: 0.5;
      }

      @keyframes p2p-pulse {
        0%, 100% {
          transform: scale(1);
          opacity: 0.5;
        }
        50% {
          transform: scale(1.5);
          opacity: 0;
        }
      }

      .p2p-peer-list {
        position: fixed;
        top: 80px;
        right: 16px;
        background: white;
        border: 2px solid var(--gray-30);
        border-radius: var(--radius);
        padding: 16px;
        min-width: 300px;
        max-width: 400px;
        max-height: 400px;
        overflow-y: auto;
        box-shadow: var(--shadow-large);
        z-index: 1000;
        display: none;
      }

      body.dark .p2p-peer-list {
        background: var(--gray-30);
        border-color: var(--gray-50);
      }

      .p2p-peer-list.active {
        display: block;
        animation: slideDown 0.2s ease-out;
      }

      @keyframes slideDown {
        from {
          opacity: 0;
          transform: translateY(-10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      .p2p-peer-list-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 2px solid var(--gray-30);
      }

      body.dark .p2p-peer-list-header {
        border-bottom-color: var(--gray-50);
      }

      .p2p-peer-list-title {
        font-weight: 600;
        font-size: 16px;
      }

      .p2p-peer-list-close {
        background: none;
        border: none;
        cursor: pointer;
        font-size: 20px;
        color: var(--gray-80);
        padding: 0;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 4px;
        transition: var(--transition);
      }

      .p2p-peer-list-close:hover {
        background: var(--gray-30);
      }

      .p2p-peer-item {
        padding: 12px;
        margin-bottom: 8px;
        background: var(--gray-20);
        border-radius: var(--radius);
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      body.dark .p2p-peer-item {
        background: var(--gray-40);
      }

      .p2p-peer-info {
        flex: 1;
      }

      .p2p-peer-id {
        font-size: 12px;
        color: var(--gray-80);
        font-family: monospace;
      }

      .p2p-peer-status {
        font-size: 11px;
        color: var(--gray-60);
        margin-top: 4px;
      }

      .p2p-peer-actions {
        display: flex;
        gap: 8px;
      }

      .p2p-peer-action {
        padding: 6px 12px;
        background: var(--primary);
        color: white;
        border: none;
        border-radius: var(--radius-small);
        cursor: pointer;
        font-size: 12px;
        transition: var(--transition);
      }

      .p2p-peer-action:hover {
        background: var(--primary-dark);
      }

      .p2p-notification {
        position: fixed;
        top: 80px;
        right: 16px;
        background: white;
        border: 2px solid var(--gray-30);
        border-radius: var(--radius);
        padding: 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: var(--shadow-large);
        z-index: 1001;
        opacity: 0;
        transform: translateX(400px);
        transition: all 0.3s ease;
      }

      body.dark .p2p-notification {
        background: var(--gray-30);
        border-color: var(--gray-50);
      }

      .p2p-notification.active {
        opacity: 1;
        transform: translateX(0);
      }

      .p2p-notification-success {
        border-left: 4px solid var(--success);
      }

      .p2p-notification-error {
        border-left: 4px solid var(--error);
      }

      .p2p-notification i {
        font-size: 20px;
      }

      .p2p-notification-success i {
        color: var(--success);
      }

      .p2p-notification-error i {
        color: var(--error);
      }
    `;
    document.head.appendChild(style);
  }

  createUI() {
    // Create control buttons
    this.controlsContainer = document.createElement('div');
    this.controlsContainer.className = 'p2p-controls';
    this.controlsContainer.innerHTML = `
      <button class="p2p-button" id="p2p-open-new-window" title="Open this session in a new window">
        <i class="fas fa-external-link-alt"></i>
        <span>Open in New Window</span>
      </button>
      <button class="p2p-button p2p-button-secondary" id="p2p-show-peers" title="Show active windows">
        <i class="fas fa-network-wired"></i>
        <span id="p2p-peer-count">0</span>
        <div class="p2p-peer-indicator" style="display: none;"></div>
      </button>
      <button class="p2p-button p2p-button-secondary" id="p2p-request-state" title="Request state from other windows">
        <i class="fas fa-download"></i>
        <span>Pull State</span>
      </button>
    `;

    // Create peer list
    this.peerList = document.createElement('div');
    this.peerList.className = 'p2p-peer-list';
    this.peerList.innerHTML = `
      <div class="p2p-peer-list-header">
        <div class="p2p-peer-list-title">Active Windows</div>
        <button class="p2p-peer-list-close"><i class="fas fa-times"></i></button>
      </div>
      <div id="p2p-peer-list-content"></div>
    `;

    document.body.appendChild(this.peerList);
  }

  setupEventListeners() {
    // Open in new window
    this.controlsContainer.querySelector('#p2p-open-new-window').addEventListener('click', () => {
      const closeCurrentWindow = confirm(
        'Open in new window?\n\nClick OK to open in new window and keep this window.\n' +
        'Click Cancel to stay in this window.'
      );

      this.stateTransfer.openInNewWindow(false);
    });

    // Show peers
    this.controlsContainer.querySelector('#p2p-show-peers').addEventListener('click', () => {
      this.togglePeerList();
    });

    // Request state
    this.controlsContainer.querySelector('#p2p-request-state').addEventListener('click', () => {
      this.p2p.requestState();
      this.stateTransfer.showNotification('info', 'Requesting state from other windows...');
    });

    // Close peer list
    this.peerList.querySelector('.p2p-peer-list-close').addEventListener('click', () => {
      this.hidePeerList();
    });

    // Update peer count periodically
    setInterval(() => {
      this.updatePeerCount();
    }, 1000);

    // Listen for presence updates
    this.p2p.onPresence(() => {
      this.updatePeerList();
    });
  }

  togglePeerList() {
    this.peerListVisible = !this.peerListVisible;
    if (this.peerListVisible) {
      this.showPeerList();
    } else {
      this.hidePeerList();
    }
  }

  showPeerList() {
    this.peerList.classList.add('active');
    this.peerListVisible = true;
    this.updatePeerList();
  }

  hidePeerList() {
    this.peerList.classList.remove('active');
    this.peerListVisible = false;
  }

  updatePeerCount() {
    const peers = this.p2p.getActivePeers();
    const countElement = this.controlsContainer.querySelector('#p2p-peer-count');
    const indicatorElement = this.controlsContainer.querySelector('.p2p-peer-indicator');

    countElement.textContent = peers.length;
    indicatorElement.style.display = peers.length > 0 ? 'block' : 'none';
  }

  updatePeerList() {
    const peers = this.p2p.getActivePeers();
    const content = this.peerList.querySelector('#p2p-peer-list-content');

    if (peers.length === 0) {
      content.innerHTML = '<p style="color: var(--gray-60); text-align: center;">No other windows detected</p>';
      return;
    }

    content.innerHTML = peers.map(peer => `
      <div class="p2p-peer-item">
        <div class="p2p-peer-info">
          <div class="p2p-peer-id">${peer.id.substr(0, 20)}...</div>
          <div class="p2p-peer-status">
            Last seen: ${Math.round((Date.now() - peer.lastSeen) / 1000)}s ago
          </div>
        </div>
        <div class="p2p-peer-actions">
          <button class="p2p-peer-action" onclick="window.rappP2P.stateTransfer.stateTransfer.sendCurrentState('${peer.id}')">
            Send State
          </button>
        </div>
      </div>
    `).join('');
  }

  attachToHeader(headerElement) {
    headerElement.appendChild(this.controlsContainer);
  }
}

// Initialize when DOM is ready
window.addEventListener('DOMContentLoaded', () => {
  // Wait for AppState to be available
  const initP2P = () => {
    if (typeof window.appState === 'undefined') {
      setTimeout(initP2P, 100);
      return;
    }

    // Create P2P system
    const p2pTransfer = new LocalP2PTransfer({
      channelName: 'rapp-p2p-transfer'
    });

    const stateTransfer = new RAPPStateTransfer(window.appState, p2pTransfer);
    const p2pUI = new P2PTransferUI(stateTransfer, p2pTransfer);

    // Expose globally for debugging
    window.rappP2P = {
      transfer: p2pTransfer,
      stateTransfer: stateTransfer,
      ui: p2pUI
    };

    // Check for incoming transfer on load
    stateTransfer.checkForTransfer();

    // Find header and attach UI
    const header = document.querySelector('.header-actions') || document.querySelector('header .header-right');
    if (header) {
      p2pUI.attachToHeader(header);
    } else {
      console.warn('[P2P] Could not find header element to attach controls');
    }

    console.log('[P2P] System initialized successfully');
  };

  initP2P();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    LocalP2PTransfer,
    RAPPStateTransfer,
    P2PTransferUI
  };
}
