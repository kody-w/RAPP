// The grail one-liner, pinned to the kernel release RAPP pins in KERNEL_PIN.json. Windows has none: the
// installer's Windows script at that tag takes no version pin and follows the installer's main branch, the
// newest channel, so it is not offered.
export const GRAIL = {
	repository: 'kody-w/rapp-installer',
	tag: 'brainstem-v0.6.9',
	unix: 'curl -fsSL https://raw.githubusercontent.com/kody-w/rapp-installer/brainstem-v0.6.9/install.sh | bash -s -- --version brainstem-v0.6.9',
	start: 'brainstem',
} as const;

export function grailOneLiner(platform: NodeJS.Platform = process.platform): { label: string; command?: string; note?: string } {
	if (platform === 'win32') {
		return {
			label: 'Windows',
			note: 'There is no pinned one-liner for Windows yet: the installer\'s Windows script at brainstem-v0.6.9 follows its newest channel instead of installing exactly that release.',
		};
	}
	return { label: platform === 'darwin' ? 'macOS' : 'Linux', command: GRAIL.unix };
}
