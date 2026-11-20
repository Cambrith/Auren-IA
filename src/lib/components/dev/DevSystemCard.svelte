<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import type { SystemCardPayload } from './types';

	export let id: string;
	export let card: SystemCardPayload;

	const dispatch = createEventDispatcher<{ dismiss: string; copy: string }>();
</script>

<div class="rounded-2xl border border-sky-500/20 bg-sky-500/[0.04] dark:bg-sky-950/20 px-4 py-3 text-xs">
	<div class="flex items-start justify-between gap-3">
		<div class="flex items-center gap-2.5 min-w-0">
			<span class="flex size-6 shrink-0 items-center justify-center rounded-lg bg-sky-500/15 text-sky-600 dark:text-sky-400 font-mono text-[11px] font-semibold">
				{card.kind === 'status'
					? '●'
					: card.kind === 'memory'
						? '◈'
						: card.kind === 'help'
							? '/'
							: '✦'}
			</span>
			<div class="min-w-0">
				<div class="font-semibold text-gray-900 dark:text-gray-100">{card.title}</div>
				{#if card.subtitle}
					<div class="truncate text-[11px] text-gray-500 dark:text-gray-400">{card.subtitle}</div>
				{/if}
			</div>
		</div>
		<button
			type="button"
			class="shrink-0 rounded-md px-1.5 py-0.5 text-gray-400 hover:bg-gray-200/70 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-200 transition"
			aria-label="Fechar cartão"
			on:click={() => dispatch('dismiss', id)}
		>
			×
		</button>
	</div>

	{#if card.body}
		<div class="mt-2.5 border-t border-sky-500/15 pt-2.5 prose dark:prose-invert prose-sm max-w-none text-xs leading-relaxed">
			<Markdown id={`dev-card-${id}`} content={card.body} />
		</div>
	{/if}

	{#if card.meta && card.kind === 'status'}
		<dl class="mt-2.5 grid grid-cols-2 sm:grid-cols-3 gap-2 border-t border-sky-500/15 pt-2.5">
			{#each Object.entries(card.meta) as [k, v]}
				<div class="rounded-lg bg-white/70 dark:bg-gray-900/60 border border-gray-200/60 dark:border-gray-800 px-2.5 py-1.5">
					<dt class="text-[10px] uppercase tracking-wider text-gray-400">{k}</dt>
					<dd class="mt-0.5 truncate font-mono text-[11px] font-medium text-gray-800 dark:text-gray-200" title={String(v)}>
						{v}
					</dd>
				</div>
			{/each}
		</dl>
	{/if}
</div>
