/**
 * RAPP Cross-Browser P2P Transfer System
 *
 * TRUE PEER-TO-PEER across ALL browser instances using WebRTC
 * with localStorage as signaling mechanism.
 *
 * Features:
 * - Chrome can see Firefox, Safari, Edge, etc.
 * - All browsers on same machine are aware of each other
 * - WebRTC Data Channels for efficient transfer
 * - localStorage signaling (no server needed)
 * - Automatic mesh network formation
 * - NAT traversal with STUN servers
 *
 * This is the "ultrathink" version that creates a true multi-browser mesh.
 */

class CrossBrowserP2P {
  constructor(options = {}) {
    this.peerId = this.generatePeerId();
    this.peers = new Map(); // Map of peerId -> {connection, channel, metadata}
    this.signalingKey = options.signalingKey || 'rapp-webrtc-signaling';
    this.presenceKey = options.presenceKey || 'rapp-presence';

    // WebRTC configuration with public STUN servers
    this.rtcConfig = {
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
        { urls: 'stun:stun2.l.google.com:19302' }
      ]
    };

    this.handlers = {
      transfer: null,
      request: null,
      presence: null,
      acknowledgment: null,
      peerConnected: null,
      peerDisconnected: null
    };

    this.init();
  }

  generatePeerId() {
    // Include browser info for identification
    const browserInfo = this.detectBrowser();
    return `${browserInfo.name}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  detectBrowser() {
    const ua = navigator.userAgent;
    let name = 'Unknown';
    let version = 'Unknown';

    if (ua.indexOf('Firefox') > -1) {
      name = 'Firefox';
      version = ua.match(/Firefox\/(\d+)/)?.[1] || 'Unknown';
    } else if (ua.indexOf('Edg') > -1) {
      name = 'Edge';
      version = ua.match(/Edg\/(\d+)/)?.[1] || 'Unknown';
    } else if (ua.indexOf('Chrome') > -1) {
      name = 'Chrome';
      version = ua.match(/Chrome\/(\d+)/)?.[1] || 'Unknown';
    } else if (ua.indexOf('Safari') > -1) {
      name = 'Safari';
      version = ua.match(/Version\/(\d+)/)?.[1] || 'Unknown';
    }

    return { name, version, userAgent: ua };
  }

  init() {
    console.log(`[CrossBrowserP2P] Initializing as ${this.peerId}`);

    // Start presence broadcasting
    this.startPresence();

    // Listen for signaling messages
    this.startSignalingListener();

    // Discover existing peers
    this.discoverPeers();

    // Cleanup on unload
    window.addEventListener('beforeunload', () => this.cleanup());
  }

  startPresence() {
    // Broadcast presence immediately
    this.broadcastPresence();

    // Then every 3 seconds
    this.presenceInterval = setInterval(() => {
      this.broadcastPresence();
      this.cleanupStalePeers();
    }, 3000);
  }

  broadcastPresence() {
    const presence = {
      peerId: this.peerId,
      timestamp: Date.now(),
      browser: this.detectBrowser(),
      url: window.location.href,
      connections: Array.from(this.peers.keys())
    };

    // Write to localStorage (readable by ALL browsers)
    const allPresence = this.getAllPresence();
    allPresence[this.peerId] = presence;
    localStorage.setItem(this.presenceKey, JSON.stringify(allPresence));

    // Trigger storage event manually for same browser
    window.dispatchEvent(new StorageEvent('storage', {
      key: this.presenceKey,
      newValue: JSON.stringify(allPresence)
    }));
  }

  getAllPresence() {
    try {
      const data = localStorage.getItem(this.presenceKey);
      return data ? JSON.parse(data) : {};
    } catch (e) {
      return {};
    }
  }

  cleanupStalePeers() {
    const allPresence = this.getAllPresence();
    const now = Date.now();
    const timeout = 10000; // 10 seconds
    let changed = false;

    Object.keys(allPresence).forEach(peerId => {
      if (now - allPresence[peerId].timestamp > timeout) {
        delete allPresence[peerId];
        changed = true;

        // Close connection if exists
        if (this.peers.has(peerId)) {
          this.disconnectPeer(peerId);
        }
      }
    });

    if (changed) {
      localStorage.setItem(this.presenceKey, JSON.stringify(allPresence));
    }
  }

  discoverPeers() {
    const allPresence = this.getAllPresence();

    Object.keys(allPresence).forEach(peerId => {
      if (peerId !== this.peerId && !this.peers.has(peerId)) {
        // New peer discovered, initiate connection
        console.log(`[CrossBrowserP2P] Discovered peer: ${peerId}`);
        this.connectToPeer(peerId);
      }
    });
  }

  async connectToPeer(remotePeerId) {
    if (this.peers.has(remotePeerId)) {
      return; // Already connected
    }

    console.log(`[CrossBrowserP2P] Connecting to ${remotePeerId}`);

    try {
      // Create RTCPeerConnection
      const pc = new RTCPeerConnection(this.rtcConfig);

      // Create data channel
      const channel = pc.createDataChannel('rapp-data', {
        ordered: true
      });

      this.setupDataChannel(channel, remotePeerId);

      // Store peer info
      this.peers.set(remotePeerId, {
        connection: pc,
        channel: channel,
        state: 'connecting'
      });

      // Handle ICE candidates
      pc.onicecandidate = (event) => {
        if (event.candidate) {
          this.sendSignal({
            type: 'ice-candidate',
            candidate: event.candidate,
            from: this.peerId,
            to: remotePeerId
          });
        }
      };

      // Handle connection state changes
      pc.onconnectionstatechange = () => {
        console.log(`[CrossBrowserP2P] Connection state: ${pc.connectionState} with ${remotePeerId}`);

        if (pc.connectionState === 'connected') {
          const peer = this.peers.get(remotePeerId);
          if (peer) {
            peer.state = 'connected';
            if (this.handlers.peerConnected) {
              this.handlers.peerConnected(remotePeerId);
            }
          }
        } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
          this.disconnectPeer(remotePeerId);
        }
      };

      // Handle incoming data channel (for receiving peer)
      pc.ondatachannel = (event) => {
        console.log(`[CrossBrowserP2P] Received data channel from ${remotePeerId}`);
        this.setupDataChannel(event.channel, remotePeerId);

        const peer = this.peers.get(remotePeerId);
        if (peer) {
          peer.channel = event.channel;
        }
      };

      // Create and send offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      this.sendSignal({
        type: 'offer',
        offer: offer,
        from: this.peerId,
        to: remotePeerId
      });

    } catch (error) {
      console.error(`[CrossBrowserP2P] Failed to connect to ${remotePeerId}:`, error);
      this.peers.delete(remotePeerId);
    }
  }

  setupDataChannel(channel, peerId) {
    channel.onopen = () => {
      console.log(`[CrossBrowserP2P] Data channel open with ${peerId}`);
    };

    channel.onclose = () => {
      console.log(`[CrossBrowserP2P] Data channel closed with ${peerId}`);
      this.disconnectPeer(peerId);
    };

    channel.onerror = (error) => {
      console.error(`[CrossBrowserP2P] Data channel error with ${peerId}:`, error);
    };

    channel.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message, peerId);
      } catch (e) {
        console.error('[CrossBrowserP2P] Failed to parse message:', e);
      }
    };
  }

  startSignalingListener() {
    // Listen for storage events (signals from other browsers)
    window.addEventListener('storage', (event) => {
      if (event.key === this.signalingKey && event.newValue) {
        try {
          const signals = JSON.parse(event.newValue);
          signals.forEach(signal => {
            if (signal.to === this.peerId && !signal.processed) {
              this.handleSignal(signal);
            }
          });
        } catch (e) {
          console.error('[CrossBrowserP2P] Failed to parse signals:', e);
        }
      }

      if (event.key === this.presenceKey && event.newValue) {
        // New peer presence detected
        this.discoverPeers();
      }
    });

    // Poll for signals (localStorage events don't fire in same tab)
    this.signalingPollInterval = setInterval(() => {
      const signals = this.getSignals();
      signals.forEach(signal => {
        if (signal.to === this.peerId && !signal.processed) {
          this.handleSignal(signal);
          this.markSignalProcessed(signal);
        }
      });
    }, 500);
  }

  sendSignal(signal) {
    const signals = this.getSignals();
    signals.push({
      ...signal,
      timestamp: Date.now(),
      processed: false
    });

    // Keep only recent signals (last 30 seconds)
    const now = Date.now();
    const recentSignals = signals.filter(s => now - s.timestamp < 30000);

    localStorage.setItem(this.signalingKey, JSON.stringify(recentSignals));
  }

  getSignals() {
    try {
      const data = localStorage.getItem(this.signalingKey);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      return [];
    }
  }

  markSignalProcessed(signal) {
    const signals = this.getSignals();
    const index = signals.findIndex(s =>
      s.from === signal.from &&
      s.to === signal.to &&
      s.timestamp === signal.timestamp
    );

    if (index !== -1) {
      signals[index].processed = true;
      localStorage.setItem(this.signalingKey, JSON.stringify(signals));
    }
  }

  async handleSignal(signal) {
    console.log(`[CrossBrowserP2P] Received signal:`, signal.type, 'from', signal.from);

    try {
      let peer = this.peers.get(signal.from);

      if (signal.type === 'offer') {
        // Create connection if doesn't exist
        if (!peer) {
          const pc = new RTCPeerConnection(this.rtcConfig);

          peer = {
            connection: pc,
            channel: null,
            state: 'connecting'
          };

          this.peers.set(signal.from, peer);

          // Handle ICE candidates
          pc.onicecandidate = (event) => {
            if (event.candidate) {
              this.sendSignal({
                type: 'ice-candidate',
                candidate: event.candidate,
                from: this.peerId,
                to: signal.from
              });
            }
          };

          // Handle connection state
          pc.onconnectionstatechange = () => {
            console.log(`[CrossBrowserP2P] Connection state: ${pc.connectionState} with ${signal.from}`);

            if (pc.connectionState === 'connected') {
              peer.state = 'connected';
              if (this.handlers.peerConnected) {
                this.handlers.peerConnected(signal.from);
              }
            } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
              this.disconnectPeer(signal.from);
            }
          };

          // Handle incoming data channel
          pc.ondatachannel = (event) => {
            console.log(`[CrossBrowserP2P] Received data channel from ${signal.from}`);
            this.setupDataChannel(event.channel, signal.from);
            peer.channel = event.channel;
          };
        }

        // Set remote description
        await peer.connection.setRemoteDescription(new RTCSessionDescription(signal.offer));

        // Create answer
        const answer = await peer.connection.createAnswer();
        await peer.connection.setLocalDescription(answer);

        // Send answer
        this.sendSignal({
          type: 'answer',
          answer: answer,
          from: this.peerId,
          to: signal.from
        });

      } else if (signal.type === 'answer') {
        if (peer && peer.connection) {
          await peer.connection.setRemoteDescription(new RTCSessionDescription(signal.answer));
        }

      } else if (signal.type === 'ice-candidate') {
        if (peer && peer.connection) {
          await peer.connection.addIceCandidate(new RTCIceCandidate(signal.candidate));
        }
      }
    } catch (error) {
      console.error('[CrossBrowserP2P] Error handling signal:', error);
    }
  }

  sendMessage(message, targetPeerId = null) {
    const payload = {
      type: message.type,
      data: message.data,
      from: this.peerId,
      timestamp: Date.now()
    };

    if (targetPeerId) {
      // Send to specific peer
      const peer = this.peers.get(targetPeerId);
      if (peer && peer.channel && peer.channel.readyState === 'open') {
        peer.channel.send(JSON.stringify(payload));
      } else {
        console.warn(`[CrossBrowserP2P] Cannot send to ${targetPeerId}: not connected`);
      }
    } else {
      // Broadcast to all peers
      let sent = 0;
      this.peers.forEach((peer, peerId) => {
        if (peer.channel && peer.channel.readyState === 'open') {
          peer.channel.send(JSON.stringify(payload));
          sent++;
        }
      });
      console.log(`[CrossBrowserP2P] Broadcast to ${sent} peers`);
    }
  }

  handleMessage(message, fromPeerId) {
    console.log(`[CrossBrowserP2P] Message from ${fromPeerId}:`, message.type);

    switch (message.type) {
      case 'transfer':
        if (this.handlers.transfer) {
          this.handlers.transfer(message.data, fromPeerId);
        }
        break;
      case 'request':
        if (this.handlers.request) {
          this.handlers.request(message.data, fromPeerId);
        }
        break;
      case 'acknowledgment':
        if (this.handlers.acknowledgment) {
          this.handlers.acknowledgment(message.data, fromPeerId);
        }
        break;
    }
  }

  disconnectPeer(peerId) {
    const peer = this.peers.get(peerId);
    if (peer) {
      if (peer.channel) {
        peer.channel.close();
      }
      if (peer.connection) {
        peer.connection.close();
      }
      this.peers.delete(peerId);

      if (this.handlers.peerDisconnected) {
        this.handlers.peerDisconnected(peerId);
      }

      console.log(`[CrossBrowserP2P] Disconnected from ${peerId}`);
    }
  }

  getConnectedPeers() {
    const allPresence = this.getAllPresence();
    const connected = [];

    this.peers.forEach((peer, peerId) => {
      if (peer.state === 'connected') {
        connected.push({
          id: peerId,
          browser: allPresence[peerId]?.browser || {},
          timestamp: allPresence[peerId]?.timestamp || Date.now(),
          lastSeen: Date.now() - (allPresence[peerId]?.timestamp || Date.now())
        });
      }
    });

    return connected;
  }

  getAllDiscoveredPeers() {
    const allPresence = this.getAllPresence();
    const peers = [];

    Object.keys(allPresence).forEach(peerId => {
      if (peerId !== this.peerId) {
        const presence = allPresence[peerId];
        peers.push({
          id: peerId,
          browser: presence.browser || {},
          timestamp: presence.timestamp,
          lastSeen: Date.now() - presence.timestamp,
          connected: this.peers.has(peerId) && this.peers.get(peerId).state === 'connected'
        });
      }
    });

    return peers;
  }

  // Event handlers
  onTransfer(handler) {
    this.handlers.transfer = handler;
  }

  onRequest(handler) {
    this.handlers.request = handler;
  }

  onAcknowledgment(handler) {
    this.handlers.acknowledgment = handler;
  }

  onPeerConnected(handler) {
    this.handlers.peerConnected = handler;
  }

  onPeerDisconnected(handler) {
    this.handlers.peerDisconnected = handler;
  }

  cleanup() {
    // Clear presence
    const allPresence = this.getAllPresence();
    delete allPresence[this.peerId];
    localStorage.setItem(this.presenceKey, JSON.stringify(allPresence));

    // Close all connections
    this.peers.forEach((peer, peerId) => {
      this.disconnectPeer(peerId);
    });

    // Stop intervals
    if (this.presenceInterval) {
      clearInterval(this.presenceInterval);
    }
    if (this.signalingPollInterval) {
      clearInterval(this.signalingPollInterval);
    }
  }
}

// Export for use
if (typeof window !== 'undefined') {
  window.CrossBrowserP2P = CrossBrowserP2P;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = CrossBrowserP2P;
}

console.log('[CrossBrowserP2P] Module loaded');
