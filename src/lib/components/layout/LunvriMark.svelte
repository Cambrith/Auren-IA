<script lang="ts">
	import { lunvriGenerating } from '$lib/stores/lunvri';
	export let active: boolean | undefined = undefined;
</script>

<span class="lunvri-mark" class:active={active ?? $lunvriGenerating} aria-hidden="true">
	{#each [0, 1, 2] as arm}
		<img src="/lunvri-logo.png" alt="" draggable="false" data-arm={arm} />
	{/each}
</span>

<style>
	.lunvri-mark {
		position: relative;
		display: inline-block;
		width: 30px;
		height: 30px;
		flex: none;
		isolation: isolate;
	}
	img {
		position: absolute;
		inset: 3px;
		width: 24px;
		height: 24px;
		object-fit: contain;
		--angle: 0deg;
		--x: 0.8660254;
		--y: -0.5;
		mask-image: conic-gradient(from var(--angle), #000 0deg 120deg, transparent 120deg 360deg);
		-webkit-mask-image: conic-gradient(
			from var(--angle),
			#000 0deg 120deg,
			transparent 120deg 360deg
		);
	}
	img[data-arm='1'] {
		--angle: 120deg;
		--x: 0;
		--y: 1;
	}
	img[data-arm='2'] {
		--angle: 240deg;
		--x: -0.8660254;
		--y: -0.5;
	}
	.active img {
		animation: lunvri-pulse 5.8s cubic-bezier(0.35, 0, 0.25, 1) infinite;
	}
	@keyframes lunvri-pulse {
		0%,
		100% {
			transform: translate(0, 0);
		}
		20% {
			transform: translate(calc(1.5px * var(--x)), calc(1.5px * var(--y)));
		}
		40% {
			transform: translate(calc(4px * var(--x)), calc(4px * var(--y)));
		}
		60% {
			transform: translate(calc(2px * var(--x)), calc(2px * var(--y)));
		}
		80% {
			transform: translate(calc(3px * var(--x)), calc(3px * var(--y)));
		}
		90% {
			transform: translate(calc(1px * var(--x)), calc(1px * var(--y)));
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.active img {
			animation: none;
		}
	}
</style>
