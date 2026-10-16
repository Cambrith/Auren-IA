<script lang="ts">
	import { models, config } from '$lib/stores';
	import { onMount } from 'svelte';
	import { canSelectImageWithoutPayment, compareProviders, matchesModelSearch } from '$lib/utils/imageSelection';
	import AurenProviderBadge from '$lib/components/common/AurenProviderBadge.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import { aurenRequest, type AurenState, type AurenModel } from '$lib/apis/auren';
	let preferredImage = '';
	import { taskProfiles, modelCardWidth } from '$lib/utils/aurenProfiles';
	import { changeTask, changeAurenTask, activeTask, type AurenOptions } from '$lib/utils/aurenTask';
	onMount(() => {
		const updatePreferred = (event: Event) =>
			(preferredImage = (event as CustomEvent<string>).detail);
		window.addEventListener('auren-image-preferences', updatePreferred);
		(async () => {
			if ($config?.auren?.local) {
				try {
					const state = await aurenRequest<AurenState>('state');
					preferredImage = state.preferences.image_model_id ?? '';
					if (state.tasks?.length) tasks = state.tasks.map((task) => ({ ...task, symbol: '' }));
				} catch {}
			}
		})();
		return () => window.removeEventListener('auren-image-preferences', updatePreferred);
	});
	import AurenChoiceIcon from './AurenChoiceIcon.svelte';
	import AurenChoiceList from './AurenChoiceList.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';

	export let selectedModels = ['cavren:auto'];
	export let options: AurenOptions = {
		mode_id: 'ether',
		web_search: false,
		billing_confirmed: false,
		image_generation: false
	};
	export let disabled = false;
	export let onChange: (value: typeof options) => void = () => {};

	const providerNames: Record<string, string> = {
		openai: 'OpenAI',
		deepseek: 'DeepSeek',
		huggingface: 'Hugging Face',
		xai: 'xAI',
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
	let showTask = false;
	let showMode = false;
	let tasks: {
		id: string;
		name: string;
		symbol: string;
		description: string;
		model_ids?: string[];
	}[] = [
		{ id: 'auto', name: 'Automática', symbol: '', description: 'Detectar a intenção entre tarefas gratuitas verificadas.' },
		{
			id: 'chat',
			name: 'Conversar',
			symbol: '◌',
			description: 'Ideias, perguntas, documentos e código.'
		},
		{
			id: 'image',
			name: 'Gerar imagens',
			symbol: '▧',
			description: 'Criar imagens com um gerador compatível.'
		}
	];
	$: task = tasks.find((item) => item.id === activeTask(options)) ?? tasks[0];
	let showModel = false;
	$: kindFilter =
		activeTask(options) === 'auto' ? 'all' : options.image_generation ? 'image' : 'chat';
	$: profileDefinition = taskProfiles(activeTask(options));
	$: profiles = profileDefinition.profiles;
	$: activeProfile =
		activeTask(options) === 'auto' ? 'auto' : activeTask(options) === 'speech'
			? 'pt-BR'
			: activeTask(options) === 'transcribe'
				? (options.transcribe_language ?? 'auto')
				: options.image_generation
					? (options.image_profile ?? 'balanced')
					: options.mode_id;
	$: visibleModels = cavrenModels
		.filter(
			(model) =>
				model.id !== 'cavren:auto' &&
				!(activeTask(options) === 'transcribe' && (options.transcribe_language ?? 'auto') === 'auto' && (model as any).cavren?.provider === 'cohere') &&
				(!['code', 'documents', 'research', 'transcribe', 'speech'].includes(activeTask(options)) ||
					task.model_ids?.includes(model.id)) &&
				(kindFilter === 'all'
					? ((model as any).cavren?.validation?.free_verified ||
						(model as AurenModel).cavren?.price_kind === 'paid' ||
						(model as AurenModel).cavren?.provider === 'huggingface') &&
						(!(model as any).cavren?.image_only || canSelectImageWithoutPayment(model))
					: kindFilter === 'chat'
						? activeTask(options) === 'speech'
							? (model as any).cavren?.task_operations?.includes('speech')
							: activeTask(options) === 'transcribe'
								? (model as any).cavren?.task_operations?.includes('transcribe')
								: !(model as any).cavren?.image_only &&
									!(model as any).cavren?.task_operations?.length
						: canSelectImageWithoutPayment(model)) &&
				matchesModelSearch(
					`${(model as any).cavren?.label ?? model.name} ${providerName((model as any).cavren?.provider)} ${model.id}`,
					modelSearch
				)
		)
		.sort(
			(a, b) =>
				compareProviders(providerName(a.cavren?.provider), providerName(b.cavren?.provider)) ||
				compareProviders(a.cavren?.label ?? a.name, b.cavren?.label ?? b.name)
		);
	// A restored paid choice cannot bypass the image composer's filtered list.
	$: ensureImageChoice(options.image_generation, selected);
	function ensureImageChoice(imageTask: boolean, model: (typeof $models)[number] | undefined) {
		if (imageTask && model && model.id !== 'cavren:auto' && !canSelectImageWithoutPayment(model)) {
			selectedModels = ['cavren:auto'];
			update({ billing_confirmed: false });
		}
	}
	function chooseModel(model: (typeof $models)[number] | undefined) {
		if (!model || model.cavren?.available === false) return;
		if (options.image_generation && model.id !== 'cavren:auto' && !canSelectImageWithoutPayment(model)) return;
		selectedModels = [model.id];
		update({ billing_confirmed: false });
		showModel = false;
	}
	function toggleImages() {
		const transition = changeTask(options, selectedModels[0], !options.image_generation);
		selectedModels = [transition.model];
		onChange(transition.options);
		modelSearch = '';
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
		choices[next].focus({ preventScroll: true });
		const list = choices[next].closest('.auren-choice-list');
		if (list) {
			const box = list.getBoundingClientRect(), item = choices[next].getBoundingClientRect();
			if (item.top < box.top) list.scrollTop -= box.top - item.top;
			else if (item.bottom > box.bottom) list.scrollTop += item.bottom - box.bottom;
		}
	}
	$: possibleCost = selectedInfo?.price_kind && selectedInfo.price_kind !== 'free';
	$: mode = profiles.find((mode) => mode.id === activeProfile) ?? profiles[0];

	function update(patch: Partial<typeof options>) {
		onChange({ ...options, ...patch });
	}
</script>

<div class="lunvri-controls no-drag" aria-label="Configurações da Auren">
	<Dropdown
		bind:show={showTask}
		contentClass="lunvri-selector-popover"
		sideOffset={8}
		visualViewportAware
		maxHeight="min(26rem, calc(100dvh - 24px))"
	>
		<button
			type="button"
			class="selector task-trigger"
			aria-label="Tarefa da Auren"
			aria-expanded={showTask}
			{disabled}
		>
			<span class="mode-symbol" aria-hidden="true"><AurenChoiceIcon kind={task.id} /></span>
			<span class="trigger-copy"><small>Tarefa</small><strong>{task.name}</strong></span><span
				class="chevron"
				aria-hidden="true">⌄</span
			>
		</button>
		<div
			slot="content"
			class="selector-panel modes-panel"
			role="menu"
			tabindex="-1"
			aria-label="Tarefas da Auren"
			on:keydown={navigateChoices}
		>
			<div class="panel-heading">
				<strong>O que vamos fazer?</strong><small>Controles próprios para cada tarefa.</small>
			</div>
			<AurenChoiceList>
			{#each tasks as item}<button
					type="button"
					class="choice mode-choice"
					class:chosen={item.id === task.id}
					role="menuitemradio"
					aria-checked={item.id === task.id}
					data-choice
					on:click={() => {
						if (item.id !== task.id) {
							const transition = changeAurenTask(options, selectedModels[0], item.id);
							selectedModels = [transition.model];
							onChange(transition.options);
							modelSearch = '';
						}
						showTask = false;
					}}
				>
					<span class="choice-symbol" aria-hidden="true"><AurenChoiceIcon kind={item.id} /></span
					><span><strong>{item.name}</strong><small>{item.description}</small></span><span
						class="check"
						aria-hidden="true">{item.id === task.id ? '✓' : ''}</span
					>
				</button>{/each}
			</AurenChoiceList>
		</div>
	</Dropdown>

	<Dropdown
		bind:show={showMode}
		contentClass="lunvri-selector-popover"
		sideOffset={8}
		visualViewportAware
		maxHeight="min(26rem, calc(100dvh - 24px))"
	>
		<button
			type="button"
			class="selector mode-trigger"
			aria-label={activeTask(options) === 'speech'
				? 'Perfil de voz'
				: activeTask(options) === 'transcribe'
					? 'Idioma da transcrição'
					: options.image_generation
						? 'Perfil de imagem da Auren'
						: 'Modo da Auren'}
			aria-expanded={showMode}
			{disabled}
		>
			<span class="mode-symbol" aria-hidden="true"><AurenChoiceIcon kind={mode.id} task={activeTask(options)} /></span>
			<span class="trigger-copy"
				><small>{profileDefinition.caption}</small><strong>{activeTask(options) === 'auto' ? 'Automático' : mode.name}</strong
				></span
			>
			<span class="chevron" aria-hidden="true">⌄</span>
		</button>
		<div
			slot="content"
			class="selector-panel modes-panel"
			role="menu"
			tabindex="-1"
			aria-label={options.image_generation
				? 'Perfis de imagem'
				: activeTask(options) === 'transcribe'
					? 'Idiomas da transcrição'
					: activeTask(options) === 'speech'
						? 'Perfil de voz'
						: 'Modos de conversa'}
			on:keydown={navigateChoices}
		>
			<div class="panel-heading">
				<strong>Como vamos trabalhar?</strong><small>{activeTask(options) === 'auto' ? 'Escolha uma tarefa para liberar os perfis manuais.' : 'Escolha o perfil desta tarefa.'}</small>
			</div>
			<AurenChoiceList>
			{#each profiles as item}
				<button
					type="button"
					class="choice mode-choice"
					class:chosen={item.id === activeProfile}
					role="menuitemradio"
					aria-checked={item.id === activeProfile}
					data-choice
					on:click={() => {
						if (activeTask(options) === 'auto' || activeTask(options) === 'speech') {
							showMode = false;
							return;
						}
						update(
							activeTask(options) === 'transcribe'
								? { transcribe_language: item.id }
								: options.image_generation
									? { image_profile: item.id, image_profile_manual: true }
									: { mode_id: item.id, mode_manual: true }
						);
						showMode = false;
					}}
				>
					<span class="choice-symbol" aria-hidden="true"><AurenChoiceIcon kind={item.id} task={activeTask(options)} /></span>
					<span><strong>{item.name}</strong><small>{item.description}</small></span>
					<span class="check" aria-hidden="true">{item.id === activeProfile ? '✓' : ''}</span>
				</button>
			{/each}
			</AurenChoiceList>
		</div>
	</Dropdown>
	<Dropdown
		bind:show={showModel}
		contentClass="lunvri-selector-popover"
		sideOffset={8}
		visualViewportAware
		maxHeight="min(32rem, calc(100dvh - 24px))"
	>
		<button
			type="button"
			class="selector model-trigger"
			class:automatic={selectedModels[0] === 'cavren:auto'}
			style:--model-card-width={`${modelCardWidth(selectedInfo?.label ?? selected?.name ?? '', selectedModels[0] === 'cavren:auto')}px`}
			title={selectedModels[0] === 'cavren:auto' ? 'Modelo automático' : `${selectedInfo?.label ?? selected?.name} · ${providerName(selectedInfo?.provider)}`}
			aria-label="Modelo da Auren"
			aria-expanded={showModel}
			{disabled}
		>
			{#if selectedModels[0] === 'cavren:auto'}
				<span class="mode-symbol" aria-hidden="true"><AurenChoiceIcon kind="auto" /></span><span class="trigger-copy"><small>Modelo</small><strong class="automatic-label">Automático</strong></span>
			{:else}
				<span class="mode-symbol model-state" aria-hidden="true">
					<AurenProviderBadge compact provider={selectedInfo?.provider} name={providerName(selectedInfo?.provider)} modelId={selectedModels[0]} modelName={selected?.name} />
					<span class="connection-dot" class:cost={possibleCost}></span>
				</span>
				<span class="trigger-copy"
					><small>Modelo</small><strong
						>{selectedInfo?.label ?? selected?.name}</strong
					></span
				>
			{/if}

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
				<strong>{kindFilter === 'image' ? 'Escolha o gerador' : 'Escolha o modelo'}</strong><small
					>{kindFilter === 'image'
						? 'Geração sem pagamento, com a fila comunitária do AI Horde.'
						: 'Alternativas gratuitas quando houver falhas ou limites.'}</small
				>
			</div>
			<div class="model-search">
				<span aria-hidden="true"><Search className="size-4" /></span><input
					type="search"
					aria-label="Filtrar modelos"
					placeholder="Buscar nome ou provedor…"
					bind:value={modelSearch}
				/>
				{#if modelSearch}<button type="button" class="clear-search" aria-label="Limpar busca" on:click={() => (modelSearch = '')}>×</button>{/if}
			</div>
			<button
				type="button"
				class="choice automatic-choice"
				class:chosen={selectedModels[0] === 'cavren:auto'}
				role="menuitemradio"
				aria-checked={selectedModels[0] === 'cavren:auto'}
				data-choice
				on:click={() => chooseModel(cavrenModels.find((m) => m.id === 'cavren:auto'))}
				>
				<span class="choice-symbol" aria-hidden="true"><AurenChoiceIcon kind="auto" /></span>
				<span><strong>Automático</strong><small>Alternativas gratuitas compatíveis com o perfil.</small></span>
				<span class="check" aria-hidden="true">{selectedModels[0] === 'cavren:auto' ? '✓' : ''}</span>
			</button
			>
			<AurenChoiceList>
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
						disabled={(item as AurenModel).cavren?.available === false}
						data-choice
						on:click={() => chooseModel(item)}
					>
						<AurenProviderBadge provider={(item as any).cavren?.provider} name={providerName((item as any).cavren?.provider)} modelId={item.id} modelName={item.name} />
						<span
							><strong>{(item as any).cavren?.label ?? item.name}{#if kindFilter === 'image' && item.id === preferredImage}<span class="default-tag">Padrão</span>{/if}</strong><small
								>{#if kindFilter === 'image'}Fila comunitária · usa Kudos{:else}{providerName((item as any).cavren?.provider) ?? 'Seleção inteligente'} · {(
									item as any
								).cavren?.price_kind === 'free'
									? (item as any).cavren?.validation?.free_verified
										? `Gratuito com limites · testado em ${new Date((item as any).cavren.validation.date).toLocaleDateString('pt-BR')}`
										: (item as any).cavren?.validation?.status === 'failed'
											? 'Não concluiu o teste'
											: (item as any).cavren?.validation?.status === 'working'
												? 'Validação incompleta'
												: 'Gratuidade não testada'
									: (item as AurenModel).cavren?.available === false ? 'Reservado · chave e saldo necessários' : (item as AurenModel).cavren?.price_kind === 'paid' ? 'Pago · exige saldo e confirmação' : 'Custo a confirmar'}{(item as any).cavren?.capabilities?.vision
									? ' · Visão'
									: ''}{(item as any).cavren?.capabilities?.image_generation
									? ' · Gera imagens'
									: ''}{/if}</small
							></span
						>
						<span class="check" aria-hidden="true">{item.id === selectedModels[0] ? '✓' : ''}</span>
					</button>
				{:else}
					<p class="empty-results">Nenhum modelo encontrado. Tente outro nome ou provedor.</p>
				{/each}
			</AurenChoiceList>
			<div class="panel-footer"><span>{visibleModels.length} {visibleModels.length === 1 ? 'modelo' : 'modelos'}</span><span>{kindFilter === 'image' ? 'Catálogo completo nas configurações' : 'Automático usa gratuitos verificados'}</span></div>
		</div>
	</Dropdown>
</div>
{#if options.image_generation}
	<div class="image-actions no-drag">
		{#if selectedModels[0] !== 'cavren:auto'}
			<label class="lunvri-cost"
				><input
					type="checkbox"
					{disabled}
					checked={options.image_fallback !== false}
					on:change={(event) => update({ image_fallback: event.currentTarget.checked })}
				/>Permitir alternativas gratuitas após falha (a rota efetiva será informada).</label
			>
		{/if}
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
	.image-actions {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 8px 16px;
		padding: 6px 0;
	}
	.image-actions button {
		border: 1px solid #2a3b50;
		border-radius: 8px;
		padding: 6px 10px;
		font-size: 11px;
		color: #a9bdd0;
	}
	.image-actions button:hover {
		background: #16263a;
		color: #f4faff;
	}
	.image-actions .lunvri-cost { padding-top: 0; }
	.automatic-choice { margin-bottom: 8px; min-height: 56px; }
	.model-choice { min-height: 58px; }
	.default-tag {
		display: inline-block;
		margin-left: 8px;
		padding: 1px 6px;
		border-radius: 5px;
		background: #21d4fb14;
		color: #59e0f3;
		font-size: 10px;
		font-weight: 500;
	}
	.choice:focus-visible, .image-actions button:focus-visible, .clear-search:focus-visible {
		outline: 2px solid #21d4fb;
		outline-offset: -2px;
	}
	.model-search:focus-within {
		border-color: #0162f8;
		box-shadow: 0 0 0 2px #0162f81c;
	}
	.clear-search {
		flex: none;
		width: 24px;
		height: 24px;
		border-radius: 6px;
		font-size: 20px;
		color: #a9bdd0;
	}
	.model-search input::-webkit-search-cancel-button { -webkit-appearance: none; }
	.provider-heading {
		padding: 8px 9px 4px;
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
		min-height: 54px;
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
	.task-trigger,
	.mode-trigger,
	.model-trigger {
		width: 176px;
		flex: 0 0 auto;
	}
	.model-trigger { width: var(--model-card-width, 176px); }
	.trigger-copy {
		display: flex;
		flex-direction: column;
		min-width: 0;
		flex: 1;
	}
	.trigger-copy small {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		font-size: 10px;
		color: #a9bdd0;
		line-height: 15px;
	}
	.trigger-copy strong,
	.automatic-label {
		font-size: 13px;
		font-weight: 600;
		line-height: 18px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.mode-symbol,
	.choice-symbol {
		flex: none;
		font-size: 24px;
		color: #59e0f3;
		line-height: 1;
	}
	.chevron {
		color: #a9bdd0;
		font-size: 18px;
	}
	.model-state {
		position: relative;
		width: 20px;
		height: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.connection-dot {
		position: absolute;
		right: -3px;
		bottom: -2px;
		width: 6px;
		height: 6px;
		border: 1px solid #101c2c;
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
		padding: 6px;
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
		width: 330px;
		flex: 1 1 auto;
		max-width: calc(100vw - 42px);
	}
	.models-panel {
		width: 420px;
		flex: 1;
		max-height: inherit;
	}
	.panel-heading {
		padding: 8px 9px 10px;
		display: flex;
		flex-direction: column;
		gap: 3px;
	}
	.panel-heading strong {
		font-size: 13px;
		font-weight: 600;
	}
	.panel-heading small {
		font-size: 11px;
		color: #a9bdd0;
	}
	.choice {
		font-size: 13px;
		line-height: 18px;
		display: flex;
		align-items: center;
		text-align: left;
		gap: 9px;
		border-radius: 10px;
		padding: 7px 9px;
		min-height: 42px;
		flex-shrink: 0;
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
		line-height: 1.35;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
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
		padding: 7px 9px;
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
	.panel-heading,
	.model-search,
	.panel-footer {
		flex-shrink: 0;
	}
	.choice small {
		overflow-wrap: anywhere;
	}
	.panel-footer {
		padding: 10px 12px 3px;
		border-top: 1px solid #2a3b50;
		display: flex;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 4px 12px;
		font-size: 10px;
		color: #a9bdd0;
		margin-top: 6px;
	}
	.empty-results {
		padding: 22px 12px;
		font-size: 13px;
		color: #a9bdd0;
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
		.task-trigger, .mode-trigger, .model-trigger {
			width: min(176px, calc((100vw - 60px) / 3));
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
	}
</style>
