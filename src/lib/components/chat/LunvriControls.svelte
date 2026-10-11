<script lang="ts">
	import { models } from '$lib/stores';

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
	$: visibleModels = cavrenModels.filter(
		(model) =>
			model.id === selectedModels[0] ||
			model.id === 'cavren:auto' ||
			((model as any).cavren?.label ?? model.name)
				.toLocaleLowerCase()
				.includes(modelSearch.toLocaleLowerCase())
	);
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
	<label class="lunvri-field">
		<span>Modo</span>
		<select
			aria-label="Modo da Lunvri"
			title={mode.description}
			value={options.mode_id}
			{disabled}
			on:change={(event) => update({ mode_id: event.currentTarget.value })}
		>
			{#each modes as mode}
				<option value={mode.id}>{mode.name}</option>
			{/each}
		</select>
	</label>
	<label class="lunvri-field lunvri-model">
		<span>Modelo</span>
		<select
			aria-label="Modelo da Lunvri"
			value={selectedModels[0]}
			{disabled}
			on:change={(event) => {
				selectedModels = [event.currentTarget.value];
				const next = cavrenModels.find((model) => model.id === event.currentTarget.value) as any;
				update({ billing_confirmed: false, image_generation: next?.cavren?.image_only === true });
			}}
		>
			{#each visibleModels as model}
				<option value={model.id} disabled={(model as any).cavren?.available === false}>
					{(model as any).cavren?.label ?? model.name}{(model as any).cavren?.available === false
						? ' · sem conexão'
						: ''}
				</option>
			{/each}
		</select>
		<input
			type="search"
			aria-label="Filtrar modelos"
			placeholder="Buscar modelo…"
			bind:value={modelSearch}
			{disabled}
		/>
		<small title={support}>{support}</small>
	</label>
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
		gap: 12px;
		max-width: 100%;
	}
	.lunvri-field {
		display: flex;
		flex-direction: column;
		min-width: 80px;
	}
	.lunvri-field > span {
		font-size: 10px;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: #a9bdd0;
	}
	.lunvri-field select {
		background: transparent;
		font-size: 13px;
		line-height: 22px;
		font-weight: 500;
		cursor: pointer;
		border: 0;
		max-width: 100%;
		padding-right: 14px;
	}
	.lunvri-field select:focus-visible,
	.lunvri-search:focus-visible {
		outline: 2px solid #59e0f3;
		outline-offset: 3px;
		border-radius: 6px;
	}
	.lunvri-field option {
		background: #fff;
		color: #222;
	}
	:global(.dark) .lunvri-field option {
		background: #0d1727;
		color: #f4faff;
	}
	.lunvri-model {
		max-width: 280px;
		min-width: 0;
		flex: 1;
	}
	.lunvri-model input {
		min-width: 0;
		width: 100%;
		background: #121e2d;
		border: 1px solid #2a3b50;
		border-radius: 6px;
		padding: 2px 6px;
		font-size: 11px;
		color: #f4faff;
	}
	.lunvri-model small {
		font-size: 9px;
		color: #a9bdd0;
		padding-top: 3px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.lunvri-search:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.lunvri-search {
		padding: 8px;
		border-radius: 10px;
		color: #a9bdd0;
		flex-shrink: 0;
	}
	.lunvri-search.active {
		background: #1a2b3d;
		color: #59e0f3;
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
			gap: 6px;
		}
		.lunvri-model {
			max-width: 155px;
		}
		.lunvri-field {
			min-width: 70px;
		}
		.lunvri-field select {
			font-size: 12px;
		}
		.lunvri-search {
			padding: 5px;
		}
	}
</style>
