import { writable } from 'svelte/store';
import { listDevHistory, type DevHistorySummary } from '$lib/apis/dev';

export const devHistoryItems = writable<DevHistorySummary[]>([]);
export const devActiveHistoryId = writable<string | null>(null);
export const devNewSessionTrigger = writable<number>(0);

export async function reloadDevHistory(token: string): Promise<void> {
	const items = await listDevHistory(token).catch(() => []);
	devHistoryItems.set(items);
}
