/** Explicit pt-BR input; keep ISO for the API/database. */
export const formatBirthDate = (iso: string) => (iso ? iso.split('-').reverse().join('/') : '');
export function parseBirthDate(text: string, now = new Date()): string {
	if (!text.trim()) return '';
	const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(text.trim());
	if (!match) throw new Error('Use DD/MM/AAAA para a data de nascimento.');
	const [, day, month, year] = match;
	const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
	if (
		date.getUTCFullYear() !== Number(year) ||
		date.getUTCMonth() !== Number(month) - 1 ||
		date.getUTCDate() !== Number(day) ||
		date > now
	)
		throw new Error('Informe uma data de nascimento válida.');
	return `${year}-${month}-${day}`;
}
