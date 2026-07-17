'use strict';

const net = require('node:net');
const tls = require('node:tls');
const dgram = require('node:dgram');
const dns = require('node:dns');

if (process.env.RAPP1_NODE_NETWORK_GUARD !== '1') {
  throw new Error('Node network guard was not preloaded');
}

function expectBlocked(label, operation) {
  try {
    operation();
  } catch (error) {
    if (
      error.code === 'RAPP1_OFFLINE_NETWORK'
      && /RAPP1 offline gate blocks/.test(String(error))
    ) {
      return;
    }
    throw new Error(`${label} raised the wrong error: ${error}`);
  }
  throw new Error(`${label} did not synchronously block external egress`);
}

expectBlocked('net.Socket.prototype.connect', () => {
  new net.Socket().connect({ host: '192.0.2.1', port: 80 });
});
expectBlocked('127-prefixed hostname', () => {
  new net.Socket().connect({ host: '127.attacker.example', port: 80 });
});
expectBlocked('tls.connect', () => {
  tls.connect({ host: '192.0.2.1', port: 443 });
});
expectBlocked('tls.TLSSocket.prototype.connect', () => {
  new tls.TLSSocket(new net.Socket()).connect({
    host: '192.0.2.1',
    port: 443,
  });
});
expectBlocked('dgram.Socket.prototype.connect', () => {
  dgram.createSocket('udp4').connect(9, '192.0.2.1');
});
expectBlocked('dgram.Socket.prototype.send', () => {
  dgram.createSocket('udp4').send(Buffer.from('x'), 9, '192.0.2.1');
});
expectBlocked('dns.lookup', () => {
  dns.lookup('example.invalid', () => {});
});
expectBlocked('dns.promises.resolve', () => {
  dns.promises.resolve('example.invalid');
});
expectBlocked('dns.setServers', () => {
  dns.setServers(['192.0.2.1']);
});
expectBlocked('global fetch', () => {
  globalThis.fetch('https://example.com/');
});

const timeout = setTimeout(() => {
  throw new Error('loopback raw-socket probe timed out');
}, 3000);
const server = net.createServer((socket) => socket.end('loopback-ok'));
server.listen(0, '127.0.0.1', () => {
  const address = server.address();
  const client = new net.Socket();
  let response = '';
  client.setEncoding('utf8');
  client.once('error', (error) => {
    throw error;
  });
  client.on('data', (chunk) => {
    response += chunk;
  });
  client.once('end', () => {
    if (response !== 'loopback-ok') {
      throw new Error(`loopback response mismatch: ${JSON.stringify(response)}`);
    }
    server.close(() => {
      clearTimeout(timeout);
      console.log('Node raw network guard blocks external egress and permits loopback');
    });
  });
  client.connect({ host: '127.0.0.1', port: address.port });
});
