export type AurenOptions = {
	mode_id: string;
	web_search: boolean;
	billing_confirmed: boolean;
	image_generation: boolean;
	task_id?: string;
	mode_manual?: boolean;
	conversation_mode?: string;
	task_models?: Record<string, string>;
	task_modes?: Record<string, string>;
	task_mode_manual?: Record<string, boolean>;
	transcribe_language?: string;
	image_fallback?: boolean;
	image_profile?: string;
	image_profile_manual?: boolean;
	conversation_model?: string;
	image_model?: string;
};
export function activeTask(options: AurenOptions) {
	return options.task_id ?? (options.image_generation ? 'image' : 'chat');
}
export function restoreAurenTask(params: Record<string, unknown>, imageOnly: boolean) {
	return params.auren_task ?? (params.lunvri_image_generation === true || imageOnly ? 'image' : 'chat');
}
export function singleAurenModel(modelIds: string[], available: string[]) {
	return modelIds.length === 1 && available.includes(modelIds[0]) ? modelIds : ['cavren:auto'];
}
export function changeAurenTask(options: AurenOptions, current: string, next: string) {
	const previous = activeTask(options);
	if (next === previous) return { options, model: current };
	const task_models = { ...options.task_models, [previous]: current };
	const task_modes = { ...options.task_modes, [previous]: options.mode_id };
	const task_mode_manual = {
		...options.task_mode_manual,
		[previous]: Boolean(options.mode_manual)
	};
	const conversation_model = previous === 'chat' ? current : options.conversation_model;
	const image_model = previous === 'image' ? current : options.image_model;
	const conversation_mode =
		previous === 'chat' ? options.mode_id : (options.conversation_mode ?? options.mode_id);
	const suggested =
		next === 'code'
			? 'arquiteto'
			: ['research', 'documents'].includes(next)
				? 'insight'
				: conversation_mode;
	return {
		options: {
			...options,
			task_id: next,
			image_generation: next === 'image',
			billing_confirmed: false,
			conversation_model,
			image_model,
			conversation_mode,
			task_models,
			task_modes,
			task_mode_manual,
			mode_manual:
				next === 'auto' ? Boolean(options.mode_manual) : (task_mode_manual[next] ?? false),
			mode_id:
				next === 'auto' && options.mode_manual ? options.mode_id : (task_modes[next] ?? suggested)
		},
		model:
			task_models[next] ??
			(next === 'chat' ? conversation_model : next === 'image' ? image_model : undefined) ??
			'cavren:auto'
	};
}
export function changeTask(options: AurenOptions, current: string, image: boolean) {
	return changeAurenTask(options, current, image ? 'image' : 'chat');
}
