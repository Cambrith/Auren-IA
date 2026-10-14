import { describe, expect, it } from 'vitest';
import { routesAurenAttachments, hasNativeAurenAttachments } from './aurenAttachments';

describe('Auren attachment admission', () => {
	it('allows Auren to route attachments even on a selected text-only model', () => {
		expect(routesAurenAttachments(['cavren:groq:openai/gpt-oss-120b'])).toBe(true);
		expect(routesAurenAttachments(['cavren:auto'])).toBe(true);
		expect(routesAurenAttachments(['cavren:auto', 'upstream-model'])).toBe(false);
		expect(routesAurenAttachments([])).toBe(false);
	});
	it('defers native media cost decisions to the bridge while ordinary text keeps its gate', () => {
		for (const file of [{ type: 'image' }, { name: 'scan.PDF' }, { content_type: 'audio/mpeg' }, { file: { meta: { content_type: 'video/mp4' } } }]) {
			expect(hasNativeAurenAttachments([file])).toBe(true);
		}
		expect(hasNativeAurenAttachments([{ name: 'notes.txt', content_type: 'text/plain' }])).toBe(false);
	});
});
