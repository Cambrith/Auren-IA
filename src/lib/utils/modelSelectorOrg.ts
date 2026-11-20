/** Organização, extração de metadados e ordenação inteligente de modelos no seletor de conversa. */

export type ProviderKey =
	| 'minerva'
	| 'gemini'
	| 'groq'
	| 'cerebras'
	| 'nvidia'
	| 'cohere'
	| 'cloudflare'
	| 'openrouter'
	| 'openai'
	| 'anthropic'
	| 'ollama'
	| 'local'
	| 'other';

export type ProviderInfo = {
	key: ProviderKey;
	badgeProvider: string;
	label: string;
	chipLabel: string;
	rank: number;
};

export type CapabilityBadge =
	| 'Raciocínio'
	| 'Visão'
	| 'Código'
	| 'Rápido'
	| 'Equilíbrio e velocidade'
	| 'Equilíbrio e inteligência'
	| 'Inteligência máxima'
	| 'Velocidade e disponibilidade';

export type ModelDisplayMeta = {
	provider: ProviderInfo;
	cleanTitle: string;
	vendorLabel: string;
	badges: CapabilityBadge[];
};

export type SelectorModelItem = {
	value: string;
	label: string;
	model?: any;
	[key: string]: any;
};

export const MINERVA_MODE_IDS = ['minerva.harmonia', 'minerva.sabia', 'minerva.impeto'] as const;

export const isMinervaModeId = (id = ''): boolean =>
	id === 'minerva.harmonia' ||
	id === 'minerva.sabia' ||
	id === 'minerva.impeto' ||
	id.startsWith('minerva.');

const minervaModeRank = (id = ''): number => {
	const idx = MINERVA_MODE_IDS.indexOf(id as (typeof MINERVA_MODE_IDS)[number]);
	return idx >= 0 ? idx : 99;
};

/**
 * No seletor principal de chat (`!includeHidden`), exibe apenas os modos oficiais da
 * Minerva (`Harmonia`, `Sábia` e `Ímpeto`), ocultando a lista técnica bruta de modelos.
 */
export const filterConversationModeItems = <T extends SelectorModelItem>(
	items: T[],
	includeHidden = false
): T[] => {
	if (includeHidden) return items;
	const modeItems = items.filter((item) => isMinervaModeId(item.value));
	if (modeItems.length === 0) return items;
	return [...modeItems].sort((a, b) => {
		const rankDiff = minervaModeRank(a.value) - minervaModeRank(b.value);
		if (rankDiff !== 0) return rankDiff;
		return a.label.localeCompare(b.label, 'pt-BR', { sensitivity: 'base' });
	});
};

/** Retorna apenas os modelos técnicos individuais (excluindo os modos Harmonia, Sábia e Ímpeto). */
export const filterManualModelItems = <T extends SelectorModelItem>(items: T[]): T[] =>
	items.filter((item) => !isMinervaModeId(item.value));

export const PROVIDER_ORDER: ProviderKey[] = [
	'minerva',
	'gemini',
	'groq',
	'cerebras',
	'nvidia',
	'cohere',
	'cloudflare',
	'openrouter',
	'openai',
	'anthropic',
	'ollama',
	'local',
	'other'
];

const PROVIDER_META: Record<ProviderKey, Omit<ProviderInfo, 'key' | 'rank'>> = {
	minerva: { badgeProvider: 'minerva', label: 'Modo da Minerva', chipLabel: 'Minerva' },
	gemini: { badgeProvider: 'gemini', label: 'Google Gemini', chipLabel: 'Gemini' },
	groq: { badgeProvider: 'groq', label: 'Groq', chipLabel: 'Groq' },
	cerebras: { badgeProvider: 'cerebras', label: 'Cerebras', chipLabel: 'Cerebras' },
	nvidia: { badgeProvider: 'nvidia', label: 'NVIDIA NIM', chipLabel: 'NVIDIA' },
	cohere: { badgeProvider: 'cohere', label: 'Cohere', chipLabel: 'Cohere' },
	cloudflare: { badgeProvider: 'cloudflare', label: 'Cloudflare', chipLabel: 'Cloudflare' },
	openrouter: { badgeProvider: 'openrouter', label: 'OpenRouter', chipLabel: 'OpenRouter' },
	openai: { badgeProvider: 'openai', label: 'OpenAI', chipLabel: 'OpenAI' },
	anthropic: { badgeProvider: 'anthropic', label: 'Anthropic', chipLabel: 'Anthropic' },
	ollama: { badgeProvider: 'ollama', label: 'Ollama', chipLabel: 'Ollama' },
	local: { badgeProvider: 'ollama', label: 'Local', chipLabel: 'Local' },
	other: { badgeProvider: 'openai', label: 'Outros', chipLabel: 'Outros' }
};

const makeProvider = (key: ProviderKey): ProviderInfo => ({
	key,
	...PROVIDER_META[key],
	rank: PROVIDER_ORDER.indexOf(key)
});

const TRAILING_PROVIDER_RE =
	/\s+·\s+(?:Google\s+Gemini|Gemini|Groq|Cerebras|NVIDIA(?:\s+NIM)?|Cohere|Cloudflare|OpenRouter|OpenAI|Anthropic|Hugging\s*Face)\s*$/i;

const LABEL_SUFFIX_PROVIDER_MAP: [RegExp, ProviderKey][] = [
	[/·\s*(?:Google\s+)?Gemini\s*$/i, 'gemini'],
	[/·\s*Groq\s*$/i, 'groq'],
	[/·\s*Cerebras\s*$/i, 'cerebras'],
	[/·\s*NVIDIA(?:\s+NIM)?\s*$/i, 'nvidia'],
	[/·\s*Cohere\s*$/i, 'cohere'],
	[/·\s*Cloudflare\s*$/i, 'cloudflare'],
	[/·\s*OpenRouter\s*$/i, 'openrouter'],
	[/·\s*OpenAI\s*$/i, 'openai'],
	[/·\s*Anthropic\s*$/i, 'anthropic']
];

const VENDOR_MAP: Record<string, string> = {
	google: 'Google',
	meta: 'Meta',
	'meta-llama': 'Meta',
	qwen: 'Qwen',
	'deepseek-ai': 'DeepSeek',
	deepseek: 'DeepSeek',
	mistralai: 'Mistral',
	mistral: 'Mistral',
	openai: 'OpenAI',
	cohere: 'Cohere',
	nvidia: 'NVIDIA',
	'zai-org': 'Z.ai',
	'z-ai': 'Z.ai',
	minimaxai: 'MiniMax',
	'stepfun-ai': 'StepFun',
	baidu: 'Baidu',
	'ibm-granite': 'IBM',
	aisingapore: 'AI Singapore',
	'daily-co': 'Daily',
	'dots-studio': 'Dots',
	inclusionai: 'InclusionAI',
	liquid: 'Liquid',
	openrouter: 'OpenRouter',
	'particle-ai': 'Particle',
	poolside: 'Poolside',
	recursive: 'Recursive',
	anthropic: 'Anthropic',
	thinkingmachines: 'Thinking Machines'
};

/** Identifica o provedor de hospedagem do modelo pela prefixação de ID, sufixo do nome ou origem local. */
export const getProviderInfo = (model: any, id = '', rawLabel = ''): ProviderInfo => {
	if (isMinervaModeId(id) || model?.info?.meta?.minerva_mode) {
		return makeProvider('minerva');
	}
	const prefix = id.includes('.') ? id.slice(0, id.indexOf('.')).toLowerCase() : '';
	if (prefix in PROVIDER_META) {
		return makeProvider(prefix as ProviderKey);
	}
	for (const [pattern, key] of LABEL_SUFFIX_PROVIDER_MAP) {
		if (pattern.test(rawLabel)) return makeProvider(key);
	}
	if (model?.owned_by === 'ollama') return makeProvider('ollama');
	if (model?.connection_type === 'local') return makeProvider('local');
	return makeProvider('other');
};

const stripTechnicalPrefixes = (value: string, providerKey: string): string => {
	let text = value.trim().replace(TRAILING_PROVIDER_RE, '').trim();
	if (providerKey && providerKey !== 'other' && text.toLowerCase().startsWith(`${providerKey}.`)) {
		text = text.slice(providerKey.length + 1);
	}
	for (const lead of ['models/', '@cf/', '@hf/']) {
		if (text.startsWith(lead)) {
			text = text.slice(lead.length);
		}
	}
	return text.replace(/:free$/i, '').replace(/:exacto$/i, '').trim();
};

/** Identifica o fabricante/família do modelo (Google, Meta, Qwen, Cohere, NVIDIA, etc.). */
export const getVendorLabel = (id = '', rawLabel = '', providerKey = 'other'): string => {
	const strippedId = stripTechnicalPrefixes(id || rawLabel, providerKey);
	if (strippedId.includes('/')) {
		const ns = strippedId.slice(0, strippedId.indexOf('/')).toLowerCase();
		if (VENDOR_MAP[ns]) return VENDOR_MAP[ns];
		return ns;
	}
	const target = `${strippedId} ${rawLabel}`.toLowerCase();
	if (/\b(?:gemini|gemma)\b|gemini-|gemma-/.test(target)) return 'Google';
	if (/^command[- ]|^c4ai-|^tiny-aya|^north-/.test(strippedId.toLowerCase())) return 'Cohere';
	if (/\bgpt[- ]|gpt-oss/.test(target)) return 'OpenAI';
	if (/\bqwen|\bqwq\b/.test(target)) return 'Qwen';
	if (/\bllama|muse-glimmer/.test(target)) return 'Meta';
	if (/deepseek/.test(target)) return 'DeepSeek';
	if (/mistral|ministral|magistral|codestral/.test(target)) return 'Mistral';
	if (/nemotron|ising-calibration/.test(target)) return 'NVIDIA';
	if (/\bglm-/.test(target)) return 'Z.ai';
	if (/minimax/.test(target)) return 'MiniMax';
	if (/step-5/.test(target)) return 'StepFun';
	if (/ernie/.test(target)) return 'Baidu';
	if (/granite/.test(target)) return 'IBM';
	if (/allam/.test(target)) return 'ALLaM';
	return PROVIDER_META[providerKey as ProviderKey]?.chipLabel ?? '';
};

/** Remove prefixos técnicos (`models/`, `@cf/`, `:free`) e a repetição ` · Provedor` no nome exibido. */
export const formatCleanModelTitle = (id = '', rawLabel = '', providerKey = 'other'): string => {
	const base = stripTechnicalPrefixes(rawLabel || id, providerKey) || stripTechnicalPrefixes(id, providerKey);
	const slashIdx = base.indexOf('/');
	if (slashIdx > 0 && slashIdx < base.length - 1) {
		const slug = base.slice(slashIdx + 1);
		if (slug.toLowerCase() !== 'free') {
			return slug;
		}
	}
	return base;
};

/** Extrai selos curtos de capacidade a partir do identificador e nome do modelo. */
export const getCapabilityBadges = (id = '', title = ''): CapabilityBadge[] => {
	const text = `${id} ${title}`;
	const badges: CapabilityBadge[] = [];
	if (/reasoning|\br1\b|\bqwq\b|thinking|step-5/i.test(text)) {
		badges.push('Raciocínio');
	}
	if (/vision|[-/]vl\b|vl-|gemma-4|gemini-3|gemini-4|llama-4-scout|aya-vision/i.test(text)) {
		badges.push('Visão');
	}
	if (/coder|\bcode\b|laguna/i.test(text)) {
		badges.push('Código');
	}
	if (/flash|lite|micro|mini|fast|bolt|lightning|tiny/i.test(text)) {
		badges.push('Rápido');
	}
	return badges;
};

/** Metadados visuais completos de um item do seletor. */
export const getModelDisplayMeta = (item: SelectorModelItem): ModelDisplayMeta => {
	if (isMinervaModeId(item.value) || item.model?.info?.meta?.minerva_mode) {
		const provider = makeProvider('minerva');
		const modeKey = item.model?.info?.meta?.minerva_mode;
		const isHarmonia = item.value === 'minerva.harmonia' || modeKey === 'harmonia';
		const isSabia = item.value === 'minerva.sabia' || modeKey === 'sabia';
		const isImpeto = item.value === 'minerva.impeto' || modeKey === 'impeto';
		const cleanTitle = isHarmonia
			? 'Harmonia'
			: isSabia
				? 'Sábia'
				: isImpeto
					? 'Ímpeto'
					: item.label || item.value;
		const badge = item.model?.info?.meta?.mode_badge
			? (item.model.info.meta.mode_badge as CapabilityBadge)
			: isHarmonia
				? 'Equilíbrio e velocidade'
				: isSabia
					? 'Inteligência máxima'
					: isImpeto
						? 'Velocidade e disponibilidade'
						: null;
		return {
			provider,
			cleanTitle,
			vendorLabel: '',
			badges: badge ? [badge] : []
		};
	}

	const provider = getProviderInfo(item.model, item.value, item.label);
	const cleanTitle = formatCleanModelTitle(item.value, item.label, provider.key);
	const vendorLabel = getVendorLabel(item.value, item.label, provider.key);
	const badges = getCapabilityBadges(item.value, cleanTitle);
	return { provider, cleanTitle, vendorLabel, badges };
};

const FAMILY_PRIORITY_PATTERNS: Record<string, [RegExp, number][]> = {
	minerva: [
		[/harmonia/i, 10],
		[/sabia|sábia/i, 20],
		[/impeto|ímpeto/i, 30]
	],
	gemini: [
		[/^gemini-4\b/i, 10],
		[/^gemini-3\.6-flash$/i, 20],
		[/^gemini-3\.6/i, 22],
		[/^gemini-3\.5-flash$/i, 30],
		[/^gemini-3\.5-flash-lite$/i, 34],
		[/^gemini-3\.5/i, 36],
		[/^gemini-3\.1-flash-lite$/i, 40],
		[/^gemini-3\.1-flash-lite-preview$/i, 44],
		[/^gemini-3-flash-preview$/i, 50],
		[/^gemini-flash-lite-latest$/i, 60],
		[/^gemini-robotics/i, 70],
		[/^gemma-4-31b/i, 80],
		[/^gemma-4-26b/i, 85]
	],
	groq: [
		[/qwen3\.8-27b/i, 10],
		[/gpt-oss-120b/i, 20],
		[/gpt-oss-20b/i, 30],
		[/allam-2-7b/i, 40]
	],
	cerebras: [
		[/qwen-?3\.8-27b/i, 10],
		[/gpt-oss-120b/i, 20]
	],
	nvidia: [
		[/minimax-m3\.1/i, 10],
		[/step-5-preview/i, 15],
		[/mistral-large-4/i, 20],
		[/laguna-xs/i, 25],
		[/nemotron-3\.5-super/i, 30],
		[/nemotron-3-ultra-550b/i, 35],
		[/gemma-4-31b/i, 40],
		[/llama-3\.2-90b/i, 45],
		[/nemotron-3-nano-omni/i, 50],
		[/nemotron-3\.5-lightning/i, 55],
		[/muse-glimmer/i, 60],
		[/ising-calibration/i, 65],
		[/nemotron-3\.5-bolt/i, 70]
	],
	cohere: [
		[/^command-a-plus/i, 10],
		[/^command-a-03/i, 15],
		[/^command-a-reasoning/i, 20],
		[/^command-a-vision/i, 25],
		[/^command-a-translate/i, 30],
		[/^command-r-plus/i, 40],
		[/^command-r-08/i, 45],
		[/^command-r7b-12/i, 50],
		[/^command-r7b/i, 52],
		[/^c4ai-aya-expanse/i, 60],
		[/^c4ai-aya-vision/i, 65],
		[/^north-mini-code/i, 70],
		[/^north-small-translate/i, 75],
		[/^tiny-aya/i, 80]
	],
	cloudflare: [
		[/llama-3\.3-70b/i, 10],
		[/gpt-oss-120b/i, 15],
		[/nemotron-3-120b/i, 20],
		[/qwq-32b/i, 25],
		[/deepseek-r1-distill-qwen-32b/i, 30],
		[/qwen2\.5-coder-32b/i, 35],
		[/qwen3-30b/i, 40],
		[/qwen3\.8-27b/i, 45],
		[/gemma-4-26b/i, 50],
		[/gemma-sea-lion/i, 55],
		[/mistral-small-3\.1-24b/i, 60],
		[/llama-4-scout-17b/i, 65],
		[/gpt-oss-20b/i, 70],
		[/llama-3\.2-11b-vision/i, 75],
		[/llama-3\.1-8b/i, 80],
		[/glm-4\.7-flash/i, 85],
		[/llama-3\.2-3b/i, 90],
		[/phonellm/i, 95],
		[/gemma-7b-it-lora/i, 105],
		[/-lora$/i, 110]
	],
	openrouter: [
		[/nemotron-3-ultra-550b/i, 10],
		[/nemotron-3\.5-super/i, 15],
		[/gemma-4-31b/i, 20],
		[/gemma-4-26b/i, 25],
		[/nemotron-3-nano-omni/i, 30],
		[/nemotron-3\.5-lightning/i, 35],
		[/ernie-5\.5/i, 40],
		[/ling-3\.2/i, 45],
		[/dots-3/i, 50],
		[/north-mini-code/i, 55],
		[/particle-1/i, 60],
		[/flint-v1\.0/i, 65],
		[/lfm-3-1\.7b/i, 70],
		[/openrouter\/free/i, 90]
	]
};

export const modelRelevanceRank = (cleanTitle: string, id: string, providerKey: string): number => {
	const patterns = FAMILY_PRIORITY_PATTERNS[providerKey];
	if (patterns) {
		for (const [regex, score] of patterns) {
			if (regex.test(cleanTitle) || regex.test(id)) return score;
		}
	}
	if (/-lora$/i.test(cleanTitle)) return 110;
	if (/preview|exp$/i.test(cleanTitle)) return 95;
	return 80;
};

/** Ordena modelos colocando fixados primeiro, depois por provedor e relevância dentro de cada família. */
export const sortModelsForSelector = <T extends SelectorModelItem>(
	items: T[],
	pinnedIds: string[] = []
): T[] => {
	const pinnedSet = new Set(pinnedIds);
	return [...items].sort((a, b) => {
		const aPinned = pinnedSet.has(a.value) ? 0 : 1;
		const bPinned = pinnedSet.has(b.value) ? 0 : 1;
		if (aPinned !== bPinned) return aPinned - bPinned;

		const aMeta = getModelDisplayMeta(a);
		const bMeta = getModelDisplayMeta(b);
		if (aMeta.provider.rank !== bMeta.provider.rank) {
			return aMeta.provider.rank - bMeta.provider.rank;
		}

		const aRel = modelRelevanceRank(aMeta.cleanTitle, a.value, aMeta.provider.key);
		const bRel = modelRelevanceRank(bMeta.cleanTitle, b.value, bMeta.provider.key);
		if (aRel !== bRel) return aRel - bRel;

		return aMeta.cleanTitle.localeCompare(bMeta.cleanTitle, undefined, {
			numeric: true,
			sensitivity: 'base'
		});
	});
};

export type DisplaySectionRow<T extends SelectorModelItem> =
	| {
			type: 'header';
			key: string;
			provider: ProviderInfo;
			title: string;
			count: number;
			pinnedSection: boolean;
	  }
	| {
			type: 'item';
			key: string;
			item: T;
			index: number;
			meta: ModelDisplayMeta;
	  };

/** Agrupa uma lista já ordenada em cabeçalhos de seção (Fixados / Provedores) + linhas de modelo. */
export const buildGroupedRows = <T extends SelectorModelItem>(
	sortedItems: T[],
	pinnedIds: string[] = []
): DisplaySectionRow<T>[] => {
	const pinnedSet = new Set(pinnedIds);
	const groups: {
		key: string;
		provider: ProviderInfo;
		title: string;
		pinnedSection: boolean;
		entries: { item: T; index: number; meta: ModelDisplayMeta }[];
	}[] = [];

	const findOrCreateGroup = (meta: ModelDisplayMeta, pinned: boolean) => {
		const groupKey = pinned ? '__pinned__' : meta.provider.key;
		let group = groups.find((g) => g.key === groupKey);
		if (!group) {
			group = {
				key: groupKey,
				provider: meta.provider,
				title: pinned ? 'Fixados' : meta.provider.label,
				pinnedSection: pinned,
				entries: []
			};
			groups.push(group);
		}
		return group;
	};

	sortedItems.forEach((item, index) => {
		const meta = getModelDisplayMeta(item);
		const pinned = pinnedSet.has(item.value);
		findOrCreateGroup(meta, pinned).entries.push({ item, index, meta });
	});

	const rows: DisplaySectionRow<T>[] = [];
	for (const group of groups) {
		rows.push({
			type: 'header',
			key: `hdr:${group.key}`,
			provider: group.provider,
			title: group.title,
			count: group.entries.length,
			pinnedSection: group.pinnedSection
		});
		for (const entry of group.entries) {
			rows.push({
				type: 'item',
				key: entry.item.value,
				item: entry.item,
				index: entry.index,
				meta: entry.meta
			});
		}
	}
	return rows;
};
