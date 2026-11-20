import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface DevModeInfo {
	id: string;
	label: string;
	description: string;
	model: string;
	model_name: string;
	fallbacks: string[];
}

export interface DevModelInfo {
	id: string;
	name: string;
	provider_id: string;
	provider_name: string;
}

export interface DevProviderInfo {
	id: string;
	name: string;
}

export interface DevStatusResponse {
	fcc_online: boolean;
	fcc_url: string;
	claude_installed: boolean;
	active_model: string;
	active_model_name: string;
	active_mode: string | null;
	providers: DevProviderInfo[];
	modes: DevModeInfo[];
	models: DevModelInfo[];
	default_cwd: string;
}

export interface DevDirEntry {
	name: string;
	path: string;
}

export interface DevDirsResponse {
	current: string;
	parent: string;
	directories: DevDirEntry[];
}

export interface DevSessionEntry {
	id: string;
	preview: string;
}

export interface DevGitFile {
	path: string;
	status: string;
	added: number;
	removed: number;
}

export interface DevGitStatusResponse {
	is_git: boolean;
	branch: string;
	files: DevGitFile[];
}

export interface DevFileEntry {
	path: string;
	name: string;
	ext: string;
}

export interface DevFilesResponse {
	cwd: string;
	files: DevFileEntry[];
	total: number;
}

export interface DevFileContentResponse {
	path: string;
	binary: boolean;
	size: number;
	lines: number;
	truncated?: boolean;
	content: string;
}

export interface DevMemoryFile {
	name: string;
	size: number;
	lines: number;
	preview: string;
}

export interface DevCommitInfo {
	hash: string;
	subject: string;
	when: string;
}

export interface DevProjectInfoResponse {
	stack: string[];
	memory_files: DevMemoryFile[];
	recent_commits: DevCommitInfo[];
}

export interface DevSideQuestionResponse {
	ok: boolean;
	model: string;
	model_name: string;
	answer: string;
}

export interface DevHistorySummary {
	id: string;
	title: string;
	cwd: string;
	session_id: string | null;
	model: string | null;
	updated_at: number;
}

export interface DevHistoryRecord extends DevHistorySummary {
	messages: any[];
}

export interface DevStreamHandlers {
	onRun?: (data: { run_id: string; cwd: string }) => void;
	onInit?: (data: { session_id: string | null }) => void;
	onThinking?: (data: { text: string }) => void;
	onText?: (data: { text: string }) => void;
	onToolUse?: (data: {
		name: string;
		label: string;
		icon: string;
		summary: string;
		input?: Record<string, any>;
	}) => void;
	onToolResult?: (data: { text: string; is_error: boolean }) => void;
	onResult?: (data: {
		session_id: string | null;
		text: string;
		is_error: boolean;
		duration_ms: number | null;
	}) => void;
	onError?: (data: { message: string }) => void;
	onDone?: (data: { run_id: string; returncode: number }) => void;
}

function authHeaders(token: string): Record<string, string> {
	return {
		Accept: 'application/json',
		'Content-Type': 'application/json',
		...(token ? { Authorization: `Bearer ${token}` } : {})
	};
}

export async function getDevStatus(
	token: string,
	ensureDefault = false
): Promise<DevStatusResponse> {
	const qs = ensureDefault ? '?ensure_default=true' : '';
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/status${qs}`, {
		method: 'GET',
		headers: authHeaders(token)
	});
	if (!res.ok) {
		throw new Error((await res.json().catch(() => ({}))).detail || 'Falha ao consultar Minerva Dev.');
	}
	return res.json();
}

export async function setDevMode(
	token: string,
	payload: { mode?: string; model?: string }
): Promise<{
	ok: boolean;
	mode: string | null;
	model: string;
	model_name: string;
	message: string;
}> {
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/mode`, {
		method: 'POST',
		headers: authHeaders(token),
		body: JSON.stringify(payload)
	});
	const body = await res.json().catch(() => ({}));
	if (!res.ok) {
		throw new Error(body.detail || 'Erro ao alterar modo/modelo.');
	}
	return body;
}

export async function listDevDirs(token: string, path?: string): Promise<DevDirsResponse> {
	const qs = path ? `?path=${encodeURIComponent(path)}` : '';
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/dirs${qs}`, {
		method: 'GET',
		headers: authHeaders(token)
	});
	if (!res.ok) {
		throw new Error('Falha ao listar pastas.');
	}
	return res.json();
}

export async function listDevSessions(
	token: string,
	cwd?: string
): Promise<{ cwd: string; sessions: DevSessionEntry[] }> {
	const qs = cwd ? `?cwd=${encodeURIComponent(cwd)}` : '';
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/sessions${qs}`, {
		method: 'GET',
		headers: authHeaders(token)
	});
	if (!res.ok) {
		throw new Error('Falha ao listar sessões.');
	}
	return res.json();
}

export async function stopDevRun(token: string, runId: string): Promise<void> {
	await fetch(`${WEBUI_API_BASE_URL}/dev/stop`, {
		method: 'POST',
		headers: authHeaders(token),
		body: JSON.stringify({ run_id: runId })
	});
}

export async function getDevGitStatus(token: string, cwd?: string): Promise<DevGitStatusResponse> {
	const qs = cwd ? `?cwd=${encodeURIComponent(cwd)}` : '';
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/git${qs}`, {
		method: 'GET',
		headers: authHeaders(token)
	});
	if (!res.ok) {
		return { is_git: false, branch: '', files: [] };
	}
	return res.json();
}

export async function getDevFileDiff(
	token: string,
	cwd: string,
	file: string
): Promise<{ file: string; diff: string }> {
	const qs = `?cwd=${encodeURIComponent(cwd)}&file=${encodeURIComponent(file)}`;
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/git/diff${qs}`, {
		method: 'GET',
		headers: authHeaders(token)
	});
	if (!res.ok) {
		throw new Error('Falha ao carregar diff.');
	}
	return res.json();
}

export async function listDevFiles(
	token: string,
	cwd: string,
	q = '',
	limit = 120
): Promise<DevFilesResponse> {
	const params = new URLSearchParams({ cwd, limit: String(limit) });
	if (q) params.set('q', q);
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/files?${params.toString()}`, {
		method: 'GET',
		headers: authHeaders(token)
	});
	if (!res.ok) {
		return { cwd, files: [], total: 0 };
	}
	return res.json();
}

export async function readDevFile(
	token: string,
	cwd: string,
	path: string
): Promise<DevFileContentResponse> {
	const params = new URLSearchParams({ cwd, path });
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/file?${params.toString()}`, {
		method: 'GET',
		headers: authHeaders(token)
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		throw new Error(err.detail || 'Não foi possível ler o arquivo.');
	}
	return res.json();
}

export async function getDevProjectInfo(
	token: string,
	cwd: string
): Promise<DevProjectInfoResponse> {
	const params = new URLSearchParams({ cwd });
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/project-info?${params.toString()}`, {
		method: 'GET',
		headers: authHeaders(token)
	});
	if (!res.ok) {
		return { stack: [], memory_files: [], recent_commits: [] };
	}
	return res.json();
}

export async function askDevSideQuestion(
	token: string,
	payload: { question: string; model?: string | null }
): Promise<DevSideQuestionResponse> {
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/side-question`, {
		method: 'POST',
		headers: authHeaders(token),
		body: JSON.stringify(payload)
	});
	const body = await res.json().catch(() => ({}));
	if (!res.ok) {
		throw new Error(body.detail || 'Falha na pergunta paralela.');
	}
	return body;
}

const TRAILING_STOPWORDS = new Set([
	'a',
	'as',
	'o',
	'os',
	'um',
	'uma',
	'uns',
	'umas',
	'de',
	'do',
	'da',
	'dos',
	'das',
	'em',
	'no',
	'na',
	'nos',
	'nas',
	'por',
	'para',
	'pra',
	'com',
	'sem',
	'sob',
	'sobre',
	'que',
	'se',
	'e',
	'ou',
	'mas',
	'ao',
	'aos',
	'à',
	'às',
	'meu',
	'minha',
	'meus',
	'minhas',
	'seu',
	'sua'
]);

/**
 * Gera instantaneamente um título preliminar conciso e com sentido (sem cortar palavras
 * no meio e sem copiar muletas conversacionais do início da frase) enquanto o resumo
 * dinâmico por IA é processado em segundo plano.
 */
export function synthesizeDevTitle(rawPrompt: string): string {
	let text = (rawPrompt || '')
		.replace(/^Arquivos em foco:[^\n]*\n+/i, '')
		.replace(/```[\s\S]*?```/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();
	if (!text) return 'Nova Sessão Dev';

	// Pega a primeira sentença relevante
	const firstSentence = text.split(/(?<=[.!?])\s+|\n+/)[0]?.trim() || text;

	// Remove prefixos conversacionais comuns para focar direto na ação/tema
	let cleaned = firstSentence
		.replace(
			/^(?:ol[aá]|oi|bom dia|boa tarde|boa noite|por favor|pfv|minerva)[,!\s-]*/i,
			''
		)
		.replace(
			/^(?:em (?:meu|minha) [a-zà-ú0-9_-]+\s*,?\s*)?(?:eu\s+)?(?:queria|quero|gostaria|preciso|consegue|pode|poderia|fa[çc]a com que|fa[çc]a|pe[çc]a ao mestre)\s+(?:que\s+)?(?:voc[êe]\s+)?/i,
			''
		)
		.replace(
			/^(?:no|na|em)\s+(?:meu|minha)\s+/i,
			''
		)
		.trim();

	if (!cleaned) cleaned = firstSentence;

	// Divide em palavras completas (nunca corta palavra ao meio)
	const words = cleaned
		.replace(/^[,;:.!?-]+|[,;:.!?-]+$/g, '')
		.split(/\s+/)
		.filter(Boolean);

	if (words.length === 0) return 'Nova Sessão Dev';

	const selected = words.slice(0, 6);
	while (
		selected.length > 2 &&
		TRAILING_STOPWORDS.has(
			selected[selected.length - 1].toLowerCase().replace(/[,;:.!?-]+$/g, '')
		)
	) {
		selected.pop();
	}

	const joined = selected
		.join(' ')
		.replace(/[,;:.!?-]+$/g, '')
		.trim();
	if (!joined) return 'Nova Sessão Dev';
	return joined.charAt(0).toUpperCase() + joined.slice(1);
}

/**
 * Solicita ao modelo ativo da Minerva Dev um título dinâmico de 2 a 5 palavras em pt-BR
 * que resuma o objetivo da primeira mensagem com sentido completo.
 */
export async function generateDevTitle(
	token: string,
	payload: { prompt: string; model?: string | null }
): Promise<string | null> {
	const cleanPrompt = (payload.prompt || '')
		.replace(/^Arquivos em foco:[^\n]*\n+/i, '')
		.replace(/\s+/g, ' ')
		.trim()
		.slice(0, 700);
	if (!cleanPrompt) return null;

	const question =
		'Gere APENAS um título dinâmico, curto e com sentido completo (de 2 a 5 palavras, em Português do Brasil) ' +
		'que resuma o objetivo principal desta solicitação. NÃO copie as primeiras palavras literalmente, ' +
		'NÃO corte palavras no meio, NÃO use aspas nem ponto final. ' +
		'Exemplos: Arquivo Python do Mundo 2, Títulos em Português no Chat, Abertura do VSCodium, Revisão de Código do Projeto.\n\n' +
		`Solicitação: ${cleanPrompt}`;

	try {
		const res = await askDevSideQuestion(token, {
			question,
			model: payload.model || null
		});
		const rawLine = (res?.answer || '')
			.split(/\r?\n/)
			.map((l) => l.trim())
			.find((l) => l.length >= 3);
		if (!rawLine) return null;
		const cleaned = rawLine
			.replace(/^(?:t[íi]tulo\s*:\s*)/i, '')
			.replace(/^["'‘’“”`*#-]+|["'‘’“”`*.!?;:,-]+$/g, '')
			.replace(/\s+/g, ' ')
			.trim();
		if (cleaned.length < 3 || cleaned.length > 75) return null;
		return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
	} catch {
		return null;
	}
}

export async function listDevHistory(token: string): Promise<DevHistorySummary[]> {
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/history`, {
		method: 'GET',
		headers: authHeaders(token)
	});
	if (!res.ok) return [];
	const data = await res.json().catch(() => ({}));
	return Array.isArray(data.items) ? data.items : [];
}

export async function getDevHistoryItem(token: string, id: string): Promise<DevHistoryRecord> {
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/history/${encodeURIComponent(id)}`, {
		method: 'GET',
		headers: authHeaders(token)
	});
	if (!res.ok) throw new Error('Conversa Dev não encontrada.');
	return res.json();
}

export async function saveDevHistoryItem(
	token: string,
	payload: {
		id?: string | null;
		title: string;
		cwd: string;
		session_id?: string | null;
		model?: string | null;
		messages: any[];
	}
): Promise<DevHistorySummary> {
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/history`, {
		method: 'POST',
		headers: authHeaders(token),
		body: JSON.stringify(payload)
	});
	if (!res.ok) throw new Error('Falha ao salvar conversa Dev.');
	return res.json();
}

export async function deleteDevHistoryItem(token: string, id: string): Promise<void> {
	await fetch(`${WEBUI_API_BASE_URL}/dev/history/${encodeURIComponent(id)}`, {
		method: 'DELETE',
		headers: authHeaders(token)
	});
}

export async function streamDevChat(
	token: string,
	payload: {
		prompt: string;
		cwd: string;
		session_id?: string | null;
		permission_mode?: string;
		model?: string | null;
		effort?: string | null;
		extra_dirs?: string[];
		run_id?: string;
	},
	handlers: DevStreamHandlers,
	signal?: AbortSignal
): Promise<void> {
	const res = await fetch(`${WEBUI_API_BASE_URL}/dev/chat`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token ? { Authorization: `Bearer ${token}` } : {})
		},
		body: JSON.stringify(payload),
		signal
	});

	if (!res.ok || !res.body) {
		const err = await res.json().catch(() => ({}));
		throw new Error(err.detail || `Erro HTTP ${res.status}`);
	}

	const reader = res.body.getReader();
	const decoder = new TextDecoder();
	let buffer = '';

	while (true) {
		const { done, value } = await reader.read();
		if (done) break;
		buffer += decoder.decode(value, { stream: true });

		let sepIdx: number;
		while ((sepIdx = buffer.indexOf('\n\n')) !== -1) {
			const block = buffer.slice(0, sepIdx);
			buffer = buffer.slice(sepIdx + 2);
			let evType = 'message';
			let evData = '';
			for (const line of block.split('\n')) {
				if (line.startsWith('event:')) {
					evType = line.slice(6).trim();
				} else if (line.startsWith('data:')) {
					evData += line.slice(5).trim();
				}
			}
			if (!evData) continue;
			try {
				const parsed = JSON.parse(evData);
				if (evType === 'run') handlers.onRun?.(parsed);
				else if (evType === 'init') handlers.onInit?.(parsed);
				else if (evType === 'thinking') handlers.onThinking?.(parsed);
				else if (evType === 'text') handlers.onText?.(parsed);
				else if (evType === 'tool_use') handlers.onToolUse?.(parsed);
				else if (evType === 'tool_result') handlers.onToolResult?.(parsed);
				else if (evType === 'result') handlers.onResult?.(parsed);
				else if (evType === 'error') handlers.onError?.(parsed);
				else if (evType === 'done') handlers.onDone?.(parsed);
			} catch {
				// ignora chunk malformado
			}
		}
	}
}
