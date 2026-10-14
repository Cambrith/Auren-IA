<script lang="ts">
	export let className = 'size-4';
	export let strokeWidth = '1.5';
</script>

<svg
	aria-hidden="true"
	xmlns="http://www.w3.org/2000/svg"
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width={strokeWidth}
	stroke-linecap="round"
	stroke-linejoin="round"
	class={className}
>
	<circle cx="10.5" cy="10.5" r="7.5" />
	<ellipse cx="10.5" cy="10.5" rx="3.3" ry="7.5" />
	<path d="M3 10.5h15m-2.2 5.3L21 21" />
</svg>
