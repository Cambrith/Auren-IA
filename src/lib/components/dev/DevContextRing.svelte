<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let tokens = 0;
	export let maxTokens = 190000;
	export let size = 20;
	export let compact = true;

	const dispatch = createEventDispatcher<{ compact: void }>();
	let open = false;

	$: pct = Math.min(100, Math.round((tokens / Math.max(1, maxTokens)) * 100));
	$: radius = 7.5;
	$: circumference = 2 * Math.PI * radius;
	$: dashOffset = circumference - (pct / 100) * circumference;
	$: strokeClass =
		pct >= 80
			? 'stroke-rose-500'
			: pct >= 55
				? 'stroke-amber-500'
				: 'stroke-sky-500';
	$: textClass =
		pct >= 80
			? 'text-rose-500'
			: pct >= 55
				? 'text-amber-500'
				: 'text-sky-500';
</script>

<div
	role="group"
	aria-label="Indicador de contexto"
	class="relative inline-flex items-center"
	on:mouseenter={() => (open = true)}
	on:mouseleave={() => (open = false)}
>
	<button
		type="button"
		class="inline-flex items-center gap-1.5 rounded-lg px-1.5 py-1 text-[11px] text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/80 transition"
		aria-label="Uso estimado da janela de contexto: {pct}%"
		on:click={() => (open = !open)}
	>
		<svg width={size} height={size} viewBox="0 0 20 20" class="-rotate-90 shrink-0">
			<circle
				cx="10"
				cy="10"
				r={radius}
				fill="none"
				stroke-width="2.2"
				class="stroke-gray-200 dark:stroke-gray-700/80"
			/>
			<circle
				cx="10"
				cy="10"
				r={radius}
				fill="none"
				stroke-width="2.2"
				stroke-linecap="round"
				stroke-dasharray={circumference}
				stroke-dashoffset={dashOffset}
				class="{strokeClass} transition-all duration-300"
			/>
		</svg>
		{#if !compact}
			<span class="font-mono tabular-nums {textClass}">{pct}%</span>
		{/if}
	</button>

	{#if open}
		<div
			class="absolute bottom-full right-0 mb-2 w-60 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-3 shadow-xl z-50 text-left"
		>
			<div class="flex items-center justify-between text-xs font-medium text-gray-800 dark:text-gray-100">
				<span>Janela de contexto</span>
				<span class="font-mono tabular-nums {textClass}">{pct}%</span>
			</div>
			<div class="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
				<div
					class="h-full rounded-full transition-all duration-300 {pct >= 80
						? 'bg-rose-500'
						: pct >= 55
							? 'bg-amber-500'
							: 'bg-sky-500'}"
					style="width: {pct}%"
				></div>
			</div>
			<div class="mt-1.5 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400 font-mono tabular-nums">
				<span>~{tokens.toLocaleString('pt-BR')} tokens</span>
				<span>{(maxTokens / 1000).toFixed(0)}k máx</span>
			</div>
			<button
				type="button"
				class="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-lg border border-gray-200 dark:border-gray-700/80 bg-gray-50 dark:bg-gray-850 px-2.5 py-1.5 text-[11px] font-medium text-gray-700 dark:text-gray-200 hover:border-sky-500/50 hover:text-sky-600 dark:hover:text-sky-400 transition"
				on:click={() => {
					open = false;
					dispatch('compact');
				}}
			>
				<span>Compactar contexto (/compactar)</span>
			</button>
		</div>
	{/if}
</div>
