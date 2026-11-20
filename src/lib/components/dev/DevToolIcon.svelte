<script lang="ts">
	export let name: string = '';
	export let className: string = 'size-3.5';

	$: key = (name || '').toLowerCase();
</script>

{#if key === 'read'}
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class={className}>
		<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 3.75h7.25L15.5 7.5v8.75a1 1 0 0 1-1 1h-10a1 1 0 0 1-1-1V4.75a1 1 0 0 1 1-1Z" />
		<path stroke-linecap="round" stroke-linejoin="round" d="M11.5 3.75V7.5h4M7 10.5h6M7 13.5h4" />
	</svg>
{:else if key === 'edit' || key === 'multiedit' || key === 'write' || key === 'notebookedit'}
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class={className}>
		<path stroke-linecap="round" stroke-linejoin="round" d="m13.75 3.75 2.5 2.5-8.5 8.5-3.25.75.75-3.25 8.5-8.5Z" />
		<path stroke-linecap="round" stroke-linejoin="round" d="M11.75 5.75 14.25 8.25" />
	</svg>
{:else if key === 'bash' || key === 'terminal'}
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class={className}>
		<rect x="2.75" y="3.75" width="14.5" height="12.5" rx="2" />
		<path stroke-linecap="round" stroke-linejoin="round" d="m6.25 8 2.5 2-2.5 2M10.25 12h3.25" />
	</svg>
{:else if key === 'glob' || key === 'grep' || key === 'search'}
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class={className}>
		<circle cx="9" cy="9" r="5.25" />
		<path stroke-linecap="round" d="m13 13 3.75 3.75" />
	</svg>
{:else if key === 'webfetch' || key === 'websearch'}
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class={className}>
		<circle cx="10" cy="10" r="6.75" />
		<path stroke-linecap="round" d="M3.5 10h13M10 3.25c1.8 2 2.75 4.25 2.75 6.75S11.8 14.75 10 16.75C8.2 14.75 7.25 12.5 7.25 10S8.2 5.25 10 3.25Z" />
	</svg>
{:else if key === 'todowrite' || key === 'tasks'}
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class={className}>
		<path stroke-linecap="round" stroke-linejoin="round" d="m4 6.5 1.5 1.5L8 5.25M10.5 6.5h5.5M4 13.25 5.5 14.75 8 12M10.5 13.5h5.5" />
	</svg>
{:else if key === 'agent' || key === 'task'}
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class={className}>
		<path stroke-linecap="round" stroke-linejoin="round" d="M10 3.25 12.1 7.6l4.65.65-3.35 3.25.8 4.65L10 13.95l-4.2 2.2.8-4.65-3.35-3.25 4.65-.65L10 3.25Z" />
	</svg>
{:else if key === 'folder'}
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class={className}>
		<path stroke-linecap="round" stroke-linejoin="round" d="M3 5.5A1.5 1.5 0 0 1 4.5 4h3.3a1.5 1.5 0 0 1 1.15.54l.85 1.02a1.5 1.5 0 0 0 1.15.54h4.55A1.5 1.5 0 0 1 17 7.6v6.9A1.5 1.5 0 0 1 15.5 16h-11A1.5 1.5 0 0 1 3 14.5v-9Z" />
	</svg>
{:else if key === 'branch'}
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class={className}>
		<circle cx="6" cy="5" r="1.75" />
		<circle cx="6" cy="15" r="1.75" />
		<circle cx="14" cy="7.5" r="1.75" />
		<path stroke-linecap="round" d="M6 6.75v6.5M14 9.25c0 2.75-2.5 3.75-8 3.75" />
	</svg>
{:else}
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class={className}>
		<path stroke-linecap="round" stroke-linejoin="round" d="M11.6 3.6a3.75 3.75 0 0 0 4.8 4.8l-7.2 7.2a1.8 1.8 0 0 1-2.55-2.55l7.2-7.2" />
	</svg>
{/if}
