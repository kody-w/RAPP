// The Brainstem mark: one geometry, rendered to SVG and rasterized to PNG/ICO/ICNS in plain Node.
// No binary artwork is committed; every icon the build needs is generated from these shapes.
import zlib from 'node:zlib';

export const PALETTE = {
	tile: '#16233f',
	stem: '#e8ecf2',
	core: '#f2b544',
	node: '#7fd3c8',
};

const NODES = [[0.315, 0.335], [0.685, 0.335], [0.5, 0.245]];
const CORE = [0.5, 0.47];

// Unit square, y down. Drawn in order.
export function iconShapes() {
	return [
		{ kind: 'rrect', x: 0.09, y: 0.09, w: 0.82, h: 0.82, r: 0.19, fill: PALETTE.tile },
		{ kind: 'segment', x1: 0.5, y1: 0.765, x2: CORE[0], y2: CORE[1], w: 0.075, fill: PALETTE.stem },
		...NODES.map(([x, y]) => ({ kind: 'segment', x1: CORE[0], y1: CORE[1], x2: x, y2: y, w: 0.05, fill: PALETTE.stem })),
		...NODES.map(([x, y]) => ({ kind: 'circle', cx: x, cy: y, r: 0.058, fill: PALETTE.node })),
		{ kind: 'circle', cx: CORE[0], cy: CORE[1], r: 0.095, fill: PALETTE.core },
	];
}

// The mark alone, one color, scaled to fill the square.
export function markShapes(color) {
	const k = 1 / 0.62, ox = 0.5 - 0.5 * k, oy = 0.5 - 0.5 * k - 0.02 * k;
	const t = (x, y) => [ox + x * k, oy + y * k];
	const [cx, cy] = t(...CORE);
	const stemEnd = t(0.5, 0.765);
	return [
		{ kind: 'segment', x1: stemEnd[0], y1: stemEnd[1], x2: cx, y2: cy, w: 0.075 * k, fill: color },
		...NODES.map(p => t(...p)).map(([x, y]) => ({ kind: 'segment', x1: cx, y1: cy, x2: x, y2: y, w: 0.05 * k, fill: color })),
		...NODES.map(p => t(...p)).map(([x, y]) => ({ kind: 'circle', cx: x, cy: y, r: 0.058 * k, fill: color })),
		{ kind: 'circle', cx, cy, r: 0.095 * k, fill: color },
	];
}

const n = v => Number(v.toFixed(2));

function shapeSvg(s, size) {
	const u = v => n(v * size);
	if (s.kind === 'rrect') {
		return `<rect x="${u(s.x)}" y="${u(s.y)}" width="${u(s.w)}" height="${u(s.h)}" rx="${u(s.r)}" fill="${s.fill}"/>`;
	}
	if (s.kind === 'circle') {
		return `<circle cx="${u(s.cx)}" cy="${u(s.cy)}" r="${u(s.r)}" fill="${s.fill}"/>`;
	}
	return `<line x1="${u(s.x1)}" y1="${u(s.y1)}" x2="${u(s.x2)}" y2="${u(s.y2)}" stroke="${s.fill}" stroke-width="${u(s.w)}" stroke-linecap="round"/>`;
}

export function toSvg(shapes, size, attrs = '') {
	return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"${attrs ? ' ' + attrs : ''}>`
		+ shapes.map(s => shapeSvg(s, size)).join('') + '</svg>\n';
}

export function iconSvg() {
	return toSvg(iconShapes(), 1024);
}

// The empty-editor watermark, in the four upstream theme variants.
export function letterpressSvg(variant) {
	const styles = {
		'letterpress-light': ['#000000', 'opacity="0.1"'],
		'letterpress-dark': ['#000000', 'opacity="0.3"'],
		'letterpress-hcLight': ['#D9D9D9', ''],
		'letterpress-hcDark': ['#3C3C3C', ''],
	};
	const style = styles[variant];
	if (!style) {
		throw new Error(`unknown letterpress variant ${variant}`);
	}
	return toSvg(markShapes(style[0]), 260, style[1]);
}

// ---- rasterizing: signed distances with a one-pixel box filter ----

function hex(color) {
	const v = parseInt(color.slice(1), 16);
	return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}

function distance(s, x, y) {
	if (s.kind === 'circle') {
		return Math.hypot(x - s.cx, y - s.cy) - s.r;
	}
	if (s.kind === 'segment') {
		const dx = s.x2 - s.x1, dy = s.y2 - s.y1;
		const len2 = dx * dx + dy * dy;
		const t = len2 ? Math.max(0, Math.min(1, ((x - s.x1) * dx + (y - s.y1) * dy) / len2)) : 0;
		return Math.hypot(x - (s.x1 + t * dx), y - (s.y1 + t * dy)) - s.w / 2;
	}
	const hx = s.w / 2 - s.r, hy = s.h / 2 - s.r;
	const qx = Math.abs(x - (s.x + s.w / 2)) - hx, qy = Math.abs(y - (s.y + s.h / 2)) - hy;
	return Math.hypot(Math.max(qx, 0), Math.max(qy, 0)) + Math.min(Math.max(qx, qy), 0) - s.r;
}

export function rasterize(shapes, size) {
	const rgba = new Uint8Array(size * size * 4);
	const colors = shapes.map(s => hex(s.fill));
	for (let py = 0; py < size; py++) {
		const y = (py + 0.5) / size;
		for (let px = 0; px < size; px++) {
			const x = (px + 0.5) / size;
			let r = 0, g = 0, b = 0, a = 0;
			for (let k = 0; k < shapes.length; k++) {
				const cover = Math.max(0, Math.min(1, 0.5 - distance(shapes[k], x, y) * size));
				if (cover === 0) {
					continue;
				}
				const [cr, cg, cb] = colors[k];
				const na = cover + a * (1 - cover);
				r = (cr * cover + r * a * (1 - cover)) / na;
				g = (cg * cover + g * a * (1 - cover)) / na;
				b = (cb * cover + b * a * (1 - cover)) / na;
				a = na;
			}
			const i = (py * size + px) * 4;
			rgba[i] = Math.round(r);
			rgba[i + 1] = Math.round(g);
			rgba[i + 2] = Math.round(b);
			rgba[i + 3] = Math.round(a * 255);
		}
	}
	return rgba;
}

const CRC = (() => {
	const table = new Uint32Array(256);
	for (let i = 0; i < 256; i++) {
		let c = i;
		for (let k = 0; k < 8; k++) {
			c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
		}
		table[i] = c >>> 0;
	}
	return table;
})();

function crc32(buf) {
	let c = 0xffffffff;
	for (const byte of buf) {
		c = CRC[(c ^ byte) & 255] ^ (c >>> 8);
	}
	return (c ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
	const head = Buffer.alloc(8);
	head.writeUInt32BE(data.length, 0);
	head.write(type, 4, 'ascii');
	const crc = Buffer.alloc(4);
	crc.writeUInt32BE(crc32(Buffer.concat([head.subarray(4), data])), 0);
	return Buffer.concat([head, data, crc]);
}

export function encodePng(size, rgba) {
	const stride = size * 4;
	const raw = Buffer.alloc((stride + 1) * size);
	for (let y = 0; y < size; y++) {
		raw[y * (stride + 1)] = 0;
		raw.set(rgba.subarray(y * stride, (y + 1) * stride), y * (stride + 1) + 1);
	}
	const ihdr = Buffer.alloc(13);
	ihdr.writeUInt32BE(size, 0);
	ihdr.writeUInt32BE(size, 4);
	ihdr.set([8, 6, 0, 0, 0], 8);
	return Buffer.concat([
		Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
		pngChunk('IHDR', ihdr),
		pngChunk('IDAT', zlib.deflateSync(raw, { level: 9 })),
		pngChunk('IEND', Buffer.alloc(0)),
	]);
}

const cache = new Map();
export function iconPng(size) {
	if (!cache.has(size)) {
		cache.set(size, encodePng(size, rasterize(iconShapes(), size)));
	}
	return cache.get(size);
}

// ICO with PNG-compressed entries (Windows Vista and later).
export function encodeIco(sizes) {
	const images = sizes.map(iconPng);
	const header = Buffer.alloc(6 + 16 * images.length);
	header.writeUInt16LE(0, 0);
	header.writeUInt16LE(1, 2);
	header.writeUInt16LE(images.length, 4);
	let offset = header.length;
	images.forEach((png, i) => {
		const e = 6 + 16 * i;
		header[e] = sizes[i] >= 256 ? 0 : sizes[i];
		header[e + 1] = sizes[i] >= 256 ? 0 : sizes[i];
		header.writeUInt16LE(1, e + 4);
		header.writeUInt16LE(32, e + 6);
		header.writeUInt32LE(png.length, e + 8);
		header.writeUInt32LE(offset, e + 12);
		offset += png.length;
	});
	return Buffer.concat([header, ...images]);
}

// ICNS with PNG entries (macOS 10.7 and later).
export function encodeIcns() {
	const entries = [['icp4', 16], ['icp5', 32], ['icp6', 64], ['ic07', 128], ['ic08', 256], ['ic09', 512],
		['ic10', 1024], ['ic11', 32], ['ic12', 64], ['ic13', 256], ['ic14', 512]].map(([type, size]) => {
		const png = iconPng(size);
		const head = Buffer.alloc(8);
		head.write(type, 0, 'ascii');
		head.writeUInt32BE(png.length + 8, 4);
		return Buffer.concat([head, png]);
	});
	const body = Buffer.concat(entries);
	const head = Buffer.alloc(8);
	head.write('icns', 0, 'ascii');
	head.writeUInt32BE(body.length + 8, 4);
	return Buffer.concat([head, body]);
}

// One asset for an overlay.json `branding.generated` kind.
export function renderAsset(kind) {
	if (kind === 'icns') {
		return encodeIcns();
	}
	if (kind === 'ico') {
		return encodeIco([16, 24, 32, 48, 64, 128, 256]);
	}
	if (kind === 'favicon') {
		return encodeIco([16, 32, 48]);
	}
	if (kind.startsWith('png:')) {
		return iconPng(Number(kind.slice(4)));
	}
	if (kind === 'svg:icon') {
		return Buffer.from(iconSvg());
	}
	if (kind.startsWith('svg:')) {
		return Buffer.from(letterpressSvg(kind.slice(4)));
	}
	throw new Error(`unknown branding kind ${kind}`);
}
