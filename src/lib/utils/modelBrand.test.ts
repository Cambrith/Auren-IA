import { describe, it, expect } from 'vitest';
import { modelBrand } from './modelBrand';
describe('model brand, separate from hosting provider', () => {
	it.each([
		['openrouter', 'cavren:openrouter:anthropic/claude-sonnet', 'claude'],
		['openrouter', 'cavren:openrouter:openai/gpt-4o', 'openai'],
		['cloudflare', 'cavren:cloudflare:@cf/deepseek-ai/deepseek-r1', 'deepseek'],
		['groq', 'cavren:groq:qwen/qwen3-32b', 'qwen'],
		['nvidia', 'cavren:nvidia:meta/llama-3.2', 'meta'],
		['gemini', 'cavren:gemini:gemini-flash', 'gemini'],
		['aihorde', 'cavren:aihorde:stable_diffusion', 'stability'],
		['aihorde', 'cavren:aihorde:unknown-community-model', 'aihorde']
	])('maps %s / %s', (provider, id, brand) => expect(modelBrand(provider, id)).toBe(brand));
	it('uses the provider mark on a connection card', () =>
		expect(modelBrand('anthropic')).toBe('anthropic'));
});
