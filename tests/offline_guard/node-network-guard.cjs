'use strict';

const net = require('node:net');
const tls = require('node:tls');
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
  return value === 'localhost'
    || value.endsWith('.localhost')
    || value === '::1'
    || value === '::'
    || value === '0.0.0.0'
    || value.startsWith('127.');
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

net.connect = guardConnect(net.connect);
net.createConnection = guardConnect(net.createConnection);
tls.connect = guardConnect(tls.connect);

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
