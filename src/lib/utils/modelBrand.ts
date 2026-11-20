/** Model families carry their own mark; the hosting provider remains a separate fallback label. */
const HOST_PREFIX_RE =
	/^(?:cerebras|cloudflare|cohere|gemini|groq|huggingface|nvidia_nim|nvidia|open_router|openrouter|openai|anthropic|mistral|deepseek|xai|zai|fireworks|deepinfra|bedrock|ollama)[./]/i;
const HOST_SUFFIX_RE =
	/\s+·\s+(?:Google\s+Gemini|Gemini|Groq|Cerebras|NVIDIA(?:\s+NIM)?|Cohere|Cloudflare|OpenRouter|Hugging\s*Face|OpenAI|Anthropic|Mistral|DeepSeek|xAI|Z\.ai|Fireworks|DeepInfra|Bedrock|Ollama)\s*$/i;

const normalizeProviderKey = (provider = ''): string => {
	const key = provider.trim().toLowerCase();
	if (key === 'nvidia_nim') return 'nvidia';
	if (key === 'open_router') return 'openrouter';
	if (key === 'openai_api') return 'openai';
	if (key === 'mistral_codestral') return 'mistral';
	if (key === 'ollama_cloud' || key === 'local') return 'ollama';
	if (key === 'kimi_code') return 'kimi';
	return key;
};

export function modelBrand(provider = '', modelId = '', name = ''): string {
	const normProvider = normalizeProviderKey(provider);
	if (!modelId && !name) return normProvider === 'gemini' ? 'gemini' : normProvider;
	const cleanId = modelId.replace(HOST_PREFIX_RE, '').replace(/^(?:models|@cf|@hf)\//i, '');
	const cleanName = name.replace(HOST_SUFFIX_RE, '');
	const text = `${cleanId} ${cleanName}`.toLowerCase();
	const families: [RegExp, string][] = [
		[/claude/, 'claude'],
		[/anthropic\//, 'anthropic'],
		[/deepseek/, 'deepseek'],
		[/qwen|\bqwq\b/, 'qwen'],
		[/gemma/, 'gemma'],
		[/gemini|nano[- ]?banana|\blyria[- ]/, 'gemini'],
		[/llama|meta\/|meta-|meta ·|\bmuse[- ]/, 'meta'],
		[/nemotron|nvidia\/|ising-calibration|riva-/, 'nvidia'],
		[/mistral|ministral|magistral|codestral|devstral/, 'mistral'],
		[/command[- ]|c4ai|cohere|tiny-aya|aya-expanse|aya-vision|\bnorth-|\brerank-|\bembed-(?:english|multilingual|v\d)|\bparse-v\d/, 'cohere'],
		[/kimi/, 'kimi'],
		[/moonshot/, 'moonshot'],
		[/glm|z[-.]?ai\/|zai-org\//, 'zai'],
		[/minimax/, 'minimax'],
		[/stepfun|\bstep-\d/, 'stepfun'],
		[/baidu\/|\bernie[- ]/, 'baidu'],
		[/ibm-granite|ibm\/|\bgranite[- ]/, 'ibm'],
		[/liquid\/|\blfm[- ]/, 'liquid'],
		[/inclusionai\/|\bling-\d|antgroup/, 'antgroup'],
		[/microsoft\/|\bphi-\d/, 'microsoft'],
		[/stable[-_ ]?diffusion|sdxl|stability\//, 'stability'],
		[/flux\.|black[- ]forest/, 'flux'],
		[/grok|x-ai\//, 'xai'],
		[/arcee|trinity/, 'arcee'],
		[/perplexity|sonar/, 'perplexity'],
		[/bytedance|seedream/, 'bytedance'],
		[/ai21|jamba/, 'ai21'],
		[/amazon\/|amazon ·|nova[- ]lite|nova[- ]pro|nova[- ]micro/, 'aws'],
		[/openai\/|openai ·|\bgpt[- ]|\bchatgpt|\bwhisper[- ]|\bo[134](?:-|\b)|(?:^|:)openai:/, 'openai'],
		[/google\/|google ·|antigravity/, 'google'],
		[/cloudflare\/|clairic|\bclef(?:[- ]|\b)/, 'cloudflare']
	];
	return families.find(([pattern]) => pattern.test(text))?.[1] || normProvider;
}

export const colorModelBrands = new Set([
	'antgroup',
	'arcee',
	'aws',
	'baidu',
	'bytedance',
	'cerebras',
	'claude',
	'cloudflare',
	'cohere',
	'deepseek',
	'gemini',
	'gemma',
	'google',
	'huggingface',
	'kimi',
	'meta',
	'microsoft',
	'minimax',
	'mistral',
	'nvidia',
	'openrouter',
	'perplexity',
	'qwen',
	'stability',
	'stepfun'
]);

export const localModelBrands = new Set([
	'ai21',
	'aihorde',
	'amazon',
	'antgroup',
	'anthropic',
	'arcee',
	'aws',
	'baidu',
	'bytedance',
	'cerebras',
	'claude',
	'cloudflare',
	'cohere',
	'deepseek',
	'flux',
	'gemini',
	'gemma',
	'google',
	'groq',
	'huggingface',
	'ibm',
	'kimi',
	'liquid',
	'meta',
	'microsoft',
	'minimax',
	'mistral',
	'moonshot',
	'nvidia',
	'ollama',
	'openai',
	'openrouter',
	'perplexity',
	'qwen',
	'stability',
	'stepfun',
	'xai',
	'zai'
]);
