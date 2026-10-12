<script lang="ts">
	import { models, config } from '$lib/stores';
	import { onMount } from 'svelte';
	import { canGenerateImage, defaultImageModel, compareProviders } from '$lib/utils/imageSelection';
	import { aurenRequest, type AurenState } from '$lib/apis/auren';
	let preferredImage = '';
	let conversationModel = 'cavren:auto';
	onMount(() => {
		const updatePreferred = (event: Event) =>
			(preferredImage = (event as CustomEvent<string>).detail);
		window.addEventListener('auren-image-preferences', updatePreferred);
		(async () => {
			if ($config?.auren?.local) {
				try {
					preferredImage =
						(await aurenRequest<AurenState>('state')).preferences.image_model_id ?? '';
				} catch {}
			}
		})();
		return () => window.removeEventListener('auren-image-preferences', updatePreferred);
	});
	import Dropdown from '$lib/components/common/Dropdown.svelte';

	export let selectedModels = ['cavren:auto'];
	export let options = {
		mode_id: 'ether',
		web_search: false,
		billing_confirmed: false,
		image_generation: false
	};
	export let disabled = false;
	export let onChange: (value: typeof options) => void = () => {};

	const modes = [
		{ id: 'ether', name: 'Éter', description: 'Versátil para qualquer tarefa.' },
		{ id: 'impeto', name: 'Ímpeto', description: 'Respostas rápidas e diretas.' },
		{ id: 'insight', name: 'Insight', description: 'Raciocínio aprofundado.' },
		{ id: 'arquiteto', name: 'Arquiteto', description: 'Código, sistemas e desenvolvimento.' }
	];
	const providerNames: Record<string, string> = {
		openai: 'OpenAI',
		anthropic: 'Anthropic',
		gemini: 'Google Gemini',
		groq: 'Groq',
		mistral: 'Mistral AI',
		openrouter: 'OpenRouter',
		cloudflare: 'Cloudflare',
		cohere: 'Cohere',
		nvidia: 'NVIDIA NIM',
		ollama: 'Ollama Cloud',
		zai: 'Z.ai',
		aihorde: 'AI Horde'
	};
	const providerName = (id?: string) => (id ? (providerNames[id] ?? id) : 'Escolha automática');
	$: cavrenModels = $models.filter((model) => model.id.startsWith('cavren:'));
	$: selected = cavrenModels.find((model) => model.id === selectedModels[0]);
	$: selectedInfo = (selected as any)?.cavren;
	let modelSearch = '';
	let showMode = false;
	let showModel = false;
	let providerFilter = 'Todos';
	let kindFilter = 'chat';
	$: providers = [
		...new Set(cavrenModels.map((model) => (model as any).cavren?.provider).filter(Boolean))
	].sort((a, b) => compareProviders(providerName(a), providerName(b)));
	$: visibleModels = cavrenModels
		.filter(
			(model) =>
				(providerFilter === 'Todos' || (model as any).cavren?.provider === providerFilter) &&
				(kindFilter === 'all' ||
					(kindFilter === 'chat'
						? !(model as any).cavren?.image_only
						: (model as any).cavren?.capabilities?.image_generation)) &&
				`${(model as any).cavren?.label ?? model.name} ${providerName((model as any).cavren?.provider)} ${model.id}`
					.toLocaleLowerCase()
					.includes(modelSearch.toLocaleLowerCase())
		)
		.sort(
			(a, b) =>
				compareProviders(providerName(a.cavren?.provider), providerName(b.cavren?.provider)) ||
				compareProviders(a.cavren?.label ?? a.name, b.cavren?.label ?? b.name)
		);
	function chooseModel(model: (typeof $models)[number] | undefined) {
		if (!model || model.cavren?.available === false) return;
		const image =
			model.cavren?.image_only === true || (kindFilter === 'image' && canGenerateImage(model));
		if (image && !options.image_generation && !selectedInfo?.image_only)
			conversationModel = selectedModels[0];
		selectedModels = [model.id];
		update({ billing_confirmed: false, image_generation: image });
		showModel = false;
	}
	function toggleImages() {
		if (options.image_generation || selectedInfo?.image_only) {
			selectedModels = [
				cavrenModels.some((m) => m.id === conversationModel && !m.cavren?.image_only)
					? conversationModel
					: 'cavren:auto'
			];
			kindFilter = 'chat';
			update({ image_generation: false, billing_confirmed: false });
			return;
		}
		const imageModel = defaultImageModel(cavrenModels, preferredImage, selectedModels[0]);
		conversationModel = selectedModels[0];
		kindFilter = 'image';
		modelSearch = '';
		providerFilter = 'Todos';
		if (imageModel) {
			selectedModels = [imageModel.id];
			update({ image_generation: true, billing_confirmed: false });
		} else {
			showModel = true;
		}
	}
	function navigateChoices(event: KeyboardEvent) {
		if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
		if ((event.target as HTMLElement).tagName === 'INPUT' && event.key !== 'ArrowDown') return;
		const choices = Array.from(
			(event.currentTarget as HTMLElement).querySelectorAll<HTMLButtonElement>(
				'button[data-choice]:not(:disabled)'
			)
		);
		if (!choices.length) return;
		event.preventDefault();
		const index = choices.indexOf(event.target as HTMLButtonElement);
		const next =
			event.key === 'Home'
				? 0
				: event.key === 'End'
					? choices.length - 1
					: (index + (event.key === 'ArrowDown' ? 1 : -1) + choices.length) % choices.length;
		choices[next].focus();
	}
	$: support = [
		'Documentos',
		...(selectedInfo?.capabilities?.vision ? ['Imagens'] : []),
		...(selectedInfo?.capabilities?.video ? ['Vídeos'] : []),
		...(selectedInfo?.capabilities?.image_generation ? ['Gera imagens'] : [])
	].join(' · ');
	$: possibleCost = selectedInfo?.price_kind && selectedInfo.price_kind !== 'free';
	$: mode = modes.find((mode) => mode.id === options.mode_id) ?? modes[0];

	function update(patch: Partial<typeof options>) {
		onChange({ ...options, ...patch });
	}
</script>

<div class="lunvri-controls no-drag" aria-label="Configurações da Auren">
	<Dropdown
		bind:show={showMode}
		contentClass="lunvri-selector-popover"
		sideOffset={8}
		visualViewportAware
		maxHeight="min(38rem, calc(100dvh - 24px))"
	>
		<button
			type="button"
			class="selector mode-trigger"
			aria-label="Modo da Auren"
			aria-expanded={showMode}
			disabled={disabled || options.image_generation}
		>
			<span class="mode-symbol" aria-hidden="true"
				>{mode.id === 'ether'
					? '✧'
					: mode.id === 'impeto'
						? 'ϟ'
						: mode.id === 'insight'
							? '◎'
							: '⌘'}</span
			>
			<span class="trigger-copy"
				><small>{options.image_generation ? 'Modo da conversa salvo' : 'Modo de conversa'}</small
				><strong>{mode.name}</strong></span
			>
			<span class="chevron" aria-hidden="true">⌄</span>
		</button>
		<div
			slot="content"
			class="selector-panel modes-panel"
			role="menu"
			tabindex="-1"
			aria-label="Modos de conversa"
			on:keydown={navigateChoices}
		>
			<div class="panel-heading">
				<strong>Como vamos trabalhar?</strong><small>Escolha o ritmo da conversa.</small>
			</div>
			{#each modes as item}
				<button
					type="button"
					class="choice mode-choice"
					class:chosen={item.id === options.mode_id}
					role="menuitemradio"
					aria-checked={item.id === options.mode_id}
					data-choice
					on:click={() => {
						update({ mode_id: item.id });
						showMode = false;
					}}
				>
					<span class="choice-symbol" aria-hidden="true"
						>{item.id === 'ether'
							? '✧'
							: item.id === 'impeto'
								? 'ϟ'
								: item.id === 'insight'
									? '◎'
									: '⌘'}</span
					>
					<span><strong>{item.name}</strong><small>{item.description}</small></span>
					<span class="check" aria-hidden="true">{item.id === options.mode_id ? '✓' : ''}</span>
				</button>
			{/each}
		</div>
	</Dropdown>
	<Dropdown
		bind:show={showModel}
		contentClass="lunvri-selector-popover"
		sideOffset={8}
		visualViewportAware
		maxHeight="min(38rem, calc(100dvh - 24px))"
	>
		<button
			type="button"
			class="selector model-trigger"
			aria-label="Modelo da Auren"
			aria-expanded={showModel}
			{disabled}
		>
			<span class="connection-dot" class:cost={possibleCost} aria-hidden="true"></span>
			<span class="trigger-copy"
				><small>{providerName(selectedInfo?.provider) ?? 'Escolha automática'}</small><strong
					>{selectedInfo?.label ?? 'Automático'}</strong
				></span
			>
			<span class="chevron" aria-hidden="true">⌄</span>
		</button>
		<div
			slot="content"
			class="selector-panel models-panel"
			role="menu"
			tabindex="-1"
			aria-label="Modelos disponíveis"
			on:keydown={navigateChoices}
		>
			<div class="panel-heading">
				<strong>Escolha o modelo</strong><small
					>{kindFilter === 'image'
						? 'Escolha quem produzirá a imagem. O modo de conversa será preservado.'
						: 'Alternativas gratuitas quando houver falhas ou limites.'}</small
				>
			</div>
			<div class="model-search">
				<span aria-hidden="true">⌕</span><input
					type="search"
					aria-label="Filtrar modelos"
					placeholder="Buscar nome ou provedor…"
					bind:value={modelSearch}
				/>
			</div>
			<div class="provider-filters" aria-label="Tipo de modelo">
				{#each [{ id: 'chat', label: 'Conversar' }, { id: 'image', label: 'Gerar imagens' }, { id: 'all', label: 'Todos os tipos' }] as kind}
					<button
						type="button"
						class:chosen={kindFilter === kind.id}
						aria-pressed={kindFilter === kind.id}
						on:click={() => {
							kindFilter = kind.id;
						}}>{kind.label}</button
					>
				{/each}
			</div>
			<label class="provider-select"
				>Provedor<select aria-label="Filtrar por provedor" bind:value={providerFilter}
					><option value="Todos">Todos os provedores</option>{#each providers as provider}<option
							value={provider}>{providerName(provider)}</option
						>{/each}</select
				></label
			>
			{#if kindFilter === 'image' && preferredImage && cavrenModels.some((m) => m.id === preferredImage)}<button
					class="default-image"
					type="button"
					on:click={() => chooseModel(cavrenModels.find((m) => m.id === preferredImage))}
					>Usar gerador padrão</button
				>{/if}
			<div class="model-list">
				{#each visibleModels as item, index}
					{#if index === 0 || (item as any).cavren?.provider !== (visibleModels[index - 1] as any).cavren?.provider}
						<div class="provider-heading">
							{providerName((item as any).cavren?.provider) ?? 'Seleção automática'}
						</div>
					{/if}
					<button
						type="button"
						class="choice model-choice"
						class:chosen={item.id === selectedModels[0]}
						role="menuitemradio"
						aria-checked={item.id === selectedModels[0]}
						disabled={(item as any).cavren?.available === false}
						data-choice
						on:click={() => chooseModel(item)}
					>
						<span
							><strong>{(item as any).cavren?.label ?? item.name}</strong><small
								>{providerName((item as any).cavren?.provider) ?? 'Seleção inteligente'} · {(
									item as any
								).cavren?.price_kind === 'free'
									? (item as any).cavren?.usage_label || 'Gratuito / cota gratuita'
									: 'Custo a confirmar'}{(item as any).cavren?.capabilities?.vision
									? ' · Visão'
									: ''}{(item as any).cavren?.capabilities?.image_generation
									? ' · Gera imagens'
									: ''}</small
							></span
						>
						<span class="check" aria-hidden="true">{item.id === selectedModels[0] ? '✓' : ''}</span>
					</button>
				{:else}
					<p class="empty-results">Nenhum modelo encontrado. Tente outro nome ou provedor.</p>
				{/each}
			</div>
			<div class="panel-footer">{visibleModels.length} opções · Modelo atual: {support}</div>
		</div>
	</Dropdown>
	<button
		type="button"
		class:active={options.web_search}
		class="lunvri-search"
		aria-label="Pesquisar na web"
		aria-pressed={options.web_search}
		title="Pesquisar na web com a Auren"
		disabled={disabled || options.image_generation}
		on:click={() => update({ web_search: !options.web_search })}
	>
		<svg
			width="18"
			height="18"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			aria-hidden="true"
			><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c5 5 5 13 0 18-5-5-5-13 0-18Z" /></svg
		>
	</button>
	<button
		type="button"
		class="lunvri-search"
		class:active={options.image_generation}
		aria-label="Gerar imagens"
		aria-pressed={options.image_generation}
		title={options.image_generation
			? 'Voltar à conversa e ao modelo anterior'
			: 'Gerar imagens com um modelo compatível'}
		{disabled}
		on:click={toggleImages}
	>
		<svg
			width="18"
			height="18"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			aria-hidden="true"
			><rect x="3" y="3" width="18" height="18" rx="3" /><circle cx="8" cy="8" r="1.5" /><path
				d="m3 17 6-6 4 4 3-3 5 5"
			/></svg
		>
	</button>
</div>
{#if options.image_generation}
	<div class="image-context no-drag" role="status">
		<span
			><strong>Gerar imagem</strong> · {selectedInfo?.label ?? selected?.name}<small
				>Descreva a imagem na mensagem. O modo {mode.name} será retomado ao voltar à conversa.</small
			></span
		>
		<button
			type="button"
			{disabled}
			on:click={() => {
				kindFilter = 'image';
				modelSearch = '';
				providerFilter = 'Todos';
				showModel = true;
			}}>Trocar gerador</button
		>
		<button type="button" {disabled} on:click={toggleImages}>Voltar à conversa</button>
	</div>
{/if}

{#if possibleCost}
	<label class="lunvri-cost no-drag">
		<input
			type="checkbox"
			checked={options.billing_confirmed}
			{disabled}
			on:change={(event) => update({ billing_confirmed: event.currentTarget.checked })}
		/>
		Confirmo o possível custo deste modelo.
	</label>
{/if}

<style>
	.image-context {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 8px;
		padding: 8px 0;
		color: #a9bdd0;
		font-size: 12px;
	}
	.image-context strong {
		color: #59e0f3;
	}
	.image-context small {
		display: block;
		font-size: 11px;
		margin-top: 3px;
	}
	.image-context button {
		border: 1px solid #2a3b50;
		border-radius: 8px;
		padding: 6px 9px;
		color: #f4faff;
	}

	.default-image {
		font-size: 12px;
		color: #59e0f3;
		padding: 8px 12px;
		border: 1px solid #2a3b50;
		border-radius: 8px;
		margin: 0 8px 10px;
		flex-shrink: 0;
	}
	.provider-select {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 0 8px 10px;
		font-size: 11px;
		color: #a9bdd0;
		flex-shrink: 0;
	}
	.provider-select select {
		flex: 1;
		background: #080d17;
		border: 1px solid #2a3b50;
		border-radius: 8px;
		padding: 7px 9px;
		color: #f4faff;
	}
	.provider-heading {
		padding: 16px 12px 6px;
		color: #59e0f3;
		font-size: 11px;
		font-weight: 650;
		letter-spacing: 0.05em;
		text-transform: uppercase;
		position: sticky;
		top: 0;
		background: #121e2d;
		z-index: 1;
	}
	.lunvri-controls {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
		max-width: 100%;
		padding: 4px 0;
	}
	.selector {
		display: flex;
		align-items: center;
		gap: 10px;
		background: linear-gradient(135deg, #16263a, #101c2c);
		border: 1px solid #2a3b50;
		border-radius: 14px;
		padding: 9px 12px;
		color: #f4faff;
		text-align: left;
		min-width: 0;
		transition:
			border-color 0.18s,
			background 0.18s;
	}
	.selector:hover {
		border-color: #50667e;
		background: #1a2b3d;
	}
	.selector:disabled {
		opacity: 0.6;
		cursor: wait;
	}
	.mode-trigger {
		min-width: 150px;
	}
	.model-trigger {
		width: clamp(170px, 24vw, 320px);
	}
	.trigger-copy {
		display: flex;
		flex-direction: column;
		min-width: 0;
		flex: 1;
	}
	.trigger-copy small {
		font-size: 10px;
		color: #a9bdd0;
		line-height: 15px;
	}
	.trigger-copy strong {
		font-size: 13px;
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.mode-symbol,
	.choice-symbol {
		font-size: 24px;
		color: #59e0f3;
		line-height: 1;
	}
	.chevron {
		color: #a9bdd0;
		font-size: 18px;
	}
	.connection-dot {
		width: 7px;
		height: 7px;
		background: #59e0f3;
		border-radius: 50%;
		box-shadow: 0 0 10px #59e0f333;
		flex: none;
	}
	.connection-dot.cost {
		background: #e7b66f;
	}
	:global(.lunvri-selector-popover) {
		z-index: 100;
		background: #0d1727;
		border: 1px solid #2a3b50;
		border-radius: 18px;
		box-shadow: 0 18px 60px #0009;
		padding: 8px;
		display: flex;
		flex-direction: column;
		overflow: hidden !important;
		color: #f4faff;
		max-width: calc(100vw - 24px);
	}
	.selector-panel {
		display: flex;
		flex-direction: column;
		min-height: 0;
		max-height: inherit;
		width: 360px;
		max-width: calc(100vw - 42px);
	}
	.models-panel {
		width: 420px;
		flex: 1;
		max-height: inherit;
	}
	.panel-heading {
		padding: 12px 12px 14px;
		display: flex;
		flex-direction: column;
		gap: 3px;
	}
	.panel-heading strong {
		font-size: 15px;
		font-weight: 600;
	}
	.panel-heading small {
		font-size: 12px;
		color: #a9bdd0;
	}
	.choice {
		display: flex;
		align-items: center;
		text-align: left;
		gap: 12px;
		border-radius: 11px;
		padding: 12px;
		width: 100%;
		border: 1px solid transparent;
	}
	.choice:hover {
		background: #16263a;
	}
	.choice.chosen {
		background: #0162f81c;
		border-color: #0162f85c;
	}
	.choice > span:not(.choice-symbol):not(.check) {
		flex: 1;
		min-width: 0;
	}
	.choice strong {
		display: block;
		font-size: 13px;
		font-weight: 600;
		overflow-wrap: anywhere;
	}
	.choice small {
		display: block;
		color: #a9bdd0;
		font-size: 11px;
		margin-top: 3px;
		line-height: 1.5;
	}
	.choice:disabled {
		opacity: 0.4;
	}
	.check {
		color: #59e0f3;
		width: 18px;
		flex: none;
	}
	.model-search {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 0 8px 10px;
		padding: 10px 12px;
		background: #080d17;
		border: 1px solid #2a3b50;
		border-radius: 11px;
	}
	.model-search span {
		font-size: 20px;
		color: #a9bdd0;
	}
	.model-search input {
		background: transparent;
		outline: none;
		width: 100%;
		font-size: 13px;
	}
	.provider-filters {
		display: flex;
		gap: 5px;
		flex-wrap: wrap;
		padding: 0 8px 10px;
	}
	.provider-filters button {
		font-size: 10px;
		border: 1px solid #2a3b50;
		border-radius: 20px;
		padding: 4px 9px;
		color: #a9bdd0;
	}
	.provider-filters .chosen {
		color: #59e0f3;
		border-color: #50667e;
		background: #1a2b3d;
	}
	.model-list {
		flex: 1 1 auto;
		min-height: 0;
		max-height: min(350px, 48dvh);
		overflow-x: hidden;
		overflow: auto;
		overscroll-behavior: contain;
	}
	.panel-heading,
	.model-search,
	.provider-filters,
	.panel-footer {
		flex-shrink: 0;
	}
	.choice small {
		overflow-wrap: anywhere;
	}
	.panel-footer {
		padding: 10px 12px 3px;
		border-top: 1px solid #2a3b50;
		font-size: 10px;
		color: #a9bdd0;
		margin-top: 6px;
	}
	.empty-results {
		padding: 22px 12px;
		font-size: 13px;
		color: #a9bdd0;
	}
	.lunvri-search {
		padding: 10px;
		border: 1px solid #2a3b50;
		border-radius: 12px;
		color: #a9bdd0;
		flex-shrink: 0;
	}
	.lunvri-search.active {
		background: #0162f826;
		color: #59e0f3;
		border-color: #0162f85c;
	}
	.lunvri-search:disabled {
		opacity: 0.4;
	}
	.lunvri-cost {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 11px;
		color: #e7b66f;
		padding-top: 5px;
	}
	@media (max-width: 600px) {
		.lunvri-controls {
			gap: 5px;
		}
		.selector {
			padding: 7px 8px;
			gap: 6px;
			border-radius: 11px;
		}
		.mode-trigger {
			min-width: 100px;
		}
		.model-trigger {
			width: clamp(105px, 35vw, 185px);
		}
		.mode-symbol {
			display: none;
		}
		.trigger-copy small {
			font-size: 9px;
		}
		.trigger-copy strong {
			font-size: 12px;
		}
		.lunvri-search {
			padding: 7px;
		}
	}
</style>
