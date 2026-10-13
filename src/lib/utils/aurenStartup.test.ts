import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { installAurenResumeGuard, revealAuren } from './aurenStartup';

let classes: Set<string>;
let doc: EventTarget & Record<string, any>;
let win: EventTarget & Record<string, any>;
let splash: { classList: { add: ReturnType<typeof vi.fn> }; remove: ReturnType<typeof vi.fn> };

beforeEach(() => {
	vi.useFakeTimers();
	classes = new Set(['auren-starting']);
	doc = Object.assign(new EventTarget(), {
		hidden: false,
		fonts: { ready: Promise.resolve() },
		documentElement: { classList: { contains: (c: string) => classes.has(c), add: (c: string) => classes.add(c), remove: (c: string) => classes.delete(c) } },
		querySelector: vi.fn(() => ({ getBoundingClientRect: () => ({ x: 0, y: 0, width: 520, height: 54 }) })),
		getAnimations: vi.fn(() => []),
	});
	splash = { classList: { add: vi.fn() }, remove: vi.fn() };
	doc.getElementById = vi.fn(() => splash);
	win = new EventTarget();
	vi.stubGlobal('document', doc); vi.stubGlobal('window', win);
	vi.stubGlobal('innerWidth', 520); vi.stubGlobal('innerHeight', 720);
	vi.stubGlobal('requestAnimationFrame', (callback: () => void) => setTimeout(callback, 16));
	vi.stubGlobal('matchMedia', () => ({ matches: false }));
});
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

describe('Auren startup sequence', () => {
	it('coalesces simultaneous callers and removes the overlay exactly once', async () => {
		const first = revealAuren(); const second = revealAuren();
		expect(second).toBe(first);
		await vi.runAllTimersAsync(); await first;
		expect(splash.remove).toHaveBeenCalledTimes(1);
		expect(classes.has('auren-starting')).toBe(false);
		expect(win.__aurenInterfaceReady).toBe(true);
	});
	it('waits for changing geometry before beginning the fade', async () => {
		let width = 400;
		doc.querySelector = () => ({ getBoundingClientRect: () => ({ x: 0, y: 0, width, height: 54 }) });
		const pending = revealAuren();
		await vi.advanceTimersByTimeAsync(32); width = 450;
		await vi.advanceTimersByTimeAsync(32); width = 520;
		expect(splash.classList.add).not.toHaveBeenCalled();
		await vi.runAllTimersAsync(); await pending;
		expect(splash.classList.add).toHaveBeenCalledWith('leaving');
	});
	it('finishes finite intros while preserving the loading pulse and response activity', async () => {
		class Target { constructor(public pulse = false) {} closest() { return this.pulse ? {} : null; } }
		vi.stubGlobal('Element', Target);
		const finite = { effect: { target: new Target(), getComputedTiming: () => ({ iterations: 1 }) }, playbackRate: 1, finish: vi.fn() };
		const pulse = { effect: { target: new Target(true), getComputedTiming: () => ({ iterations: Infinity }) }, playbackRate: 1, finish: vi.fn() };
		const response = { effect: { target: new Target(), getComputedTiming: () => ({ iterations: Infinity }) }, playbackRate: 1, finish: vi.fn() };
		doc.getAnimations = () => [finite, pulse, response];
		const pending = revealAuren(); await vi.runAllTimersAsync(); await pending;
		expect(finite.finish).toHaveBeenCalledTimes(1); expect(pulse.finish).not.toHaveBeenCalled(); expect(response.finish).not.toHaveBeenCalled();
	});
	it('reduced motion does not wait for a 380ms fade', async () => {
		vi.stubGlobal('matchMedia', () => ({ matches: true }));
		const pending = revealAuren(); await vi.advanceTimersByTimeAsync(100); await pending;
		expect(splash.remove).toHaveBeenCalledTimes(1);
	});
	it('does not reset startup or reveal an already visible document', async () => {
		classes.delete('auren-starting'); await revealAuren();
		expect(doc.getAnimations).not.toHaveBeenCalled(); expect(splash.remove).not.toHaveBeenCalled();
	});
	it('guards resume after a long hidden period without clock-based expiry', async () => {
		classes.delete('auren-starting'); const dispose = installAurenResumeGuard(() => true);
		doc.hidden = true; doc.dispatchEvent(new Event('visibilitychange'));
		await vi.advanceTimersByTimeAsync(12 * 60 * 60 * 1000);
		expect(classes.has('auren-resuming')).toBe(true);
		doc.hidden = false; doc.dispatchEvent(new Event('visibilitychange'));
		await vi.runAllTimersAsync();
		expect(classes.has('auren-resuming')).toBe(false);
		expect(splash.remove).not.toHaveBeenCalled(); dispose();
	});
	it('unregisters resume handlers when disposed', () => {
		const dispose = installAurenResumeGuard(() => true); dispose();
		win.dispatchEvent(new Event('auren-resume')); expect(classes.has('auren-resuming')).toBe(false);
	});
});
