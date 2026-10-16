<script lang="ts">
	import { modelBrand, localModelBrands } from '$lib/utils/modelBrand';
	import { providerIcons } from '$lib/utils/providerIcons';
	export let provider = '';
	export let name = '';
	export let modelId = '';
	export let modelName = '';
	export let compact = false;
	const monochromeBrands = new Set([
		'anthropic',
		'assemblyai',
		'elevenlabs',
		'groq',
		'ollama',
		'openai',
		'voyage',
		'xai',
		'zai'
	]);
	// Remove only the tile surface at render time; keep the original public assets intact.
	const tileSurfaces: Record<string, string> = {
		bedrock: '#232f3e',
		cerebras: '#ffffff',
		deepgram: '#000000',
		fal: '#ffc4d8',
		hyperbolic: '#1a1a1a'
	};
	const whiteMarksOnGradient = new Set(['canva', 'replicate']);
	$: cutout = tileSurfaces[brand] || whiteMarksOnGradient.has(brand);
	let failed = false;
	$: requestedBrand = modelBrand(provider, modelId, modelName);
	$: brand =
		localModelBrands.has(requestedBrand) || providerIcons[requestedBrand]
			? requestedBrand
			: provider;
	$: source =
		providerIcons[brand]?.src ||
		(localModelBrands.has(brand)
			? `/brand-icons/${brand}.${brand === 'aihorde' ? 'png' : 'svg'}`
			: '');
	$: if (source) failed = false;
</script>

{#if cutout}
	<svg class="surface-filter" aria-hidden="true" width="0" height="0"
		><defs>
			<filter
				id={`provider-cutout-${brand}`}
				color-interpolation-filters="sRGB"
				x="0"
				y="0"
				width="100%"
				height="100%"
			>
				{#if tileSurfaces[brand]}
					<feFlood flood-color={tileSurfaces[brand]} result="surface" />
					<feColorMatrix
						in="SourceGraphic"
						type="matrix"
						values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 0 1"
						result="opaqueColors"
					/>
					<feBlend in="opaqueColors" in2="surface" mode="difference" result="difference" />
					<feColorMatrix
						in="difference"
						type="matrix"
						values={brand === 'deepgram'
							? '0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 2 2 2 0 -0.6'
							: '0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 20 20 20 0 0'}
						result="mark"
					/>
				{:else}
					<feColorMatrix
						in="SourceGraphic"
						type="matrix"
						values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 2.5 2.5 2.5 0 -6.5"
						result="mark"
					/>
				{/if}
				<feComposite in="SourceGraphic" in2="mark" operator="in" />
			</filter></defs
		></svg
	>
{/if}

<span class="provider-badge" class:compact title={name} aria-label={name}>
	{#if source && !failed}
		<img
			src={source}
			class:monochrome={monochromeBrands.has(brand)}
			data-transparent-surface={cutout ? brand : undefined}
			style:filter={cutout ? `url(#provider-cutout-${brand})` : undefined}
			alt=""
			aria-hidden="true"
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
	svg.surface-filter {
		width: 0;
		height: 0;
		position: absolute;
		pointer-events: none;
	}
	.provider-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 8px;
		background: transparent;
		border: none;
		color: #a9bdd0;
		flex: none;
	}
	img,
	svg {
		width: 20px;
		height: 20px;
		object-fit: contain;
	}
	:global(.dark) .provider-badge img.monochrome {
		filter: brightness(0) invert(1);
	}
	.provider-badge.compact {
		width: 20px;
		height: 20px;
		border: none;
		border-radius: 4px;
	}
</style>
