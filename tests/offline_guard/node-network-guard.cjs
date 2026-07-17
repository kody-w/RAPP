'use strict';

const net = require('node:net');
const tls = require('node:tls');
const dgram = require('node:dgram');
const dns = require('node:dns');
const http = require('node:http');
const https = require('node:https');

function normalizeHost(host) {
  if (host === undefined || host === null || host === '') return 'localhost';
  let value = String(host).toLowerCase();
  if (value.startsWith('[') && value.includes(']')) {
    value = value.slice(1, value.indexOf(']'));
  } else if (net.isIP(value) === 0 && value.includes(':')) {
    value = value.split(':', 1)[0];
  }
  const zone = value.indexOf('%');
  return zone === -1 ? value : value.slice(0, zone);
}

function isLocalHost(host) {
  const value = normalizeHost(host);
  const ipVersion = net.isIP(value);
  const firstOctet = ipVersion === 4
    ? Number.parseInt(value.split('.')[0], 10)
    : null;
  return value === 'localhost'
    || value.endsWith('.localhost')
    || value === '::1'
    || value === '::'
    || value === '0.0.0.0'
    || (ipVersion === 4 && firstOctet === 127);
}

function requireLocal(host) {
  if (!isLocalHost(host)) {
    const error = new Error(
      `RAPP1 offline gate blocks external network host ${JSON.stringify(host)}`,
    );
    error.code = 'RAPP1_OFFLINE_NETWORK';
    throw error;
  }
}

function connectHost(args) {
  const first = args[0];
  if (Array.isArray(first)) return connectHost(first);
  if (first && typeof first === 'object') {
    if (first.path) return null;
    return first.hostname || first.host || 'localhost';
  }
  if (typeof first === 'number') {
    return typeof args[1] === 'string' ? args[1] : 'localhost';
  }
  return null;
}

function guardConnect(original) {
  return function guardedConnect(...args) {
    const host = connectHost(args);
    if (host !== null) requireLocal(host);
    return original.apply(this, args);
  };
}

net.Socket.prototype.connect = guardConnect(net.Socket.prototype.connect);
net.connect = guardConnect(net.connect);
net.createConnection = guardConnect(net.createConnection);
tls.connect = guardConnect(tls.connect);

if (
  tls.TLSSocket
  && Object.prototype.hasOwnProperty.call(tls.TLSSocket.prototype, 'connect')
) {
  tls.TLSSocket.prototype.connect = guardConnect(tls.TLSSocket.prototype.connect);
}

const originalDgramConnect = dgram.Socket.prototype.connect;
dgram.Socket.prototype.connect = function guardedDgramConnect(...args) {
  const host = typeof args[1] === 'string' ? args[1] : 'localhost';
  requireLocal(host);
  return originalDgramConnect.apply(this, args);
};

const originalDgramSend = dgram.Socket.prototype.send;
dgram.Socket.prototype.send = function guardedDgramSend(...args) {
  let host = null;
  for (let index = args.length - 1; index > 0; index -= 1) {
    if (typeof args[index] === 'string') {
      host = args[index];
      break;
    }
  }
  if (host !== null) requireLocal(host);
  return originalDgramSend.apply(this, args);
};

function guardDnsCall(original) {
  return function guardedDnsCall(host, ...args) {
    requireLocal(host);
    return original.call(this, host, ...args);
  };
}

for (const name of [
  'lookup',
  'lookupService',
  'resolve',
  'resolve4',
  'resolve6',
  'resolveAny',
  'resolveCaa',
  'resolveCname',
  'resolveMx',
  'resolveNaptr',
  'resolveNs',
  'resolvePtr',
  'resolveSoa',
  'resolveSrv',
  'resolveTxt',
  'reverse',
]) {
  if (typeof dns[name] === 'function') dns[name] = guardDnsCall(dns[name]);
  if (dns.Resolver && typeof dns.Resolver.prototype[name] === 'function') {
    dns.Resolver.prototype[name] = guardDnsCall(dns.Resolver.prototype[name]);
  }
  if (dns.promises && typeof dns.promises[name] === 'function') {
    dns.promises[name] = guardDnsCall(dns.promises[name]);
  }
  if (
    dns.promises
    && dns.promises.Resolver
    && typeof dns.promises.Resolver.prototype[name] === 'function'
  ) {
    dns.promises.Resolver.prototype[name] = guardDnsCall(
      dns.promises.Resolver.prototype[name],
    );
  }
}

function guardSetServers(original) {
  return function guardedSetServers(servers) {
    for (const server of servers) requireLocal(server);
    return original.call(this, servers);
  };
}

dns.setServers = guardSetServers(dns.setServers);
if (dns.Resolver && typeof dns.Resolver.prototype.setServers === 'function') {
  dns.Resolver.prototype.setServers = guardSetServers(
    dns.Resolver.prototype.setServers,
  );
}
if (
  dns.promises
  && dns.promises.Resolver
  && typeof dns.promises.Resolver.prototype.setServers === 'function'
) {
  dns.promises.Resolver.prototype.setServers = guardSetServers(
    dns.promises.Resolver.prototype.setServers,
  );
}

function requestHost(input, options) {
  if (options && (options.hostname || options.host)) {
    return options.hostname || options.host;
  }
  if (typeof input === 'string' || input instanceof URL) {
    return new URL(input).hostname;
  }
  if (input && typeof input === 'object') {
    return input.hostname || input.host || 'localhost';
  }
  return 'localhost';
}

function guardRequest(original) {
  return function guardedRequest(input, options, callback) {
    requireLocal(requestHost(input, options));
    return original.call(this, input, options, callback);
  };
}

http.request = guardRequest(http.request);
http.get = guardRequest(http.get);
https.request = guardRequest(https.request);
https.get = guardRequest(https.get);

if (typeof globalThis.fetch === 'function') {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = function guardedFetch(input, options) {
    const url = input instanceof URL ? input : new URL(
      typeof input === 'string' ? input : input.url,
    );
    requireLocal(url.hostname);
    return originalFetch.call(this, input, options);
  };
}

process.env.RAPP1_NODE_NETWORK_GUARD = '1';
