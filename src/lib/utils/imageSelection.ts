export type ImageModel = {
	id: string;
	name?: string;
	cavren?: {
		label?: string;
		provider?: string;
		available?: boolean;
		image_only?: boolean;
		price_kind?: string;
		capabilities?: { image_generation?: boolean };
	};
};
export const canGenerateImage = (model?: ImageModel) =>
	model?.id !== 'cavren:auto' &&
	model?.cavren?.available !== false &&
	model?.cavren?.capabilities?.image_generation === true;
export const compareProviders = (a: string, b: string) =>
	a.localeCompare(b, 'pt-BR', { sensitivity: 'base', numeric: true });
export function defaultImageModel(models: ImageModel[], preferred: string, current: string) {
	const selected = models.find((m) => m.id === current);
	// A manually chosen compatible model remains the explicit choice, including its cost gate.
	if (canGenerateImage(selected)) return selected;
	const free = models.filter((m) => canGenerateImage(m) && m.cavren?.price_kind === 'free');
	return (
		free.find((m) => m.id === preferred) ??
		free.find((m) => m.id === 'cavren:aihorde:stable_diffusion') ??
		[...free].sort((a, b) =>
			compareProviders(a.cavren?.label ?? a.name ?? a.id, b.cavren?.label ?? b.name ?? b.id)
		)[0]
	);
}
