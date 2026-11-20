import { describe, expect, it } from 'vitest';
import {
	allowedRawIds,
	classifyResult,
	cleanName,
	filterModels,
	fromBaseline,
	isBlockedInSelector,
	isChatModel,
	isPaidKind,
	parkedModels,
	loadResults,
	priceKind,
	providerName,
	rawModelId,
	safeToTest,
	summarize,
	testDelayMs,
	workingRawIds,
	type TestResult
} from './centralIA';

const ok = (): TestResult => classifyResult(200, 'ok', 1);
const models = [
	{ id: 'openrouter.a/free:free', name: 'openrouter.A Free', pricing: { prompt: '0', completion: '0' } },
	{ id: 'openrouter.b/paid', name: 'openrouter.B Paid', pricing: { prompt: '0.000001', completion: '0.000002' } },
	{ id: 'groq.llama', name: 'groq.Llama' }
];

describe('centralIA', () => {
	it('classifica as respostas de teste', () => {
		expect(classifyResult(200).kind).toBe('ok');
		expect(classifyResult(402).kind).toBe('sem_saldo');
		expect(classifyResult(429).kind).toBe('limite');
		expect(classifyResult(401).kind).toBe('chave');
		expect(classifyResult(404).kind).toBe('indisponivel');
		expect(classifyResult(500).kind).toBe('erro');
		expect(classifyResult(503, 'currently experiencing high demand').kind).toBe('ocupado');
		expect(classifyResult(0, 'timed out').kind).toBe('ocupado');
		expect(classifyResult(0, 'x'.repeat(500)).detail.length).toBe(200);
		expect(classifyResult(402, 'Purchase pre-paid credits').kind).toBe('sem_saldo');
		expect(classifyResult(429, "quota exceeded ... limit: 0, model: x").kind).toBe('plano_pago');
		expect(classifyResult(429, 'Provider returned error').kind).toBe('limite');
		expect(classifyResult(403, 'Model x is not available on the Workers Free plan').kind).toBe('plano_pago');
		expect(classifyResult(400, 'requires terms acceptance. Please have the org admin accept').kind).toBe('termos');
		expect(classifyResult(404, "Function 'a': Not found for account 'b'").kind).toBe('indisponivel');
		expect(classifyResult(404, 'This model is no longer available to new users').kind).toBe('indisponivel');
		expect(classifyResult(400, 'This model only supports Interactions API.').kind).toBe('nao_chat');
		expect(classifyResult(400, 'AI model does not have config').kind).toBe('indisponivel');
		expect(classifyResult(403, 'This account is not allowed to access @cf/x').kind).toBe('indisponivel');
		expect(isPaidKind('plano_pago') && isPaidKind('sem_saldo') && !isPaidKind('limite')).toBe(true);
	});

	it('só chama de grátis quando o preço informado é zero', () => {
		expect(priceKind(models[0])).toBe('gratis');
		expect(priceKind(models[1])).toBe('pago');
		expect(priceKind(models[2])).toBe('desconhecido');
		expect(priceKind({ id: 'x', pricing: { prompt: '0' } })).toBe('desconhecido');
	});

	it('nunca sugere testar modelos pagos sem pedir', () => {
		expect(safeToTest(models).map((m) => m.id)).toEqual(['openrouter.a/free:free', 'groq.llama']);
	});

	it('não trata embeddings e rerank como modelos de chat', () => {
		expect(isChatModel({ id: 'cohere.embed-v4.0' })).toBe(false);
		expect(isChatModel({ id: 'cohere.rerank-v3.5' })).toBe(false);
		expect(isChatModel({ id: 'cohere.command-r-08-2024' })).toBe(true);
		expect(isChatModel({ id: 'groq.canopylabs/orpheus-v1-english' })).toBe(false);
		expect(safeToTest([{ id: 'x.embed-1' }, { id: 'x.chat-1' }]).map((m) => m.id)).toEqual(['x.chat-1']);
	});

	it('limpa prefixos e nomes de provedor', () => {
		expect(rawModelId('openrouter.a/b:free', 'openrouter')).toBe('a/b:free');
		expect(rawModelId('semprefixo', 'openrouter')).toBe('semprefixo');
		expect(cleanName(models[0], 'openrouter')).toBe('A Free');
		expect(providerName('https://openrouter.ai/api/v1')).toBe('OpenRouter');
		expect(providerName('https://exemplo.com/v1', 'meu')).toBe('meu');
		expect(providerName('lixo')).toBe('lixo');
	});

	it('filtra por busca, estado e preço', () => {
		const results = { [models[0].id]: ok(), [models[1].id]: classifyResult(402) };
		const f = (filter: any, query = '') => filterModels(models, { filter, query, results, prefix: 'openrouter' }).map((m) => m.id);
		expect(f('funcionam')).toEqual([models[0].id]);
		expect(f('falham')).toEqual([]);
		expect(f('exige_pago')).toEqual([models[1].id]);
		expect(f('sem_teste')).toEqual([models[2].id]);
		expect(f('gratis')).toEqual([models[0].id]);
		expect(f('pagos')).toEqual([models[1].id]);
		expect(f('todos', 'paid')).toEqual([models[1].id]);
	});

	it('resume e lista só os que funcionam, sem o prefixo', () => {
		const results = { [models[0].id]: ok(), [models[1].id]: classifyResult(402) };
		expect(summarize(models, results)).toEqual({ total: 3, ok: 1, falha: 0, semTeste: 1, gratis: 1, pagos: 1, exigePago: 1, outra: 0 });
		expect(workingRawIds(models, results, 'openrouter')).toEqual(['a/free:free']);
	});

	it('respeita o limite de 20 por minuto dos gratuitos do OpenRouter', () => {
		expect(testDelayMs(true, true)).toBeGreaterThanOrEqual(3000);
		expect(testDelayMs(false, true)).toBeLessThan(3000);
	});

	it('converte resultados de um arquivo de testes', () => {
		const r = fromBaseline({ testedAt: 5, results: { a: { status: 200, msg: 'ok' }, b: { status: 402, msg: 'x' } } });
		expect(r.a.kind).toBe('ok');
		expect(r.b.kind).toBe('sem_saldo');
		expect(r.b.at).toBe(5);
		expect(fromBaseline(null)).toEqual({});
	});

	it('libera só aprovados e guarda os de outra função', () => {
		const results = {
			[models[0].id]: ok(),
			[models[1].id]: { ...classifyResult(402), kind: 'sem_saldo' as const },
			[models[2].id]: { ...ok(), kind: 'outra_funcao' as const }
		};
		expect(allowedRawIds(models, results, 'openrouter')).toEqual(['a/free:free', 'groq.llama']);
		expect(parkedModels(models, results).map((m) => m.id)).toEqual([models[2].id]);
		expect(summarize(models, results).outra).toBe(1);
		expect(filterModels(models, { filter: 'outra_funcao', results }).length).toBe(1);
	});

	it('o veredito da triagem rigorosa vence o status HTTP', () => {
		const r = fromBaseline({
			testedAt: 1,
			results: { a: { status: 200, msg: 'ok', kind: 'reprovado' }, b: { status: 200, msg: 'ok', kind: 'invalido' } }
		});
		expect(r.a.kind).toBe('reprovado');
		expect(r.b.kind).toBe('ok');
	});

	it('ignora armazenamento corrompido', () => {
		expect(loadResults({ getItem: () => '{quebrado' })).toEqual({});
		expect(loadResults({ getItem: () => '[]' })).toEqual({});
		expect(loadResults(undefined)).toEqual({});
	});

	it('oculta modelos indisponíveis, reprovados, pagos ou de outra função no seletor de conversa', () => {
		const results: Record<string, TestResult> = {
			ok_model: ok(),
			untested_model: undefined as any,
			dead_model: classifyResult(404, 'not found'),
			paid_model: classifyResult(402, 'credits required'),
			failed_model: { ...ok(), kind: 'reprovado' },
			other_fn: { ...ok(), kind: 'outra_funcao' },
			busy_model: classifyResult(503, 'high demand'),
			limited_model: classifyResult(429, 'rate limit')
		};
		expect(isBlockedInSelector('ok_model', results)).toBe(false);
		expect(isBlockedInSelector('missing_model', results)).toBe(false);
		expect(isBlockedInSelector('limited_model', results)).toBe(false);
		expect(isBlockedInSelector('dead_model', results)).toBe(true);
		expect(isBlockedInSelector('paid_model', results)).toBe(true);
		expect(isBlockedInSelector('failed_model', results)).toBe(true);
		expect(isBlockedInSelector('other_fn', results)).toBe(true);
		expect(isBlockedInSelector('busy_model', results)).toBe(true);
	});
});
