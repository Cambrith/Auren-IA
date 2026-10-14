<script lang="ts">
	import { modelBrand, colorModelBrands, localModelBrands } from '$lib/utils/modelBrand';
	export let provider = '';
	export let name = '';
	export let modelId = '';
	export let modelName = '';
	export let compact = false;
	let failed = false;
	$: requestedBrand = modelBrand(provider, modelId, modelName);
	$: brand = localModelBrands.has(requestedBrand) ? requestedBrand : provider;
	$: source = localModelBrands.has(brand)
		? `/brand-icons/${brand}.${brand === 'aihorde' ? 'png' : 'svg'}`
		: '';
	$: if (source) failed = false;
</script>

<span class="provider-badge" class:compact title={name} aria-label={name}>
	{#if source && !failed}
		<img
			src={source}
			alt=""
			aria-hidden="true"
			class:mono={!colorModelBrands.has(brand) && brand !== 'aihorde'}
			on:error={() => (failed = true)}
			loading="lazy"
			decoding="async"
		/>
	{:else}
		<svg aria-hidden="true" viewBox="0 0 24 24"
			><path
				d="M5 7h14M5 12h14M5 17h14"
				fill="none"
				stroke="currentColor"
				stroke-width="1.6"
			/><circle cx="8" cy="7" r="2" fill="currentColor" /><circle
				cx="16"
				cy="12"
				r="2"
				fill="currentColor"
			/><circle cx="10" cy="17" r="2" fill="currentColor" /></svg
		>
	{/if}
</span>

<style>
	.provider-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 8px;
		background: #1a2b3d;
		border: 1px solid #2a3b50;
		color: #a9bdd0;
		flex: none;
	}
	img,
	svg {
		width: 20px;
		height: 20px;
		object-fit: contain;
	}
	img.mono {
		filter: brightness(0) invert(1);
	}
	.provider-badge.compact {
		width: 20px;
		height: 20px;
		border: none;
		background: transparent;
		border-radius: 4px;
	}
</style>
