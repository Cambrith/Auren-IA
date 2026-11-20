export type PermissionMode = 'plan' | 'acceptEdits' | 'bypassPermissions';
export type EffortLevel = '' | 'low' | 'medium' | 'high';

export interface DevTodoItem {
	content: string;
	status: 'pending' | 'in_progress' | 'completed' | string;
	priority?: string;
}

export interface ToolCallItem {
	id: string;
	name: string;
	label: string;
	icon: string;
	summary: string;
	input?: Record<string, any>;
	result?: string;
	isError?: boolean;
	done: boolean;
	expanded?: boolean;
	startedAt?: number;
	finishedAt?: number;
}

export interface SystemCardPayload {
	kind: 'status' | 'memory' | 'side_question' | 'model_switch' | 'help';
	title: string;
	subtitle?: string;
	body?: string;
	meta?: Record<string, any>;
}

export interface DevMessage {
	id: string;
	role: 'user' | 'assistant' | 'system_card';
	content: string;
	thinking?: string;
	thinkingExpanded?: boolean;
	attachments?: string[];
	tools: ToolCallItem[];
	toolsCollapsed?: boolean;
	phase: string;
	streaming: boolean;
	durationMs?: number | null;
	modelName?: string;
	isError?: boolean;
	createdAt?: number;
	card?: SystemCardPayload;
}

export interface SlashCommandOption {
	value: string;
	label: string;
	description?: string;
}

export interface SlashCommandItem {
	name: string;
	args: string;
	category: 'Sessão' | 'Execução' | 'Modelo' | 'Ambiente';
	description: string;
	aliases?: string[];
	options?: SlashCommandOption[];
}

export const SLASH_COMMANDS: SlashCommandItem[] = [
	{
		name: '/revisar',
		args: '[arquivo]',
		category: 'Execução',
		description: 'Revisa alterações Git locais apontando bugs, riscos e melhorias',
		aliases: ['/review']
	},
	{
		name: '/planejar',
		args: '[tarefa]',
		category: 'Execução',
		description: 'Ativa modo Planejar (somente leitura) para estruturar a solução',
		aliases: ['/plan']
	},
	{
		name: '/paralela',
		args: '<pergunta>',
		category: 'Sessão',
		description: 'Pergunta rápida lateral sem poluir o contexto principal',
		aliases: ['/btw']
	},
	{
		name: '/compactar',
		args: '',
		category: 'Sessão',
		description: 'Condensa o histórico da conversa para liberar contexto',
		aliases: ['/compact']
	},
	{
		name: '/status',
		args: '',
		category: 'Ambiente',
		description: 'Exibe cartão de diagnóstico do FCC, modelo, provedores e escopo do PC'
	},
	{
		name: '/memoria',
		args: '',
		category: 'Ambiente',
		description: 'Inspeciona instruções do projeto ou o perfil do sistema do PC',
		aliases: ['/memory']
	},
	{
		name: '/perfil',
		args: '[harmonia|sabia|impeto]',
		category: 'Modelo',
		description: 'Alterna entre os perfis inteligentes Harmonia, Sábia e Ímpeto',
		options: [
			{ value: 'harmonia', label: 'Harmonia', description: 'Equilíbrio entre código agêntico e velocidade' },
			{ value: 'sabia', label: 'Sábia', description: 'Máxima profundidade e raciocínio complexo' },
			{ value: 'impeto', label: 'Ímpeto', description: 'Velocidade extrema (<1s) e cota alta' }
		]
	},
	{
		name: '/modo',
		args: '[livre|editar|planejar]',
		category: 'Execução',
		description: 'Alterna a política de permissão de execução (atalho: Shift+Tab)',
		options: [
			{ value: 'livre', label: 'Acesso total', description: 'Controle total do PC sem pedir permissões' },
			{ value: 'editar', label: 'Auto-edição', description: 'Edita arquivos e confirma comandos críticos' },
			{ value: 'planejar', label: 'Planejar', description: 'Somente leitura — analisa antes de alterar' }
		]
	},
	{
		name: '/esforco',
		args: '[padrao|baixo|medio|alto]',
		category: 'Modelo',
		description: 'Ajusta a profundidade do raciocínio do modelo',
		aliases: ['/effort', '/esforço'],
		options: [
			{ value: 'padrao', label: 'Padrão', description: 'Profundidade equilibrada' },
			{ value: 'baixo', label: 'Baixo', description: 'Respostas mais diretas e rápidas' },
			{ value: 'medio', label: 'Médio', description: 'Análise intermediária' },
			{ value: 'alto', label: 'Alto', description: 'Raciocínio profundo para problemas difíceis' }
		]
	},
	{
		name: '/pasta',
		args: '[nenhuma|caminho]',
		category: 'Ambiente',
		description: 'Escolhe uma pasta de projeto ou libera para controle total do PC (sem pasta)',
		aliases: ['/sem-pasta', '/pc', '/cwd'],
		options: [
			{ value: 'nenhuma', label: 'Sem pasta (PC inteiro)', description: 'Operar livremente em todo o computador' },
			{ value: 'escolher', label: 'Escolher pasta…', description: 'Abrir seletor de diretório do projeto' }
		]
	},
	{
		name: '/add-dir',
		args: '',
		category: 'Ambiente',
		description: 'Adiciona um diretório extra acessível ao agente (--add-dir)'
	},
	{
		name: '/exportar',
		args: '',
		category: 'Sessão',
		description: 'Baixa o histórico desta sessão em Markdown (.md)',
		aliases: ['/export']
	},
	{
		name: '/nova',
		args: '',
		category: 'Sessão',
		description: 'Inicia uma nova sessão limpa preservando o histórico salvo',
		aliases: ['/clear', '/new']
	},
	{
		name: '/ajuda',
		args: '',
		category: 'Ambiente',
		description: 'Mostra os comandos slash e atalhos de teclado da Minerva Dev',
		aliases: ['/help']
	}
];
