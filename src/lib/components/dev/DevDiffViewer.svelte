<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let file: string = '';
	export let diff: string = '';
	export let loading = false;

	const dispatch = createEventDispatcher<{
		copy: string;
		reviewFile: string;
	}>();

	interface DiffLine {
		type: 'add' | 'del' | 'hunk' | 'meta' | 'ctx';
		text: string;
		oldNum: string;
		newNum: string;
	}

	function parseUnifiedDiff(raw: string): DiffLine[] {
		if (!raw) return [];
		const lines = raw.split('\n');
		const out: DiffLine[] = [];
		let oldLine = 0;
		let newLine = 0;

		for (const line of lines) {
			if (line.startsWith('@@')) {
				const m = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
				if (m) {
					oldLine = parseInt(m[1], 10);
					newLine = parseInt(m[2], 10);
				}
				out.push({ type: 'hunk', text: line, oldNum: '…', newNum: '…' });
			} else if (
				line.startsWith('diff --git') ||
				line.startsWith('index ') ||
				line.startsWith('--- ') ||
				line.startsWith('+++ ')
			) {
				out.push({ type: 'meta', text: line, oldNum: '', newNum: '' });
			} else if (line.startsWith('+')) {
				out.push({
					type: 'add',
					text: line.slice(1),
					oldNum: '',
					newNum: newLine ? String(newLine++) : ''
				});
			} else if (line.startsWith('-')) {
				out.push({
					type: 'del',
					text: line.slice(1),
					oldNum: oldLine ? String(oldLine++) : '',
					newNum: ''
				});
			} else {
				out.push({
					type: 'ctx',
					text: line.startsWith(' ') ? line.slice(1) : line,
					oldNum: oldLine ? String(oldLine++) : '',
					newNum: newLine ? String(newLine++) : ''
				});
			}
		}
		return out;
	}

	$: parsedLines = parseUnifiedDiff(diff);
	$: addedCount = parsedLines.filter((l) => l.type === 'add').length;
	$: removedCount = parsedLines.filter((l) => l.type === 'del').length;
</script>

<div class="border-t border-gray-200/80 dark:border-gray-800 bg-gray-950 text-gray-200">
	<div class="flex items-center justify-between gap-2 border-b border-gray-800/90 bg-gray-900/90 px-2.5 py-1.5 text-[10px]">
		<div class="flex items-center gap-2 font-mono">
			{#if addedCount > 0}
				<span class="text-emerald-400">+{addedCount}</span>
			{/if}
			{#if removedCount > 0}
				<span class="text-rose-400">-{removedCount}</span>
			{/if}
			{#if addedCount === 0 && removedCount === 0 && !loading}
				<span class="text-gray-400">diff</span>
			{/if}
		</div>
		<div class="flex items-center gap-2">
			{#if file}
				<button
					type="button"
					class="rounded px-1.5 py-0.5 text-sky-400 hover:bg-sky-500/15 transition"
					on:click={() => dispatch('reviewFile', file)}
				>
					Revisar com Minerva
				</button>
			{/if}
			{#if diff}
				<button
					type="button"
					class="rounded px-1.5 py-0.5 text-gray-400 hover:bg-gray-800 hover:text-gray-200 transition"
					on:click={() => dispatch('copy', diff)}
				>
					Copiar
				</button>
			{/if}
		</div>
	</div>

	<div class="max-h-72 overflow-auto font-mono text-[10.5px] leading-[1.45]">
		{#if loading}
			<div class="px-3 py-4 text-center text-gray-400">Carregando diff…</div>
		{:else if parsedLines.length === 0}
			<div class="px-3 py-4 text-center text-gray-500">Sem alterações visíveis.</div>
		{:else}
			<table class="w-full border-collapse">
				<tbody>
					{#each parsedLines as row}
						{#if row.type === 'meta'}
							<tr class="bg-gray-900/60 text-gray-500">
								<td colspan="4" class="px-2.5 py-0.5 select-none">{row.text}</td>
							</tr>
						{:else if row.type === 'hunk'}
							<tr class="bg-sky-500/10 text-sky-300">
								<td class="w-7 px-1.5 py-0.5 text-right text-sky-500/70 select-none">…</td>
								<td class="w-7 px-1.5 py-0.5 text-right text-sky-500/70 select-none">…</td>
								<td colspan="2" class="px-2 py-0.5">{row.text}</td>
							</tr>
						{:else}
							<tr
								class={row.type === 'add'
									? 'bg-emerald-500/12 text-emerald-200'
									: row.type === 'del'
										? 'bg-rose-500/12 text-rose-200'
										: 'text-gray-300/90 hover:bg-white/[0.02]'}
							>
								<td class="w-7 border-r border-gray-800/70 px-1.5 text-right text-[9.5px] text-gray-600 select-none tabular-nums">
									{row.oldNum}
								</td>
								<td class="w-7 border-r border-gray-800/70 px-1.5 text-right text-[9.5px] text-gray-600 select-none tabular-nums">
									{row.newNum}
								</td>
								<td
									class="w-4 px-1 text-center select-none {row.type === 'add'
										? 'text-emerald-400'
										: row.type === 'del'
											? 'text-rose-400'
											: 'text-gray-600'}"
								>
									{row.type === 'add' ? '+' : row.type === 'del' ? '-' : ' '}
								</td>
								<td class="pr-3 whitespace-pre">{row.text}</td>
							</tr>
						{/if}
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
</div>
