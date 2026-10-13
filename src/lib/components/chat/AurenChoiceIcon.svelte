<script lang="ts">
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import Adjustments from '$lib/components/icons/AdjustmentsHorizontal.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import CodeBracket from '$lib/components/icons/CodeBracket.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Document from '$lib/components/icons/DocumentArrowUp.svelte';
	import Mic from '$lib/components/icons/Mic.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';
	export let kind = 'chat';
	const icons = {
		transcribe: Mic,
		speech: Mic,
		chat: ChatBubble,
		image: Photo,
		rapid: Bolt,
		balanced: Adjustments,
		detailed: Sparkles,
		ether: Sparkles,
		impeto: Bolt,
		insight: Cube,
		arquiteto: CodeBracket,
		code: CodeBracket,
		research: GlobeAlt,
		documents: Document,
		auto: Sparkles
	};
	$: icon = icons[kind as keyof typeof icons] ?? ChatBubble;
</script>

{#if kind === 'speech'}
	<svg
		viewBox="0 0 24 24"
		fill="none"
		stroke="currentColor"
		stroke-width="1.5"
		class="size-5"
		aria-hidden="true"
		><path
			stroke-linecap="round"
			stroke-linejoin="round"
			d="M11 5 6 9H3v6h3l5 4V5Zm4 3a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"
		/></svg
	>
{:else}<svelte:component this={icon} className="size-5" />{/if}
