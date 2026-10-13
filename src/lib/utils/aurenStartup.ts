/** One reveal operation per document, shared by layout and chat initialization. */
let revealing: Promise<void> | null = null;

function nextFrame() {
	return new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
}

export async function stableAurenLayout() {
	await document.fonts.ready;
	let previous = '';
	let stable = 0;
	while (stable < 4) {
		await nextFrame();
		const geometry = ['#sidebar', '.lunvri-controls', '#chat-input', '#main-content'].map((selector) => {
			const box = document.querySelector(selector)?.getBoundingClientRect();
			return box ? [box.x, box.y, box.width, box.height].map((n) => Math.round(n * 10) / 10) : null;
		});
		const current = JSON.stringify([innerWidth, innerHeight, geometry]);
		stable = current === previous ? stable + 1 : 0;
		previous = current;
	}
}

export function revealAuren(): Promise<void> {
	if (!document.documentElement.classList.contains('auren-starting')) return Promise.resolve();
	if (revealing) return revealing;
	revealing = (async () => {
		// Finish finite intro effects under the opaque overlay. Infinite response
		// activity and the isolated loading pulse continue independently.
		for (const animation of document.getAnimations()) {
			const target = (animation.effect as KeyframeEffect | null)?.target;
			const timing = animation.effect?.getComputedTiming();
			if (target instanceof Element && !target.closest('#splash-screen') &&
				timing?.iterations !== Infinity && animation.playbackRate > 0) {
				try { animation.finish(); } catch { /* idle effects have no finish position */ }
			}
		}
		await stableAurenLayout();
		const splash = document.getElementById('splash-screen');
		splash?.classList.add('leaving');
		const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
		await new Promise<void>((resolve) => setTimeout(resolve, reducedMotion ? 0 : 380));
		splash?.remove();
		document.documentElement.classList.remove('auren-starting');
		(window as Window & { __aurenInterfaceReady?: boolean }).__aurenInterfaceReady = true;
	})().finally(() => { revealing = null; });
	return revealing;
}

/** Suppress structural transitions before the first visible frame after resume. */
export function installAurenResumeGuard(enabled: () => boolean) {
	let restoring: Promise<void> | null = null;
	let disposed = false;
	const resume = () => {
		if (!enabled() || disposed) return;
		document.documentElement.classList.add('auren-resuming');
		if (document.hidden || restoring) return;
		restoring = stableAurenLayout().finally(() => {
			if (!disposed && !document.hidden) document.documentElement.classList.remove('auren-resuming');
			restoring = null;
		});
	};
	document.addEventListener('visibilitychange', resume);
	window.addEventListener('pageshow', resume);
	window.addEventListener('auren-resume', resume);
	return () => {
		disposed = true;
		document.removeEventListener('visibilitychange', resume);
		window.removeEventListener('pageshow', resume);
		window.removeEventListener('auren-resume', resume);
	};
}
