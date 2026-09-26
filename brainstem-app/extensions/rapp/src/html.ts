import { randomBytes } from 'crypto';
import * as vscode from 'vscode';

export function makeNonce(): string {
	return randomBytes(18).toString('base64');
}

export function escapeHtml(text: string): string {
	return text.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\'': '&#39;' })[c] as string);
}

// A strict policy: nothing loads except this extension's own media, styles and scripts carrying the nonce.
export function contentSecurityPolicy(webview: vscode.Webview, nonce: string, options: { scripts: boolean; styleHashes?: readonly string[] }): string {
	const styles = [`'nonce-${nonce}'`, ...(options.styleHashes?.length ? ['\'unsafe-hashes\'', ...options.styleHashes.map(h => `'${h}'`)] : [])];
	return [
		'default-src \'none\'',
		`img-src ${webview.cspSource}`,
		`style-src ${styles.join(' ')}`,
		`script-src ${options.scripts ? `'nonce-${nonce}'` : '\'none\''}`,
		'connect-src \'none\'',
		'frame-src \'none\'',
		'form-action \'none\'',
		'base-uri \'none\'',
	].join('; ');
}
