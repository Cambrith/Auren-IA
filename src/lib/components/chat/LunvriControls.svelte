<script lang="ts">
	import { models } from '$lib/stores';
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
	$: cavrenModels = $models.filter((model) => model.id.startsWith('cavren:'));
	$: selected = cavrenModels.find((model) => model.id === selectedModels[0]);
	$: selectedInfo = (selected as any)?.cavren;
	let modelSearch = '';
	let showMode = false;
	let showModel = false;
	let providerFilter = 'Todos';
	$: providers = [
		...new Set(cavrenModels.map((model) => (model as any).cavren?.provider).filter(Boolean))
	].sort();
	$: visibleModels = cavrenModels.filter(
		(model) =>
			(providerFilter === 'Todos' || (model as any).cavren?.provider === providerFilter) &&
			((model as any).cavren?.label ?? model.name)
				.toLocaleLowerCase()
				.includes(modelSearch.toLocaleLowerCase())
	);
	function chooseModel(model) {
		selectedModels = [model.id];
		update({ billing_confirmed: false, image_generation: model.cavren?.image_only === true });
		showModel = false;
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

<div class="lunvri-controls no-drag" aria-label="Configurações da Lunvri">
	<Dropdown bind:show={showMode} contentClass="lunvri-selector-popover" sideOffset={10}>
		<button
			type="button"
			class="selector mode-trigger"
			aria-label="Modo da Lunvri"
			aria-expanded={showMode}
			{disabled}
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
			<span class="trigger-copy"><small>Modo de conversa</small><strong>{mode.name}</strong></span>
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
	<Dropdown bind:show={showModel} contentClass="lunvri-selector-popover" sideOffset={10}>
		<button
			type="button"
			class="selector model-trigger"
			aria-label="Modelo da Lunvri"
			aria-expanded={showModel}
			{disabled}
		>
			<span class="connection-dot" class:cost={possibleCost} aria-hidden="true"></span>
			<span class="trigger-copy"
				><small>{selectedInfo?.provider ?? 'Escolha automática'}</small><strong
					>{selectedInfo?.label?.replace(/ · [^·]+$/, '') ?? 'Automático'}</strong
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
				<strong>Escolha o modelo</strong><small>O modo e o modelo são independentes.</small>
			</div>
			<div class="model-search">
				<span aria-hidden="true">⌕</span><input
					type="search"
					aria-label="Filtrar modelos"
					placeholder="Buscar nome ou provedor…"
					bind:value={modelSearch}
				/>
			</div>
			<div class="provider-filters" aria-label="Filtrar por provedor">
				{#each ['Todos', ...providers] as provider}
					<button
						type="button"
						class:chosen={providerFilter === provider}
						aria-pressed={providerFilter === provider}
						on:click={() => (providerFilter = provider)}>{provider}</button
					>
				{/each}
			</div>
			<div class="model-list">
				{#each visibleModels as item}
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
							><strong>{((item as any).cavren?.label ?? item.name).replace(/ · [^·]+$/, '')}</strong
							><small
								>{(item as any).cavren?.provider ?? 'Seleção inteligente'} · {(item as any).cavren
									?.price_kind === 'free'
									? 'Gratuito / cota gratuita'
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
			<div class="panel-footer">{visibleModels.length} opções · {support}</div>
		</div>
	</Dropdown>
	<button
		type="button"
		class:active={options.web_search}
		class="lunvri-search"
		aria-label="Pesquisar na web"
		aria-pressed={options.web_search}
		title="Pesquisar na web com a Lunvri"
		{disabled}
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
		title={selectedInfo?.capabilities?.image_generation
			? 'Gerar uma imagem com o modelo selecionado'
			: 'Escolha um modelo com suporte a geração de imagens'}
		disabled={disabled || !selectedInfo?.capabilities?.image_generation}
		on:click={() =>
			update({ image_generation: selectedInfo?.image_only === true || !options.image_generation })}
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
	.lunvri-controls {
		display: flex;
		align-items: center;
		gap: 8px;
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
		color: #f4faff;
		max-width: calc(100vw - 24px);
	}
	.selector-panel {
		width: 360px;
		max-width: calc(100vw - 42px);
	}
	.models-panel {
		width: 440px;
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
		max-height: min(350px, 45dvh);
		overflow: auto;
		overscroll-behavior: contain;
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
