<script lang="ts">
	import { onMount } from 'svelte';
	let list: HTMLDivElement;
	onMount(() => {
		let frame = 0;
		const revealSelection = () => {
			cancelAnimationFrame(frame);
			frame = requestAnimationFrame(() => {
				const selected = list.querySelector<HTMLElement>('[aria-checked="true"]');
				if (!selected) return;
				const viewport = list.getBoundingClientRect();
				const item = selected.getBoundingClientRect();
				const scale = viewport.height ? list.clientHeight / viewport.height : 1;
				if (item.top < viewport.top) list.scrollTop -= (viewport.top - item.top) * scale;
				else if (item.bottom > viewport.bottom) list.scrollTop += (item.bottom - viewport.bottom) * scale;
			});
		};
		const changes = new MutationObserver(revealSelection);
		changes.observe(list, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-checked'] });
		const resize = new ResizeObserver(revealSelection);
		resize.observe(list);
		revealSelection();
		return () => { changes.disconnect(); resize.disconnect(); cancelAnimationFrame(frame); };
	});
</script>

<div bind:this={list} class="auren-choice-list"><slot /></div>

<style>
	.auren-choice-list {
		flex: 1 1 auto;
		min-height: 0;
		max-height: min(18rem, 45dvh);
		overflow-y: auto;
		overflow-x: hidden;
		overscroll-behavior: contain;
		scrollbar-gutter: stable;
		scrollbar-width: thin;
		scrollbar-color: #3b5065 transparent;
		scroll-behavior: auto;
	}
	.auren-choice-list::-webkit-scrollbar { width: 5px; }
	.auren-choice-list::-webkit-scrollbar-thumb { background: #3b5065; border-radius: 8px; }
	.auren-choice-list::-webkit-scrollbar-track { background: transparent; }
</style>
