import { describe, it, expect } from 'vitest';
import { formatBirthDate, parseBirthDate } from './birthDate';
describe('pt-BR birth date', () => {
	const now = new Date('2026-10-11T15:00:00Z');
	it('keeps day and month distinct', () => {
		expect(parseBirthDate('08/04/2008', now)).toBe('2008-04-08');
		expect(formatBirthDate('2008-04-08')).toBe('08/04/2008');
	});
	it('handles blank and leap days', () => {
		expect(parseBirthDate('', now)).toBe('');
		expect(formatBirthDate('')).toBe('');
		expect(parseBirthDate('29/02/2024', now)).toBe('2024-02-29');
	});
	it.each([
		'29/02/2023',
		'31/04/2020',
		'10/13/2020',
		'11/10/2027',
		'2020-04-08',
		'4/8/2008',
		'00/01/2000'
	])('rejects %s', (text) => expect(() => parseBirthDate(text, now)).toThrow());
});
