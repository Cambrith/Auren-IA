<script lang="ts">
	import { onMount } from 'svelte';
	import { compareProviders } from '$lib/utils/imageSelection';
	import { toast } from 'svelte-sonner';
	import AurenProviderBadge from '$lib/components/common/AurenProviderBadge.svelte';
	import { aurenRequest, type AurenState } from '$lib/apis/auren';
	let state: AurenState | null = null;
	let busy = false;
	let provider = '';
	let key = '';
	let freeTrial = false;
	let error = '';
	const labels: Record<string, string> = {
		unconfigured: 'Não configurado',
		catalog_available: 'Catálogo acessível',
		configured: 'Configurado; geração a verificar',
		vault_unavailable: 'Chave salva; aguardando acesso ao cofre',
		auth_error: 'Chave salva; provedor recusou a consulta',
		unavailable: 'Chave salva; serviço temporariamente indisponível'
	};
	async function load(refresh = false) {
		busy = true;
		error = '';
		try {
			state = await aurenRequest<AurenState>(`state${refresh ? '?refresh=true' : ''}`);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
	async function save() {
		busy = true;
		error = '';
		try {
			await aurenRequest('provider', { provider, key, free_trial: freeTrial });
			key = '';
			provider = '';
			await load(true);
			toast.success('Chave salva no cofre do sistema.');
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
	onMount(() => load());
</script>

<section class="auren-settings auren-settings-page" aria-label="Conexões da Auren">
	<header>
		<div>
			<h2>Conexões da Auren</h2>
			<p>Provedores usados pelo motor local. As credenciais ficam no cofre do sistema.</p>
		</div>
		<button on:click={() => load(true)} disabled={busy}>Revalidar catálogos</button>
	</header>
	{#if error}<p role="alert">{error}</p>{/if}
	{#if state}<div class="connection-grid">
			{#each [...state.connections].sort( (a, b) => compareProviders(a.name, b.name) ) as connection (connection.id)}<article
				>
					<div>
						<div class="connection-brand">
							<AurenProviderBadge provider={connection.id} name={connection.name} /><strong
								>{connection.name}</strong
							>
						</div>
						<span class:healthy={connection.state === 'catalog_available'}
							>{labels[connection.state]}</span
						>
					</div>
					<p>{connection.count} {connection.count <= 1 ? 'modelo' : 'modelos'}</p>
					<button
						disabled={busy}
						on:click={() => {
							provider = connection.id;
							key = '';
							freeTrial = false;
						}}>Configurar chave</button
					>
				</article>{/each}
		</div>{:else if busy}<p role="status">Consultando conexões…</p>{/if}
	{#if provider}<form on:submit|preventDefault={save}>
			<h3>Configurar {state?.connections.find((c) => c.id === provider)?.name}</h3>
			<label
				>Nova chave de API<input
					type="password"
					bind:value={key}
					autocomplete="new-password"
					required
					minlength="8"
					maxlength="1000"
				/></label
			>{#if ['cohere', 'nvidia'].includes(provider)}<label class="check"
					><input type="checkbox" bind:checked={freeTrial} />Esta chave é de teste/desenvolvimento
					gratuito, com cota limitada.</label
				>{/if}
			<p>
				A chave atual permanece no cofre até você salvar uma substituição. O valor não é exibido
				pela interface.
			</p>
			<div>
				<button type="submit" disabled={busy || !key}>Salvar no cofre</button><button
					type="button"
					disabled={busy}
					on:click={() => {
						key = '';
						provider = '';
					}}>Cancelar</button
				>
			</div>
		</form>{/if}
	<p class="notice">
		O uso direto exige uma chave de API válida e, quando houver cobrança, saldo disponível e
		autorização de uso pago. Esses modelos também podem estar disponíveis por meio dos provedores
		conectados.
	</p>
</section>
