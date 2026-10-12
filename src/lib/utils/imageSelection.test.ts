import { describe, it, expect } from 'vitest';
import {
	canGenerateImage,
	defaultImageModel,
	compareProviders,
	type ImageModel
} from './imageSelection';
const model = (
	id: string,
	price_kind = 'free',
	available = true,
	image_generation = true
): ImageModel => ({ id, cavren: { price_kind, available, capabilities: { image_generation } } });
describe('image route selection', () => {
	it('never routes automatic chat as an image generator', () =>
		expect(canGenerateImage(model('cavren:auto'))).toBe(false));
	it('keeps an explicitly selected capable model', () =>
		expect(defaultImageModel([model('paid', 'paid')], '', 'paid')?.id).toBe('paid'));
	it('uses the available free preference', () =>
		expect(
			defaultImageModel([model('a'), model('preferred')], 'preferred', 'cavren:auto')?.id
		).toBe('preferred'));
	it('does not automatically select a paid preference', () =>
		expect(
			defaultImageModel([model('paid', 'paid'), model('free')], 'paid', 'cavren:auto')?.id
		).toBe('free'));
	it('excludes unavailable and conversation-only routes', () =>
		expect(
			defaultImageModel(
				[model('offline', 'free', false), model('chat', 'free', true, false)],
				'offline',
				'chat'
			)
		).toBeUndefined());
	it('prefers the standard Horde route when no preference works', () =>
		expect(
			defaultImageModel(
				[model('a'), model('cavren:aihorde:stable_diffusion')],
				'missing',
				'cavren:auto'
			)?.id
		).toBe('cavren:aihorde:stable_diffusion'));
	it('does not select a paid route without explicit selection', () =>
		expect(defaultImageModel([model('paid', 'paid')], 'paid', 'cavren:auto')).toBeUndefined());
	it('orders displayed provider names alphabetically in Portuguese', () =>
		expect(
			['OpenRouter', 'Z.ai', 'Anthropic', 'AI Horde', 'Google Gemini', 'Cloudflare'].sort(
				compareProviders
			)
		).toEqual(['AI Horde', 'Anthropic', 'Cloudflare', 'Google Gemini', 'OpenRouter', 'Z.ai']));
});
