<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import DevToolIcon from './DevToolIcon.svelte';
	import type { ToolCallItem } from './types';

	export let tools: ToolCallItem[] = [];
	export let streaming = false;

	const dispatch = createEventDispatcher<{
		toggleTool: string;
		previewFile: string;
		copy: string;
	}>();

	let manualExpanded: boolean | null = null;

	$: allDone = tools.length > 0 && tools.every((t) => t.done);
	$: hasErrors = tools.some((t) => t.isError);
	$: runningTools = tools.filter((t) => !t.done);
	$: shouldCollapseGroup =
		manualExpanded === null ? allDone && !hasErrors && tools.length >= 2 && !streaming : !manualExpanded;

	function summarizeTools(items: ToolCallItem[]): string {
		let reads = 0;
		let edits = 0;
		let cmds = 0;
		let searches = 0;
		let others = 0;
		for (const t of items) {
			if (t.name === 'Read') reads++;
			else if (t.name === 'Edit' || t.name === 'MultiEdit' || t.name === 'Write') edits++;
			else if (t.name === 'Bash') cmds++;
			else if (t.name === 'Grep' || t.name === 'Glob') searches++;
			else others++;
		}
		const parts: string[] = [];
		if (reads) parts.push(`${reads} ${reads === 1 ? 'leitura' : 'leituras'}`);
		if (edits) parts.push(`${edits} ${edits === 1 ? 'edição' : 'edições'}`);
		if (cmds) parts.push(`${cmds} ${cmds === 1 ? 'comando' : 'comandos'}`);
		if (searches) parts.push(`${searches} ${searches === 1 ? 'busca' : 'buscas'}`);
		if (others) parts.push(`${others} ${others === 1 ? 'ação' : 'ações'}`);
		return parts.join(' · ');
	}

	$: summaryText = summarizeTools(tools);
</script>

{#if tools.length > 0}
	<div class="rounded-xl border border-gray-200/80 dark:border-gray-800/90 bg-gray-50/70 dark:bg-gray-900/50 overflow-hidden">
		<!-- Cabeçalho estilo Claude Code Desktop (collapsed-steps-toggle) -->
		{#if tools.length >= 2}
			<button
				type="button"
				class="flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-[11.5px] text-gray-600 dark:text-gray-300 hover:bg-gray-100/70 dark:hover:bg-gray-800/50 transition"
				on:click={() => (manualExpanded = shouldCollapseGroup)}
			>
				<div class="flex items-center gap-2 min-w-0">
					{#if runningTools.length > 0}
						<span class="size-2 rounded-full bg-sky-500 animate-pulse shrink-0"></span>
					{:else if hasErrors}
						<span class="size-2 rounded-full bg-rose-500 shrink-0"></span>
					{:else}
						<span class="size-2 rounded-full bg-emerald-500 shrink-0"></span>
					{/if}
					<span class="font-medium text-gray-800 dark:text-gray-200 shrink-0">
						{runningTools.length > 0
							? `Executando etapa ${tools.length}`
							: `${tools.length} etapas executadas`}
					</span>
					{#if summaryText}
						<span class="truncate text-gray-500 dark:text-gray-400">· {summaryText}</span>
					{/if}
				</div>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5 shrink-0 text-gray-400 transition-transform {shouldCollapseGroup ? '' : 'rotate-180'}"
				>
					<path
						fill-rule="evenodd"
						d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.938a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		{/if}

		{#if !shouldCollapseGroup}
			<div class="divide-y divide-gray-200/70 dark:divide-gray-800/80 {tools.length >= 2 ? 'border-t border-gray-200/70 dark:border-gray-800/80' : ''}">
				{#each tools as tool (tool.id)}
					<div class="text-xs">
						<button
							type="button"
							class="flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left hover:bg-gray-100/60 dark:hover:bg-gray-800/40 transition"
							on:click={() => dispatch('toggleTool', tool.id)}
						>
							<div class="flex items-center gap-2 min-w-0">
								<span
									class="flex size-5 shrink-0 items-center justify-center rounded-md {tool.isError
										? 'bg-rose-500/15 text-rose-500'
										: tool.done
											? 'bg-sky-500/10 text-sky-600 dark:text-sky-400'
											: 'bg-sky-500/20 text-sky-500 animate-pulse'}"
								>
									<DevToolIcon name={tool.name} className="size-3.5" />
								</span>
								<span class="font-medium text-gray-800 dark:text-gray-200 shrink-0">{tool.label}</span>
								{#if tool.summary}
									<span class="truncate font-mono text-[11px] text-gray-500 dark:text-gray-400">
										{tool.summary}
									</span>
								{/if}
							</div>

							<div class="flex items-center gap-2 shrink-0">
								{#if (tool.name === 'Read' || tool.name === 'Edit' || tool.name === 'Write') && tool.summary}
									<span
										role="button"
										tabindex="0"
										class="hidden sm:inline-flex rounded px-1.5 py-0.5 text-[10px] text-gray-400 hover:bg-sky-500/10 hover:text-sky-500 transition"
										on:click|stopPropagation={() => dispatch('previewFile', tool.summary)}
										on:keydown|stopPropagation={(e) => {
											if (e.key === 'Enter') dispatch('previewFile', tool.summary);
										}}
									>
										Abrir
									</span>
								{/if}
								<span
									class="text-[11px] font-medium {tool.isError
										? 'text-rose-500'
										: tool.done
											? 'text-emerald-500'
											: 'text-sky-500'}"
								>
									{#if tool.isError}
										Erro
									{:else if tool.done}
										✓
									{:else}
										<span class="inline-block size-1.5 rounded-full bg-sky-500 animate-ping"></span>
									{/if}
								</span>
							</div>
						</button>

						{#if tool.expanded}
							<div class="border-t border-gray-200/60 dark:border-gray-800/80 bg-gray-950/95 px-3 py-2.5 text-[11px] text-gray-300 space-y-2">
								<!-- Bash command view -->
								{#if tool.name === 'Bash' && tool.input?.command}
									<div class="flex items-start justify-between gap-2 rounded-lg bg-black/50 border border-gray-800 px-2.5 py-1.5 font-mono text-[11px]">
										<div class="min-w-0 break-all">
											<span class="text-sky-400 select-none">$ </span>
											<span class="text-gray-100">{tool.input.command}</span>
										</div>
										<button
											type="button"
											class="shrink-0 text-[10px] text-gray-400 hover:text-sky-400"
											on:click={() => dispatch('copy', tool.input?.command || '')}
										>
											Copiar
										</button>
									</div>
								{/if}

								<!-- Inline Edit diff preview -->
								{#if (tool.name === 'Edit' || tool.name === 'MultiEdit') && (tool.input?.old_string || tool.input?.new_string)}
									<div class="rounded-lg border border-gray-800 overflow-hidden font-mono text-[10.5px]">
										{#if tool.input?.old_string}
											<div class="bg-rose-500/12 px-2.5 py-1.5 text-rose-200 whitespace-pre-wrap break-all max-h-32 overflow-y-auto">
												{#each String(tool.input.old_string).split('\n').slice(0, 14) as ln}
													<div><span class="text-rose-400 select-none">- </span>{ln}</div>
												{/each}
											</div>
										{/if}
										{#if tool.input?.new_string}
											<div class="border-t border-gray-800/80 bg-emerald-500/12 px-2.5 py-1.5 text-emerald-200 whitespace-pre-wrap break-all max-h-32 overflow-y-auto">
												{#each String(tool.input.new_string).split('\n').slice(0, 14) as ln}
													<div><span class="text-emerald-400 select-none">+ </span>{ln}</div>
												{/each}
											</div>
										{/if}
									</div>
								{/if}

								<!-- TodoWrite inline checklist -->
								{#if tool.name === 'TodoWrite' && Array.isArray(tool.input?.todos)}
									<div class="space-y-1">
										{#each tool.input.todos as todo}
											<div class="flex items-center gap-2 text-[11px]">
												<span
													class="inline-flex size-4 items-center justify-center rounded-full text-[9px] {todo.status === 'completed'
														? 'bg-emerald-500/20 text-emerald-400'
														: todo.status === 'in_progress'
															? 'bg-sky-500/20 text-sky-400'
															: 'bg-gray-800 text-gray-500'}"
												>
													{todo.status === 'completed' ? '✓' : todo.status === 'in_progress' ? '●' : '○'}
												</span>
												<span class={todo.status === 'completed' ? 'line-through text-gray-500' : 'text-gray-200'}>
													{todo.content}
												</span>
											</div>
										{/each}
									</div>
								{/if}

								<!-- Tool output -->
								{#if tool.result}
									<pre class="max-h-44 overflow-auto whitespace-pre-wrap break-words font-mono text-[10.5px] leading-relaxed {tool.isError ? 'text-rose-300' : 'text-gray-400'}">{tool.result}</pre>
								{:else if !tool.done}
									<div class="text-gray-500 italic">Aguardando retorno da ferramenta…</div>
								{/if}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}
