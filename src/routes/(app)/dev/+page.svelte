<script lang="ts">
	import { onDestroy, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		askDevSideQuestion,
		getDevFileDiff,
		getDevGitStatus,
		getDevHistoryItem,
		getDevProjectInfo,
		getDevStatus,
		listDevDirs,
		listDevFiles,
		listDevSessions,
		readDevFile,
		saveDevHistoryItem,
		setDevMode,
		stopDevRun,
		streamDevChat,
		type DevDirEntry,
		type DevFileContentResponse,
		type DevFileEntry,
		type DevGitFile,
		type DevModeInfo,
		type DevModelInfo,
		type DevProjectInfoResponse,
		type DevProviderInfo,
		type DevSessionEntry
	} from '$lib/apis/dev';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import DevComposer from '$lib/components/dev/DevComposer.svelte';
	import DevInspector from '$lib/components/dev/DevInspector.svelte';
	import DevSystemCard from '$lib/components/dev/DevSystemCard.svelte';
	import DevToolIcon from '$lib/components/dev/DevToolIcon.svelte';
	import DevToolTimeline from '$lib/components/dev/DevToolTimeline.svelte';
	import {
		SLASH_COMMANDS,
		type DevMessage,
		type DevTodoItem,
		type EffortLevel,
		type PermissionMode
	} from '$lib/components/dev/types';
	import { get } from 'svelte/store';
	import { showSidebar } from '$lib/stores';
	import {
		devActiveHistoryId,
		devLiveSessions,
		devNewSessionTrigger,
		persistDevLiveSession,
		reloadDevHistory,
		updateDevLiveSession,
		type DevLiveSession
	} from '$lib/stores/dev';

	// Estado do motor FCC & Minerva
	let loadingStatus = true;
	let fccOnline = false;
	let claudeInstalled = false;
	let activeModel = '';
	let activeModelName = '';
	let activeMode: string | null = 'harmonia';
	let providers: DevProviderInfo[] = [];
	let modes: DevModeInfo[] = [];
	let models: DevModelInfo[] = [];

	// Estado da sessão e workspace
	let cwd = '';
	let extraDirs: string[] = [];
	let attachedFiles: string[] = [];
	let currentConvId: string | null = null;
	let lastLoadedConvId: string | null = null;
	let lastNewTrigger = 0;
	let sessionId: string | null = null;
	let permissionMode: PermissionMode = 'bypassPermissions';
	let effort: EffortLevel = '';
	let promptText = '';
	let queuedPrompt: string | null = null;
	let messages: DevMessage[] = [];
	let isStreaming = false;
	let activeRunId: string | null = null;
	let abortController: AbortController | null = null;
	let mascotMood: 'idle' | 'listening' | 'happy' = 'idle';
	let moodResetTimer: ReturnType<typeof setTimeout> | null = null;

	// Cronômetro ao vivo do turno em andamento (session-turn-status-row)
	let turnStartedAt = 0;
	let turnElapsedSec = 0;
	let elapsedInterval: ReturnType<typeof setInterval> | null = null;

	// Inteligência de projeto, Git e Painel Inspetor (começa fechado como no Claude Code Desktop)
	let showInspector = false;
	let inspectorTab: 'changes' | 'files' | 'activity' | 'context' = 'changes';
	let gitIsRepo = false;
	let gitBranch = '';
	let gitFiles: DevGitFile[] = [];
	let selectedDiffFile = '';
	let selectedDiffText = '';
	let loadingDiff = false;
	let projectInfo: DevProjectInfoResponse | null = null;

	// Explorador de arquivos (@ menções + aba Arquivos)
	let projectFiles: DevFileEntry[] = [];
	let fileSearchQuery = '';
	let loadingFiles = false;
	let previewFile: DevFileContentResponse | null = null;
	let loadingPreview = false;
	let fileSearchDebounce: ReturnType<typeof setTimeout> | null = null;

	// Modais
	let showDirModal = false;
	let dirModalMode: 'cwd' | 'extra' = 'cwd';
	let dirBrowserCurrent = '';
	let dirBrowserParent = '';
	let dirBrowserEntries: DevDirEntry[] = [];

	let showSessionsModal = false;
	let recentSessions: DevSessionEntry[] = [];

	let feedContainer: HTMLElement | null = null;
	let composerRef: DevComposer | null = null;
	let userScrolledUp = false;

	// Sessões em execução em paralelo
	$: activeLiveSession = currentConvId ? ($devLiveSessions[currentConvId] ?? null) : null;
	$: if (activeLiveSession) {
		messages = activeLiveSession.messages;
		isStreaming = activeLiveSession.isStreaming;
		activeRunId = activeLiveSession.activeRunId;
		abortController = activeLiveSession.abortController;
		sessionId = activeLiveSession.sessionId;
		queuedPrompt = activeLiveSession.queuedPrompt;
		turnStartedAt = activeLiveSession.turnStartedAt;
	}
	$: backgroundRunningSessions = Object.values($devLiveSessions).filter(
		(s) => s.isStreaming && s.convId !== currentConvId
	);
	$: if (isStreaming && turnStartedAt > 0) {
		turnElapsedSec = Math.max(0, (Date.now() - turnStartedAt) / 1000);
		if (!elapsedInterval) {
			elapsedInterval = setInterval(() => {
				if (isStreaming && turnStartedAt > 0) {
					turnElapsedSec = Math.max(0, (Date.now() - turnStartedAt) / 1000);
				}
			}, 100);
		}
	} else if (!isStreaming && elapsedInterval) {
		clearInterval(elapsedInterval);
		elapsedInterval = null;
	}

	// Reativos derivados
	$: folderName = cwd ? cwd.split('/').filter(Boolean).pop() || cwd : 'PC inteiro';
	$: allTools = messages.flatMap((m) => m.tools || []);
	$: activeModeObj = modes.find((m) => m.id === activeMode) ?? null;
	$: estTokens = Math.round(
		messages.reduce(
			(acc, m) =>
				acc +
				(m.content?.length || 0) +
				(m.thinking?.length || 0) +
				(m.tools || []).reduce((ta, t) => ta + (t.result?.length || 0) + (t.summary?.length || 0), 0),
			0
		) / 4
	);
	$: activeTodos = extractLatestTodos(messages);
	$: resolvedMascotState =
		promptText.trim().length > 0 ? 'listening' : mascotMood;

	$: greeting = (() => {
		const h = new Date().getHours();
		if (h < 12) return 'Bom dia';
		if (h < 18) return 'Boa tarde';
		return 'Boa noite';
	})();

	function extractLatestTodos(list: DevMessage[]): DevTodoItem[] {
		let latest: DevTodoItem[] = [];
		for (const m of list) {
			for (const t of m.tools || []) {
				if (t.name === 'TodoWrite' && Array.isArray(t.input?.todos)) {
					latest = t.input.todos;
				}
			}
		}
		return latest;
	}

	function pulseMascotMood(mood: 'happy' | 'idle') {
		mascotMood = mood;
		if (moodResetTimer) clearTimeout(moodResetTimer);
		moodResetTimer = setTimeout(() => {
			mascotMood = 'idle';
		}, 2400);
	}

	function handleFeedScroll() {
		if (!feedContainer) return;
		const dist =
			feedContainer.scrollHeight - feedContainer.scrollTop - feedContainer.clientHeight;
		if (dist > 90) {
			userScrolledUp = true;
		} else if (dist <= 45) {
			userScrolledUp = false;
		}
	}

	async function scrollToBottom(force = false) {
		if (force) {
			userScrolledUp = false;
		} else if (userScrolledUp) {
			return;
		}
		await tick();
		if (feedContainer && (force || !userScrolledUp)) {
			feedContainer.scrollTop = feedContainer.scrollHeight;
		}
	}

	const CWD_STORAGE_KEY = 'minerva.dev.cwd';

	async function refreshGit() {
		if (!cwd) {
			gitIsRepo = false;
			gitBranch = '';
			gitFiles = [];
			selectedDiffFile = '';
			selectedDiffText = '';
			return;
		}
		const res = await getDevGitStatus(localStorage.token || '', cwd).catch(() => ({
			is_git: false,
			branch: '',
			files: []
		}));
		gitIsRepo = res.is_git;
		gitBranch = res.branch;
		gitFiles = res.files;
		if (selectedDiffFile && !gitFiles.some((f) => f.path === selectedDiffFile)) {
			selectedDiffFile = '';
			selectedDiffText = '';
		}
	}

	async function refreshProjectContext() {
		loadingFiles = true;
		try {
			const [info, filesRes] = await Promise.all([
				getDevProjectInfo(localStorage.token || '', cwd),
				listDevFiles(localStorage.token || '', cwd, fileSearchQuery, 150)
			]);
			projectInfo = info;
			projectFiles = filesRes.files;
		} finally {
			loadingFiles = false;
		}
	}

	function handleFileSearch(query: string) {
		fileSearchQuery = query;
		if (fileSearchDebounce) clearTimeout(fileSearchDebounce);
		fileSearchDebounce = setTimeout(async () => {
			const res = await listDevFiles(localStorage.token || '', cwd, query, 120);
			projectFiles = res.files;
		}, 120);
	}

	async function handlePreviewFile(rawPath: string) {
		if (!rawPath) return;
		let relPath = rawPath.trim();
		if (cwd && relPath.startsWith(cwd)) {
			relPath = relPath.slice(cwd.length).replace(/^\/+/, '');
		}
		showInspector = true;
		inspectorTab = 'files';
		loadingPreview = true;
		try {
			previewFile = await readDevFile(localStorage.token || '', cwd, relPath);
		} catch (err: any) {
			toast.error(err?.message || 'Não foi possível abrir o arquivo.');
			previewFile = null;
		} finally {
			loadingPreview = false;
		}
	}

	async function openFileDiff(filePath: string) {
		if (!cwd) return;
		if (selectedDiffFile === filePath) {
			selectedDiffFile = '';
			selectedDiffText = '';
			return;
		}
		selectedDiffFile = filePath;
		loadingDiff = true;
		try {
			const res = await getDevFileDiff(localStorage.token || '', cwd, filePath);
			selectedDiffText = res.diff;
		} catch {
			selectedDiffText = 'Não foi possível carregar o diff deste arquivo.';
		} finally {
			loadingDiff = false;
		}
	}

	async function loadStatus() {
		loadingStatus = true;
		try {
			const st = await getDevStatus(localStorage.token || '', true);
			fccOnline = st.fcc_online;
			claudeInstalled = st.claude_installed;
			activeModel = st.active_model;
			activeModelName = st.active_model_name;
			activeMode = st.active_mode || 'harmonia';
			providers = st.providers;
			modes = st.modes;
			models = st.models;
			// Permite conversar sem pasta (controle total do PC) por padrão, respeitando escolha explícita salva
			if (typeof localStorage !== 'undefined') {
				const savedCwd = localStorage.getItem(CWD_STORAGE_KEY);
				if (savedCwd !== null) {
					cwd = savedCwd;
				}
			}
			await Promise.all([refreshGit(), refreshProjectContext()]);
		} catch (err: any) {
			toast.error(err?.message || 'Erro ao carregar estado da Minerva Dev.');
		} finally {
			loadingStatus = false;
		}
	}

	function cyclePermissionMode() {
		const order: PermissionMode[] = ['bypassPermissions', 'acceptEdits', 'plan'];
		const next = order[(order.indexOf(permissionMode) + 1) % order.length];
		permissionMode = next;
		const labels: Record<PermissionMode, string> = {
			plan: 'Planejar (somente leitura)',
			acceptEdits: 'Auto-edição',
			bypassPermissions: 'Acesso total (controle total do PC)'
		};
		toast.info(`Permissão: ${labels[next]}`);
	}

	function toggleInspectorPanel() {
		showInspector = !showInspector;
		if (showInspector && !gitIsRepo && inspectorTab === 'changes') {
			inspectorTab = 'files';
		}
	}

	function handleGlobalKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			if (showDirModal) {
				showDirModal = false;
				return;
			}
			if (showSessionsModal) {
				showSessionsModal = false;
				return;
			}
			if (isStreaming) {
				stopGeneration();
				return;
			}
		}

		// Shift+Tab cicla modo de permissão (atalho nativo do Claude Code)
		if (e.key === 'Tab' && e.shiftKey) {
			e.preventDefault();
			e.stopPropagation();
			cyclePermissionMode();
			return;
		}

		// Ctrl+\ ou Cmd+\ alterna o painel direito (suporta layouts ABNT2 e US)
		if (
			(e.ctrlKey || e.metaKey) &&
			!e.altKey &&
			(e.key === '\\' || e.key === '|' || e.code === 'Backslash' || e.code === 'IntlBackslash')
		) {
			e.preventDefault();
			e.stopPropagation();
			toggleInspectorPanel();
		}
	}

	onMount(() => {
		loadStatus();
		reloadDevHistory(localStorage.token || '');
		window.addEventListener('keydown', handleGlobalKeydown, true);
		return () => {
			window.removeEventListener('keydown', handleGlobalKeydown, true);
		};
	});

	onDestroy(() => {
		if (elapsedInterval) clearInterval(elapsedInterval);
		if (moodResetTimer) clearTimeout(moodResetTimer);
		if (fileSearchDebounce) clearTimeout(fileSearchDebounce);
	});

	$: if (
		$devActiveHistoryId &&
		$devActiveHistoryId !== lastLoadedConvId &&
		$devActiveHistoryId !== currentConvId
	) {
		loadSavedConversation($devActiveHistoryId);
	}

	$: if ($devNewSessionTrigger > lastNewTrigger) {
		lastNewTrigger = $devNewSessionTrigger;
		openBlankSessionView();
	}

	function openBlankSessionView() {
		currentConvId = null;
		lastLoadedConvId = null;
		sessionId = null;
		messages = [];
		isStreaming = false;
		activeRunId = null;
		abortController = null;
		attachedFiles = [];
		queuedPrompt = null;
		userScrolledUp = false;
		mascotMood = 'idle';
	}

	async function loadSavedConversation(convId: string) {
		const inMemory = get(devLiveSessions)[convId];
		if (inMemory) {
			currentConvId = inMemory.convId;
			lastLoadedConvId = inMemory.convId;
			const nextCwd = inMemory.cwd || '';
			if (nextCwd !== cwd) {
				cwd = nextCwd;
				void Promise.all([refreshGit(), refreshProjectContext()]);
			} else {
				void refreshGit();
			}
			extraDirs = [...inMemory.extraDirs];
			sessionId = inMemory.sessionId;
			messages = inMemory.messages;
			isStreaming = inMemory.isStreaming;
			activeRunId = inMemory.activeRunId;
			abortController = inMemory.abortController;
			queuedPrompt = inMemory.queuedPrompt;
			turnStartedAt = inMemory.turnStartedAt;
			await scrollToBottom(true);
			return;
		}

		try {
			const rec = await getDevHistoryItem(localStorage.token || '', convId);
			currentConvId = rec.id;
			lastLoadedConvId = rec.id;
			const nextCwd = rec.cwd || '';
			if (nextCwd !== cwd) {
				cwd = nextCwd;
				await Promise.all([refreshGit(), refreshProjectContext()]);
			} else {
				await refreshGit();
			}
			sessionId = rec.session_id || null;
			const loadedMessages = Array.isArray(rec.messages) ? rec.messages : [];
			messages = loadedMessages;
			isStreaming = false;
			activeRunId = null;
			abortController = null;
			queuedPrompt = null;
			devLiveSessions.update((map) => ({
				...map,
				[rec.id]: {
					convId: rec.id,
					title: rec.title || 'Sessão Minerva Dev',
					cwd: nextCwd,
					extraDirs: [...extraDirs],
					sessionId: rec.session_id || null,
					permissionMode,
					effort,
					model: rec.model || activeModel || '',
					modelName: activeModelName,
					messages: loadedMessages,
					isStreaming: false,
					activeRunId: null,
					abortController: null,
					queuedPrompt: null,
					turnStartedAt: 0,
					updatedAt: rec.updated_at || Date.now() / 1000
				}
			}));
			await scrollToBottom(true);
		} catch (err: any) {
			toast.error(err?.message || 'Não foi possível abrir esta conversa Dev.');
		}
	}

	async function persistCurrentConversation() {
		if (!currentConvId) return;
		await persistDevLiveSession(localStorage.token || '', currentConvId, true);
	}

	async function selectMode(modeId: string) {
		try {
			const res = await setDevMode(localStorage.token || '', { mode: modeId });
			activeMode = res.mode;
			activeModel = res.model;
			activeModelName = res.model_name;
			toast.success(res.message);
		} catch (err: any) {
			toast.error(err?.message || 'Falha ao trocar perfil.');
		}
	}

	async function selectManualModel(modelId: string) {
		try {
			const res = await setDevMode(localStorage.token || '', { model: modelId });
			activeMode = res.mode;
			activeModel = res.model;
			activeModelName = res.model_name;
			toast.success(res.message);
		} catch (err: any) {
			toast.error(err?.message || 'Falha ao trocar modelo.');
		}
	}

	async function openDirPicker(target?: string, mode: 'cwd' | 'extra' = 'cwd') {
		dirModalMode = mode;
		try {
			const res = await listDevDirs(localStorage.token || '', target || cwd);
			dirBrowserCurrent = res.current;
			dirBrowserParent = res.parent;
			dirBrowserEntries = res.directories;
			showDirModal = true;
		} catch {
			toast.error('Não foi possível listar as pastas.');
		}
	}

	async function confirmDirectory(path: string) {
		showDirModal = false;
		if (dirModalMode === 'extra') {
			if (path !== cwd && !extraDirs.includes(path)) {
				extraDirs = [...extraDirs, path];
				toast.success(`Pasta extra adicionada: ${path.split('/').pop() || path}`);
			}
			return;
		}
		cwd = path;
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem(CWD_STORAGE_KEY, cwd);
		}
		sessionId = null;
		selectedDiffFile = '';
		selectedDiffText = '';
		previewFile = null;
		attachedFiles = [];
		toast.success(`Projeto ativo: ${path}`);
		await Promise.all([refreshGit(), refreshProjectContext()]);
	}

	async function clearCwd() {
		showDirModal = false;
		cwd = '';
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem(CWD_STORAGE_KEY, '');
		}
		sessionId = null;
		selectedDiffFile = '';
		selectedDiffText = '';
		previewFile = null;
		attachedFiles = [];
		toast.success('Modo PC inteiro (sem pasta fixa) ativado.');
		await Promise.all([refreshGit(), refreshProjectContext()]);
	}

	async function openSessionsPicker() {
		try {
			const res = await listDevSessions(localStorage.token || '', cwd);
			recentSessions = res.sessions;
			showSessionsModal = true;
		} catch {
			toast.error('Erro ao buscar sessões recentes.');
		}
	}

	function resumeSession(id: string) {
		sessionId = id;
		showSessionsModal = false;
		toast.success(`Sessão ${id.slice(0, 8)} retomada.`);
	}

	function startNewSession() {
		const hadRunning = isStreaming;
		devActiveHistoryId.set(null);
		openBlankSessionView();
		toast.success(
			hadRunning
				? 'Nova conversa aberta (a sessão anterior segue trabalhando em paralelo).'
				: 'Nova sessão iniciada.'
		);
	}

	function pushSystemCard(card: NonNullable<DevMessage['card']>) {
		const cardMsg: DevMessage = {
			id: crypto.randomUUID(),
			role: 'system_card',
			content: '',
			tools: [],
			phase: '',
			streaming: false,
			card
		};
		messages = [...messages, cardMsg];
		if (currentConvId) {
			updateDevLiveSession(currentConvId, (s) => ({
				...s,
				messages: [...s.messages, cardMsg]
			}));
		}
		scrollToBottom(true);
	}

	function exportMarkdown() {
		const lines = [`# Sessão Minerva Dev — ${folderName}`, '', `Workspace: \`${cwd}\``, ''];
		for (const m of messages) {
			if (m.role === 'user') {
				lines.push(`## Usuário`, '', m.content, '');
			} else if (m.role === 'assistant') {
				lines.push(`## Minerva Dev`, '', m.content, '');
			}
		}
		const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `minerva-dev-${folderName.replace(/[^a-z0-9_-]/gi, '-')}.md`;
		a.click();
		URL.revokeObjectURL(url);
		toast.success('Conversa exportada em Markdown.');
	}

	async function handleSlashCommand(name: string, raw: string) {
		const arg = raw.slice(raw.indexOf(' ') + 1).trim();
		const hasArg = raw.includes(' ') && arg.length > 0;

		if (name === '/nova') {
			startNewSession();
			return;
		}
		if (name === '/exportar') {
			if (messages.length === 0) {
				toast.info('Nenhuma mensagem para exportar ainda.');
				return;
			}
			exportMarkdown();
			return;
		}
		if (name === '/pasta' || name === '/sem-pasta' || name === '/pc' || name === '/cwd') {
			const low = arg.toLowerCase();
			if (
				name === '/sem-pasta' ||
				name === '/pc' ||
				low === 'nenhuma' ||
				low === 'limpar' ||
				low === 'pc' ||
				low === 'sem-pasta' ||
				low === 'none'
			) {
				await clearCwd();
			} else if (!hasArg || low === 'escolher') {
				await openDirPicker(cwd || undefined, 'cwd');
			} else {
				await confirmDirectory(arg);
			}
			return;
		}
		if (name === '/add-dir') {
			await openDirPicker(cwd || undefined, 'extra');
			return;
		}
		if (name === '/status') {
			const permLabels: Record<PermissionMode, string> = {
				plan: 'Planejar (somente leitura)',
				acceptEdits: 'Auto-edição',
				bypassPermissions: 'Acesso total (controle total do PC)'
			};
			pushSystemCard({
				kind: 'status',
				title: 'Diagnóstico da Minerva Dev',
				subtitle: cwd || 'PC inteiro (sem pasta fixa)',
				meta: {
					'Motor FCC': fccOnline ? 'Online (127.0.0.1:8082)' : 'Offline',
					'Modelo ativo': activeModelName || '—',
					'Perfil': activeModeObj?.label || 'Manual',
					'Permissão': permLabels[permissionMode],
					'Escopo': cwd || 'Controle total do PC ($HOME e /)',
					'Provedores': `${providers.length} ativos`,
					'Git Branch': gitIsRepo ? `${gitBranch} (${gitFiles.length} alt.)` : 'Sem Git'
				}
			});
			return;
		}
		if (name === '/memoria') {
			const mfiles = projectInfo?.memory_files || [];
			if (mfiles.length === 0) {
				pushSystemCard({
					kind: 'memory',
					title: cwd ? 'Memória do Projeto' : 'Memória do Sistema',
					subtitle: cwd || 'PC inteiro (sem pasta fixa)',
					body: 'Nenhum arquivo `MINERVA.md`, `CLAUDE.md`, `AGENTS.md` ou perfil do sistema encontrado.'
				});
			} else {
				const md = mfiles
					.map((f) => `### \`${f.name}\` (${f.lines} linhas)\n\n${f.preview.slice(0, 420)}${f.preview.length > 420 ? '\n…' : ''}`)
					.join('\n\n---\n\n');
				pushSystemCard({
					kind: 'memory',
					title: `${cwd ? 'Memória do Projeto' : 'Memória do Sistema'} (${mfiles.length} ${mfiles.length === 1 ? 'arquivo' : 'arquivos'})`,
					subtitle: cwd || 'PC inteiro (sem pasta fixa)',
					body: md
				});
			}
			return;
		}
		if (name === '/ajuda') {
			const md = SLASH_COMMANDS.map((c) => `- \`${c.name}${c.args ? ' ' + c.args : ''}\` — ${c.description}`).join('\n');
			pushSystemCard({
				kind: 'help',
				title: 'Comandos e Atalhos da Minerva Dev',
				subtitle: 'Shift+Tab troca permissão · @ anexa arquivo · Ctrl+\\ alterna painel · Esc interrompe',
				body: md
			});
			return;
		}
		if (name === '/perfil') {
			if (hasArg) {
				const normalized = arg.toLowerCase().replace('á', 'a').replace('í', 'i');
				await selectMode(normalized);
			} else {
				const order = ['harmonia', 'sabia', 'impeto'];
				const next = order[(order.indexOf(activeMode || 'harmonia') + 1) % order.length];
				await selectMode(next);
			}
			return;
		}
		if (name === '/modo') {
			const low = arg.toLowerCase();
			if (low.includes('plan')) permissionMode = 'plan';
			else if (low.includes('edit') || low.includes('auto')) permissionMode = 'acceptEdits';
			else if (low.includes('livr') || low.includes('total') || low.includes('bypass'))
				permissionMode = 'bypassPermissions';
			else {
				cyclePermissionMode();
				return;
			}
			const labels: Record<PermissionMode, string> = {
				plan: 'Planejar (somente leitura)',
				acceptEdits: 'Auto-edição',
				bypassPermissions: 'Acesso total (controle total do PC)'
			};
			toast.success(`Modo de permissão alterado para: ${labels[permissionMode]}`);
			return;
		}
		if (name === '/esforco') {
			const low = arg.toLowerCase();
			if (!hasArg) {
				const order: EffortLevel[] = ['', 'low', 'medium', 'high'];
				effort = order[(order.indexOf(effort) + 1) % order.length];
			} else if (low.startsWith('b') || low === 'low') effort = 'low';
			else if (low.startsWith('m')) effort = 'medium';
			else if (low.startsWith('a') || low === 'high') effort = 'high';
			else effort = '';
			const labels: Record<EffortLevel, string> = {
				'': 'Padrão',
				low: 'Baixo',
				medium: 'Médio',
				high: 'Alto'
			};
			toast.success(`Esforço ajustado: ${labels[effort]}`);
			return;
		}
		if (name === '/paralela') {
			if (!hasArg) {
				toast.info('Uso: /paralela <sua pergunta rápida>');
				return;
			}
			const toastId = toast.loading('Consultando pergunta paralela…');
			try {
				const res = await askDevSideQuestion(localStorage.token || '', {
					question: arg,
					model: activeModel || null
				});
				toast.dismiss(toastId);
				pushSystemCard({
					kind: 'side_question',
					title: `Pergunta paralela: ${arg}`,
					subtitle: `Respondida fora do contexto principal via ${res.model_name}`,
					body: res.answer
				});
			} catch (err: any) {
				toast.dismiss(toastId);
				toast.error(err?.message || 'Erro na pergunta paralela.');
			}
			return;
		}
		if (name === '/planejar') {
			permissionMode = 'plan';
			if (hasArg) {
				await sendPrompt(arg);
			} else {
				toast.success('Modo Planejar (somente leitura) ativado.');
			}
			return;
		}
		if (name === '/revisar') {
			const prompt = hasArg
				? `Revise cuidadosamente as alterações e o código em \`${arg}\`, apontando bugs, riscos de regressão e melhorias concretas.`
				: gitIsRepo
					? 'Execute git status e git diff e faça uma revisão crítica detalhada das alterações locais, destacando bugs, riscos e pontos de melhoria.'
					: 'Peça ao Mestre qual arquivo ou pasta deseja revisar ou inspecione o contexto recente para apontar bugs, riscos e melhorias.';
			await sendPrompt(prompt);
			return;
		}
		if (name === '/compactar') {
			if (messages.filter((m) => m.role !== 'system_card').length === 0) {
				toast.info('Ainda não há mensagens nesta sessão para compactar.');
				return;
			}
			await sendPrompt(
				'Faça um resumo técnico conciso de tudo que foi descoberto, alterado e decidido até aqui nesta sessão para compactarmos o contexto e seguir de forma enxuta.'
			);
		}
	}

	function toggleToolExpand(msgId: string, toolId: string) {
		const mapFn = (m: DevMessage) =>
			m.id !== msgId
				? m
				: {
						...m,
						tools: m.tools.map((t) => (t.id === toolId ? { ...t, expanded: !t.expanded } : t))
					};
		messages = messages.map(mapFn);
		if (currentConvId) {
			updateDevLiveSession(currentConvId, (s) => ({
				...s,
				messages: s.messages.map(mapFn)
			}));
		}
	}

	function toggleThinkingExpand(msgId: string) {
		const mapFn = (m: DevMessage) =>
			m.id !== msgId ? m : { ...m, thinkingExpanded: !m.thinkingExpanded };
		messages = messages.map(mapFn);
		if (currentConvId) {
			updateDevLiveSession(currentConvId, (s) => ({
				...s,
				messages: s.messages.map(mapFn)
			}));
		}
	}

	async function copyText(txt: string, label = 'Copiado!') {
		try {
			await navigator.clipboard.writeText(txt);
			toast.success(label);
		} catch {
			toast.error('Não foi possível copiar.');
		}
	}

	function setSessionQueue(val: string | null) {
		queuedPrompt = val;
		if (currentConvId) {
			updateDevLiveSession(currentConvId, (s) => ({ ...s, queuedPrompt: val }));
		}
	}

	async function stopGeneration() {
		const targetId = currentConvId;
		setSessionQueue(null);
		if (abortController) {
			abortController.abort();
		}
		if (activeRunId) {
			await stopDevRun(localStorage.token || '', activeRunId).catch(() => {});
		}
		if (targetId) {
			updateDevLiveSession(targetId, (s) => ({
				...s,
				queuedPrompt: null
			}));
		}
	}

	async function sendPrompt(overrideText?: string, targetConvIdOverride?: string) {
		const isForegroundCall = !targetConvIdOverride || targetConvIdOverride === currentConvId;
		const existingSession = targetConvIdOverride
			? get(devLiveSessions)[targetConvIdOverride]
			: currentConvId
				? get(devLiveSessions)[currentConvId]
				: undefined;

		if (existingSession?.isStreaming) return;

		const rawText = (overrideText ?? promptText).trim();
		const filesSnapshot = isForegroundCall ? [...attachedFiles] : [];
		if (!rawText && filesSnapshot.length === 0) return;

		if (!overrideText && isForegroundCall) promptText = '';
		if (isForegroundCall) attachedFiles = [];

		let targetConvId = targetConvIdOverride || currentConvId;
		if (!targetConvId) {
			targetConvId = crypto.randomUUID().replace(/-/g, '').slice(0, 12);
			currentConvId = targetConvId;
			lastLoadedConvId = targetConvId;
			devActiveHistoryId.set(targetConvId);
		}

		const promptForModel =
			filesSnapshot.length > 0
				? `Arquivos em foco: ${filesSnapshot.map((f) => `@${f}`).join(', ')}\n\n${rawText || 'Analise os arquivos citados acima.'}`
				: rawText;

		const userMsg: DevMessage = {
			id: crypto.randomUUID(),
			role: 'user',
			content: rawText || 'Analise os arquivos anexados.',
			attachments: filesSnapshot,
			tools: [],
			phase: '',
			streaming: false,
			createdAt: Date.now()
		};

		const assistantId = crypto.randomUUID();
		const sessionModelName = existingSession?.modelName || activeModelName;
		const assistantMsg: DevMessage = {
			id: assistantId,
			role: 'assistant',
			content: '',
			thinking: '',
			thinkingExpanded: false,
			tools: [],
			phase: 'Minerva está analisando…',
			streaming: true,
			modelName: sessionModelName,
			createdAt: Date.now()
		};

		const sessionAbort = new AbortController();
		const startedAt = Date.now();
		if (isForegroundCall) {
			userScrolledUp = false;
		}
		const baseMessages = existingSession ? existingSession.messages : messages;
		const nextMessages = [...baseMessages, userMsg, assistantMsg];
		const firstUserText =
			nextMessages.find((m) => m.role === 'user')?.content || 'Sessão Minerva Dev';
		const computedTitle =
			existingSession?.title ||
			firstUserText.replace(/\s+/g, ' ').trim().slice(0, 65) ||
			'Sessão Minerva Dev';

		const sessionSnapshot: DevLiveSession = {
			convId: targetConvId,
			title: computedTitle,
			cwd: existingSession ? existingSession.cwd : cwd,
			extraDirs: existingSession ? [...existingSession.extraDirs] : [...extraDirs],
			sessionId: existingSession ? existingSession.sessionId : sessionId,
			permissionMode: existingSession ? existingSession.permissionMode : permissionMode,
			effort: existingSession ? existingSession.effort : effort,
			model: existingSession ? existingSession.model : activeModel || '',
			modelName: sessionModelName,
			messages: nextMessages,
			isStreaming: true,
			activeRunId: null,
			abortController: sessionAbort,
			queuedPrompt: existingSession?.queuedPrompt ?? null,
			turnStartedAt: startedAt,
			updatedAt: Date.now() / 1000
		};

		devLiveSessions.update((map) => ({
			...map,
			[targetConvId!]: sessionSnapshot
		}));

		// Salva IMEDIATAMENTE ao enviar a primeira mensagem para já aparecer na barra lateral
		const token = localStorage.token || '';
		void persistDevLiveSession(token, targetConvId, true);

		if (currentConvId === targetConvId) {
			await scrollToBottom(true);
		}

		const updateAssistant = (updater: (m: DevMessage) => DevMessage) => {
			updateDevLiveSession(targetConvId!, (s) => ({
				...s,
				updatedAt: Date.now() / 1000,
				messages: s.messages.map((m) => (m.id === assistantId ? updater(m) : m))
			}));
		};

		let hadError = false;
		let wasAborted = false;

		try {
			await streamDevChat(
				token,
				{
					prompt: promptForModel,
					cwd: sessionSnapshot.cwd,
					session_id: sessionSnapshot.sessionId,
					permission_mode: sessionSnapshot.permissionMode,
					model: sessionSnapshot.model || null,
					effort: sessionSnapshot.effort || null,
					extra_dirs: sessionSnapshot.extraDirs
				},
				{
					onRun: ({ run_id }) => {
						updateDevLiveSession(targetConvId!, (s) => ({
							...s,
							activeRunId: run_id
						}));
					},
					onInit: ({ session_id }) => {
						if (session_id) {
							updateDevLiveSession(targetConvId!, (s) => ({
								...s,
								sessionId: session_id
							}));
							void persistDevLiveSession(token, targetConvId!, false);
						}
					},
					onThinking: ({ text }) => {
						updateAssistant((m) => ({
							...m,
							thinking: (m.thinking || '') + (text || ''),
							phase: 'Raciocinando…'
						}));
					},
					onText: ({ text: delta }) => {
						updateAssistant((m) => ({
							...m,
							content: m.content + delta,
							phase: 'Respondendo…'
						}));
						if (currentConvId === targetConvId) {
							void scrollToBottom(false);
						}
					},
					onToolUse: ({ name, label, icon, summary, input }) => {
						updateAssistant((m) => {
							let nextContent = m.content;
							if (nextContent && !nextContent.endsWith('\n\n')) {
								nextContent += nextContent.endsWith('\n') ? '\n' : '\n\n';
							}
							return {
								...m,
								content: nextContent,
								phase: `${label}${summary ? ` · ${summary.slice(0, 42)}` : '…'}`,
								tools: [
									...m.tools,
									{
										id: crypto.randomUUID(),
										name,
										label,
										icon,
										summary,
										input,
										done: false,
										expanded: name === 'TodoWrite',
										startedAt: Date.now()
									}
								]
							};
						});
						if (currentConvId === targetConvId) {
							void scrollToBottom(false);
						}
					},
					onToolResult: ({ text: resText, is_error }) => {
						updateAssistant((m) => {
							const tools = [...m.tools];
							if (tools.length > 0) {
								const last = { ...tools[tools.length - 1] };
								last.done = true;
								last.isError = is_error;
								last.result = resText;
								last.finishedAt = Date.now();
								if (is_error) last.expanded = true;
								tools[tools.length - 1] = last;
							}
							return { ...m, tools, phase: 'Avaliando resultado…' };
						});
						void persistDevLiveSession(token, targetConvId!, false);
						if (currentConvId === targetConvId) {
							void scrollToBottom(false);
						}
					},
					onResult: ({ session_id, text: finalText, is_error, duration_ms }) => {
						if (session_id) {
							updateDevLiveSession(targetConvId!, (s) => ({
								...s,
								sessionId: session_id
							}));
						}
						if (is_error) hadError = true;
						updateAssistant((m) => ({
							...m,
							content: (m.content || finalText || '').trim(),
							durationMs: duration_ms ?? Date.now() - startedAt,
							isError: is_error,
							streaming: false,
							phase: ''
						}));
					},
					onError: ({ message }) => {
						hadError = true;
						updateAssistant((m) => ({
							...m,
							content: m.content || `**Erro:** ${message}`,
							isError: true,
							streaming: false,
							phase: ''
						}));
					},
					onDone: () => {
						updateAssistant((m) => ({
							...m,
							durationMs: m.durationMs ?? Date.now() - startedAt,
							streaming: false,
							phase: ''
						}));
						if (currentConvId === targetConvId) {
							void refreshGit();
						}
					}
				},
				sessionAbort.signal
			);
		} catch (err: any) {
			wasAborted = err?.name === 'AbortError';
			if (!wasAborted) hadError = true;
			updateAssistant((m) => ({
				...m,
				content:
					m.content ||
					(wasAborted
						? 'Execução interrompida pelo usuário.'
						: `**Erro:** ${err?.message || 'Falha na requisição.'}`),
				isError: !wasAborted,
				streaming: false,
				phase: ''
			}));
		} finally {
			const finished = updateDevLiveSession(targetConvId!, (s) => ({
				...s,
				isStreaming: false,
				activeRunId: null,
				abortController: null,
				updatedAt: Date.now() / 1000
			}));
			await persistDevLiveSession(token, targetConvId!, true);

			if (currentConvId === targetConvId) {
				pulseMascotMood(hadError ? 'idle' : 'happy');
				await scrollToBottom(false);
			} else if (finished && !wasAborted) {
				toast.success(`Sessão "${finished.title}" concluiu a tarefa em segundo plano.`);
			}

			const nextQueued = finished?.queuedPrompt;
			if (nextQueued && !wasAborted) {
				updateDevLiveSession(targetConvId!, (s) => ({
					...s,
					queuedPrompt: null
				}));
				await sendPrompt(nextQueued, targetConvId!);
			}
		}
	}
</script>

<svelte:head>
	<title>Minerva Dev · {folderName}</title>
</svelte:head>

<div
	class="flex h-screen max-h-[100dvh] w-full flex-1 min-w-0 flex-col {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} bg-white dark:bg-[#080d17] text-gray-900 dark:text-gray-100"
>
	<!-- Barra superior limpa integrada ao fundo do Chat Minerva (#080d17) sem linha divisória -->
	<header
		class="flex h-11 shrink-0 items-center justify-between gap-2 bg-white/90 dark:bg-[#080d17]/95 backdrop-blur-sm px-3"
	>
		<div class="flex items-center gap-2 min-w-0">
			{#if !$showSidebar}
				<button
					type="button"
					class="flex size-7 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-slate-800 hover:text-gray-900 dark:hover:text-slate-100 transition"
					aria-label="Abrir barra lateral"
					on:click={() => showSidebar.set(true)}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
						<path fill-rule="evenodd" d="M2 4.75A.75.75 0 0 1 2.75 4h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 4.75Zm0 10.5a.75.75 0 0 1 .75-.75h14.5a.75.75 0 0 1 0 1.5H2.75a.75.75 0 0 1-.75-.75ZM2 10a.75.75 0 0 1 .75-.75h7.5a.75.75 0 0 1 0 1.5h-7.5A.75.75 0 0 1 2 10Z" clip-rule="evenodd" />
					</svg>
				</button>
			{/if}

			<div class="flex items-center gap-2 shrink-0">
				<span class="font-semibold text-[13px] tracking-tight text-gray-800 dark:text-slate-100">Minerva Dev</span>
			</div>

			{#if messages.length > 0}
				<span class="text-gray-300 dark:text-slate-700">/</span>
				<button
					type="button"
					class="inline-flex items-center gap-1.5 rounded-lg px-2 py-0.5 text-xs text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800/80 hover:text-gray-900 dark:hover:text-slate-100 transition max-w-[220px]"
					title={cwd || 'Sem pasta fixa — controle total do PC'}
					on:click={() => openDirPicker(cwd || undefined, 'cwd')}
				>
					<DevToolIcon
						name={cwd ? 'folder' : 'terminal'}
						className="size-3.5 {cwd ? 'text-sky-400/90' : 'text-emerald-400/90'} shrink-0"
					/>
					<span class="truncate">{folderName}</span>
				</button>
			{/if}
		</div>

		<!-- Ícones de ação minimalistas à direita (estilo topbar do Claude Code Desktop) -->
		<div class="flex items-center gap-1 shrink-0">
			{#if backgroundRunningSessions.length > 0}
				<button
					type="button"
					class="inline-flex items-center gap-1.5 rounded-lg bg-sky-500/12 px-2.5 py-1 text-xs font-medium text-sky-600 dark:text-sky-300 hover:bg-sky-500/20 transition"
					title={`Alternar para: ${backgroundRunningSessions[0].title}`}
					on:click={() => {
						devActiveHistoryId.set(backgroundRunningSessions[0].convId);
					}}
				>
					<span class="size-2 rounded-full bg-sky-400 animate-pulse"></span>
					<span>
						{backgroundRunningSessions.length}
						{backgroundRunningSessions.length === 1 ? 'em paralelo' : 'em paralelo'}
					</span>
				</button>
			{/if}

			<button
				type="button"
				class="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800/80 hover:text-gray-900 dark:hover:text-slate-100 transition"
				title="Retomar sessão recente do CLI"
				on:click={openSessionsPicker}
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class="size-3.5">
					<circle cx="10" cy="10" r="6.75" />
					<path stroke-linecap="round" stroke-linejoin="round" d="M10 6.5V10l2.5 1.5" />
				</svg>
				<span class="hidden sm:inline">Sessões</span>
			</button>

			<button
				type="button"
				class="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800/80 hover:text-gray-900 dark:hover:text-slate-100 transition"
				title="Iniciar nova sessão"
				on:click={startNewSession}
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5">
					<path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z" />
				</svg>
				<span class="hidden sm:inline">Nova</span>
			</button>

			<button
				type="button"
				class="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-medium transition {showInspector
					? 'bg-sky-500/12 text-sky-600 dark:text-sky-400'
					: 'text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800/80 hover:text-gray-900 dark:hover:text-slate-100'}"
				title="Alternar painel lateral (Ctrl+\)"
				on:click={toggleInspectorPanel}
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" class="size-3.5">
					<rect x="2.75" y="3.75" width="14.5" height="12.5" rx="2" />
					<path d="M12.25 3.75v12.5" />
				</svg>
				<span class="hidden sm:inline">Painel</span>
				{#if gitFiles.length > 0}
					<span class="rounded-full bg-sky-500/20 px-1.5 text-[10px] font-semibold tabular-nums">
						{gitFiles.length}
					</span>
				{/if}
			</button>
		</div>
	</header>

	<!-- Corpo dividido: Palco/Conversa + Inspetor Lateral -->
	<div class="relative flex flex-1 min-h-0 overflow-hidden">
		<!-- Coluna Principal -->
		<div class="flex flex-1 min-w-0 flex-col">
			{#if messages.length === 0}
				<!-- START STAGE CENTRALIZADO (calmo e limpo como o epitaxy-start-card do Claude Code Desktop) -->
				<div class="flex flex-1 flex-col items-center justify-center overflow-y-auto px-5 py-8">
					<div class="w-full max-w-[740px]">
						<!-- Cabeçalho editorial minimalista -->
						<div class="mb-6 space-y-1.5 pr-20">
							<h1 class="text-2xl sm:text-[26px] font-medium tracking-tight text-gray-900 dark:text-slate-50">
								{#if cwd}
									{greeting}, o que vamos criar em <span class="text-sky-600 dark:text-sky-400">{folderName}</span>?
								{:else}
									{greeting}, o que vamos fazer no seu <span class="text-sky-600 dark:text-sky-400">PC</span>?
								{/if}
							</h1>
							<div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] leading-5 text-gray-500 dark:text-slate-400">
								{#if !loadingStatus}
									<span class="inline-flex items-center gap-1.5">
										<span class="size-1.5 rounded-full {activeModeObj ? 'bg-sky-400' : 'bg-violet-400'}"></span>
										<span>{activeModeObj ? activeModeObj.label : 'Manual'}</span>
									</span>
									{#if activeModelName}
										<span class="text-gray-300 dark:text-slate-700" aria-hidden="true">·</span>
										<span class="font-medium text-gray-700 dark:text-slate-300">{activeModelName}</span>
									{/if}
									{#if !cwd && permissionMode === 'bypassPermissions'}
										<span class="text-gray-300 dark:text-slate-700" aria-hidden="true">·</span>
										<span class="text-emerald-600 dark:text-emerald-400">Controle total do PC</span>
									{:else if projectInfo?.stack && projectInfo.stack.length > 0}
										<span class="text-gray-300 dark:text-slate-700" aria-hidden="true">·</span>
										<span>{projectInfo.stack.slice(0, 3).join(', ')}</span>
									{/if}
									{#if projectInfo?.memory_files && projectInfo.memory_files.length > 0}
										<span class="text-gray-300 dark:text-slate-700" aria-hidden="true">·</span>
										<button
											type="button"
											class="inline-flex items-center text-sky-600 dark:text-sky-400 hover:underline underline-offset-2"
											title={projectInfo.memory_files[0].name}
											on:click={() => handleSlashCommand('/memoria', '/memoria')}
										>
											{projectInfo.memory_files[0].name === 'minerva_system_profile.md'
												? 'Perfil do sistema'
												: projectInfo.memory_files[0].name}
										</button>
									{/if}
									{#if !claudeInstalled}
										<span class="text-amber-400 font-medium">· CLI Claude ausente</span>
									{/if}
								{:else}
									<span>Conectando ao motor Minerva Dev…</span>
								{/if}
							</div>
						</div>

						<!-- Composer central com a Coruja da Minerva empoleirada na borda -->
						<DevComposer
							bind:this={composerRef}
							bind:value={promptText}
							isStartStage={true}
							{isStreaming}
							mascotState={resolvedMascotState}
							{modes}
							{models}
							{activeMode}
							{activeModel}
							{activeModelName}
							{permissionMode}
							{effort}
							{estTokens}
							{attachedFiles}
							{extraDirs}
							{queuedPrompt}
							{projectFiles}
							{cwd}
							{gitBranch}
							gitDirtyCount={gitFiles.length}
							{fccOnline}
							on:send={(e) => sendPrompt(e.detail)}
							on:copyBranch={() => copyText(gitBranch, 'Branch copiada!')}
							on:queue={(e) => setSessionQueue(e.detail)}
							on:cancelQueue={() => setSessionQueue(null)}
							on:stop={stopGeneration}
							on:selectMode={(e) => selectMode(e.detail)}
							on:selectModel={(e) => selectManualModel(e.detail)}
							on:setPermission={(e) => (permissionMode = e.detail)}
							on:cyclePermission={cyclePermissionMode}
							on:setEffort={(e) => (effort = e.detail)}
							on:openDirPicker={() => openDirPicker(cwd || undefined, 'cwd')}
							on:clearCwd={clearCwd}
							on:addExtraDir={() => openDirPicker(cwd || undefined, 'extra')}
							on:removeExtraDir={(e) => (extraDirs = extraDirs.filter((d) => d !== e.detail))}
							on:addAttachment={(e) => {
								if (!attachedFiles.includes(e.detail)) attachedFiles = [...attachedFiles, e.detail];
							}}
							on:removeAttachment={(e) => (attachedFiles = attachedFiles.filter((f) => f !== e.detail))}
							on:slashCommand={(e) => handleSlashCommand(e.detail.name, e.detail.raw)}
							on:queryFiles={(e) => handleFileSearch(e.detail)}
							on:compact={() => handleSlashCommand('/compactar', '/compactar')}
						/>

						<!-- Comandos e atalhos interativos (clicáveis e via teclado) -->
						<div class="mt-4 flex flex-wrap items-center justify-between gap-2 px-1 text-[11px] text-gray-400/90 dark:text-slate-500">
							<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
								<button
									type="button"
									class="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 hover:bg-gray-100 dark:hover:bg-slate-800/70 hover:text-gray-800 dark:hover:text-slate-200 transition cursor-pointer"
									title="Abrir menu de comandos slash (/)"
									on:click={() => composerRef?.openSlashMenu()}
								>
									<kbd class="font-mono text-[10.5px] text-gray-500 dark:text-slate-400">/</kbd>
									<span>comandos</span>
								</button>
								<button
									type="button"
									class="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 hover:bg-gray-100 dark:hover:bg-slate-800/70 hover:text-gray-800 dark:hover:text-slate-200 transition cursor-pointer"
									title="Mencionar e anexar arquivo (@)"
									on:click={() => composerRef?.openMentionMenu()}
								>
									<kbd class="font-mono text-[10.5px] text-gray-500 dark:text-slate-400">@</kbd>
									<span>arquivos</span>
								</button>
								<button
									type="button"
									class="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 hover:bg-gray-100 dark:hover:bg-slate-800/70 hover:text-gray-800 dark:hover:text-slate-200 transition cursor-pointer"
									title="Alternar modo de permissão (Shift+Tab)"
									on:click={cyclePermissionMode}
								>
									<kbd class="font-mono text-[10.5px] text-gray-500 dark:text-slate-400">Shift+Tab</kbd>
									<span>permissão</span>
								</button>
								<button
									type="button"
									class="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 hover:bg-gray-100 dark:hover:bg-slate-800/70 hover:text-gray-800 dark:hover:text-slate-200 transition cursor-pointer"
									title="Abrir ou fechar painel lateral (Ctrl+\)"
									on:click={toggleInspectorPanel}
								>
									<kbd class="font-mono text-[10.5px] text-gray-500 dark:text-slate-400">Ctrl+\</kbd>
									<span>painel</span>
								</button>
							</div>
							{#if projectInfo?.recent_commits && projectInfo.recent_commits.length > 0}
								<span class="truncate max-w-xs font-mono text-[10.5px]" title={projectInfo.recent_commits[0].subject}>
									{projectInfo.recent_commits[0].hash} · {projectInfo.recent_commits[0].when}
								</span>
							{/if}
						</div>
					</div>
				</div>
			{:else}
				<!-- TRANSCRIPT ATIVO (estilo Claude Code Desktop) -->
				<div
					bind:this={feedContainer}
					on:scroll={handleFeedScroll}
					class="relative flex-1 overflow-y-auto px-4 py-6"
				>
					<div class="mx-auto max-w-3xl space-y-6">
						{#each messages as msg (msg.id)}
							{#if msg.role === 'system_card' && msg.card}
								<DevSystemCard
									id={msg.id}
									card={msg.card}
									on:dismiss={(e) => {
										messages = messages.filter((m) => m.id !== e.detail);
										if (currentConvId) {
											updateDevLiveSession(currentConvId, (s) => ({
												...s,
												messages: s.messages.filter((m) => m.id !== e.detail)
											}));
										}
									}}
									on:copy={(e) => copyText(e.detail)}
								/>
							{:else if msg.role === 'user'}
								<div class="group flex flex-col items-end gap-1">
									<div class="max-w-[88%] rounded-2xl border border-sky-500/20 bg-sky-500/[0.08] dark:bg-sky-500/12 px-4 py-2.5 text-[13.5px] leading-relaxed text-gray-900 dark:text-gray-100">
										{#if msg.attachments && msg.attachments.length > 0}
											<div class="mb-1.5 flex flex-wrap gap-1">
												{#each msg.attachments as af}
													<button
														type="button"
														class="inline-flex items-center gap-1 rounded-md bg-sky-500/15 px-1.5 py-0.5 font-mono text-[10.5px] text-sky-700 dark:text-sky-300 hover:bg-sky-500/25 transition"
														on:click={() => handlePreviewFile(af)}
													>
														@{af}
													</button>
												{/each}
											</div>
										{/if}
										<div class="whitespace-pre-wrap">{msg.content}</div>
									</div>
									<div class="flex items-center gap-2 px-1 text-[10.5px] text-gray-400 opacity-0 group-hover:opacity-100 transition">
										<button
											type="button"
											class="hover:text-sky-500"
											on:click={() => copyText(msg.content, 'Prompt copiado!')}
										>
											Copiar
										</button>
										<button
											type="button"
											class="hover:text-sky-500"
											on:click={() => {
												promptText = msg.content;
												composerRef?.focusInput();
											}}
										>
											Reutilizar
										</button>
									</div>
								</div>
							{:else}
								<!-- Turno da Minerva Dev -->
								<div class="space-y-3">
									<!-- Raciocínio minimalista estilo Claude Code Desktop -->
									{#if msg.thinking}
										<div>
											<button
												type="button"
												class="inline-flex items-center gap-1.5 rounded-lg px-1.5 py-0.5 text-xs text-gray-500 dark:text-slate-400 hover:bg-gray-100/70 dark:hover:bg-slate-800/50 hover:text-gray-800 dark:hover:text-slate-200 transition"
												on:click={() => toggleThinkingExpand(msg.id)}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="size-3.5 transition-transform {msg.thinkingExpanded ? 'rotate-90' : ''}"
												>
													<path
														fill-rule="evenodd"
														d="M7.21 14.77a.75.75 0 0 1 .02-1.06L11.168 10 7.23 6.29a.75.75 0 1 1 1.04-1.08l4.5 4.25a.75.75 0 0 1 0 1.08l-4.5 4.25a.75.75 0 0 1-1.06-.02Z"
														clip-rule="evenodd"
													/>
												</svg>
												<span>Raciocínio</span>
												<span class="font-mono text-[10.5px] opacity-60 tabular-nums">
													· {msg.thinking.length.toLocaleString('pt-BR')} chars
												</span>
											</button>
											{#if msg.thinkingExpanded}
												<div class="mt-1.5 ml-2 border-l-2 border-gray-200 dark:border-slate-800 pl-3 py-1 max-h-56 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-gray-500 dark:text-slate-400">
													{msg.thinking}
												</div>
											{/if}
										</div>
									{/if}

									<!-- Timeline agrupada de Ferramentas -->
									{#if msg.tools.length > 0}
										<DevToolTimeline
											tools={msg.tools}
											streaming={msg.streaming}
											on:toggleTool={(e) => toggleToolExpand(msg.id, e.detail)}
											on:previewFile={(e) => handlePreviewFile(e.detail)}
											on:copy={(e) => copyText(e.detail, 'Comando copiado!')}
										/>
									{/if}

									<!-- Conteúdo Markdown -->
									{#if msg.content}
										<div class="prose dark:prose-invert max-w-none text-[14px] leading-relaxed">
											<Markdown id={`dev-${msg.id}`} content={msg.content} />
										</div>
									{/if}

									<!-- Linha de Status ao Vivo (session-turn-status-row) com pulso orbital limpo -->
									{#if msg.streaming}
										<div class="flex items-center justify-between gap-3 py-1 text-xs text-gray-500 dark:text-slate-400">
											<div class="flex items-center gap-2.5 min-w-0">
												<span class="inline-flex items-center gap-1 shrink-0" aria-hidden="true">
													<span class="size-1.5 rounded-full bg-sky-400 animate-pulse"></span>
													<span class="size-1.5 rounded-full bg-sky-400/70 animate-pulse" style="animation-delay: 150ms"></span>
													<span class="size-1.5 rounded-full bg-sky-400/40 animate-pulse" style="animation-delay: 300ms"></span>
												</span>
												<span class="truncate text-sky-600 dark:text-sky-300/90">
													{msg.phase || 'Minerva está pensando…'}
												</span>
											</div>
											<div class="flex items-center gap-2 shrink-0 font-mono text-[11px] opacity-75 tabular-nums">
												{#if msg.tools.length > 0}
													<span>{msg.tools.length} {msg.tools.length === 1 ? 'etapa' : 'etapas'}</span>
												{/if}
												{#if msg.content.length > 0}
													<span class="hidden sm:inline">~{msg.content.length.toLocaleString('pt-BR')} chars</span>
												{/if}
												<span class="text-sky-400">{turnElapsedSec.toFixed(1)}s</span>
											</div>
										</div>
									{:else if msg.content || msg.tools.length > 0}
										<!-- Recibo discreto do turno concluído (epitaxy-receipt-at-rest) -->
										<div class="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px] text-gray-400">
											<div class="flex flex-wrap items-center gap-2.5 font-mono tabular-nums">
												<span class={msg.isError ? 'text-rose-500' : 'text-emerald-500'}>
													{msg.isError ? '✖' : '✓'}
													{#if msg.durationMs != null}
														{(msg.durationMs / 1000).toFixed(1)}s
													{/if}
												</span>
												{#if msg.tools.length > 0}
													<span>· {msg.tools.length} {msg.tools.length === 1 ? 'ferramenta' : 'ferramentas'}</span>
												{/if}
												{#if msg.modelName}
													<span class="hidden sm:inline text-gray-400/80">· {msg.modelName}</span>
												{/if}
											</div>
											<div class="flex items-center gap-2.5">
												{#if gitFiles.length > 0 && msg.tools.some((t) => ['Edit', 'MultiEdit', 'Write'].includes(t.name))}
													<button
														type="button"
														class="text-sky-500 hover:underline"
														on:click={() => {
															showInspector = true;
															inspectorTab = 'changes';
														}}
													>
														Ver diff ({gitFiles.length})
													</button>
												{/if}
												{#if msg.content}
													<button
														type="button"
														class="hover:text-sky-500 transition"
														on:click={() => copyText(msg.content, 'Resposta copiada!')}
													>
														Copiar
													</button>
												{/if}
											</div>
										</div>
									{/if}
								</div>
							{/if}
						{/each}
					</div>

					{#if userScrolledUp}
						<div class="pointer-events-none sticky bottom-2 mt-4 flex justify-center z-20">
							<button
								type="button"
								class="pointer-events-auto inline-flex items-center gap-1.5 rounded-full border border-sky-500/30 bg-white/95 dark:bg-[#0f1726]/95 px-3 py-1.5 text-xs font-medium text-sky-600 dark:text-sky-300 shadow-lg backdrop-blur-md hover:bg-sky-50 dark:hover:bg-slate-800 transition"
								on:click={() => scrollToBottom(true)}
							>
								<span>↓</span>
								<span>{isStreaming ? 'Acompanhar execução' : 'Ir para o final'}</span>
							</button>
						</div>
					{/if}
				</div>

				<!-- Composer ancorado inferior (rail-composer-dock, sem linha horizontal divisória) -->
				<div class="shrink-0 bg-white/90 dark:bg-[#080d17]/95 backdrop-blur-sm px-4 py-3">
					<div class="mx-auto max-w-3xl">
						<DevComposer
							bind:this={composerRef}
							bind:value={promptText}
							isStartStage={false}
							{isStreaming}
							mascotState={resolvedMascotState}
							{modes}
							{models}
							{activeMode}
							{activeModel}
							{activeModelName}
							{permissionMode}
							{effort}
							{estTokens}
							{attachedFiles}
							{extraDirs}
							{queuedPrompt}
							{projectFiles}
							{cwd}
							{gitBranch}
							gitDirtyCount={gitFiles.length}
							{fccOnline}
							on:send={(e) => sendPrompt(e.detail)}
							on:copyBranch={() => copyText(gitBranch, 'Branch copiada!')}
							on:queue={(e) => setSessionQueue(e.detail)}
							on:cancelQueue={() => setSessionQueue(null)}
							on:stop={stopGeneration}
							on:selectMode={(e) => selectMode(e.detail)}
							on:selectModel={(e) => selectManualModel(e.detail)}
							on:setPermission={(e) => (permissionMode = e.detail)}
							on:cyclePermission={cyclePermissionMode}
							on:setEffort={(e) => (effort = e.detail)}
							on:openDirPicker={() => openDirPicker(cwd || undefined, 'cwd')}
							on:clearCwd={clearCwd}
							on:addExtraDir={() => openDirPicker(cwd || undefined, 'extra')}
							on:removeExtraDir={(e) => (extraDirs = extraDirs.filter((d) => d !== e.detail))}
							on:addAttachment={(e) => {
								if (!attachedFiles.includes(e.detail)) attachedFiles = [...attachedFiles, e.detail];
							}}
							on:removeAttachment={(e) => (attachedFiles = attachedFiles.filter((f) => f !== e.detail))}
							on:slashCommand={(e) => handleSlashCommand(e.detail.name, e.detail.raw)}
							on:queryFiles={(e) => handleFileSearch(e.detail)}
							on:compact={() => handleSlashCommand('/compactar', '/compactar')}
						/>
						<div class="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 px-1 text-[10.5px] text-gray-400/80 dark:text-slate-500">
							<button
								type="button"
								class="inline-flex items-center gap-1 rounded px-1 py-0.5 hover:bg-gray-100 dark:hover:bg-slate-800/70 hover:text-gray-700 dark:hover:text-slate-300 transition cursor-pointer"
								on:click={() => composerRef?.openSlashMenu()}
							>
								<kbd class="font-mono text-[10px]">/</kbd> comandos
							</button>
							<button
								type="button"
								class="inline-flex items-center gap-1 rounded px-1 py-0.5 hover:bg-gray-100 dark:hover:bg-slate-800/70 hover:text-gray-700 dark:hover:text-slate-300 transition cursor-pointer"
								on:click={() => composerRef?.openMentionMenu()}
							>
								<kbd class="font-mono text-[10px]">@</kbd> arquivos
							</button>
							<button
								type="button"
								class="inline-flex items-center gap-1 rounded px-1 py-0.5 hover:bg-gray-100 dark:hover:bg-slate-800/70 hover:text-gray-700 dark:hover:text-slate-300 transition cursor-pointer"
								on:click={cyclePermissionMode}
							>
								<kbd class="font-mono text-[10px]">Shift+Tab</kbd> permissão
							</button>
							<button
								type="button"
								class="inline-flex items-center gap-1 rounded px-1 py-0.5 hover:bg-gray-100 dark:hover:bg-slate-800/70 hover:text-gray-700 dark:hover:text-slate-300 transition cursor-pointer"
								on:click={toggleInspectorPanel}
							>
								<kbd class="font-mono text-[10px]">Ctrl+\</kbd> painel
							</button>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Painel Inspetor Lateral Direito (desktop fixo + mobile/tablet drawer) -->
		{#if showInspector}
			<div class="hidden lg:block w-[340px] xl:w-[400px] shrink-0 h-full">
				<DevInspector
					bind:tab={inspectorTab}
					{cwd}
					{extraDirs}
					{gitIsRepo}
					{gitBranch}
					{gitFiles}
					{selectedDiffFile}
					{selectedDiffText}
					{loadingDiff}
					{projectFiles}
					{fileSearchQuery}
					{loadingFiles}
					{previewFile}
					{loadingPreview}
					{allTools}
					{activeTodos}
					{estTokens}
					{activeModelName}
					{activeModeObj}
					{providers}
					{projectInfo}
					{sessionId}
					on:close={() => (showInspector = false)}
					on:refreshGit={refreshGit}
					on:openDiff={(e) => openFileDiff(e.detail)}
					on:reviewAll={() => handleSlashCommand('/revisar', '/revisar')}
					on:reviewFile={(e) => handleSlashCommand('/revisar', `/revisar ${e.detail}`)}
					on:searchFiles={(e) => handleFileSearch(e.detail)}
					on:previewFile={(e) => handlePreviewFile(e.detail)}
					on:closePreview={() => (previewFile = null)}
					on:attachFile={(e) => {
						if (!attachedFiles.includes(e.detail)) {
							attachedFiles = [...attachedFiles, e.detail];
							toast.success(`@${e.detail} anexado ao prompt`);
						}
						composerRef?.focusInput();
					}}
					on:addExtraDir={() => openDirPicker(cwd, 'extra')}
					on:removeExtraDir={(e) => (extraDirs = extraDirs.filter((d) => d !== e.detail))}
					on:compact={() => handleSlashCommand('/compactar', '/compactar')}
					on:copy={(e) => copyText(e.detail.text, e.detail.label)}
				/>
			</div>

			<!-- Overlay responsivo para telas menores que lg -->
			<div class="lg:hidden fixed inset-0 z-40 flex justify-end bg-black/40 backdrop-blur-[1px]">
				<button
					type="button"
					class="flex-1 cursor-default"
					aria-label="Fechar painel"
					on:click={() => (showInspector = false)}
				></button>
				<div class="w-[min(90vw,380px)] h-full bg-white dark:bg-gray-900 shadow-2xl">
					<DevInspector
						bind:tab={inspectorTab}
						{cwd}
						{extraDirs}
						{gitIsRepo}
						{gitBranch}
						{gitFiles}
						{selectedDiffFile}
						{selectedDiffText}
						{loadingDiff}
						{projectFiles}
						{fileSearchQuery}
						{loadingFiles}
						{previewFile}
						{loadingPreview}
						{allTools}
						{activeTodos}
						{estTokens}
						{activeModelName}
						{activeModeObj}
						{providers}
						{projectInfo}
						{sessionId}
						on:close={() => (showInspector = false)}
						on:refreshGit={refreshGit}
						on:openDiff={(e) => openFileDiff(e.detail)}
						on:reviewAll={() => {
							showInspector = false;
							handleSlashCommand('/revisar', '/revisar');
						}}
						on:reviewFile={(e) => {
							showInspector = false;
							handleSlashCommand('/revisar', `/revisar ${e.detail}`);
						}}
						on:searchFiles={(e) => handleFileSearch(e.detail)}
						on:previewFile={(e) => handlePreviewFile(e.detail)}
						on:closePreview={() => (previewFile = null)}
						on:attachFile={(e) => {
							if (!attachedFiles.includes(e.detail)) {
								attachedFiles = [...attachedFiles, e.detail];
								toast.success(`@${e.detail} anexado ao prompt`);
							}
							showInspector = false;
							composerRef?.focusInput();
						}}
						on:addExtraDir={() => openDirPicker(cwd, 'extra')}
						on:removeExtraDir={(e) => (extraDirs = extraDirs.filter((d) => d !== e.detail))}
						on:compact={() => handleSlashCommand('/compactar', '/compactar')}
						on:copy={(e) => copyText(e.detail.text, e.detail.label)}
					/>
				</div>
			</div>
		{/if}
	</div>
</div>

<!-- Modal Seletor de Pasta (Workspace ou --add-dir) -->
{#if showDirModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-[2px] p-4">
		<div class="w-full max-w-lg rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 shadow-2xl">
			<div class="flex items-center justify-between">
				<h2 class="text-sm font-semibold">
					{dirModalMode === 'extra'
						? 'Adicionar diretório extra (--add-dir)'
						: 'Selecionar pasta do projeto'}
				</h2>
				<button
					type="button"
					class="rounded-md px-1.5 py-0.5 text-xs text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-200"
					on:click={() => (showDirModal = false)}
				>
					Fechar
				</button>
			</div>
			<div class="mt-2.5 rounded-xl border border-gray-200/70 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 px-3 py-2 font-mono text-xs truncate text-gray-700 dark:text-gray-200">
				{dirBrowserCurrent}
			</div>
			<div class="mt-3 max-h-64 overflow-y-auto space-y-0.5">
				{#if dirBrowserParent}
					<button
						type="button"
						class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
						on:click={() => openDirPicker(dirBrowserParent, dirModalMode)}
					>
						<span class="font-mono text-sky-500">↑</span>
						<span>.. (pasta anterior)</span>
					</button>
				{/if}
				{#each dirBrowserEntries as entry}
					<button
						type="button"
						class="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
						on:click={() => openDirPicker(entry.path, dirModalMode)}
					>
						<DevToolIcon name="folder" className="size-3.5 text-sky-500 shrink-0" />
						<span class="truncate">{entry.name}</span>
					</button>
				{/each}
			</div>
			<div class="mt-4 flex flex-wrap items-center justify-between gap-2">
				{#if dirModalMode === 'cwd'}
					<button
						type="button"
						class="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/20 transition"
						on:click={clearCwd}
					>
						<DevToolIcon name="terminal" className="size-3.5" />
						<span>Sem pasta (PC inteiro)</span>
					</button>
				{:else}
					<span></span>
				{/if}
				<div class="flex items-center gap-2">
					<button
						type="button"
						class="rounded-xl border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-xs hover:bg-gray-50 dark:hover:bg-gray-800 transition"
						on:click={() => (showDirModal = false)}
					>
						Cancelar
					</button>
					<button
						type="button"
						class="rounded-xl bg-sky-500 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-sky-600 transition"
						on:click={() => confirmDirectory(dirBrowserCurrent)}
					>
						{dirModalMode === 'extra' ? 'Adicionar pasta extra' : 'Usar esta pasta'}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Modal Sessões Recentes do CLI -->
{#if showSessionsModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-[2px] p-4">
		<div class="w-full max-w-lg rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 shadow-2xl">
			<div class="flex items-center justify-between">
				<div>
					<h2 class="text-sm font-semibold">Sessões recentes neste projeto</h2>
					<p class="text-[11px] text-gray-400 truncate max-w-sm">{cwd}</p>
				</div>
				<button
					type="button"
					class="rounded-md px-1.5 py-0.5 text-xs text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-200"
					on:click={() => (showSessionsModal = false)}
				>
					Fechar
				</button>
			</div>
			<div class="mt-3 max-h-72 overflow-y-auto space-y-1.5">
				{#if recentSessions.length === 0}
					<p class="py-8 text-center text-xs text-gray-400">Nenhuma sessão salva para esta pasta ainda.</p>
				{:else}
					{#each recentSessions as s}
						<button
							type="button"
							class="w-full rounded-xl border border-gray-200/80 dark:border-gray-800 p-2.5 text-left hover:border-sky-500/50 hover:bg-sky-500/[0.04] transition"
							on:click={() => resumeSession(s.id)}
						>
							<div class="flex items-center justify-between gap-2">
								<span class="font-mono text-xs text-sky-600 dark:text-sky-400">{s.id.slice(0, 16)}…</span>
								<span class="text-[10px] text-gray-400">Retomar →</span>
							</div>
							<div class="mt-0.5 text-xs text-gray-600 dark:text-gray-300 truncate">{s.preview}</div>
						</button>
					{/each}
				{/if}
			</div>
		</div>
	</div>
{/if}
