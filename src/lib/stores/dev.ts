import { get, writable } from 'svelte/store';
import {
	generateDevTitle,
	listDevHistory,
	saveDevHistoryItem,
	synthesizeDevTitle,
	type DevHistorySummary
} from '$lib/apis/dev';
import type {
	DevMessage,
	EffortLevel,
	PermissionMode
} from '$lib/components/dev/types';

export interface DevLiveSession {
	convId: string;
	title: string;
	cwd: string;
	extraDirs: string[];
	sessionId: string | null;
	permissionMode: PermissionMode;
	effort: EffortLevel;
	model: string;
	modelName: string;
	messages: DevMessage[];
	isStreaming: boolean;
	activeRunId: string | null;
	abortController: AbortController | null;
	queuedPrompt: string | null;
	turnStartedAt: number;
	updatedAt: number;
}

export const devHistoryItems = writable<DevHistorySummary[]>([]);
export const devActiveHistoryId = writable<string | null>(null);
export const devNewSessionTrigger = writable<number>(0);
export const devLiveSessions = writable<Record<string, DevLiveSession>>({});

export async function reloadDevHistory(token: string): Promise<void> {
	const items = await listDevHistory(token).catch(() => []);
	// Garante que sessões recém-criadas em memória já apareçam no topo mesmo durante o salvamento inicial
	const liveMap = get(devLiveSessions);
	const mergedMap = new Map<string, DevHistorySummary>();
	for (const it of items) {
		mergedMap.set(it.id, it);
	}
	for (const s of Object.values(liveMap)) {
		const persistable = s.messages.filter((m) => m.role !== 'system_card');
		if (persistable.length === 0) continue;
		const existing = mergedMap.get(s.convId);
		mergedMap.set(s.convId, {
			id: s.convId,
			title: s.title || existing?.title || 'Sessão Minerva Dev',
			cwd: s.cwd ?? existing?.cwd ?? '',
			session_id: s.sessionId ?? existing?.session_id ?? null,
			model: s.model || existing?.model || null,
			updated_at: Math.max(s.updatedAt, existing?.updated_at ?? 0)
		});
	}
	const merged = Array.from(mergedMap.values()).sort((a, b) => b.updated_at - a.updated_at);
	devHistoryItems.set(merged);
}

export function updateDevLiveSession(
	convId: string,
	updater: (session: DevLiveSession) => DevLiveSession
): DevLiveSession | null {
	let updated: DevLiveSession | null = null;
	devLiveSessions.update((map) => {
		const current = map[convId];
		if (!current) return map;
		updated = updater(current);
		return { ...map, [convId]: updated };
	});
	return updated;
}

export function removeDevLiveSession(convId: string): void {
	devLiveSessions.update((map) => {
		if (!(convId in map)) return map;
		const next = { ...map };
		delete next[convId];
		return next;
	});
}

export async function persistDevLiveSession(
	token: string,
	convId: string,
	refreshList = true
): Promise<void> {
	const session = get(devLiveSessions)[convId];
	if (!session) return;
	const persistable = session.messages.filter((m) => m.role !== 'system_card');
	if (persistable.length === 0) return;

	const firstUser =
		persistable.find((m) => m.role === 'user')?.content || 'Sessão Minerva Dev';
	const title =
		session.title ||
		synthesizeDevTitle(firstUser) ||
		'Sessão Minerva Dev';

	const nowSec = Date.now() / 1000;
	// Atualização otimista imediata na barra lateral
	devHistoryItems.update((items) => {
		const summary: DevHistorySummary = {
			id: convId,
			title,
			cwd: session.cwd,
			session_id: session.sessionId,
			model: session.model || null,
			updated_at: nowSec
		};
		const filtered = items.filter((it) => it.id !== convId);
		return [summary, ...filtered];
	});

	try {
		await saveDevHistoryItem(token, {
			id: convId,
			title,
			cwd: session.cwd,
			session_id: session.sessionId,
			model: session.model || null,
			messages: persistable.map((m) => ({
				...m,
				streaming: false,
				phase: m.streaming ? m.phase : ''
			}))
		});
		if (refreshList) {
			await reloadDevHistory(token);
		}
	} catch {
		// silencioso
	}
}

export async function refreshDynamicDevTitle(
	token: string,
	convId: string,
	prompt: string,
	model?: string | null
): Promise<void> {
	const dynamicTitle = await generateDevTitle(token, { prompt, model });
	if (!dynamicTitle) return;
	const updated = updateDevLiveSession(convId, (s) => ({
		...s,
		title: dynamicTitle
	}));
	if (updated) {
		await persistDevLiveSession(token, convId, true);
	}
}
