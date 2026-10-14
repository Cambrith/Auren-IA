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
	import Eye from '$lib/components/icons/Eye.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import DocumentChart from '$lib/components/icons/DocumentChartBar.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';
	export let kind = 'chat';
	export let task = '';
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
	// Profiles share IDs with conversation modes but describe different work.
	const profileIcons = {
		auto: { auto: Adjustments },
		code: { ether: Wrench, impeto: Bolt, insight: LightBulb, arquiteto: Cube },
		documents: { ether: Document, impeto: Eye, insight: DocumentChart, arquiteto: DocumentDuplicate },
		research: { ether: ChatBubbleOval, impeto: Search, insight: GlobeAlt, arquiteto: DocumentChart },
		transcribe: { auto: Mic, pt: ChatBubble, en: GlobeAlt }
	};
	$: scoped = profileIcons[task as keyof typeof profileIcons] as Record<string, typeof Mic> | undefined;
	$: icon = scoped?.[kind] ?? icons[kind as keyof typeof icons] ?? ChatBubble;
</script>

{#if kind === 'speech' || task === 'speech'}
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
