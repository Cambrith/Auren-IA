export type AurenModelInfo = {
	label: string;
	provider?: string;
	provider_name?: string;
	available?: boolean;
	image_only?: boolean;
	price_kind: string;
	usage_label?: string;
	context_window?: number;
	capabilities: Record<string, boolean>;
};
export type AurenModel = { id: string; name: string; cavren: AurenModelInfo };
export type AurenPreferences = {
	image_model_id: string;
	image_width: number;
	image_height: number;
	image_steps: number;
};
export type AurenState = {
	connections: { id: string; name: string; state: string; count: number; image_count: number }[];
	models: AurenModel[];
	preferences: AurenPreferences;
	version: string;
	local: boolean;
};
export type AurenImageFile = { name: string; url: string; type: string };
export async function aurenRequest<T = unknown>(path: string, data?: unknown) {
	const response = await fetch(`/api/v1/auren/${path}`, {
		method: data === undefined ? 'GET' : 'POST',
		headers: {
			Authorization: `Bearer ${localStorage.token}`,
			...(data === undefined ? {} : { 'Content-Type': 'application/json' })
		},
		...(data === undefined ? {} : { body: JSON.stringify(data) })
	});
	const result = await response.json();
	if (!response.ok)
		throw new Error(result.detail ?? result.error?.message ?? 'Não foi possível acessar a Auren.');
	return result as T;
}
