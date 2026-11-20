// Lógica pura da Central de IA: classificação de testes, preços, agrupamento e filtros.

export type ResultKind =
	| 'ok'
	| 'sem_saldo'
	| 'plano_pago'
	| 'limite'
	| 'termos'
	| 'chave'
	| 'indisponivel'
	| 'nao_chat'
	| 'ocupado'
	| 'reprovado'
	| 'outra_funcao'
	| 'erro';

export type TestResult = { kind: ResultKind; label: string; detail: string; at: number };

export type ModelLike = {
	id: string;
	name?: string;
	urlIdx?: number;
	pricing?: { prompt?: string | number; completion?: string | number };
};

export type PriceKind = 'gratis' | 'pago' | 'desconhecido';

export const RESULT_LABEL: Record<ResultKind, string> = {
	ok: 'Liberado',
	sem_saldo: 'Exige crédito pago',
	plano_pago: 'Exige plano pago',
	limite: 'Limite atingido',
	termos: 'Aceitar termos',
	chave: 'Chave recusada',
	indisponivel: 'Indisponível na conta',
	nao_chat: 'Não é de chat',
	ocupado: 'Sobrecarregado agora',
	reprovado: 'Reprovado no teste',
	outra_funcao: 'Outra função',
	erro: 'Erro'
};

/** Estados em que o modelo é de fato pago (não é falha nem limite passageiro). */
export const isPaidKind = (kind?: ResultKind): boolean => kind === 'sem_saldo' || kind === 'plano_pago';

/** Traduz a resposta HTTP de uma chamada de teste em um estado simples. */
export const classifyResult = (status: number, message = '', now = Date.now()): TestResult => {
	const text = (message ?? '').toString();
	const detail = text.slice(0, 200);
	const make = (kind: ResultKind): TestResult => ({ kind, label: RESULT_LABEL[kind], detail, at: now });
	if (status >= 200 && status < 300) return make('ok');
	if (status === 402) return make('sem_saldo');
	if (/terms acceptance|must submit the prompt 'agree'|model agreement/i.test(text)) return make('termos');
	if (/not available on the workers free plan|upgrade to access/i.test(text)) return make('plano_pago');
	if (status === 503 || /high demand|timed out/i.test(text)) return make('ocupado');
	if (status === 429) return make(/limit:\s*0\b/i.test(text) ? 'plano_pago' : 'limite');
	if (status === 401 || status === 403) {
		return make(/not allowed to access|not found for account/i.test(text) ? 'indisponivel' : 'chave');
	}
	if (/does not have config/i.test(text)) return make('indisponivel');
	if (/interactions api|only supports|required properties|not a chat model|text-to-speech/i.test(text)) {
		return make('nao_chat');
	}
	if (
		status === 404 ||
		status === 410 ||
		/no longer available|not found for account|page not found/i.test(text)
	) {
		return make('indisponivel');
	}
	return make('erro');
};

const toNumber = (value: unknown): number | null => {
	if (value === undefined || value === null || value === '') return null;
	const n = Number(value);
	return Number.isFinite(n) ? n : null;
};

/** Gratuito só quando o provedor informa preço zero para entrada e saída. */
export const priceKind = (model: ModelLike): PriceKind => {
	const prompt = toNumber(model.pricing?.prompt);
	const completion = toNumber(model.pricing?.completion);
	if (prompt === null || completion === null) return 'desconhecido';
	return prompt === 0 && completion === 0 ? 'gratis' : 'pago';
};

export const PRICE_LABEL: Record<PriceKind, string> = {
	gratis: 'Grátis',
	pago: 'Pago',
	desconhecido: 'Preço n/d'
};

export const PROVIDER_NAMES: Record<string, string> = {
	'api.openai.com': 'OpenAI',
	'generativelanguage.googleapis.com': 'Google Gemini',
	'api.groq.com': 'Groq',
	'openrouter.ai': 'OpenRouter',
	'api.cerebras.ai': 'Cerebras',
	'integrate.api.nvidia.com': 'NVIDIA NIM',
	'api.cohere.ai': 'Cohere',
	'router.huggingface.co': 'Hugging Face',
	'api.cloudflare.com': 'Cloudflare Workers AI',
	'api.anthropic.com': 'Anthropic',
	'api.deepseek.com': 'DeepSeek',
	'api.mistral.ai': 'Mistral',
	'api.x.ai': 'xAI',
	'api.fireworks.ai': 'Fireworks AI',
	'api.deepinfra.com': 'DeepInfra'
};

export const providerName = (url: string, prefix?: string): string => {
	try {
		const host = new URL(url).hostname;
		if (PROVIDER_NAMES[host]) return PROVIDER_NAMES[host];
		return prefix || host;
	} catch {
		return prefix || url;
	}
};

export const isOpenRouter = (url: string): boolean => {
	try {
		return new URL(url).hostname === 'openrouter.ai';
	} catch {
		return false;
	}
};

/** Remove o prefixo de conexão ("openrouter.") do ID mostrado na interface. */
export const rawModelId = (id: string, prefix?: string): string =>
	prefix && id.startsWith(prefix + '.') ? id.slice(prefix.length + 1) : id;

/** Nome legível: tira o prefixo técnico que o Open WebUI coloca no nome. */
export const cleanName = (model: ModelLike, prefix?: string): string => {
	const name = model.name || model.id;
	return prefix && name.startsWith(prefix + '.') ? name.slice(prefix.length + 1) : name;
};

export type Filter = 'todos' | 'funcionam' | 'outra_funcao' | 'exige_pago' | 'falham' | 'sem_teste' | 'gratis' | 'pagos';

export const FILTER_LABEL: Record<Filter, string> = {
	todos: 'Todos',
	funcionam: 'Liberados',
	outra_funcao: 'Outra função',
	exige_pago: 'Exigem pagamento',
	falham: 'Outras falhas',
	sem_teste: 'Sem teste',
	gratis: 'Grátis',
	pagos: 'Pagos'
};

export const filterModels = <T extends ModelLike>(
	models: T[],
	opts: { query?: string; filter?: Filter; results?: Record<string, TestResult>; prefix?: string }
): T[] => {
	const q = (opts.query ?? '').trim().toLowerCase();
	const results = opts.results ?? {};
	return models.filter((m) => {
		if (q && !`${cleanName(m, opts.prefix)} ${m.id}`.toLowerCase().includes(q)) return false;
		const r = results[m.id];
		switch (opts.filter ?? 'todos') {
			case 'funcionam':
				return r?.kind === 'ok';
			case 'outra_funcao':
				return r?.kind === 'outra_funcao';
			case 'exige_pago':
				return isPaidKind(r?.kind);
			case 'falham':
				return !!r && r.kind !== 'ok' && r.kind !== 'outra_funcao' && !isPaidKind(r.kind);
			case 'sem_teste':
				return !r;
			case 'gratis':
				return priceKind(m) === 'gratis';
			case 'pagos':
				return priceKind(m) === 'pago';
			default:
				return true;
		}
	});
};

export const summarize = (models: ModelLike[], results: Record<string, TestResult>) => {
	const out = { total: models.length, ok: 0, falha: 0, semTeste: 0, gratis: 0, pagos: 0, exigePago: 0, outra: 0 };
	for (const m of models) {
		const r = results[m.id];
		if (!r) out.semTeste++;
		else if (r.kind === 'ok') out.ok++;
		else if (r.kind === 'outra_funcao') out.outra++;
		else if (isPaidKind(r.kind)) out.exigePago++;
		else out.falha++;
		const p = priceKind(m);
		if (p === 'gratis') out.gratis++;
		else if (p === 'pago') out.pagos++;
	}
	return out;
};

const NOT_CHAT = /(embed|rerank|transcribe|\bparse\b|moderation|whisper|\btts\b|guard|orpheus|imagen|veo|lyria|-image\b)/i;

/** Embeddings, rerank e áudio não respondem a conversa; testá-los como chat só geraria erro. */
export const isChatModel = (m: ModelLike): boolean => !NOT_CHAT.test(m.id);

/** Modelos que vale testar sem risco de cobrança: de chat, gratuitos ou de preço desconhecido. */
export const safeToTest = <T extends ModelLike>(models: T[]): T[] =>
	models.filter((m) => isChatModel(m) && priceKind(m) !== 'pago');

export const workingRawIds = (
	models: ModelLike[],
	results: Record<string, TestResult>,
	prefix?: string
): string[] => models.filter((m) => results[m.id]?.kind === 'ok').map((m) => rawModelId(m.id, prefix));

/** IDs (sem prefixo) que podem ficar ativos na conexão: aprovados e os de outra função (guardados para depois). */
export const allowedRawIds = (
	models: ModelLike[],
	results: Record<string, TestResult>,
	prefix?: string
): string[] =>
	models
		.filter((m) => results[m.id]?.kind === 'ok' || results[m.id]?.kind === 'outra_funcao')
		.map((m) => rawModelId(m.id, prefix));

/** Modelos de outra função: ficam fora do seletor de conversa até ganharem uma tela própria. */
export const parkedModels = <T extends ModelLike>(models: T[], results: Record<string, TestResult>): T[] =>
	models.filter((m) => results[m.id]?.kind === 'outra_funcao');

const BLOCKED_IN_SELECTOR_KINDS = new Set<ResultKind>([
	'indisponivel',
	'reprovado',
	'nao_chat',
	'outra_funcao',
	'sem_saldo',
	'plano_pago',
	'chave',
	'ocupado',
	'erro'
]);

/** Indica se o modelo deve ser ocultado no seletor de conversa com base na triagem mais recente. */
export const isBlockedInSelector = (
	modelId: string,
	results: Record<string, TestResult> | null | undefined
): boolean => {
	const kind = results?.[modelId]?.kind;
	return Boolean(kind && BLOCKED_IN_SELECTOR_KINDS.has(kind));
};

/** Intervalo entre testes: OpenRouter limita modelos gratuitos a 20 por minuto. */
export const testDelayMs = (openrouter: boolean, free: boolean): number =>
	openrouter ? (free ? 4000 : 400) : 1200;

export const RESULTS_KEY = 'minerva.central-ia.v1';

export const loadResults = (storage: Pick<Storage, 'getItem'> | undefined): Record<string, TestResult> => {
	try {
		const parsed = JSON.parse(storage?.getItem(RESULTS_KEY) ?? '{}');
		return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
	} catch {
		return {};
	}
};

export const saveResults = (
	storage: Pick<Storage, 'setItem'> | undefined,
	results: Record<string, TestResult>
) => {
	try {
		storage?.setItem(RESULTS_KEY, JSON.stringify(results));
	} catch {
		// Navegador sem armazenamento: a página continua funcionando sem lembrar os testes.
	}
};

export type Baseline = {
	testedAt: number;
	results: Record<string, { status: number; msg: string; kind?: string }>;
};

/** Resultados de testes feitos fora da página (arquivo estático), convertidos para o mesmo formato. */
export const fromBaseline = (b: Baseline | null | undefined): Record<string, TestResult> => {
	const out: Record<string, TestResult> = {};
	if (!b || typeof b !== 'object' || !b.results) return out;
	for (const [id, r] of Object.entries(b.results)) {
		if (!r || typeof r.status !== 'number') continue;
		const result = classifyResult(r.status, r.msg ?? '', b.testedAt);
		// Veredito da triagem rigorosa: tem prioridade sobre a leitura do status HTTP.
		if (r.kind && r.kind in RESULT_LABEL) {
			result.kind = r.kind as ResultKind;
			result.label = RESULT_LABEL[result.kind];
		}
		out[id] = result;
	}
	return out;
};

let baselineCache: { url: string; promise: Promise<Record<string, TestResult>> } | null = null;

/** Carrega a linha de base estática (com cache em memória) e mescla com os testes salvos no navegador. */
export const loadEffectiveResults = async (
	baseUrl: string,
	storage: Pick<Storage, 'getItem'> | undefined,
	fetchFn: typeof fetch = fetch
): Promise<Record<string, TestResult>> => {
	const url = `${baseUrl}/central-ia-testes.json`;
	if (!baselineCache || baselineCache.url !== url) {
		baselineCache = {
			url,
			promise: fetchFn(url)
				.then(async (res) => (res.ok ? fromBaseline(await res.json()) : {}))
				.catch(() => ({}))
		};
	}
	const baseline = await baselineCache.promise;
	return { ...baseline, ...loadResults(storage) };
};
