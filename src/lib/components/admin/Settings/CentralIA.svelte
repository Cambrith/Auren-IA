<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { config, models, settings } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import { getOpenAIConfig, updateOpenAIConfig } from '$lib/apis/openai';
	import { createNewModel, updateModelById } from '$lib/apis/models';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import {
		FILTER_LABEL,
		allowedRawIds,
		parkedModels,
		PRICE_LABEL,
		classifyResult,
		cleanName,
		filterModels,
		fromBaseline,
		isChatModel,
		isPaidKind,
		isOpenRouter,
		loadResults,
		priceKind,
		providerName,
		saveResults,
		safeToTest,
		summarize,
		testDelayMs,
		type Filter,
		type TestResult
	} from '$lib/utils/centralIA';

	const i18n = getContext('i18n');

	type Provider = {
		idx: number;
		url: string;
		prefix: string;
		name: string;
		enabled: boolean;
		hasKey: boolean;
		restricted: boolean;
		models: any[];
	};

	let loading = true;
	let cfg: any = null;
	let results: Record<string, TestResult> = {};
	let openIdx: number | null = null;
	let query = '';
	let filter: Filter = 'todos';
	let running: { idx: number; done: number; total: number } | null = null;
	let stopRequested = false;
	let busy = false;

	const buildProviders = (c: any, all: any[]): Provider[] => {
		if (!c) return [];
		return (c.OPENAI_API_BASE_URLS ?? []).map((url: string, idx: number) => {
			const conf = c.OPENAI_API_CONFIGS?.[String(idx)] ?? {};
			const prefix = conf.prefix_id ?? '';
			return {
				idx,
				url,
				prefix,
				name: providerName(url, prefix),
				enabled: conf.enable !== false,
				hasKey: Boolean(c.OPENAI_API_KEYS?.[idx]),
				restricted: (conf.model_ids?.length ?? 0) > 0,
				models: (all ?? []).filter((m) => m.urlIdx === idx && m.connection_type !== 'local')
			};
		});
	};

	let providers: Provider[] = [];
	$: providers = buildProviders(cfg, $models);

	const reload = async () => {
		cfg = await getOpenAIConfig(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections ? ($settings?.directConnections ?? null) : null
			)
		);
	};

	let baselineDate = '';

	onMount(async () => {
		// Testes já feitos em arquivo (static/central-ia-testes.json); os seus próprios testes têm prioridade.
		let baseline: Record<string, TestResult> = {};
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/central-ia-testes.json`);
			if (res.ok) {
				const data = await res.json();
				baseline = fromBaseline(data);
				baselineDate = data?.testedAt ? new Date(data.testedAt).toLocaleDateString('pt-BR') : '';
			}
		} catch {
			// sem arquivo de testes: a página funciona só com os testes locais
		}
		results = { ...baseline, ...loadResults(localStorage) };
		await reload();
		loading = false;
	});

	const saveConfig = async (next: any) => {
		await updateOpenAIConfig(localStorage.token, {
			ENABLE_OPENAI_API: next.ENABLE_OPENAI_API,
			OPENAI_API_BASE_URLS: next.OPENAI_API_BASE_URLS,
			OPENAI_API_KEYS: next.OPENAI_API_KEYS,
			OPENAI_API_CONFIGS: next.OPENAI_API_CONFIGS
		});
		await reload();
	};

	const patchConnection = async (idx: number, patch: Record<string, unknown>) => {
		const current = cfg.OPENAI_API_CONFIGS?.[String(idx)] ?? {};
		await saveConfig({
			...cfg,
			OPENAI_API_CONFIGS: { ...cfg.OPENAI_API_CONFIGS, [String(idx)]: { ...current, ...patch } }
		});
	};

	const toggleProvider = async (p: Provider, value: boolean) => {
		busy = true;
		try {
			await patchConnection(p.idx, { enable: value });
		} catch (error) {
			toast.error(`${error}`);
		}
		busy = false;
	};

	const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

	const testOne = async (m: any) => {
		let status = 0;
		let message = '';
		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/chat/completions`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.token}` },
				body: JSON.stringify({
					model: m.id,
					messages: [{ role: 'user', content: 'Responda: ok' }],
					max_tokens: 8,
					stream: false
				})
			});
			status = res.status;
			try {
				const body = await res.json();
				const raw = body?.error?.message ?? body?.detail?.error?.message ?? body?.detail ?? '';
				message = typeof raw === 'string' ? raw : JSON.stringify(raw);
			} catch {
				// resposta sem corpo legível
			}
		} catch (error) {
			message = `${error}`;
		}
		results = { ...results, [m.id]: classifyResult(status, message) };
		saveResults(localStorage, results);
	};

	const runTests = async (p: Provider, list: any[]) => {
		if (running || list.length === 0) return;
		running = { idx: p.idx, done: 0, total: list.length };
		stopRequested = false;
		const openrouter = isOpenRouter(p.url);
		for (const m of list) {
			if (stopRequested) break;
			await testOne(m);
			running = { idx: p.idx, done: running.done + 1, total: list.length };
			if (results[m.id]?.kind === 'limite' && /per-day|daily/i.test(results[m.id].detail)) {
				toast.warning('O limite diário do provedor foi atingido; os testes pararam.');
				break;
			}
			await sleep(testDelayMs(openrouter, priceKind(m) === 'gratis'));
		}
		running = null;
	};

	const testSafe = (p: Provider) => {
		const list = safeToTest(p.models);
		if (isOpenRouter(p.url)) {
			const frees = list.filter((m) => priceKind(m) === 'gratis').length;
			if (
				!confirm(
					`Cada teste de modelo grátis do OpenRouter conta no limite diário (50 pedidos por dia sem créditos comprados). Serão ${frees} testes. Continuar?`
				)
			)
				return;
		}
		return runTests(p, list);
	};

	const testPaid = (p: Provider) => {
		const list = p.models.filter((m) => isChatModel(m) && priceKind(m) === 'pago');
		if (
			!confirm(
				`Testar ${list.length} modelos PAGOS. Se a conta tiver saldo, cada teste (1 chamada curta) pode gerar cobrança. Sem saldo, o provedor apenas recusa (erro 402). Continuar?`
			)
		)
			return;
		return runTests(p, list);
	};

	/** Modelos de outra função ficam guardados, mas escondidos do seletor de conversa. */
	const hideParked = async (p: Provider) => {
		for (const m of parkedModels(p.models, results)) {
			const form = {
				id: m.id,
				base_model_id: null,
				name: cleanName(m, p.prefix),
				meta: { ...(m.info?.meta ?? {}), hidden: true },
				params: m.info?.params ?? {},
				is_active: true
			};
			const created = await createNewModel(localStorage.token, form).catch(() => null);
			if (!created) await updateModelById(localStorage.token, m.id, form).catch(() => null);
		}
	};

	const triageProvider = async (p: Provider) => {
		const ids = allowedRawIds(p.models, results, p.prefix);
		await patchConnection(p.idx, { model_ids: ids });
		await hideParked(p);
		return ids.length;
	};

	const applyTriage = async (p: Provider) => {
		const ids = allowedRawIds(p.models, results, p.prefix);
		if (ids.length === 0) return toast.error('Nenhum modelo foi liberado nos testes ainda.');
		if (
			!confirm(
				`Liberar só os ${ids.length} modelos aprovados em ${p.name}? Os demais ficam bloqueados e não aparecem nem podem ser usados. Você pode voltar com "Mostrar todos".`
			)
		)
			return;
		busy = true;
		try {
			toast.success(`${p.name}: ${await triageProvider(p)} modelos liberados.`);
			await reload();
		} catch (error) {
			toast.error(`${error}`);
		}
		busy = false;
	};

	const applyTriageAll = async () => {
		const tested = providers.filter((p) => p.models.some((m) => results[m.id]));
		if (!tested.length) return toast.error('Rode os testes primeiro.');
		if (
			!confirm(
				`Aplicar a triagem em ${tested.length} provedores? Só os modelos aprovados nos testes continuam ativos; o restante fica bloqueado.`
			)
		)
			return;
		busy = true;
		let total = 0;
		try {
			for (const p of tested) total += await triageProvider(p);
			await reload();
			toast.success(`${total} modelos liberados em ${tested.length} provedores.`);
		} catch (error) {
			toast.error(`${error}`);
		}
		busy = false;
	};

	const showAll = async (p: Provider) => {
		busy = true;
		try {
			await patchConnection(p.idx, { model_ids: [] });
			toast.success(`${p.name}: todos os modelos voltaram a aparecer.`);
		} catch (error) {
			toast.error(`${error}`);
		}
		busy = false;
	};

	const clearResults = (p: Provider) => {
		const next = { ...results };
		for (const m of p.models) delete next[m.id];
		results = next;
		saveResults(localStorage, results);
	};

	const badgeClass = (kind?: string) =>
		kind === 'ok'
			? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
			: isPaidKind(kind as any) || kind === 'limite' || kind === 'termos' || kind === 'ocupado'
				? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
				: kind === 'nao_chat'
					? 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
					: kind
						? 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
						: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
</script>

<div id="tab-ai-hub" class="flex flex-col h-full text-sm">
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-1">Central de Inteligência Artificial</h2>
	<p class="text-xs text-gray-600 dark:text-gray-400 mb-3">
		Todos os provedores conectados, com os modelos de cada um. Teste o que funciona de verdade e
		deixe no seletor só o que você usa.
		{#if baselineDate}<span class="block mt-0.5">Testes iniciais de {baselineDate}; refaça quando quiser.</span>{/if}
	</p>

	{#if loading}
		<div class="flex-1 flex items-center justify-center"><Spinner className="size-5" /></div>
	{:else if !cfg}
		<div class="text-xs text-red-600">Não foi possível ler as conexões.</div>
	{:else}
		<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5 space-y-2">
			<div class="flex items-center gap-2">
				<button
					class="px-2 py-1 rounded-md bg-gray-900 text-white dark:bg-white dark:text-gray-900 text-xs disabled:opacity-50"
					disabled={!!running || busy}
					on:click={applyTriageAll}>Aplicar triagem em todos</button
				>
				<span class="text-xs text-gray-600 dark:text-gray-400"
					>Libera só o que passou nos testes; o resto fica bloqueado.</span
				>
			</div>
			<details class="rounded-lg border border-gray-200 dark:border-gray-800 px-3 py-2 text-xs">
				<summary class="cursor-pointer font-medium text-gray-800 dark:text-gray-200">
					Como o OpenRouter limita o uso
				</summary>
				<ul class="mt-2 list-disc pl-4 space-y-1 text-gray-600 dark:text-gray-400">
					<li>
						<b>Modelos pagos</b> usam <b>saldo</b> (créditos). Sem créditos comprados, o erro é 402.
					</li>
					<li>
						<b>Modelos grátis (:free)</b> não gastam saldo, mas têm limite de pedidos:
						<b>20 por minuto</b> e <b>50 por dia</b> enquanto você tiver comprado menos de US$ 10
						em créditos. Depois de comprar US$ 10, o limite diário sobe para <b>1.000</b>.
					</li>
					<li>Saldo negativo bloqueia até os modelos grátis (erro 402).</li>
					<li>Cada teste de modelo grátis conta no limite diário.</li>
				</ul>
			</details>

			{#each providers as p (p.idx)}
				{@const sum = summarize(p.models, results)}
				<section class="rounded-lg border border-gray-200 dark:border-gray-800">
					<div class="flex items-center gap-3 px-3 py-2">
						<button
							class="flex-1 min-w-0 text-left"
							on:click={() => (openIdx = openIdx === p.idx ? null : p.idx)}
							aria-expanded={openIdx === p.idx}
						>
							<div class="font-medium text-gray-900 dark:text-white truncate">{p.name}</div>
							<div class="text-xs text-gray-600 dark:text-gray-400">
								{#if !p.hasKey}
									<span class="text-amber-700 dark:text-amber-400">sem chave</span> ·
								{/if}
								{sum.total} modelos
								{#if sum.gratis} · {sum.gratis} grátis{/if}
								{#if sum.pagos} · {sum.pagos} pagos{/if}
								{#if sum.ok} · <span class="text-emerald-700 dark:text-emerald-400">{sum.ok} funcionam</span>{/if}
								{#if sum.outra} · {sum.outra} outra função{/if}
								{#if sum.exigePago} · <span class="text-amber-700 dark:text-amber-400">{sum.exigePago} exigem pagamento</span>{/if}
								{#if sum.falha} · <span class="text-red-700 dark:text-red-400">{sum.falha} indisponíveis</span>{/if}
								{#if p.restricted} · lista filtrada{/if}
							</div>
						</button>
						<Switch
							state={p.enabled}
							ariaLabel={`Ativar ${p.name}`}
							on:change={(e) => toggleProvider(p, e.detail)}
						/>
					</div>

					{#if openIdx === p.idx}
						<div class="border-t border-gray-200 dark:border-gray-800 px-3 py-2 space-y-2">
							<div class="flex flex-wrap gap-1.5">
								<button
									class="px-2 py-1 rounded-md bg-gray-900 text-white dark:bg-white dark:text-gray-900 text-xs disabled:opacity-50"
									disabled={!!running || busy || !p.hasKey}
									on:click={() => testSafe(p)}>Testar grátis e sem preço</button
								>
								{#if sum.pagos}
									<button
										class="px-2 py-1 rounded-md border border-gray-300 dark:border-gray-700 text-xs disabled:opacity-50"
										disabled={!!running || busy || !p.hasKey}
										on:click={() => testPaid(p)}>Testar pagos…</button
									>
								{/if}
								<button
									class="px-2 py-1 rounded-md border border-gray-300 dark:border-gray-700 text-xs disabled:opacity-50"
									disabled={!!running || busy || sum.ok === 0}
									on:click={() => applyTriage(p)}>Aplicar triagem</button
								>
								{#if p.restricted}
									<button
										class="px-2 py-1 rounded-md border border-gray-300 dark:border-gray-700 text-xs disabled:opacity-50"
										disabled={!!running || busy}
										on:click={() => showAll(p)}>Mostrar todos</button
									>
								{/if}
								{#if running?.idx === p.idx}
									<button
										class="px-2 py-1 rounded-md border border-red-400 text-red-700 dark:text-red-300 text-xs"
										on:click={() => (stopRequested = true)}>Parar</button
									>
								{:else}
									<button
										class="px-2 py-1 rounded-md text-xs text-gray-600 dark:text-gray-400 underline"
										disabled={!!running}
										on:click={() => clearResults(p)}>Limpar testes</button
									>
								{/if}
							</div>

							{#if running?.idx === p.idx}
								<div class="text-xs text-gray-600 dark:text-gray-400" role="status">
									Testando… {running.done} de {running.total}
								</div>
							{/if}

							<div class="flex flex-wrap items-center gap-1.5">
								<input
									class="flex-1 min-w-[10rem] rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1 text-xs"
									placeholder="Buscar modelo"
									aria-label="Buscar modelo"
									bind:value={query}
								/>
								{#each Object.entries(FILTER_LABEL) as [key, label]}
									<button
										class="px-2 py-1 rounded-md text-xs {filter === key
											? 'bg-gray-200 dark:bg-gray-700 font-medium'
											: 'text-gray-600 dark:text-gray-400'}"
										on:click={() => (filter = key as Filter)}>{label}</button
									>
								{/each}
							</div>

							<ul class="max-h-72 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-800">
								{#each filterModels(p.models, { query, filter, results, prefix: p.prefix }) as m (m.id)}
									{@const r = results[m.id]}
									<li class="flex items-center gap-2 py-1.5">
										<div class="flex-1 min-w-0">
											<div class="truncate text-xs text-gray-900 dark:text-gray-100">
												{cleanName(m, p.prefix)}
											</div>
											{#if r && r.kind !== 'ok' && r.detail}
												<div class="truncate text-[0.65rem] text-gray-500" title={r.detail}>{r.detail}</div>
											{/if}
										</div>
										<span class="shrink-0 rounded px-1.5 py-0.5 text-[0.65rem] bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
											>{PRICE_LABEL[priceKind(m)]}</span
										>
										<span class="shrink-0 rounded px-1.5 py-0.5 text-[0.65rem] {badgeClass(r?.kind)}"
											>{r ? r.label : 'Sem teste'}</span
										>
										{#if isChatModel(m)}
											<button
												class="shrink-0 text-xs underline text-gray-600 dark:text-gray-400 disabled:opacity-50"
												disabled={!!running || !p.hasKey}
												on:click={async () => {
													running = { idx: p.idx, done: 0, total: 1 };
													await testOne(m);
													running = null;
												}}>Testar</button
											>
										{:else}
											<span class="shrink-0 text-[0.65rem] text-gray-500">não é de chat</span>
										{/if}
									</li>
								{:else}
									<li class="py-3 text-xs text-gray-500">Nenhum modelo neste filtro.</li>
								{/each}
							</ul>
						</div>
					{/if}
				</section>
			{/each}
		</div>
	{/if}
</div>
