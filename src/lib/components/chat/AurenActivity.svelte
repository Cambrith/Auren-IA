<script lang="ts">
	import { onDestroy } from 'svelte';
	import LunvriMark from '$lib/components/layout/LunvriMark.svelte';
	import StatusItem from './Messages/ResponseMessage/StatusHistory/StatusItem.svelte';
	export let phase: 'waiting' | 'searching' | 'organizing' | 'streaming' | 'image' = 'waiting';
	export let description = '';
	export let status: any = null;
	const labels = ['Pensando…', 'Raciocinando…', 'Ponderando…'];
	let index = 0;
	let timer: ReturnType<typeof setInterval> | undefined;
	$: {
		if (timer) clearInterval(timer);
		timer = undefined;
		if (phase === 'waiting' && !description && !status) timer = setInterval(() => (index = (index + 1) % labels.length), 8000);
	}
	$: label = description || (
		phase === 'image'
			? 'Gerando a imagem…'
			: phase === 'searching'
				? 'Pesquisando na web…'
				: phase === 'organizing'
					? 'Organizando as informações…'
					: phase === 'streaming'
						? 'Redigindo a resposta…'
						: labels[index]);
	onDestroy(() => {
		if (timer) clearInterval(timer);
	});
</script>

<div class="auren-activity" role="status" aria-live="polite" aria-atomic="true">
	<LunvriMark active={true} />
	{#if status}<StatusItem {status} />{:else}<span>{label}</span>{/if}
</div>

<style>
	.auren-activity {
		display: flex;
		align-items: center;
		gap: 12px;
		margin: 12px 0;
		color: #a9bdd0;
		font-size: 13px;
		min-height: 38px;
	}
</style>
