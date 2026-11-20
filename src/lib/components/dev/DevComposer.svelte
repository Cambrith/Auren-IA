<script lang="ts">
	import { createEventDispatcher, onMount, tick } from 'svelte';
	import type { DevFileEntry, DevModeInfo, DevModelInfo } from '$lib/apis/dev';
	import AurenProviderBadge from '$lib/components/common/AurenProviderBadge.svelte';
	import DevContextRing from './DevContextRing.svelte';
	import DevToolIcon from './DevToolIcon.svelte';
	import MinervaOwlMascot from './MinervaOwlMascot.svelte';
	import {
		SLASH_COMMANDS,
		type EffortLevel,
		type PermissionMode,
		type SlashCommandItem,
		type SlashCommandOption
	} from './types';

	export let value = '';
	export let isStreaming = false;
	export let isStartStage = false;
	export let mascotState: 'idle' | 'listening' | 'happy' = 'idle';
	export let modes: DevModeInfo[] = [];
	export let models: DevModelInfo[] = [];
	export let activeMode: string | null = 'harmonia';
	export let activeModel = '';
	export let activeModelName = '';
	export let permissionMode: PermissionMode = 'bypassPermissions';
	export let effort: EffortLevel = '';
	export let estTokens = 0;
	export let attachedFiles: string[] = [];
	export let extraDirs: string[] = [];
	export let queuedPrompt: string | null = null;
	export let projectFiles: DevFileEntry[] = [];
	export let cwd = '';
	export let gitBranch = '';
	export let gitDirtyCount = 0;
	export let fccOnline = false;

	const dispatch = createEventDispatcher<{
		send: string;
		queue: string;
		cancelQueue: void;
		stop: void;
		selectMode: string;
		selectModel: string;
		setPermission: PermissionMode;
		cyclePermission: void;
		setEffort: EffortLevel;
		openDirPicker: void;
		clearCwd: void;
		addExtraDir: void;
		removeExtraDir: string;
		removeAttachment: string;
		addAttachment: string;
		slashCommand: { name: string; raw: string };
		queryFiles: string;
		compact: void;
		copyBranch: void;
	}>();

	let textareaEl: HTMLTextAreaElement | null = null;
	let manualSearchInputEl: HTMLInputElement | null = null;
	let showPlusMenu = false;
	let showModelMenu = false;
	let showManualModels = false;
	let showPermMenu = false;
	let showEffortMenu = false;
	let modelSearch = '';

	// Slash & @-mention popovers
	let slashIndex = 0;
	let slashOptionIndex = 0;
	let mentionIndex = 0;
	let mentionTokenStart = -1;
	let mentionQuery = '';

	$: folderShort = cwd ? cwd.split('/').filter(Boolean).pop() || cwd : 'PC inteiro';
	$: activeModeObj = modes.find((m) => m.id === activeMode) ?? null;

	$: isSlashOpen =
		value.startsWith('/') && !value.includes('\n') && !value.slice(1).includes(' ');
	$: slashMatches = isSlashOpen ? filterSlash(value) : [];
	$: if (slashIndex >= slashMatches.length) slashIndex = 0;

	$: slashArgContext = (() => {
		if (!value.startsWith('/') || value.includes('\n') || !value.slice(1).includes(' ')) {
			return null;
		}
		const spaceIdx = value.indexOf(' ');
		const cmdWord = value.slice(0, spaceIdx).toLowerCase();
		const argPart = value.slice(spaceIdx + 1).trim().toLowerCase();
		const cmd = SLASH_COMMANDS.find(
			(c) => (c.name === cmdWord || (c.aliases || []).includes(cmdWord)) && (c.options?.length ?? 0) > 0
		);
		if (!cmd || !cmd.options) return null;
		const matches = argPart
			? cmd.options.filter(
					(o) =>
						o.value.toLowerCase().includes(argPart) ||
						o.label.toLowerCase().includes(argPart)
				)
			: cmd.options;
		return matches.length > 0 ? { cmd, options: matches } : null;
	})();
	$: isSlashOptionOpen = Boolean(slashArgContext);
	$: if (slashArgContext && slashOptionIndex >= slashArgContext.options.length) {
		slashOptionIndex = 0;
	}

	$: isMentionOpen = mentionTokenStart >= 0 && !isSlashOpen && !isSlashOptionOpen;
	$: mentionMatches = isMentionOpen ? filterMentions(projectFiles, mentionQuery) : [];
	$: if (mentionIndex >= mentionMatches.length) mentionIndex = 0;

	$: filteredModels = (() => {
		const q = modelSearch.trim().toLowerCase();
		if (!q) return models;
		return models.filter(
			(m) =>
				m.name.toLowerCase().includes(q) ||
				m.id.toLowerCase().includes(q) ||
				m.provider_name.toLowerCase().includes(q)
		);
	})();

	const PERM_META: Record<
		PermissionMode,
		{ label: string; short: string; desc: string; dot: string }
	> = {
		plan: {
			label: 'Planejar',
			short: 'Planejar',
			desc: 'Somente leitura — analisa e propõe plano antes de editar',
			dot: 'bg-amber-400'
		},
		acceptEdits: {
			label: 'Auto-edição',
			short: 'Auto-edição',
			desc: 'Edita arquivos automaticamente e confirma comandos críticos',
			dot: 'bg-sky-400'
		},
		bypassPermissions: {
			label: 'Acesso total',
			short: 'Acesso total',
			desc: 'Acesso livre aos seus arquivos e comandos, sem pedir permissões',
			dot: 'bg-emerald-400'
		}
	};

	const EFFORT_META: Record<EffortLevel, { label: string; short: string; bars: number }> = {
		'': { label: 'Esforço padrão', short: 'Padrão', bars: 2 },
		low: { label: 'Esforço baixo', short: 'Baixo', bars: 1 },
		medium: { label: 'Esforço médio', short: 'Médio', bars: 2 },
		high: { label: 'Esforço alto', short: 'Alto', bars: 3 }
	};

	function filterSlash(raw: string): SlashCommandItem[] {
		const q = raw.trim().toLowerCase();
		if (q === '/') return SLASH_COMMANDS;
		return SLASH_COMMANDS.filter(
			(c) =>
				c.name.startsWith(q) ||
				(c.aliases || []).some((a) => a.startsWith(q)) ||
				c.description.toLowerCase().includes(q.slice(1))
		);
	}

	function filterMentions(files: DevFileEntry[], q: string): DevFileEntry[] {
		const low = q.trim().toLowerCase();
		if (!low) return files.slice(0, 12);
		return files
			.filter((f) => f.path.toLowerCase().includes(low))
			.sort((a, b) => {
				const aName = a.name.toLowerCase().startsWith(low) ? 0 : 1;
				const bName = b.name.toLowerCase().startsWith(low) ? 0 : 1;
				return aName - bName || a.path.length - b.path.length;
			})
			.slice(0, 12);
	}

	function closeAllMenus() {
		showPlusMenu = false;
		showModelMenu = false;
		showManualModels = false;
		showPermMenu = false;
		showEffortMenu = false;
	}

	async function openManualModelsSection() {
		showManualModels = true;
		modelSearch = '';
		await tick();
		manualSearchInputEl?.focus();
	}

	function autoResize() {
		if (!textareaEl) return;
		textareaEl.style.height = 'auto';
		const maxH = isStartStage ? 180 : 156;
		textareaEl.style.height = `${Math.min(maxH, Math.max(44, textareaEl.scrollHeight))}px`;
	}

	function detectMentionToken() {
		if (!textareaEl) return;
		const pos = textareaEl.selectionStart ?? value.length;
		const before = value.slice(0, pos);
		const m = before.match(/(?:^|\s)@([^\s@]*)$/);
		if (m) {
			mentionTokenStart = pos - m[1].length - 1;
			mentionQuery = m[1];
			dispatch('queryFiles', mentionQuery);
		} else {
			mentionTokenStart = -1;
			mentionQuery = '';
		}
	}

	function insertTrigger(token: '@' | '/') {
		closeAllMenus();
		if (token === '/') {
			value = '/';
		} else {
			value = value && !value.endsWith(' ') ? `${value} @` : `${value}@`;
		}
		tick().then(() => {
			autoResize();
			textareaEl?.focus();
			if (textareaEl) {
				const end = value.length;
				textareaEl.setSelectionRange(end, end);
			}
			detectMentionToken();
		});
	}

	function applyMention(filePath: string) {
		if (mentionTokenStart < 0 || !textareaEl) return;
		const pos = textareaEl.selectionStart ?? value.length;
		const before = value.slice(0, mentionTokenStart);
		const after = value.slice(pos);

		// Se o item for uma pasta terminada em '/', navega dentro dela mantendo o menu @ aberto
		if (filePath.endsWith('/')) {
			const inserted = `@${filePath}`;
			value = `${before}${inserted}${after}`;
			const nextCursor = before.length + inserted.length;
			tick().then(() => {
				autoResize();
				textareaEl?.focus();
				textareaEl?.setSelectionRange(nextCursor, nextCursor);
				detectMentionToken();
			});
			return;
		}

		value = `${before}${after}`.replace(/\s{2,}/g, ' ');
		mentionTokenStart = -1;
		mentionQuery = '';
		dispatch('addAttachment', filePath);
		tick().then(() => {
			autoResize();
			textareaEl?.focus();
		});
	}

	function applySlashOption(cmd: SlashCommandItem, opt: SlashCommandOption) {
		value = '';
		tick().then(autoResize);
		dispatch('slashCommand', { name: cmd.name, raw: `${cmd.name} ${opt.value}` });
	}

	function applySlashSelection(cmd: SlashCommandItem) {
		if ((cmd.options && cmd.options.length > 0) || (cmd.args && cmd.args.startsWith('<'))) {
			value = `${cmd.name} `;
			slashOptionIndex = 0;
			tick().then(() => {
				autoResize();
				textareaEl?.focus();
				if (textareaEl) {
					const end = value.length;
					textareaEl.setSelectionRange(end, end);
				}
			});
			return;
		}
		value = '';
		tick().then(autoResize);
		dispatch('slashCommand', { name: cmd.name, raw: cmd.name });
	}

	function submitPrompt() {
		const trimmed = value.trim();
		if (!trimmed && attachedFiles.length === 0) return;

		if (trimmed.startsWith('/')) {
			const cmdWord = trimmed.split(/\s+/)[0].toLowerCase();
			const matched = SLASH_COMMANDS.find(
				(c) => c.name === cmdWord || (c.aliases || []).includes(cmdWord)
			);
			if (matched) {
				value = '';
				tick().then(autoResize);
				dispatch('slashCommand', { name: matched.name, raw: trimmed });
				return;
			}
		}

		if (isStreaming) {
			dispatch('queue', trimmed);
			value = '';
			tick().then(autoResize);
			return;
		}

		dispatch('send', trimmed);
		value = '';
		tick().then(autoResize);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Tab' && e.shiftKey) {
			e.preventDefault();
			e.stopPropagation();
			dispatch('cyclePermission');
			return;
		}

		if (isSlashOptionOpen && slashArgContext) {
			const opts = slashArgContext.options;
			if (e.key === 'ArrowDown') {
				e.preventDefault();
				slashOptionIndex = (slashOptionIndex + 1) % opts.length;
				return;
			}
			if (e.key === 'ArrowUp') {
				e.preventDefault();
				slashOptionIndex = (slashOptionIndex - 1 + opts.length) % opts.length;
				return;
			}
			if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) {
				e.preventDefault();
				applySlashOption(slashArgContext.cmd, opts[slashOptionIndex]);
				return;
			}
			if (e.key === 'Escape') {
				e.preventDefault();
				value = '';
				return;
			}
		}

		if (isSlashOpen && slashMatches.length > 0) {
			if (e.key === 'ArrowDown') {
				e.preventDefault();
				slashIndex = (slashIndex + 1) % slashMatches.length;
				return;
			}
			if (e.key === 'ArrowUp') {
				e.preventDefault();
				slashIndex = (slashIndex - 1 + slashMatches.length) % slashMatches.length;
				return;
			}
			if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) {
				e.preventDefault();
				applySlashSelection(slashMatches[slashIndex]);
				return;
			}
			if (e.key === 'Escape') {
				e.preventDefault();
				value = '';
				return;
			}
		}

		if (isMentionOpen) {
			if (mentionMatches.length > 0) {
				if (e.key === 'ArrowDown') {
					e.preventDefault();
					mentionIndex = (mentionIndex + 1) % mentionMatches.length;
					return;
				}
				if (e.key === 'ArrowUp') {
					e.preventDefault();
					mentionIndex = (mentionIndex - 1 + mentionMatches.length) % mentionMatches.length;
					return;
				}
				if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) {
					e.preventDefault();
					applyMention(mentionMatches[mentionIndex].path);
					return;
				}
			} else if ((e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) && mentionQuery.trim()) {
				e.preventDefault();
				applyMention(mentionQuery.trim());
				return;
			}
			if (e.key === 'Escape') {
				e.preventDefault();
				mentionTokenStart = -1;
				return;
			}
		}

		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			submitPrompt();
		}
	}

	function handleInput() {
		autoResize();
		detectMentionToken();
	}

	export function focusInput() {
		textareaEl?.focus();
	}

	export function openSlashMenu() {
		insertTrigger('/');
	}

	export function openMentionMenu() {
		insertTrigger('@');
	}

	onMount(() => {
		const onDocClick = (ev: MouseEvent) => {
			const target = ev.target as HTMLElement | null;
			if (!target?.closest('[data-dev-menu]')) {
				closeAllMenus();
			}
		};
		document.addEventListener('click', onDocClick);
		return () => document.removeEventListener('click', onDocClick);
	});
</script>

<div class="relative w-full">
	<!-- Mascote Coruja Oficial da Minerva: aparece EXCLUSIVAMENTE ao iniciar um novo chat (start-card-clawd) -->
	{#if isStartStage}
		<div class="pointer-events-none relative h-0">
			<div class="pointer-events-auto absolute right-6 -top-[98px] z-20">
				<MinervaOwlMascot state={mascotState} size={106} interactive={true} />
			</div>
		</div>
	{/if}

	<!-- Popover de Comandos Slash (/) -->
	{#if isSlashOpen && slashMatches.length > 0}
		<div
			class="absolute left-0 right-0 overflow-y-auto rounded-2xl border border-gray-200 dark:border-slate-800 bg-white/95 dark:bg-[#0f1726]/95 backdrop-blur-md shadow-2xl z-40 p-1.5 {isStartStage
				? 'top-full mt-2 max-h-[min(15rem,34vh)]'
				: 'bottom-full mb-2 max-h-72'}"
		>
			<div class="flex items-center justify-between px-2.5 py-1 text-[10.5px] font-medium text-gray-400">
				<span>Comandos Minerva Dev</span>
				<span class="font-mono text-[10px]">↑↓ navegar · Tab/↵ executar</span>
			</div>
			{#each slashMatches as cmd, idx (cmd.name)}
				<button
					type="button"
					class="flex w-full items-center justify-between gap-3 rounded-xl px-2.5 py-2 text-left transition {idx === slashIndex
						? 'bg-sky-500/12 text-sky-700 dark:text-sky-300'
						: 'hover:bg-gray-100/80 dark:hover:bg-slate-800/70 text-gray-800 dark:text-slate-200'}"
					on:mouseenter={() => (slashIndex = idx)}
					on:click={() => applySlashSelection(cmd)}
				>
					<div class="min-w-0">
						<div class="flex items-center gap-1.5">
							<span class="font-mono text-xs font-semibold text-sky-600 dark:text-sky-400">{cmd.name}</span>
							{#if cmd.args}
								<span class="font-mono text-[10.5px] text-gray-400">{cmd.args}</span>
							{/if}
						</div>
						<div class="truncate text-[11px] text-gray-500 dark:text-slate-400">{cmd.description}</div>
					</div>
					<span class="shrink-0 rounded-md bg-gray-100 dark:bg-slate-800 px-1.5 py-0.5 text-[10px] text-gray-500 dark:text-slate-400">
						{cmd.category}
					</span>
				</button>
			{/each}
		</div>
	{/if}

	<!-- Popover de Opções de Subcomando Slash (ex.: /perfil, /modo, /esforco, /pasta) -->
	{#if isSlashOptionOpen && slashArgContext}
		<div
			class="absolute left-0 right-0 overflow-y-auto rounded-2xl border border-gray-200 dark:border-slate-800 bg-white/95 dark:bg-[#0f1726]/95 backdrop-blur-md shadow-2xl z-40 p-1.5 {isStartStage
				? 'top-full mt-2 max-h-[min(15rem,34vh)]'
				: 'bottom-full mb-2 max-h-64'}"
		>
			<div class="flex items-center justify-between px-2.5 py-1 text-[10.5px] font-medium text-gray-400">
				<span>Opções para <span class="font-mono text-sky-500">{slashArgContext.cmd.name}</span></span>
				<span class="font-mono text-[10px]">↑↓ · ↵ aplicar</span>
			</div>
			{#each slashArgContext.options as opt, idx (opt.value)}
				<button
					type="button"
					class="flex w-full items-center justify-between gap-3 rounded-xl px-2.5 py-2 text-left transition {idx === slashOptionIndex
						? 'bg-sky-500/12 text-sky-700 dark:text-sky-300'
						: 'hover:bg-gray-100/80 dark:hover:bg-slate-800/70 text-gray-800 dark:text-slate-200'}"
					on:mouseenter={() => (slashOptionIndex = idx)}
					on:click={() => applySlashOption(slashArgContext.cmd, opt)}
				>
					<div class="min-w-0">
						<div class="text-xs font-medium">{opt.label}</div>
						{#if opt.description}
							<div class="truncate text-[11px] text-gray-500 dark:text-slate-400">{opt.description}</div>
						{/if}
					</div>
					<span class="shrink-0 font-mono text-[10.5px] text-sky-500/80">{opt.value}</span>
				</button>
			{/each}
		</div>
	{/if}

	<!-- Popover de Menção de Arquivos (@) -->
	{#if isMentionOpen}
		<div
			class="absolute left-0 right-0 overflow-y-auto rounded-2xl border border-gray-200 dark:border-slate-800 bg-white/95 dark:bg-[#0f1726]/95 backdrop-blur-md shadow-2xl z-40 p-1.5 {isStartStage
				? 'top-full mt-2 max-h-[min(15rem,34vh)]'
				: 'bottom-full mb-2 max-h-64'}"
		>
			<div class="flex items-center justify-between px-2.5 py-1 text-[10.5px] font-medium text-gray-400">
				<span>
					Anexar arquivo ao contexto (@{mentionQuery || (cwd ? '…' : '~/ ou /caminho')})
				</span>
				<span class="font-mono text-[10px]">↑↓ · ↵ anexar</span>
			</div>
			{#if mentionMatches.length > 0}
				{#each mentionMatches as file, idx (file.path)}
					<button
						type="button"
						class="flex w-full items-center justify-between gap-2 rounded-xl px-2.5 py-1.5 text-left transition {idx === mentionIndex
							? 'bg-sky-500/12 text-sky-700 dark:text-sky-300'
							: 'hover:bg-gray-100/80 dark:hover:bg-slate-800/70 text-gray-700 dark:text-slate-200'}"
						on:mouseenter={() => (mentionIndex = idx)}
						on:click={() => applyMention(file.path)}
					>
						<div class="flex items-center gap-2 min-w-0">
							<DevToolIcon
								name={file.ext === 'dir' ? 'folder' : 'read'}
								className="size-3.5 shrink-0 {file.ext === 'dir' ? 'text-amber-400' : 'text-sky-400'}"
							/>
							<span class="truncate font-mono text-xs">{file.path}</span>
						</div>
						{#if file.ext}
							<span class="shrink-0 rounded bg-gray-100 dark:bg-slate-800 px-1.5 py-0.5 font-mono text-[9.5px] uppercase text-gray-400">
								{file.ext}
							</span>
						{/if}
					</button>
				{/each}
			{:else if mentionQuery.trim()}
				<button
					type="button"
					class="flex w-full items-center justify-between gap-2 rounded-xl px-2.5 py-2 text-left text-xs text-sky-600 dark:text-sky-400 hover:bg-sky-500/10 transition"
					on:click={() => applyMention(mentionQuery.trim())}
				>
					<span class="truncate font-mono">Anexar caminho: {mentionQuery.trim()}</span>
					<span class="shrink-0 text-[10px] text-gray-400">↵</span>
				</button>
			{:else}
				<div class="px-2.5 py-2 text-xs text-gray-400">
					Digite o nome de um arquivo ou um caminho absoluto (ex.: <span class="font-mono text-gray-300">@/etc/hostname</span>).
				</div>
			{/if}
		</div>
	{/if}

	<!-- Faixa de Prompt Enfileirado (rail-queued-status) -->
	{#if queuedPrompt}
		<div class="mb-2 flex items-center justify-between gap-2 rounded-xl border border-sky-500/25 bg-sky-500/[0.07] px-3 py-1.5 text-xs">
			<div class="flex items-center gap-2 min-w-0">
				<span class="rounded-full bg-sky-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-sky-600 dark:text-sky-400 shrink-0">
					Na fila
				</span>
				<span class="truncate text-gray-700 dark:text-slate-200">{queuedPrompt}</span>
			</div>
			<button
				type="button"
				class="shrink-0 text-[11px] text-gray-400 hover:text-rose-500 transition"
				on:click={() => dispatch('cancelQueue')}
			>
				Cancelar
			</button>
		</div>
	{/if}

	<!-- Cartão Principal do Composer (elevado #0d1727 com borda #2a3b50 sobre o palco #080d17, harmonizado com o Chat) -->
	<div
		class="rounded-2xl border bg-white dark:bg-[#0d1727] transition-all {isStartStage
			? 'border-gray-200/90 dark:border-[#2a3b50] shadow-lg shadow-black/[0.04] dark:shadow-black/40 focus-within:border-sky-500/70 focus-within:ring-1 focus-within:ring-sky-500/20'
			: 'border-gray-200/80 dark:border-[#2a3b50] focus-within:border-sky-500/70 focus-within:ring-1 focus-within:ring-sky-500/15'}"
	>
		<!-- Chips de arquivos anexados (@) e pastas extras (--add-dir) -->
		{#if attachedFiles.length > 0 || extraDirs.length > 0}
			<div class="flex flex-wrap items-center gap-1.5 px-3.5 pt-3">
				{#each attachedFiles as fpath (fpath)}
					<span
						class="inline-flex items-center gap-1 rounded-lg border border-sky-500/20 bg-sky-500/10 px-2 py-0.5 font-mono text-[11px] text-sky-700 dark:text-sky-300"
					>
						<span class="text-sky-400">@</span>
						<span class="max-w-[200px] truncate">{fpath}</span>
						<button
							type="button"
							class="ml-0.5 text-sky-400 hover:text-rose-400"
							aria-label="Remover arquivo"
							on:click={() => dispatch('removeAttachment', fpath)}
						>
							×
						</button>
					</span>
				{/each}
				{#each extraDirs as dir (dir)}
					<span
						class="inline-flex items-center gap-1 rounded-lg border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 font-mono text-[11px] text-amber-700 dark:text-amber-300"
						title="Diretório extra (--add-dir): {dir}"
					>
						<DevToolIcon name="folder" className="size-3" />
						<span class="max-w-[160px] truncate">+{dir.split('/').filter(Boolean).pop() || dir}</span>
						<button
							type="button"
							class="ml-0.5 text-amber-400 hover:text-rose-400"
							aria-label="Remover pasta extra"
							on:click={() => dispatch('removeExtraDir', dir)}
						>
							×
						</button>
					</span>
				{/each}
			</div>
		{/if}

		<!-- Campo de texto limpo -->
		<div class="px-4 pt-3.5 pb-1.5">
			<textarea
				bind:this={textareaEl}
				bind:value
				on:keydown={handleKeydown}
				on:input={handleInput}
				on:click={detectMentionToken}
				rows={isStartStage ? 3 : 2}
				placeholder={isStreaming
					? 'Enfileire sua próxima instrução ou pressione Esc para interromper…'
					: cwd
						? 'O que vamos construir ou corrigir hoje?'
						: 'Peça qualquer tarefa, script ou comando no seu PC…'}
				class="w-full resize-none bg-transparent text-[14px] leading-relaxed text-gray-900 dark:text-slate-100 outline-none placeholder:text-gray-400 dark:placeholder:text-slate-500"
			></textarea>
		</div>

		<!-- Rodapé minimalista dentro do cartão (exatamente como no Claude Code Desktop) -->
		<div class="flex items-center justify-between gap-2 px-2.5 pb-2.5 pt-0.5">
			<!-- Esquerda: apenas botão '+' -->
			<div class="relative" data-dev-menu>
				<button
					type="button"
					class="inline-flex size-7 items-center justify-center rounded-lg text-gray-400 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800/80 hover:text-gray-800 dark:hover:text-slate-100 transition"
					aria-label="Adicionar arquivo, pasta ou comando"
					title="Mencionar arquivo (@), adicionar pasta extra ou comandos (/)"
					on:click|stopPropagation={() => {
						const next = !showPlusMenu;
						closeAllMenus();
						showPlusMenu = next;
					}}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
						<path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z" />
					</svg>
				</button>

				{#if showPlusMenu}
					<div
						class="absolute bottom-full left-0 mb-2 w-60 rounded-xl border border-gray-200 dark:border-slate-800 bg-white dark:bg-[#0f1726] shadow-2xl z-50 p-1 space-y-0.5 text-xs"
					>
						<button
							type="button"
							class="flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-gray-700 dark:text-slate-200 hover:bg-gray-100 dark:hover:bg-slate-800/80 transition"
							on:click={() => insertTrigger('@')}
						>
							<span class="flex items-center gap-2">
								<DevToolIcon name="read" className="size-3.5 text-sky-400" />
								<span>Mencionar arquivo</span>
							</span>
							<span class="font-mono text-[10px] text-gray-400">@</span>
						</button>
						<button
							type="button"
							class="flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-gray-700 dark:text-slate-200 hover:bg-gray-100 dark:hover:bg-slate-800/80 transition"
							on:click={() => {
								showPlusMenu = false;
								dispatch('addExtraDir');
							}}
						>
							<span class="flex items-center gap-2">
								<DevToolIcon name="folder" className="size-3.5 text-amber-400" />
								<span>Adicionar pasta extra</span>
							</span>
							<span class="font-mono text-[10px] text-gray-400">+dir</span>
						</button>
						<button
							type="button"
							class="flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-gray-700 dark:text-slate-200 hover:bg-gray-100 dark:hover:bg-slate-800/80 transition"
							on:click={() => insertTrigger('/')}
						>
							<span class="flex items-center gap-2">
								<DevToolIcon name="terminal" className="size-3.5 text-sky-400" />
								<span>Comandos slash</span>
							</span>
							<span class="font-mono text-[10px] text-gray-400">/</span>
						</button>
					</div>
				{/if}
			</div>

			<!-- Direita: apenas botão Enviar / Enfileirar / Parar -->
			<div class="flex items-center gap-1.5">
				{#if isStreaming}
					{#if value.trim()}
						<button
							type="button"
							class="inline-flex h-7 items-center gap-1 rounded-lg bg-sky-500/15 px-2.5 text-xs font-medium text-sky-400 hover:bg-sky-500/25 transition"
							on:click={submitPrompt}
						>
							Enfileirar
						</button>
					{/if}
					<button
						type="button"
						class="inline-flex h-7 items-center gap-1.5 rounded-lg bg-rose-500 px-2.5 text-xs font-medium text-white hover:bg-rose-600 transition"
						title="Interromper execução (Esc)"
						on:click={() => dispatch('stop')}
					>
						<span class="size-2 rounded-[2px] bg-white"></span>
						<span>Parar</span>
					</button>
				{:else}
					<button
						type="button"
						disabled={!value.trim() && attachedFiles.length === 0}
						class="inline-flex size-8 items-center justify-center rounded-xl bg-sky-500 text-white hover:bg-sky-400 disabled:bg-gray-200 dark:disabled:bg-slate-800/90 disabled:text-gray-400 dark:disabled:text-slate-600 transition"
						aria-label="Enviar instrução"
						on:click={submitPrompt}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
							<path fill-rule="evenodd" d="M10 17a.75.75 0 0 1-.75-.75V5.612L5.29 9.77a.75.75 0 0 1-1.08-1.04l5.25-5.5a.75.75 0 0 1 1.08 0l5.25 5.5a.75.75 0 1 1-1.08 1.04l-3.96-4.158V16.25A.75.75 0 0 1 10 17Z" clip-rule="evenodd" />
						</svg>
					</button>
				{/if}
			</div>
		</div>
	</div>

	<!-- Barra de Ambiente Única logo ABAIXO do Composer (alinhamento uniforme em altura e baseline) -->
	<div class="mt-2 flex flex-wrap items-center justify-between gap-2 px-1 text-[12px] leading-none text-gray-500 dark:text-slate-400">
		<!-- Esquerda: Local · Pasta · Branch -->
		<div class="flex flex-wrap items-center gap-0.5 min-w-0">
			<span
				class="inline-flex h-7 items-center gap-1.5 rounded-lg px-2 text-[12px] leading-none text-gray-500 dark:text-slate-400"
				title={fccOnline ? 'Motor FCC local conectado' : 'Motor FCC offline'}
			>
				<span class="size-1.5 rounded-full shrink-0 {fccOnline ? 'bg-emerald-400' : 'bg-amber-400'}"></span>
				<span>Local</span>
			</span>

			<div class="inline-flex items-center max-w-[230px]">
				<button
					type="button"
					class="inline-flex h-7 items-center gap-1.5 rounded-lg px-2 text-[12px] leading-none text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-800/70 transition min-w-0"
					title={cwd ? `Pasta ativa: ${cwd} (clique para trocar)` : 'Sem pasta fixa — controle total do PC (clique para escolher uma pasta)'}
					on:click={() => dispatch('openDirPicker')}
				>
					{#if cwd}
						<DevToolIcon name="folder" className="size-3.5 text-sky-400/90 shrink-0" />
					{:else}
						<DevToolIcon name="terminal" className="size-3.5 text-emerald-400/90 shrink-0" />
					{/if}
					<span class="truncate">{folderShort}</span>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3 shrink-0 opacity-60">
						<path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.938a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z" clip-rule="evenodd" />
					</svg>
				</button>
				{#if cwd}
					<button
						type="button"
						class="inline-flex size-6 items-center justify-center rounded-md text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-800/80 hover:text-rose-400 transition shrink-0"
						title="Remover pasta (usar controle total do PC)"
						aria-label="Usar sem pasta (PC inteiro)"
						on:click|stopPropagation={() => dispatch('clearCwd')}
					>
						×
					</button>
				{/if}
			</div>

			{#if gitBranch}
				<button
					type="button"
					class="inline-flex h-7 items-center gap-1.5 rounded-lg px-2 font-mono text-[11.5px] leading-none text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800/70 hover:text-gray-800 dark:hover:text-slate-200 transition max-w-[150px]"
					title="Copiar nome da branch"
					on:click={() => dispatch('copyBranch')}
				>
					<DevToolIcon name="branch" className="size-3 text-sky-400/80 shrink-0" />
					<span class="truncate">{gitBranch}</span>
					{#if gitDirtyCount > 0}
						<span class="rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[9.5px] font-semibold leading-none text-amber-400">
							{gitDirtyCount}
						</span>
					{/if}
				</button>
			{/if}
		</div>

		<!-- Direita: Modelo/Perfil (Harmonia) · Permissão · Esforço · Context Ring -->
		<div class="flex items-center gap-0.5">
			<!-- Seletor Unificado de Perfil Minerva & Modelo Manual -->
			<div class="relative" data-dev-menu>
				<button
					type="button"
					class="inline-flex h-7 items-center gap-1.5 rounded-lg px-2 text-[12px] font-medium leading-none text-gray-700 dark:text-slate-200 hover:bg-gray-100 dark:hover:bg-slate-800/70 transition max-w-[200px]"
					title={activeModelName ? `Modelo ativo: ${activeModelName}` : 'Selecionar perfil ou modelo'}
					on:click|stopPropagation={() => {
						const next = !showModelMenu;
						closeAllMenus();
						showModelMenu = next;
						modelSearch = '';
					}}
				>
					<span class="size-1.5 rounded-full shrink-0 {activeModeObj ? 'bg-sky-400' : 'bg-violet-400'}"></span>
					<span class="truncate">{activeModeObj ? activeModeObj.label : activeModelName || 'Harmonia'}</span>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3 shrink-0 opacity-60">
						<path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.938a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z" clip-rule="evenodd" />
					</svg>
				</button>

				{#if showModelMenu}
					<div
						class="absolute bottom-full right-0 mb-2 w-80 rounded-2xl border border-gray-200/90 dark:border-slate-800 bg-white dark:bg-[#0f1726] shadow-2xl z-50 overflow-hidden"
					>
						{#if !showManualModels}
							<div class="p-1.5 space-y-0.5">
								{#each modes as m (m.id)}
									<button
										type="button"
										class="flex w-full items-start justify-between gap-3 rounded-xl px-3 py-2.5 text-left transition {activeMode === m.id
											? 'bg-sky-500/12 text-sky-700 dark:text-sky-300'
											: 'text-gray-700 dark:text-slate-200 hover:bg-gray-100/80 dark:hover:bg-slate-800/60'}"
										on:click={() => {
											showModelMenu = false;
											showManualModels = false;
											dispatch('selectMode', m.id);
										}}
									>
										<div class="min-w-0 flex-1">
											<div class="flex items-center gap-1.5 text-[12.5px] font-medium leading-tight">
												<span>{m.label}</span>
												{#if m.id === 'harmonia'}
													<span class="inline-flex items-center rounded bg-sky-500/12 px-1.5 py-0.5 text-[9.5px] font-medium text-sky-500 dark:text-sky-400 leading-none">
														Padrão
													</span>
												{/if}
											</div>
											<div class="mt-1 text-[11px] text-gray-500 dark:text-slate-400 leading-snug">{m.description}</div>
										</div>
										{#if activeMode === m.id}
											<span class="mt-0.5 text-sky-400 text-xs leading-none shrink-0">✓</span>
										{/if}
									</button>
								{/each}
							</div>

							<div class="flex items-center justify-between gap-2 border-t border-gray-100/80 dark:border-slate-800/80 px-3 py-2">
								<button
									type="button"
									class="shrink-0 text-[11px] font-normal leading-none text-gray-400/90 dark:text-slate-500 hover:text-sky-500 dark:hover:text-sky-400 hover:underline underline-offset-2 transition"
									on:click|stopPropagation={openManualModelsSection}
								>
									Selecionar modelo manualmente
								</button>
								{#if !activeModeObj && activeModelName}
									<span
										class="truncate text-[10.5px] leading-none text-violet-400/90"
										title={`Modelo manual ativo: ${activeModelName}`}
									>
										{activeModelName}
									</span>
								{/if}
							</div>
						{:else}
							<div class="flex items-center justify-between gap-2 border-b border-gray-100/80 dark:border-slate-800/80 px-3 py-2">
								<button
									type="button"
									class="inline-flex items-center gap-1 text-[11px] font-medium leading-none text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-slate-100 transition"
									on:click|stopPropagation={() => {
										showManualModels = false;
										modelSearch = '';
									}}
								>
									<span aria-hidden="true">←</span>
									<span>Voltar aos modos</span>
								</button>
								<span class="text-[10.5px] leading-none text-gray-400 dark:text-slate-500">Seleção manual</span>
							</div>

							<div class="p-2 border-b border-gray-100/70 dark:border-slate-800/70">
								<input
									bind:this={manualSearchInputEl}
									type="text"
									bind:value={modelSearch}
									placeholder="Buscar modelo ou provedor…"
									class="w-full rounded-lg border border-gray-200 dark:border-slate-700/80 bg-gray-50 dark:bg-slate-950 px-2.5 py-1.5 text-xs outline-none focus:border-sky-500"
								/>
							</div>

							<div class="max-h-60 overflow-y-auto p-1.5 space-y-0.5">
								{#if filteredModels.length === 0}
									<div class="py-4 text-center text-xs text-gray-400">Nenhum modelo encontrado.</div>
								{:else}
									{#each filteredModels as item (item.id)}
										<button
											type="button"
											class="flex h-8 w-full items-center justify-between gap-2.5 rounded-lg px-2.5 text-left text-xs leading-none transition {activeModel === item.id
												? 'bg-sky-500/12 text-sky-600 dark:text-sky-400 font-medium'
												: 'text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-800/70'}"
											on:click={() => {
												showModelMenu = false;
												showManualModels = false;
												dispatch('selectModel', item.id);
											}}
										>
											<span class="flex items-center gap-2 min-w-0">
												<span class="inline-flex size-4 shrink-0 items-center justify-center">
													<AurenProviderBadge
														compact
														provider={item.provider_id}
														modelId={item.id}
														modelName={item.name}
														name={item.provider_name}
													/>
												</span>
												<span class="truncate leading-tight">{item.name}</span>
											</span>
											<span class="shrink-0 inline-flex items-center rounded bg-gray-100 dark:bg-slate-800 px-1.5 py-0.5 text-[10px] leading-none text-gray-500 dark:text-slate-400">
												{item.provider_name}
											</span>
										</button>
									{/each}
								{/if}
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Seletor de Permissão -->
			<div class="relative" data-dev-menu>
				<button
					type="button"
					class="inline-flex h-7 items-center gap-1.5 rounded-lg px-2 text-[12px] leading-none text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-800/70 transition"
					title="Permissões da sessão (Shift+Tab)"
					on:click|stopPropagation={() => {
						const next = !showPermMenu;
						closeAllMenus();
						showPermMenu = next;
					}}
				>
					<span class="size-1.5 rounded-full shrink-0 {PERM_META[permissionMode].dot}"></span>
					<span>{PERM_META[permissionMode].short}</span>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3 shrink-0 opacity-60">
						<path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.938a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z" clip-rule="evenodd" />
					</svg>
				</button>

				{#if showPermMenu}
					<div
						class="absolute bottom-full right-0 mb-2 w-72 rounded-2xl border border-gray-200 dark:border-slate-800 bg-white dark:bg-[#0f1726] shadow-2xl z-50 p-1.5 space-y-0.5"
					>
						<div class="flex items-center justify-between px-2.5 py-1 text-[10.5px] font-medium text-gray-400">
							<span>Permissões da sessão</span>
							<span class="font-mono text-[10px]">Shift+Tab</span>
						</div>
						{#each ['plan', 'acceptEdits', 'bypassPermissions'] as pm}
							{@const meta = PERM_META[pm]}
							<button
								type="button"
								class="flex w-full items-start justify-between gap-2 rounded-xl px-2.5 py-2 text-left transition {permissionMode === pm
									? 'bg-sky-500/12'
									: 'hover:bg-gray-100 dark:hover:bg-slate-800/70'}"
								on:click={() => {
									showPermMenu = false;
									dispatch('setPermission', pm);
								}}
							>
								<div class="flex items-start gap-2 min-w-0">
									<span class="mt-1.5 size-2 shrink-0 rounded-full {meta.dot}"></span>
									<div class="min-w-0">
										<div class="text-xs font-medium text-gray-800 dark:text-slate-100">{meta.label}</div>
										<div class="text-[10.5px] text-gray-500 dark:text-slate-400 leading-snug">{meta.desc}</div>
									</div>
								</div>
								{#if permissionMode === pm}
									<span class="text-sky-400 text-xs shrink-0">✓</span>
								{/if}
							</button>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Seletor de Esforço -->
			<div class="relative" data-dev-menu>
				<button
					type="button"
					class="inline-flex h-7 items-center gap-1.5 rounded-lg px-2 text-[12px] leading-none text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800/70 hover:text-gray-800 dark:hover:text-slate-200 transition"
					title={EFFORT_META[effort].label}
					on:click|stopPropagation={() => {
						const next = !showEffortMenu;
						closeAllMenus();
						showEffortMenu = next;
					}}
				>
					<span class="inline-flex items-end gap-[1.5px] h-2.5 shrink-0">
						{#each [1, 2, 3] as bar}
							<span
								class="w-[2.5px] rounded-xs {bar <= EFFORT_META[effort].bars
									? 'bg-sky-400'
									: 'bg-gray-300 dark:bg-slate-700'}"
								style="height: {bar * 3 + 1}px"
							></span>
						{/each}
					</span>
					<span class="hidden sm:inline">{EFFORT_META[effort].short}</span>
				</button>

				{#if showEffortMenu}
					<div
						class="absolute bottom-full right-0 mb-2 w-44 rounded-xl border border-gray-200 dark:border-slate-800 bg-white dark:bg-[#0f1726] shadow-2xl z-50 p-1 space-y-0.5"
					>
						<div class="px-2 py-1 text-[10.5px] font-medium text-gray-400">Esforço de raciocínio</div>
						{#each ['', 'low', 'medium', 'high'] as ef}
							<button
								type="button"
								class="flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-xs transition {effort === ef
									? 'bg-sky-500/12 text-sky-600 dark:text-sky-400 font-medium'
									: 'text-gray-700 dark:text-slate-200 hover:bg-gray-100 dark:hover:bg-slate-800/70'}"
								on:click={() => {
									showEffortMenu = false;
									dispatch('setEffort', ef);
								}}
							>
								<span>{EFFORT_META[ef].short}</span>
								{#if effort === ef}
									<span>✓</span>
								{/if}
							</button>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Anel de Contexto (discreto, somente em sessões ativas) -->
			{#if !isStartStage}
				<DevContextRing tokens={estTokens} size={17} compact={true} on:compact={() => dispatch('compact')} />
			{/if}
		</div>
	</div>
</div>
