<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	/**
	 * Mascote oficial da Minerva Dev (arte definitiva sem acessórios).
	 * Aparece exclusivamente ao iniciar um novo chat, empoleirada na borda do composer
	 * com pouso suave, respiração orgânica, aura ciano sutil, inclinação atenta ao digitar
	 * e reverência/saudação discreta ao clicar.
	 */
	export let state: 'idle' | 'listening' | 'happy' = 'idle';
	export let size = 104;
	export let interactive = true;

	let landed = false;
	let hovered = false;
	let saluting = false;
	let chirpText = '';
	let chirpIdx = 0;

	let saluteTimer: ReturnType<typeof setTimeout> | null = null;
	let chirpTimer: ReturnType<typeof setTimeout> | null = null;

	const CHIRPS = [
		'Às suas ordens, Mestre.',
		'Pronta para servir.',
		'Em vigília no projeto.',
		'Modo Harmonia ativo.'
	];

	$: isListening = state === 'listening';

	function handleClick() {
		if (!interactive) return;
		saluting = true;
		if (saluteTimer) clearTimeout(saluteTimer);
		saluteTimer = setTimeout(() => {
			saluting = false;
		}, 650);

		chirpText = CHIRPS[chirpIdx % CHIRPS.length];
		chirpIdx += 1;
		if (chirpTimer) clearTimeout(chirpTimer);
		chirpTimer = setTimeout(() => {
			chirpText = '';
		}, 2400);
	}

	onMount(() => {
		requestAnimationFrame(() => {
			landed = true;
		});
	});

	onDestroy(() => {
		if (saluteTimer) clearTimeout(saluteTimer);
		if (chirpTimer) clearTimeout(chirpTimer);
	});
</script>

<button
	type="button"
	class="minerva-owl-root relative inline-flex select-none items-end justify-center border-0 bg-transparent p-0 focus:outline-none {interactive
		? 'cursor-pointer'
		: 'pointer-events-none'}"
	class:landed
	class:hovered
	class:listening={isListening}
	class:saluting
	aria-label="Coruja Mascote da Minerva"
	on:mouseenter={() => (hovered = true)}
	on:mouseleave={() => (hovered = false)}
	on:click={handleClick}
>
	{#if chirpText}
		<span
			class="minerva-chirp pointer-events-none absolute -top-7 right-0 z-30 whitespace-nowrap rounded-full border border-sky-400/30 bg-[#0d1727]/95 px-2.5 py-1 text-[11px] font-medium text-sky-200 shadow-lg backdrop-blur-md"
		>
			{chirpText}
		</span>
	{/if}

	<!-- Aura ciano sutil abaixo das garras pousadas na borda do composer -->
	<span class="minerva-perch-glow pointer-events-none absolute bottom-0 left-1/2 -translate-x-1/2 h-3.5 w-14 rounded-full" aria-hidden="true"></span>

	<!-- Imagem oficial em alta definição com transparência limpa -->
	<img
		src="/minerva-owl-mascot.png"
		alt="Minerva"
		draggable="false"
		style="height: {size}px; width: auto;"
		class="minerva-owl-img relative z-10 block object-contain"
	/>
</button>

<style>
	.minerva-owl-root {
		opacity: 0;
		transform: translateY(-14px) scale(0.94);
		transform-origin: bottom center;
		transition:
			opacity 380ms ease-out,
			transform 540ms cubic-bezier(0.22, 1, 0.36, 1);
	}
	.minerva-owl-root.landed {
		opacity: 1;
		transform: translateY(0) scale(1);
	}
	.minerva-perch-glow {
		background: radial-gradient(ellipse at center, rgba(56, 189, 248, 0.42) 0%, rgba(1, 98, 248, 0.14) 55%, rgba(8, 13, 23, 0) 78%);
		filter: blur(4px);
		opacity: 0.72;
		transition: opacity 260ms ease, transform 260ms ease;
	}
	.minerva-owl-root.hovered .minerva-perch-glow,
	.minerva-owl-root.saluting .minerva-perch-glow {
		opacity: 1;
		transform: translateX(-50%) scaleX(1.18);
	}
	.minerva-owl-img {
		transform-origin: bottom center;
		filter: drop-shadow(0 6px 14px rgba(1, 98, 248, 0.25));
		animation: minerva-breathe 4.4s ease-in-out infinite;
		transition:
			transform 300ms cubic-bezier(0.22, 1, 0.36, 1),
			filter 280ms ease;
	}
	.minerva-owl-root.hovered .minerva-owl-img {
		filter: drop-shadow(0 8px 20px rgba(56, 189, 248, 0.42));
		transform: translateY(-2px) rotate(-2deg);
	}
	.minerva-owl-root.listening .minerva-owl-img {
		transform: translateY(1px) rotate(-4.5deg) scale(0.99);
		filter: drop-shadow(0 6px 18px rgba(89, 224, 243, 0.36));
	}
	.minerva-owl-root.saluting .minerva-owl-img {
		animation: minerva-salute 620ms cubic-bezier(0.34, 1.56, 0.64, 1);
		filter: drop-shadow(0 10px 24px rgba(89, 224, 243, 0.55));
	}
	.minerva-chirp {
		animation: minerva-chirp-in 200ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
	}

	@keyframes minerva-breathe {
		0%,
		100% {
			transform: translateY(0) scaleY(1);
		}
		50% {
			transform: translateY(-1.5px) scaleY(1.015);
		}
	}
	@keyframes minerva-salute {
		0% {
			transform: translateY(0) rotate(0deg) scale(1);
		}
		30% {
			transform: translateY(2px) rotate(-8deg) scale(0.97, 0.96);
		}
		65% {
			transform: translateY(-5px) rotate(2deg) scale(1.03);
		}
		100% {
			transform: translateY(0) rotate(0deg) scale(1);
		}
	}
	@keyframes minerva-chirp-in {
		from {
			opacity: 0;
			transform: translateY(5px) scale(0.95);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.minerva-owl-img,
		.minerva-owl-root.saluting .minerva-owl-img {
			animation: none;
		}
	}
</style>
