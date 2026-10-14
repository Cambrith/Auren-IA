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
