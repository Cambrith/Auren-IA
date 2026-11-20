import { describe, expect, it } from 'vitest';
import {
	buildGroupedRows,
	filterConversationModeItems,
	formatCleanModelTitle,
	getCapabilityBadges,
	getModelDisplayMeta,
	getProviderInfo,
	isMinervaModeId,
	sortModelsForSelector
} from './modelSelectorOrg';

describe('modelSelectorOrg', () => {
	it('identifica provedores na ordem de prioridade correta', () => {
		expect(getProviderInfo({}, 'gemini.models/gemini-3.5-flash', 'gemini-3.5-flash · Gemini')).toMatchObject({
			key: 'gemini',
			label: 'Google Gemini',
			chipLabel: 'Gemini'
		});
		expect(getProviderInfo({}, 'groq.openai/gpt-oss-120b', 'openai/gpt-oss-120b · Groq').key).toBe('groq');
		expect(getProviderInfo({}, 'cerebras.gpt-oss-120b', 'gpt-oss-120b · Cerebras').key).toBe('cerebras');
		expect(getProviderInfo({}, 'nvidia.stepfun-ai/step-5-preview', 'stepfun-ai/step-5-preview · NVIDIA').key).toBe(
			'nvidia'
		);
		expect(getProviderInfo({}, 'cohere.command-a-03-2025', 'command-a-03-2025 · Cohere').key).toBe('cohere');
		expect(
			getProviderInfo(
				{},
				'cloudflare.@cf/meta/llama-3.3-70b-instruct-fp8-fast',
				'meta/llama-3.3-70b-instruct-fp8-fast · Cloudflare'
			).key
		).toBe('cloudflare');
		expect(
			getProviderInfo({}, 'openrouter.nvidia/nemotron-3-ultra-550b-a55b:free', 'nvidia/nemotron-3-ultra:free · OpenRouter')
				.key
		).toBe('openrouter');
	});

	it('limpa prefixos técnicos e sufixos repetidos mantendo identificabilidade', () => {
		expect(formatCleanModelTitle('gemini.models/gemini-4-hydrogen', 'gemini-4-hydrogen · Gemini', 'gemini')).toBe(
			'gemini-4-hydrogen'
		);
		expect(
			formatCleanModelTitle(
				'cloudflare.@cf/deepseek-ai/deepseek-r1-distill-qwen-32b',
				'deepseek-ai/deepseek-r1-distill-qwen-32b · Cloudflare',
				'cloudflare'
			)
		).toBe('deepseek-r1-distill-qwen-32b');
		expect(
			formatCleanModelTitle(
				'openrouter.baidu/ernie-5.5-flash-preview:free',
				'baidu/ernie-5.5-flash-preview:free · OpenRouter',
				'openrouter'
			)
		).toBe('ernie-5.5-flash-preview');
		expect(
			formatCleanModelTitle('openrouter.openrouter/free', 'openrouter/free · OpenRouter', 'openrouter')
		).toBe('openrouter/free');
	});

	it('extrai selos de capacidade e fabricante', () => {
		expect(
			getModelDisplayMeta({
				value: 'gemini.models/gemini-3.5-flash',
				label: 'gemini-3.5-flash · Gemini'
			})
		).toMatchObject({
			vendorLabel: 'Google',
			badges: ['Visão', 'Rápido']
		});

		expect(getCapabilityBadges('nvidia.stepfun-ai/step-5-preview', 'step-5-preview')).toContain('Raciocínio');
		expect(getCapabilityBadges('openrouter.cohere/north-mini-code:free', 'north-mini-code')).toEqual([
			'Código',
			'Rápido'
		]);
		expect(getCapabilityBadges('cloudflare.@cf/qwen/qwen2.5-coder-32b-instruct', 'qwen2.5-coder-32b-instruct')).toEqual([
			'Código'
		]);
	});

	it('ordena fixados primeiro, depois provedores e modelos principais no topo', () => {
		const sample = [
			{ value: 'openrouter.liquid/lfm-3-1.7b:free', label: 'liquid/lfm-3-1.7b:free · OpenRouter' },
			{ value: 'gemini.models/gemma-4-31b-it', label: 'gemma-4-31b-it · Gemini' },
			{ value: 'gemini.models/gemini-4-hydrogen', label: 'gemini-4-hydrogen · Gemini' },
			{ value: 'cloudflare.@cf/meta/llama-3.3-70b-instruct-fp8-fast', label: 'meta/llama-3.3-70b · Cloudflare' },
			{ value: 'groq.openai/gpt-oss-120b', label: 'openai/gpt-oss-120b · Groq' }
		];

		const sorted = sortModelsForSelector(sample, ['openrouter.liquid/lfm-3-1.7b:free']);
		expect(sorted.map((s) => s.value)).toEqual([
			'openrouter.liquid/lfm-3-1.7b:free',
			'gemini.models/gemini-4-hydrogen',
			'gemini.models/gemma-4-31b-it',
			'groq.openai/gpt-oss-120b',
			'cloudflare.@cf/meta/llama-3.3-70b-instruct-fp8-fast'
		]);

		const rows = buildGroupedRows(sorted, ['openrouter.liquid/lfm-3-1.7b:free']);
		expect(rows.filter((r) => r.type === 'header').map((r) => r.title)).toEqual([
			'Fixados',
			'Google Gemini',
			'Groq',
			'Cloudflare'
		]);
	});

	it('reconhece modos oficiais da Minerva e restringe seletor de chat apenas a eles', () => {
		expect(isMinervaModeId('minerva.harmonia')).toBe(true);
		expect(isMinervaModeId('minerva.sabia')).toBe(true);
		expect(isMinervaModeId('minerva.impeto')).toBe(true);
		expect(isMinervaModeId('gemini.models/gemini-3.6-flash')).toBe(false);

		const items = [
			{ value: 'gemini.models/gemini-3.6-flash', label: 'gemini-3.6-flash · Gemini' },
			{
				value: 'minerva.impeto',
				label: 'Ímpeto',
				model: { info: { meta: { minerva_mode: 'impeto', mode_badge: 'Velocidade e disponibilidade' } } }
			},
			{
				value: 'minerva.sabia',
				label: 'Sábia',
				model: { info: { meta: { minerva_mode: 'sabia', mode_badge: 'Inteligência máxima' } } }
			},
			{
				value: 'minerva.harmonia',
				label: 'Harmonia',
				model: { info: { meta: { minerva_mode: 'harmonia', mode_badge: 'Equilíbrio e velocidade' } } }
			},
			{ value: 'groq.openai/gpt-oss-120b', label: 'openai/gpt-oss-120b · Groq' }
		];

		const chatItems = filterConversationModeItems(items, false);
		expect(chatItems.map((i) => i.value)).toEqual([
			'minerva.harmonia',
			'minerva.sabia',
			'minerva.impeto'
		]);

		const adminItems = filterConversationModeItems(items, true);
		expect(adminItems).toHaveLength(5);

		expect(getModelDisplayMeta(chatItems[0])).toMatchObject({
			cleanTitle: 'Harmonia',
			vendorLabel: '',
			badges: ['Equilíbrio e velocidade'],
			provider: { key: 'minerva', label: 'Modo da Minerva', badgeProvider: 'minerva' }
		});
		expect(getModelDisplayMeta(chatItems[1])).toMatchObject({
			cleanTitle: 'Sábia',
			vendorLabel: '',
			badges: ['Inteligência máxima'],
			provider: { key: 'minerva', label: 'Modo da Minerva', badgeProvider: 'minerva' }
		});
		expect(getModelDisplayMeta(chatItems[2])).toMatchObject({
			cleanTitle: 'Ímpeto',
			vendorLabel: '',
			badges: ['Velocidade e disponibilidade'],
			provider: { key: 'minerva', label: 'Modo da Minerva', badgeProvider: 'minerva' }
		});
	});
});
