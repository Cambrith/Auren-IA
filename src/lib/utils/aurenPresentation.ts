/** Technical route data stays in history; normal responses show only useful progress. */
export function imageProgress(status: any, elapsedSeconds = 0) {
	const duration = (seconds: number) => {
		const whole = Math.floor(seconds);
		return whole < 60 ? `${whole} s` : `${Math.floor(whole / 60)} min ${String(whole % 60).padStart(2, '0')} s`;
	};
	const valid = (value: any) => typeof value === 'number' && Number.isFinite(value) && value >= 0;
	const parts = [`Tempo decorrido: ${duration(valid(elapsedSeconds) ? elapsedSeconds : 0)}`];
	if (valid(status.queue_position)) parts.push(`Posição na fila: ${status.queue_position}`);
	if (valid(status.wait_time)) parts.push(`Estimativa do provedor: ${duration(status.wait_time)}`);
	if (valid(status.eligible_workers) && status.eligible_workers === 0) parts.push('Nenhum trabalhador elegível no momento');
	return parts.join(' · ');
}

export function aurenStatuses(statuses: any[], showDetails: boolean, done = false, elapsedSeconds = 0) {
	if (showDetails) return statuses.map((s) => s.action === 'auren_details' ? { ...s, hidden: false } : s);
	return statuses.filter((s) => !['task', 'fallback', 'auren_details'].includes(s.action) && !(done && s.action === 'image_generation')).map((s) => {
		if (s.action !== 'image_generation') return s;
		return { ...s, description: s.done ? 'Imagem pronta.' : imageProgress(s, elapsedSeconds) };
	});
}
export function aurenFiles(files: any[], isAuren: boolean, done: boolean | undefined) {
	return files.filter((f) => !(isAuren && done === false && (f.type === 'image' || f.content_type?.startsWith('image/'))));
}

/** One live indicator owns the current step; the stored history remains intact. */
export function aurenActivity(statuses: any[], hasContent = false, elapsedSeconds = 0): {
	phase: 'waiting' | 'searching' | 'organizing' | 'streaming' | 'image';
	description: string;
	status: any;
} {
	if (hasContent) return { phase: 'streaming', description: '', status: null };
	const status = statuses.filter((entry) => !entry.hidden).at(-1);
	if (!status) return { phase: 'waiting', description: '', status: null };
	if (status.action === 'image_generation') {
		return {
			phase: 'image', status: null,
			description: status.done ? 'Finalizando a imagem…' :
				`${status.state === 'queued' ? 'Aguardando a geração…' : 'Gerando a imagem…'} · ${imageProgress(status, elapsedSeconds)}`
		};
	}
	const search = ['web_search', 'web_search_queries_generated', 'knowledge_search', 'queries_generated', 'sources_retrieved'].includes(status.action);
	return {
		phase: search ? (status.done ? 'organizing' : 'searching') : 'waiting',
		description: '',
		status: status.action === 'web_search' && status.done
			? { ...status, description: `${status.description || 'Pesquisa concluída'} · Organizando as informações…` }
			: status
	};
}
