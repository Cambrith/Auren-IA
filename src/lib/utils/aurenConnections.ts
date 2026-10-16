import { compareProviders } from './imageSelection';

/** Stable provider IDs keep fields, checks and credentials attached across moves. */
export function orderConnections<T extends { id: string; name: string }>(
	items: T[],
	saved: string[] = []
): T[] {
	const byId = new Map(items.map((item) => [item.id, item]));
	const result: T[] = [];
	for (const id of saved) {
		const item = byId.get(id);
		if (item) {
			result.push(item);
			byId.delete(id);
		}
	}
	return [...result, ...[...byId.values()].sort((a, b) => compareProviders(a.name, b.name))];
}

export function moveConnection<T>(items: T[], from: number, to: number): T[] {
	if (from < 0 || to < 0 || from >= items.length || to >= items.length || from === to) return items;
	const next = [...items];
	const [item] = next.splice(from, 1);
	next.splice(to, 0, item);
	return next;
}
