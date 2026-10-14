<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		aurenRequest,
		type AurenState,
		type AurenPreferences,
		type AurenImageFile
	} from '$lib/apis/auren';
	let state: AurenState | null = null;
	let prefs: AurenPreferences = {
		image_model_id: '',
		image_width: 512,
		image_height: 512,
		image_steps: 20
	};
	let selected = '';
	let busy = false;
	let generating = false;
	let error = '';
	let prompt = 'Uma esfera azul sobre fundo claro, ilustração simples.';
	let files: AurenImageFile[] = [];
	let billing = false;
	$: imageModels = state?.models?.filter((m) => m.cavren.capabilities.image_generation) ?? [];
	$: model = imageModels.find((m) => m.id === selected);
	$: possibleCost = !!model && model.cavren.price_kind !== 'free';
	onMount(async () => {
		try {
			state = await aurenRequest<AurenState>('state');
			prefs = { ...prefs, ...state.preferences };
			await tick();
			selected =
				prefs.image_model_id ||
				imageModels.find((m) => m.id === 'cavren:aihorde:stable_diffusion')?.id ||
				imageModels.find((m) => m.cavren.price_kind === 'free')?.id ||
				'';
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		}
	});
	async function save() {
		busy = true;
		error = '';
		try {
			prefs = await aurenRequest<AurenPreferences>('preferences', {
				...prefs,
				image_model_id: selected
			});
			window.dispatchEvent(new CustomEvent('auren-image-preferences', { detail: selected }));
			toast.success('Preferências de imagens salvas.');
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
	async function generate() {
		generating = true;
		error = '';
		files = [];
		try {
			prefs = await aurenRequest<AurenPreferences>('preferences', {
				...prefs,
				image_model_id: selected
			});
			window.dispatchEvent(new CustomEvent('auren-image-preferences', { detail: selected }));
			const result = await aurenRequest<{ files?: AurenImageFile[] }>('images/generations', {
				model: selected,
				prompt,
				billing_confirmed: billing
			});
			files = result.files ?? [];
			if (!files.length) throw new Error('O provedor não retornou uma imagem.');
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			generating = false;
		}
	}
</script>

<section class="auren-settings auren-settings-page">
	<header>
		<div>
			<h2>Geração de imagens</h2>
			<p>
				Geradores anunciados no catálogo. Disponibilidade, cota e compatibilidade ainda dependem do
				provedor.
			</p>
		</div>
	</header>
	{#if error}<p role="alert">{error}</p>{/if}
	<form on:submit|preventDefault={save}>
		<label
			>Modelo padrão<select bind:value={selected} on:change={() => (billing = false)}
				><option value="">Escolha um gerador</option>{#each imageModels as item}<option
						value={item.id}
						>{item.cavren.provider_name} — {item.name}{item.cavren.price_kind === 'free'
							? ' · Gratuito'
							: ' · Custo a confirmar'}</option
					>{/each}</select
			></label
		>
		{#if model?.cavren.provider === 'aihorde'}<p class="notice">
				AI Horde usa uma fila comunitária. A disponibilidade varia conforme os trabalhadores e o
				saldo de kudos; não há compra automática.
			</p>
			<div class="fields">
				<label
					>Largura<select bind:value={prefs.image_width}
						>{#each [512, 768, 1024] as n}<option value={n}>{n} px</option>{/each}</select
					></label
				><label
					>Altura<select bind:value={prefs.image_height}
						>{#each [512, 768, 1024] as n}<option value={n}>{n} px</option>{/each}</select
					></label
				><label>Etapas<input type="number" min="5" max="50" bind:value={prefs.image_steps} /></label
				>
			</div>{:else if model}<p class="notice">
				Para este provedor, a Auren envia a descrição e usa os parâmetros nativos do modelo.
				Dimensões e etapas do Horde não são enviadas.
			</p>{/if}
		<button disabled={busy || !selected}>Salvar preferências</button>
	</form>
	<form on:submit|preventDefault={generate}>
		<h3>Verificar geração</h3>
		<label
			>Descrição da imagem<textarea bind:value={prompt} rows="3" maxlength="12000" required
			></textarea></label
		>{#if possibleCost}<label class="check"
				><input type="checkbox" bind:checked={billing} />Autorizo o possível custo desta geração.</label
			>{/if}<button
			disabled={generating || !selected || !prompt.trim() || (possibleCost && !billing)}
			>{generating ? 'Solicitando geração…' : 'Gerar imagem de teste'}</button
		>
		<p>Este teste usa a cota do provedor. A configuração, sozinha, não inicia uma geração.</p>
	</form>
	{#if generating}<p role="status">
			Aguardando o provedor. A fila de imagens pode demorar alguns minutos.
		</p>{/if}
	{#each files as file}<figure>
			<img src={file.url} alt="Imagem gerada pela Auren" />
			<figcaption><a href={file.url} download={file.name}>Salvar imagem gerada</a></figcaption>
		</figure>{/each}
	<p class="notice">
		Na conversa, a tarefa “Gerar imagens” oferece apenas o AI Horde, sem pagamento em dinheiro.
		O modelo salvo recebe a indicação “Padrão” nessa lista quando é compatível. Os demais
		geradores continuam disponíveis nestas configurações para uso futuro.
	</p>
</section>
