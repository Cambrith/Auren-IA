import { describe, expect, it } from 'vitest';
import { moveConnection, orderConnections } from './aurenConnections';
const items = [
	{ id: 'zai', name: 'Z.ai API', credential: 'synthetic-z' },
	{ id: 'canva', name: 'Canva Connect', credential: 'synthetic-c' },
	{ id: 'aihorde', name: 'AI Horde', credential: 'synthetic-a' }
];
describe('connection ordering', () => {
	it('starts alphabetical without changing input', () => {
		expect(orderConnections(items).map((c) => c.id)).toEqual(['aihorde', 'canva', 'zai']);
		expect(items[0].id).toBe('zai');
	});
	it('keeps stable IDs, values and object identities after a vertical move', () => {
		const initial = orderConnections(items);
		const moved = moveConnection(initial, 2, 0);
		expect(moved.map((c) => c.id)).toEqual(['zai', 'aihorde', 'canva']);
		expect(moved[0]).toBe(items[0]);
		expect(moved[0].credential).toBe('synthetic-z');
		expect(
			orderConnections(
				items,
				moved.map((c) => c.id)
			)
		).toEqual(moved);
	});
	it('restores after serialization and appends newly added cards alphabetically', () => {
		const saved = JSON.parse(JSON.stringify(['zai', 'aihorde']));
		expect(orderConnections(items, saved).map((c) => c.id)).toEqual(['zai', 'aihorde', 'canva']);
	});
	it('ignores removed or duplicated saved IDs', () =>
		expect(orderConnections(items, ['removed', 'canva', 'canva']).map((c) => c.id)).toEqual([
			'canva',
			'aihorde',
			'zai'
		]));
	it('does not wrap cards at either end', () => {
		expect(moveConnection(items, 0, -1)).toBe(items);
		expect(moveConnection(items, 2, 3)).toBe(items);
		expect(moveConnection(items, 0, 0)).toBe(items);
	});
});
