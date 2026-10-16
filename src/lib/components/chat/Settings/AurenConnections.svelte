<script lang="ts">
	import { onMount, tick } from 'svelte';
	import Sortable from 'sortablejs';
	import { orderConnections, moveConnection } from '$lib/utils/aurenConnections';
	import { toast } from 'svelte-sonner';
	import AurenProviderBadge from '$lib/components/common/AurenProviderBadge.svelte';
	import { aurenRequest, type AurenState } from '$lib/apis/auren';
	let state: AurenState | null = null;
	let busy = false;
	let provider = '';
	let values: Record<string, string> = {};
	let freeTrial = false;
	let error = '';
	let orderMessage = '';
	let formElement: HTMLFormElement;
	let oauthMessage = '';
	$: connections = state
		? orderConnections(state.connections, state.preferences.connection_order)
		: [];
	$: selected = state?.connections.find((c) => c.id === provider);
	const labels: Record<string, string> = {
		unconfigured: 'Não configurado',
		catalog_available: 'Catálogo acessível',
		configured: 'Configurado; geração a verificar',
		vault_unavailable: 'Chave salva; aguardando acesso ao cofre',
		auth_error: 'Chave salva; provedor recusou a consulta',
		unavailable: 'Chave salva; serviço temporariamente indisponível'
	};
	const checkLabels: Record<string, string> = {
		ok: 'Conexão validada',
		future_credentials: 'Reservado para ativação futura',
		inference_not_run: 'Inferência não executada nesta validação',
		inference_ok: 'Inferência mínima validada',
		account_ok: 'Conta autenticada; inferência a verificar',
		account_blocked: 'Chave ou conta bloqueada no provedor',
		credit_required: 'Saldo ou cobrança a regularizar',
		missing_credential: 'Pendente: credencial ausente',
		rotation_required: 'Pendente: credencial rotacionada',
		missing_account_id: 'Pendente: ID da conta',
		missing_region: 'Pendente: região AWS',
		oauth_required: 'Pendente: autorização OAuth',
		vault_unavailable: 'Aguardando acesso ao cofre',
		auth_error: 'Credencial ou permissão recusada',
		rate_limit: 'Limite de requisições atingido',
		unavailable: 'Serviço temporariamente indisponível',
		endpoint: 'Endpoint incompatível',
		public_catalog: 'Catálogo público; chave a verificar',
		invalid_response: 'Resposta incompatível',
		bedrock_runtime: 'Pendente: runtime e modelo AWS'
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
			await aurenRequest('provider', { provider, fields: values, free_trial: freeTrial });
			values = {};
			if (provider !== 'canva') provider = '';
			await load();
			toast.success('Credenciais salvas no cofre do sistema.');
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
	async function validate(id: string) {
		if (busy) return;
		busy = true;
		error = '';
		try {
			const check = await aurenRequest<NonNullable<AurenState['connections'][number]['check']>>(
				'connections/validate',
				{ provider: id }
			);
			if (state)
				state = {
					...state,
					connections: state.connections.map((c) => (c.id === id ? { ...c, check } : c))
				};
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
	async function authorizeCanva() {
		busy = true;
		error = '';
		try {
			const result = await aurenRequest<{ url: string }>('oauth/canva/start', {});
			const destination = new URL(result.url);
			if (
				destination.origin !== 'https://www.canva.com' ||
				destination.pathname !== '/api/oauth/authorize'
			)
				throw new Error('Endereço de autorização Canva inválido.');
			oauthMessage = 'Conclua a autorização no navegador e depois clique em Validar conexão.';
			// The native Qt page hands external navigation to the system browser.
			// Avoid window.open: Qt may return a handle without displaying a new window.
			window.location.assign(result.url);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
	async function editConnection(id: string) {
		provider = id;
		values = {};
		freeTrial = false;
		oauthMessage = '';
		await tick();
		formElement?.scrollIntoView({ behavior: 'smooth', block: 'start' });
		formElement?.querySelector('h3')?.focus({ preventScroll: true });
	}
	async function reorder(from: number, to: number) {
		if (!state || busy || from === to || to < 0 || to >= connections.length) return;
		const before = state.preferences.connection_order;
		const moved = moveConnection(connections, from, to);
		state = {
			...state,
			preferences: { ...state.preferences, connection_order: moved.map((c) => c.id) }
		};
		busy = true;
		error = '';
		orderMessage = '';
		try {
			const prefs = await aurenRequest<AurenState['preferences']>('preferences', {
				connection_order: moved.map((c) => c.id)
			});
			state = { ...state, preferences: prefs };
			orderMessage = 'Ordem das conexões salva.';
		} catch (e) {
			state = { ...state, preferences: { ...state.preferences, connection_order: before } };
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
	function sortableGrid(node: HTMLElement) {
		const sortable = new Sortable(node, {
			animation: 150,
			forceFallback: true,
			handle: '.connection-drag-handle',
			draggable: 'article[data-connection-id]',
			direction: 'vertical',
			ghostClass: 'connection-dragging',
			onMove: () => !busy,
			onEnd: (event) => {
				const from = event.oldIndex,
					to = event.newIndex;
				if (from == null || to == null || from === to) return;
				// Restore Sortable's DOM move before Svelte applies the keyed data change.
				const item = event.item;
				item.remove();
				node.insertBefore(item, node.children[from] ?? null);
				void reorder(from, to);
			}
		});
		return { destroy: () => sortable.destroy() };
	}
	onMount(() => {
		void load();
		return () => {
			values = {};
		};
	});
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
	{#if orderMessage}<p role="status">{orderMessage}</p>{/if}
	{#if state}
		<div class="connection-grid" use:sortableGrid>
			{#each connections as connection, index (connection.id)}
				<article data-connection-id={connection.id}>
					<button
						class="connection-drag-handle"
						type="button"
						disabled={busy}
						aria-label={`Reordenar ${connection.name}`}
						title="Arraste para reordenar; use as setas para cima e para baixo no teclado"
						on:keydown={(event) => {
							if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
								event.preventDefault();
								void reorder(index, index + (event.key === 'ArrowUp' ? -1 : 1));
							}
						}}>⠿</button
					>
					<div>
						<div class="connection-brand">
							<AurenProviderBadge provider={connection.id} name={connection.name} /><strong
								>{connection.name}</strong
							>
						</div>
						<span
							title={connection.check?.message}
							class:healthy={connection.check
								? connection.check.status === 'success'
								: connection.state === 'catalog_available'}
							>{(connection.check ? checkLabels[connection.check.reason] : undefined) ??
								(connection.auth_kind === 'oauth'
									? 'OAuth; autorização a verificar'
									: labels[connection.state])}</span
						>
					</div>
					<p>
						{connection.auth_kind === 'oauth'
							? 'Integração OAuth 2.0 · Canva'
							: connection.count === 0 && connection.service_type
								? connection.service_type
								: `${connection.count} ${connection.count <= 1 ? 'modelo' : 'modelos'}`}
					</p>
					<button disabled={busy} on:click={() => editConnection(connection.id)}
						>{connection.auth_kind === 'oauth' ? 'Configurar OAuth' : 'Configurar chave'}</button
					>
					<button disabled={busy} on:click={() => validate(connection.id)}>Validar conexão</button>
				</article>
			{/each}
		</div>
	{:else if busy}<p role="status">Consultando conexões…</p>{/if}
	{#if provider}
		<form bind:this={formElement} on:submit|preventDefault={save}>
			<h3 tabindex="-1">Configurar {selected?.name}</h3>
			{#if oauthMessage}<p role="status">{oauthMessage}</p>{/if}
			{#each selected?.fields ?? [{ id: 'key', label: 'Nova chave de API', required: true }] as field (`${provider}:${field.id}`)}
				<label
					>{field.label}<input
						type="password"
						bind:value={values[field.id]}
						autocomplete="new-password"
						maxlength="4096"
						placeholder="Deixe vazio para manter o valor salvo"
					/></label
				>
			{/each}
			{#if selected?.auth_kind === 'oauth'}<p>
					OAuth 2.0 com PKCE. Cadastre no painel Canva uma Redirect URL como
					http://127.0.0.1:8176/oauth/canva/callback e habilite profile:read. Após salvar, use
					Autorizar Canva.
				</p>{/if}
			{#if ['cohere', 'nvidia'].includes(provider)}<label class="check"
					><input type="checkbox" bind:checked={freeTrial} />Esta chave é de teste/desenvolvimento
					gratuito, com cota limitada.</label
				>{/if}
			<p>
				A chave atual permanece no cofre até você salvar uma substituição. O valor não é exibido
				pela interface.
			</p>
			<div>
				<button type="submit" disabled={busy || !Object.values(values).some(Boolean)}
					>Salvar no cofre</button
				>
				{#if selected?.auth_kind === 'oauth'}<button
						type="button"
						disabled={busy}
						on:click={authorizeCanva}>Autorizar Canva</button
					>{/if}
				<button
					type="button"
					disabled={busy}
					on:click={() => {
						values = {};
						provider = '';
					}}>Cancelar</button
				>
			</div>
		</form>
	{/if}
</section>
