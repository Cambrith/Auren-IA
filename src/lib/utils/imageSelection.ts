export type ImageModel = {
	id: string;
	name?: string;
	cavren?: {
		label?: string;
		provider?: string;
		available?: boolean;
		image_only?: boolean;
		price_kind?: string;
		image_workers?: number;
		capabilities?: { image_generation?: boolean };
	};
};
export const canGenerateImage = (model?: ImageModel) =>
	model?.id !== 'cavren:auto' &&
	model?.cavren?.available !== false &&
	model?.cavren?.capabilities?.image_generation === true;
// The composer offers only the native community route without paid credits.
// Keep the full catalog and future paid-provider setup in Settings.
export const canSelectImageWithoutPayment = (model?: ImageModel) =>
	canGenerateImage(model) &&
	model?.cavren?.provider === 'aihorde' &&
	model?.cavren?.price_kind === 'free';

export function matchesModelSearch(text: string, query: string) {
	const normalize = (value: string) =>
		value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');
	const haystack = normalize(text);
	return normalize(query).trim().split(/\s+/).every((term) => haystack.includes(term));
}
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
		[...free].sort((a, b) => (b.cavren?.image_workers ?? 0) - (a.cavren?.image_workers ?? 0))[0]
	);
}
