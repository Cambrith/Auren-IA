// Auren chooses a compatible route per request after it prepares owned files.
export const routesAurenAttachments = (ids: string[]) =>
	ids.length > 0 && ids.every((id) => id.startsWith('cavren:'));

export function hasNativeAurenAttachments(files: any[]) {
	return files.some((file) => {
		const mime = file.content_type ?? file.file?.meta?.content_type ?? '';
		return file.type === 'image' || /^(image|audio|video)\//.test(mime) ||
			mime === 'application/pdf' || /\.(pdf|png|jpe?g|webp|mp3|wav|ogg|flac|aac|mp4|webm|mov)$/i.test(file.name ?? '');
	});
}
