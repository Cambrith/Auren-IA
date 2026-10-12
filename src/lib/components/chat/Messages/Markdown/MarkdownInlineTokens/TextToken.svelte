<script lang="ts">
	import { settings } from '$lib/stores';
	export let token;
	export let done = true;
	let previous = '';
	let fragments: string[] = [];
	$: raw = token?.raw ?? '';
	// Preserve earlier DOM fragments and exact whitespace; animate only newly received prose.
	$: if (raw !== previous) {
		if (raw.startsWith(previous)) fragments = [...fragments, raw.slice(previous.length)];
		else fragments = [raw];
		previous = raw;
	}
</script>

{#if done || !($settings?.chatFadeStreamingText ?? true)}
	{raw}
{:else}
	{#each fragments as fragment, index (index)}<span class="fade-in-token">{fragment}</span>{/each}
{/if}
