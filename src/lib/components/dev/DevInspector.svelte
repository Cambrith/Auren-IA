<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type {
		DevFileContentResponse,
		DevFileEntry,
		DevGitFile,
		DevModeInfo,
		DevProjectInfoResponse,
		DevProviderInfo
	} from '$lib/apis/dev';
	import DevContextRing from './DevContextRing.svelte';
	import DevDiffViewer from './DevDiffViewer.svelte';
	import DevToolIcon from './DevToolIcon.svelte';
	import type { DevTodoItem, ToolCallItem } from './types';

	export let tab: 'changes' | 'files' | 'activity' | 'context' = 'changes';
	export let cwd = '';
	export let extraDirs: string[] = [];
	export let gitIsRepo = false;
	export let gitBranch = '';
	export let gitFiles: DevGitFile[] = [];
	export let selectedDiffFile = '';
	export let selectedDiffText = '';
	export let loadingDiff = false;

	export let projectFiles: DevFileEntry[] = [];
	export let fileSearchQuery = '';
	export let loadingFiles = false;
	export let previewFile: DevFileContentResponse | null = null;
	export let loadingPreview = false;

	export let allTools: ToolCallItem[] = [];
	export let activeTodos: DevTodoItem[] = [];

	export let estTokens = 0;
	export let activeModelName = '';
	export let activeModeObj: DevModeInfo | null = null;
	export let providers: DevProviderInfo[] = [];
	export let projectInfo: DevProjectInfoResponse | null = null;
	export let sessionId: string | null = null;

	const dispatch = createEventDispatcher<{
		close: void;
		refreshGit: void;
		openDiff: string;
		reviewAll: void;
		reviewFile: string;
		searchFiles: string;
		previewFile: string;
		closePreview: void;
		attachFile: string;
		removeExtraDir: string;
		addExtraDir: void;
		compact: void;
		copy: { text: string; label: string };
	}>();

	$: totalAdded = gitFiles.reduce((acc, f) => acc + (f.added || 0), 0);
	$: totalRemoved = gitFiles.reduce((acc, f) => acc + (f.removed || 0), 0);

	function statusBadgeStyle(status: string): string {
		if (status.includes('A') || status === '??') return 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400';
		if (status.includes('D')) return 'bg-rose-500/15 text-rose-600 dark:text-rose-400';
		if (status.includes('R')) return 'bg-violet-500/15 text-violet-600 dark:text-violet-400';
		return 'bg-amber-500/15 text-amber-600 dark:text-amber-400';
	}

	function cleanModelLeaf(id: string): string {
		const leaf = id.split('/').pop() || id;
		return leaf.replace(':free', ' (free)');
	}
</script>

<aside class="flex h-full w-full flex-col border-l border-gray-200/80 dark:border-[#2a3b50] bg-gray-50/70 dark:bg-[#0d1727]">
	<!-- Drawer Tabs Row (inspirado no drawer-tabs-row do Claude Code Desktop) -->
	<div class="flex items-center justify-between gap-1 border-b border-gray-200/80 dark:border-gray-800/90 px-2.5 py-2">
		<div class="flex items-center gap-0.5 overflow-x-auto">
			<button
				type="button"
				class="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11.5px] font-medium transition whitespace-nowrap {tab === 'changes'
					? 'bg-sky-500/15 text-sky-600 dark:text-sky-400'
					: 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'}"
				on:click={() => (tab = 'changes')}
			>
				<span>Alterações</span>
				{#if gitFiles.length > 0}
					<span class="rounded-full bg-sky-500/20 px-1.5 text-[10px] font-semibold tabular-nums">
						{gitFiles.length}
					</span>
				{/if}
			</button>

			<button
				type="button"
				class="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11.5px] font-medium transition whitespace-nowrap {tab === 'files'
					? 'bg-sky-500/15 text-sky-600 dark:text-sky-400'
					: 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'}"
				on:click={() => (tab = 'files')}
			>
				<span>Arquivos</span>
			</button>

			<button
				type="button"
				class="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11.5px] font-medium transition whitespace-nowrap {tab === 'activity'
					? 'bg-sky-500/15 text-sky-600 dark:text-sky-400'
					: 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'}"
				on:click={() => (tab = 'activity')}
			>
				<span>Atividade</span>
				{#if allTools.length > 0}
					<span class="rounded-full bg-gray-200/80 dark:bg-gray-800 px-1.5 text-[10px] tabular-nums">
						{allTools.length}
					</span>
				{/if}
			</button>

			<button
				type="button"
				class="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11.5px] font-medium transition whitespace-nowrap {tab === 'context'
					? 'bg-sky-500/15 text-sky-600 dark:text-sky-400'
					: 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'}"
				on:click={() => (tab = 'context')}
			>
				<span>Contexto</span>
			</button>
		</div>

		<button
			type="button"
			class="flex size-6 shrink-0 items-center justify-center rounded-md text-gray-400 hover:bg-gray-200/70 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-200 transition"
			aria-label="Fechar painel"
			on:click={() => dispatch('close')}
		>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5">
				<path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
			</svg>
		</button>
	</div>

	<div class="flex-1 overflow-y-auto p-3 text-xs space-y-2.5">
		<!-- TAB 1: ALTERAÇÕES / DIFFS -->
		{#if tab === 'changes'}
			{#if !gitIsRepo}
				<div class="rounded-xl border border-dashed border-gray-200 dark:border-gray-800 px-4 py-10 text-center text-gray-400">
					<div class="mx-auto mb-2 flex size-8 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-900">
						<DevToolIcon name={cwd ? 'branch' : 'terminal'} className="size-4 text-gray-400" />
					</div>
					{#if cwd}
						Esta pasta não é um repositório Git.
					{:else}
						Modo PC inteiro ativo (sem pasta fixa). Selecione uma pasta Git para acompanhar diffs.
					{/if}
				</div>
			{:else}
				<div class="flex items-center justify-between gap-2 rounded-xl border border-gray-200/80 dark:border-gray-800 bg-white dark:bg-gray-900 px-3 py-2">
					<div class="flex items-center gap-2 min-w-0">
						<DevToolIcon name="branch" className="size-3.5 text-sky-500 shrink-0" />
						<span class="truncate font-mono text-[11px] font-medium text-gray-800 dark:text-gray-200">
							{gitBranch || 'HEAD'}
						</span>
						{#if totalAdded > 0 || totalRemoved > 0}
							<span class="font-mono text-[10px] shrink-0">
								<span class="text-emerald-500">+{totalAdded}</span>
								<span class="text-rose-500 ml-1">-{totalRemoved}</span>
							</span>
						{/if}
					</div>
					<div class="flex items-center gap-1.5 shrink-0">
						{#if gitFiles.length > 0}
							<button
								type="button"
								class="rounded-md bg-sky-500/10 px-2 py-0.5 text-[10.5px] font-medium text-sky-600 dark:text-sky-400 hover:bg-sky-500/20 transition"
								on:click={() => dispatch('reviewAll')}
							>
								Revisar
							</button>
						{/if}
						<button
							type="button"
							class="rounded-md px-1.5 py-0.5 text-[10.5px] text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-200 transition"
							title="Atualizar Git"
							on:click={() => dispatch('refreshGit')}
						>
							↻
						</button>
					</div>
				</div>

				{#if gitFiles.length === 0}
					<div class="rounded-xl border border-dashed border-gray-200 dark:border-gray-800 px-4 py-8 text-center text-gray-400">
						Árvore limpa na branch <span class="font-mono text-sky-500">{gitBranch}</span>.
					</div>
				{:else}
					<div class="space-y-2">
						{#each gitFiles as f (f.path)}
							<div class="rounded-xl border border-gray-200/80 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden">
								<button
									type="button"
									class="flex w-full items-center justify-between gap-2 px-2.5 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-850 transition"
									on:click={() => dispatch('openDiff', f.path)}
								>
									<div class="flex items-center gap-1.5 min-w-0">
										<span class="rounded px-1.5 py-0.5 font-mono text-[9.5px] font-semibold shrink-0 {statusBadgeStyle(f.status)}">
											{f.status}
										</span>
										<span class="truncate font-mono text-[11px] text-gray-800 dark:text-gray-200" title={f.path}>
											{f.path}
										</span>
									</div>
									<div class="flex items-center gap-1.5 shrink-0 font-mono text-[10px] tabular-nums">
										{#if f.added > 0}<span class="text-emerald-500">+{f.added}</span>{/if}
										{#if f.removed > 0}<span class="text-rose-500">-{f.removed}</span>{/if}
									</div>
								</button>

								{#if selectedDiffFile === f.path}
									<DevDiffViewer
										file={f.path}
										diff={selectedDiffText}
										loading={loadingDiff}
										on:copy={(e) => dispatch('copy', { text: e.detail, label: 'Diff copiado!' })}
										on:reviewFile={(e) => dispatch('reviewFile', e.detail)}
									/>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			{/if}

		<!-- TAB 2: ARQUIVOS DO PROJETO -->
		{:else if tab === 'files'}
			<div class="space-y-2.5">
				<div class="relative">
					<input
						type="text"
						value={fileSearchQuery}
						placeholder={cwd ? 'Filtrar arquivos do projeto…' : 'Buscar em ~ ou digite /caminho/…'}
						class="w-full rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 pl-8 pr-3 py-1.5 text-xs outline-none focus:border-sky-500 transition"
						on:input={(e) => dispatch('searchFiles', e.currentTarget.value)}
					/>
					<span class="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400">
						<DevToolIcon name="search" className="size-3.5" />
					</span>
				</div>

				{#if previewFile || loadingPreview}
					<div class="rounded-xl border border-sky-500/30 bg-gray-950 overflow-hidden">
						<div class="flex items-center justify-between gap-2 border-b border-gray-800 bg-gray-900 px-2.5 py-1.5 text-[11px]">
							<span class="truncate font-mono text-sky-300">{previewFile?.path || 'Carregando…'}</span>
							<div class="flex items-center gap-1.5 shrink-0">
								{#if previewFile}
									<button
										type="button"
										class="rounded bg-sky-500/15 px-1.5 py-0.5 text-[10px] font-medium text-sky-300 hover:bg-sky-500/25 transition"
										on:click={() => previewFile && dispatch('attachFile', previewFile.path)}
									>
										@ Anexar
									</button>
								{/if}
								<button
									type="button"
									class="text-gray-400 hover:text-white px-1"
									on:click={() => dispatch('closePreview')}
								>
									×
								</button>
							</div>
						</div>
						<div class="max-h-72 overflow-auto p-2 font-mono text-[10.5px] leading-relaxed text-gray-300">
							{#if loadingPreview}
								<div class="py-6 text-center text-gray-400">Lendo arquivo…</div>
							{:else if previewFile?.binary}
								<div class="py-6 text-center text-gray-500">Arquivo binário ({previewFile.size} bytes).</div>
							{:else if previewFile}
								{#each previewFile.content.split('\n').slice(0, 350) as ln, idx}
									<div class="flex gap-2 hover:bg-white/[0.03]">
										<span class="w-7 shrink-0 select-none text-right text-gray-600 tabular-nums">{idx + 1}</span>
										<span class="whitespace-pre">{ln}</span>
									</div>
								{/each}
							{/if}
						</div>
					</div>
				{/if}

				{#if loadingFiles}
					<div class="py-6 text-center text-gray-400">Indexando arquivos…</div>
				{:else if projectFiles.length === 0}
					<div class="py-8 text-center text-gray-400">Nenhum arquivo encontrado.</div>
				{:else}
					<div class="space-y-0.5">
						{#each projectFiles as f (f.path)}
							<div class="group flex items-center justify-between gap-1.5 rounded-lg px-2 py-1.5 hover:bg-white dark:hover:bg-gray-900 border border-transparent hover:border-gray-200/70 dark:hover:border-gray-800 transition">
								<button
									type="button"
									class="flex min-w-0 flex-1 items-center gap-2 text-left"
									on:click={() => dispatch('previewFile', f.path)}
								>
									<DevToolIcon name="read" className="size-3.5 shrink-0 text-gray-400 group-hover:text-sky-500" />
									<span class="truncate font-mono text-[11px] text-gray-700 dark:text-gray-300" title={f.path}>
										{f.path}
									</span>
								</button>
								<button
									type="button"
									class="opacity-0 group-hover:opacity-100 rounded bg-sky-500/10 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-sky-600 dark:text-sky-400 hover:bg-sky-500/20 transition shrink-0"
									title="Mencionar @arquivo no prompt"
									on:click={() => dispatch('attachFile', f.path)}
								>
									@
								</button>
							</div>
						{/each}
					</div>
				{/if}
			</div>

		<!-- TAB 3: ATIVIDADE (TAREFAS + TIMELINE DE FERRAMENTAS) -->
		{:else if tab === 'activity'}
			<div class="space-y-3">
				{#if activeTodos.length > 0}
					<div class="rounded-xl border border-sky-500/25 bg-white dark:bg-gray-900 p-3 space-y-2">
						<div class="flex items-center justify-between">
							<span class="text-[11px] font-semibold text-sky-600 dark:text-sky-400">
								Plano de Tarefas
							</span>
							<span class="font-mono text-[10px] text-gray-400 tabular-nums">
								{activeTodos.filter((t) => t.status === 'completed').length}/{activeTodos.length}
							</span>
						</div>
						<div class="space-y-1.5">
							{#each activeTodos as todo}
								<div class="flex items-start gap-2 text-[11.5px]">
									<span
										class="mt-0.5 inline-flex size-4 shrink-0 items-center justify-center rounded-full text-[9px] {todo.status === 'completed'
											? 'bg-emerald-500/15 text-emerald-500'
											: todo.status === 'in_progress'
												? 'bg-sky-500/20 text-sky-500 animate-pulse'
												: 'bg-gray-100 dark:bg-gray-800 text-gray-400'}"
									>
										{todo.status === 'completed' ? '✓' : todo.status === 'in_progress' ? '●' : '○'}
									</span>
									<span class={todo.status === 'completed' ? 'line-through text-gray-400' : 'text-gray-700 dark:text-gray-200'}>
										{todo.content}
									</span>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				{#if allTools.length === 0}
					<div class="rounded-xl border border-dashed border-gray-200 dark:border-gray-800 px-4 py-10 text-center text-gray-400">
						Nenhuma ferramenta executada nesta sessão ainda.
					</div>
				{:else}
					<div class="space-y-1.5">
						{#each [...allTools].reverse() as t (t.id)}
							<div class="flex items-start justify-between gap-2 rounded-xl border border-gray-200/80 dark:border-gray-800 bg-white dark:bg-gray-900 px-2.5 py-2">
								<div class="flex items-start gap-2 min-w-0">
									<span class="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-md bg-sky-500/10 text-sky-600 dark:text-sky-400">
										<DevToolIcon name={t.name} className="size-3" />
									</span>
									<div class="min-w-0">
										<div class="font-medium text-gray-800 dark:text-gray-200">{t.label}</div>
										{#if t.summary}
											<div class="mt-0.5 truncate font-mono text-[10.5px] text-gray-400" title={t.summary}>
												{t.summary}
											</div>
										{/if}
									</div>
								</div>
								<span
									class="shrink-0 text-[10.5px] font-medium {t.isError
										? 'text-rose-500'
										: t.done
											? 'text-emerald-500'
											: 'text-sky-500 animate-pulse'}"
								>
									{t.isError ? 'Erro' : t.done ? '✓' : '…'}
								</span>
							</div>
						{/each}
					</div>
				{/if}
			</div>

		<!-- TAB 4: CONTEXTO & MOTOR INTELIGENTE -->
		{:else}
			<div class="space-y-3">
				<div class="rounded-xl border border-gray-200/80 dark:border-gray-800 bg-white dark:bg-gray-900 p-3">
					<div class="flex items-center justify-between">
						<div>
							<div class="text-[11px] font-medium text-gray-400">Janela de contexto</div>
							<div class="mt-0.5 font-mono text-sm font-semibold text-gray-800 dark:text-gray-100 tabular-nums">
								~{estTokens.toLocaleString('pt-BR')} <span class="text-[11px] font-normal text-gray-400">/ 190k</span>
							</div>
						</div>
						<DevContextRing tokens={estTokens} size={30} compact={false} on:compact={() => dispatch('compact')} />
					</div>
				</div>

				<!-- Motor & Cadeia de Fallback -->
				<div class="rounded-xl border border-gray-200/80 dark:border-gray-800 bg-white dark:bg-gray-900 p-3 space-y-2">
					<div class="flex items-center justify-between">
						<span class="text-[11px] font-medium text-gray-400">Inteligência ativa</span>
						{#if activeModeObj}
							<span class="rounded-full bg-sky-500/15 px-2 py-0.5 text-[10px] font-semibold text-sky-600 dark:text-sky-400">
								Perfil {activeModeObj.label}
							</span>
						{:else}
							<span class="rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-[10px] text-gray-500">
								Manual
							</span>
						{/if}
					</div>
					<div class="font-medium text-gray-900 dark:text-gray-100">{activeModelName || '—'}</div>
					{#if activeModeObj && activeModeObj.fallbacks.length > 0}
						<div class="pt-1 border-t border-gray-100 dark:border-gray-800/80 space-y-1">
							<div class="text-[10px] uppercase tracking-wider text-gray-400">Fallbacks automáticos</div>
							{#each activeModeObj.fallbacks as fb, i}
								<div class="flex items-center gap-1.5 text-[11px] leading-snug text-gray-500 dark:text-gray-400">
									<span class="w-4 shrink-0 text-right font-mono text-[10px] tabular-nums text-sky-500">{i + 1}.</span>
									<span class="truncate">{cleanModelLeaf(fb)}</span>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<!-- Memória & Stack do Projeto -->
				{#if projectInfo && (projectInfo.stack.length > 0 || projectInfo.memory_files.length > 0)}
					<div class="rounded-xl border border-gray-200/80 dark:border-gray-800 bg-white dark:bg-gray-900 p-3 space-y-2">
						{#if projectInfo.stack.length > 0}
							<div>
								<div class="text-[11px] font-medium text-gray-400 mb-1.5">Stack detectada</div>
								<div class="flex flex-wrap gap-1">
									{#each projectInfo.stack as tech}
										<span class="rounded-md bg-sky-500/10 px-2 py-0.5 text-[10.5px] font-medium text-sky-700 dark:text-sky-300">
											{tech}
										</span>
									{/each}
								</div>
							</div>
						{/if}

						{#if projectInfo.memory_files.length > 0}
							<div class="pt-1 border-t border-gray-100 dark:border-gray-800/80">
								<div class="text-[11px] font-medium text-gray-400 mb-1">Instruções & Memória</div>
								<div class="space-y-1">
									{#each projectInfo.memory_files as mf}
										<button
											type="button"
											class="flex w-full items-center justify-between rounded-lg px-2 py-1 text-left hover:bg-gray-50 dark:hover:bg-gray-850 transition"
											on:click={() => {
												tab = 'files';
												dispatch('previewFile', mf.name);
											}}
										>
											<span class="font-mono text-[11px] text-gray-700 dark:text-gray-200">{mf.name}</span>
											<span class="text-[10px] text-gray-400 tabular-nums">{mf.lines} linhas</span>
										</button>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Pastas Extras (--add-dir) -->
				<div class="rounded-xl border border-gray-200/80 dark:border-gray-800 bg-white dark:bg-gray-900 p-3 space-y-2">
					<div class="flex items-center justify-between">
						<span class="text-[11px] font-medium text-gray-400">Diretórios acessíveis</span>
						<button
							type="button"
							class="text-[10.5px] font-medium text-sky-600 dark:text-sky-400 hover:underline"
							on:click={() => dispatch('addExtraDir')}
						>
							+ Adicionar
						</button>
					</div>
					<div class="rounded-lg bg-gray-50 dark:bg-gray-950 px-2 py-1 font-mono text-[10.5px] text-gray-600 dark:text-gray-300 truncate" title={cwd}>
						{cwd || '—'}
					</div>
					{#each extraDirs as ed}
						<div class="flex items-center justify-between gap-1 rounded-lg bg-sky-500/10 px-2 py-1 font-mono text-[10.5px] text-sky-700 dark:text-sky-300">
							<span class="truncate" title={ed}>{ed}</span>
							<button
								type="button"
								class="shrink-0 text-sky-500 hover:text-rose-500"
								on:click={() => dispatch('removeExtraDir', ed)}
							>
								×
							</button>
						</div>
					{/each}
				</div>

				<!-- Provedores & Sessão -->
				<div class="rounded-xl border border-gray-200/80 dark:border-gray-800 bg-white dark:bg-gray-900 p-3 space-y-2">
					<div class="text-[11px] font-medium text-gray-400">Provedores FCC ({providers.length})</div>
					<div class="flex flex-wrap gap-1">
						{#each providers as p}
							<span class="rounded-md bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-[10px] text-gray-600 dark:text-gray-300">
								{p.name}
							</span>
						{/each}
					</div>
					<div class="pt-2 border-t border-gray-100 dark:border-gray-800/80 space-y-1">
						<div class="text-[11px] font-medium text-gray-400">Sessão CLI</div>
						<div class="font-mono text-[10.5px] break-all text-gray-600 dark:text-gray-300">
							{sessionId || 'Nova sessão'}
						</div>
						{#if sessionId}
							<button
								type="button"
								class="text-[11px] text-sky-500 hover:underline"
								on:click={() =>
									sessionId &&
									dispatch('copy', {
										text: `claude --resume ${sessionId}`,
										label: 'Comando de retomada copiado!'
									})}
							>
								Copiar comando --resume
							</button>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</div>
</aside>
