import logging
import math
import re
import uuid
from datetime import datetime
from typing import Any, Optional

from open_webui.config import DEFAULT_RAG_TEMPLATE
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.misc import get_content_from_message, get_last_user_message, get_messages_content

log = logging.getLogger(__name__)


# Let the right tool be given for the work at hand,
# not the one that flatters, but the one that serves.
def get_task_model_id(default_model_id: str, task_model: str, task_model_external: str, models) -> str:
    if default_model_id.startswith('agent:'):
        # Agent sessions cannot serve ordinary completion requests for background tasks.
        return next(
            (
                model
                for model in (task_model_external, task_model)
                if model and model in models and not model.startswith('agent:')
            ),
            default_model_id,
        )
    task_model_id = default_model_id
    # Use an available task model override for the local or external connection.
    if models.get(task_model_id, {}).get('connection_type') == 'local':
        if task_model and task_model in models:
            task_model_id = task_model
    else:
        if task_model_external and task_model_external in models:
            task_model_id = task_model_external

    return task_model_id


def prompt_variables_template(template: str, variables: dict[str, str]) -> str:
    for variable, value in variables.items():
        template = template.replace(variable, value)
    return template


async def prompt_template(template: str, user: Optional[Any] = None) -> str:
    USER_VARIABLES = {}

    if user:
        if hasattr(user, 'model_dump'):
            user = user.model_dump()

        if isinstance(user, dict):
            user_info = user.get('info', {}) or {}
            birth_date = user.get('date_of_birth')
            age = None

            if birth_date:
                try:
                    # If birth_date is str, convert to datetime
                    if isinstance(birth_date, str):
                        birth_date = datetime.strptime(birth_date, '%Y-%m-%d')

                    today = datetime.now()
                    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                except Exception as e:
                    pass

            # Resolve user groups from DB only when the template uses {{USER_GROUPS}}
            groups = ''
            if '{{USER_GROUPS}}' in template:
                user_id = user.get('id')
                if user_id:
                    try:
                        from open_webui.models.groups import Groups

                        user_groups = await Groups.get_groups_by_member_id(user_id, include_inherited=True)
                        groups = ', '.join(g.name for g in user_groups)
                    except Exception:
                        pass

            USER_VARIABLES = {
                'name': str(user.get('name')),
                'email': str(user.get('email')),
                'role': str(user.get('role')),
                'location': str(user_info.get('location')),
                'bio': str(user.get('bio')),
                'gender': str(user.get('gender')),
                'birth_date': str(birth_date),
                'age': str(age),
                'groups': groups,
            }

    # Get the current date
    current_date = datetime.now()

    # YYYY-MM-DD: one date format, fewer international incidents.
    formatted_date = current_date.strftime('%Y-%m-%d')
    formatted_time = current_date.strftime('%I:%M:%S %p')
    formatted_weekday = current_date.strftime('%A')

    template = template.replace('{{CURRENT_DATE}}', formatted_date)
    template = template.replace('{{CURRENT_TIME}}', formatted_time)
    template = template.replace('{{CURRENT_DATETIME}}', f'{formatted_date} {formatted_time}')
    template = template.replace('{{CURRENT_WEEKDAY}}', formatted_weekday)

    template = template.replace('{{USER_NAME}}', USER_VARIABLES.get('name', 'Unknown'))
    template = template.replace('{{USER_EMAIL}}', USER_VARIABLES.get('email', 'Unknown'))
    template = template.replace('{{USER_ROLE}}', USER_VARIABLES.get('role', 'Unknown'))
    template = template.replace('{{USER_BIO}}', USER_VARIABLES.get('bio', 'Unknown'))
    template = template.replace('{{USER_GENDER}}', USER_VARIABLES.get('gender', 'Unknown'))
    template = template.replace('{{USER_BIRTH_DATE}}', USER_VARIABLES.get('birth_date', 'Unknown'))
    template = template.replace('{{USER_AGE}}', str(USER_VARIABLES.get('age', 'Unknown')))
    template = template.replace('{{USER_LOCATION}}', USER_VARIABLES.get('location', 'Unknown'))
    template = template.replace('{{USER_GROUPS}}', USER_VARIABLES.get('groups', ''))

    return template


def replace_prompt_variable(template: str, prompt: str) -> str:
    def replacement_function(match):
        full_match = match.group(0).lower()  # Normalize to lowercase for consistent handling
        start_length = match.group(1)
        end_length = match.group(2)
        middle_length = match.group(3)

        if full_match == '{{prompt}}':
            return prompt
        elif start_length is not None:
            return prompt[: int(start_length)]
        elif end_length is not None:
            return prompt[-int(end_length) :]
        elif middle_length is not None:
            middle_length = int(middle_length)
            if len(prompt) <= middle_length:
                return prompt
            start = prompt[: math.ceil(middle_length / 2)]
            end = prompt[-math.floor(middle_length / 2) :]
            return f'{start}...{end}'
        return ''

    # Updated regex pattern to make it case-insensitive with the `(?i)` flag
    pattern = r'(?i){{prompt}}|{{prompt:start:(\d+)}}|{{prompt:end:(\d+)}}|{{prompt:middletruncate:(\d+)}}'
    template = re.sub(pattern, replacement_function, template)
    return template


def truncate_content(content: str, max_chars: int, mode: str = 'middletruncate') -> str:
    """Truncate a string to max_chars using the specified mode.

    Modes:
        - middletruncate: keep beginning and end, join with '...'
        - start: keep first max_chars characters
        - end: keep last max_chars characters
    """
    if max_chars <= 0:
        return ''

    if not content or len(content) <= max_chars:
        return content

    if mode == 'start':
        return content[:max_chars]
    elif mode == 'end':
        return content[-max_chars:]
    else:  # middletruncate
        half = max_chars // 2
        return f'{content[:half]}...{content[-(max_chars - half) :]}'


def apply_content_filter(messages: list[dict], filter_str: str) -> list[dict]:
    """Apply a content filter to each message's content.

    filter_str is like 'middletruncate:500', 'start:200', or 'end:200'.
    Returns a new list with truncated content (original messages are not mutated).
    """
    parts = filter_str.split(':')
    if len(parts) != 2:
        return messages

    mode = parts[0].lower()
    try:
        max_chars = int(parts[1])
    except ValueError:
        return messages

    if mode not in ('middletruncate', 'start', 'end'):
        return messages

    result = []
    for msg in messages:
        new_msg = dict(msg)
        if isinstance(new_msg.get('content'), str):
            new_msg['content'] = truncate_content(new_msg['content'], max_chars, mode)
        elif isinstance(new_msg.get('content'), list):
            new_content = []
            for item in new_msg['content']:
                if isinstance(item, dict) and item.get('type') == 'text':
                    new_item = dict(item)
                    new_item['text'] = truncate_content(item.get('text', ''), max_chars, mode)
                    new_content.append(new_item)
                else:
                    new_content.append(item)
            new_msg['content'] = new_content
        result.append(new_msg)
    return result


def replace_messages_variable(
    template: str, messages: Optional[list[dict]] = None, variable_name: str = 'MESSAGES'
) -> str:
    def replacement_function(match):
        # Groups: (1) filter for bare MESSAGES
        #         (2) START count, (3) filter for START
        #         (4) END count,   (5) filter for END
        #         (6) MIDDLE count,(7) filter for MIDDLE
        bare_filter = match.group(1)
        start_length = match.group(2)
        start_filter = match.group(3)
        end_length = match.group(4)
        end_filter = match.group(5)
        middle_length = match.group(6)
        middle_filter = match.group(7)

        # If messages is None, handle it as an empty list
        if messages is None:
            return ''

        # Select messages based on the variant
        if start_length is not None:
            selected = messages[: int(start_length)]
            content_filter = start_filter
        elif end_length is not None:
            selected = messages[-int(end_length) :]
            content_filter = end_filter
        elif middle_length is not None:
            mid = int(middle_length)
            if len(messages) <= mid:
                selected = messages
            else:
                half = mid // 2
                start_msgs = messages[:half]
                end_msgs = messages[-half:] if mid % 2 == 0 else messages[-(half + 1) :]
                selected = start_msgs + end_msgs
            content_filter = middle_filter
        else:
            # Bare {{MESSAGES}} or {{MESSAGES|filter}}
            selected = messages
            content_filter = bare_filter

        # Apply content filter if present
        if content_filter:
            selected = apply_content_filter(selected, content_filter)

        return get_messages_content(selected)

    variable_pattern = re.escape(variable_name)
    template = re.sub(
        r'(?:'
        rf'\{{\{{{variable_pattern}(?:\|(\w+:\d+))?\}}\}}'
        rf'|\{{\{{{variable_pattern}:START:(\d+)(?:\|(\w+:\d+))?\}}\}}'
        rf'|\{{\{{{variable_pattern}:END:(\d+)(?:\|(\w+:\d+))?\}}\}}'
        rf'|\{{\{{{variable_pattern}:MIDDLETRUNCATE:(\d+)(?:\|(\w+:\d+))?\}}\}}'
        r')',
        replacement_function,
        template,
    )

    return template


# {{prompt:middletruncate:8000}}


# Let the context given here not distort the question,
# but illuminate it, so that the answer serves the one who asked.
async def rag_template(template: str, context: str, query: str):
    if template.strip() == '':
        template = DEFAULT_RAG_TEMPLATE

    template = await prompt_template(template)

    if '[context]' not in template and '{{CONTEXT}}' not in template:
        log.debug("WARNING: The RAG template does not contain the '[context]' or '{{CONTEXT}}' placeholder.")

    if '<context>' in context and '</context>' in context:
        log.debug(
            'WARNING: Potential prompt injection attack: the RAG '
            "context contains '<context>' and '</context>'. This might be "
            'nothing, or the user might be trying to hack something.'
        )

    query_placeholders = []
    if '[query]' in context:
        query_placeholder = '{{QUERY' + str(uuid.uuid4()) + '}}'
        template = template.replace('[query]', query_placeholder)
        query_placeholders.append((query_placeholder, '[query]'))

    if '{{QUERY}}' in context:
        query_placeholder = '{{QUERY' + str(uuid.uuid4()) + '}}'
        template = template.replace('{{QUERY}}', query_placeholder)
        query_placeholders.append((query_placeholder, '{{QUERY}}'))

    template = template.replace('[context]', context)
    template = template.replace('{{CONTEXT}}', context)

    template = template.replace('[query]', query)
    template = template.replace('{{QUERY}}', query)

    for query_placeholder, original_placeholder in query_placeholders:
        template = template.replace(query_placeholder, original_placeholder)

    return template


async def title_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = await prompt_template(template, user)

    return template


_EXACT_ENGLISH_TITLE_MAP: dict[str, str] = {
    'new chat': 'Nova Conversa',
    'untitled': 'Nova Conversa',
    'untitled chat': 'Nova Conversa',
    'chat': 'Nova Conversa',
    'greeting': 'Saudação Inicial',
    'greetings': 'Saudação Inicial',
    'simple greeting': 'Saudação Inicial',
    'initial greeting': 'Saudação Inicial',
    'casual greeting': 'Saudação Inicial',
    'brief greeting': 'Saudação Inicial',
    'friendly greeting': 'Saudação Inicial',
    'short greeting': 'Saudação Inicial',
    'basic greeting': 'Saudação Inicial',
    'quick greeting': 'Saudação Inicial',
    'warm greeting': 'Saudação Inicial',
    'greeting exchange': 'Saudação Inicial',
    'friendly exchange': 'Saudação Inicial',
    'hello': 'Saudação Inicial',
    'hi': 'Saudação Inicial',
    'hello greeting': 'Saudação Inicial',
    'conversation start': 'Início de Conversa',
    'starting conversation': 'Início de Conversa',
    'start of conversation': 'Início de Conversa',
    'chat introduction': 'Início de Conversa',
    'system prompt': 'Prompt do Sistema',
    'system prompt inquiry': 'Consulta sobre Prompt do Sistema',
    'system prompt request': 'Consulta sobre Prompt do Sistema',
    'general inquiry': 'Consulta Geral',
    'general question': 'Pergunta Geral',
    'help request': 'Pedido de Ajuda',
    'assistance request': 'Pedido de Ajuda',
}

_ENGLISH_TITLE_STRONG_WORDS = frozenset(
    {
        'meaning',
        'greeting',
        'greetings',
        'exchange',
        'overview',
        'summary',
        'discussion',
        'question',
        'questions',
        'request',
        'inquiry',
        'assistance',
        'explanation',
        'introduction',
        'conversation',
        'troubleshooting',
        'debugging',
        'understanding',
        'exploring',
        'learning',
        'creating',
        'building',
        'fixing',
        'updating',
        'checking',
        'finding',
        'comparing',
        'comparison',
        'difference',
        'differences',
        'between',
        'about',
        'with',
        'without',
        'from',
        'into',
        'using',
        'how',
        'what',
        'why',
        'when',
        'where',
        'which',
        'the',
        'and',
        'for',
        'your',
        'simple',
        'initial',
        'casual',
        'brief',
        'friendly',
        'quick',
        'new',
        'chat',
        'help',
        'guide',
        'tips',
        'issue',
        'issues',
        'error',
        'errors',
        'problem',
        'problems',
        'setup',
        'review',
        'analysis',
        'translation',
        'definition',
        'acronym',
        'abbreviation',
        'code',
        'coding',
        'programming',
        'file',
        'files',
        'folder',
        'folders',
        'model',
        'models',
        'system',
        'setting',
        'settings',
        'config',
        'configuration',
        'update',
        'fix',
        'task',
        'project',
        'recipe',
        'trends',
        'work',
        'remote',
        'music',
        'story',
        'writing',
        'idea',
        'ideas',
        'plan',
        'planning',
        'research',
        'search',
        'report',
        'data',
        'user',
        'assistant',
    }
)

_PTBR_SIGNAL_WORDS = frozenset(
    {
        'de',
        'da',
        'do',
        'das',
        'dos',
        'em',
        'no',
        'na',
        'nos',
        'nas',
        'para',
        'com',
        'sem',
        'sobre',
        'como',
        'qual',
        'quais',
        'por',
        'pelo',
        'pela',
        'entre',
        'uma',
        'uns',
        'umas',
        'saudação',
        'conversa',
        'início',
        'significado',
        'sigla',
        'ajuda',
        'dúvida',
        'duvida',
        'análise',
        'analise',
        'revisão',
        'revisao',
        'código',
        'codigo',
        'sistema',
        'configuração',
        'configuracao',
        'instalação',
        'instalacao',
        'correção',
        'correcao',
        'resumo',
        'explicação',
        'explicacao',
        'consulta',
        'pedido',
        'erro',
        'problema',
        'guia',
        'dicas',
        'receita',
        'trabalho',
        'projeto',
        'arquivo',
        'arquivos',
        'pasta',
        'modelo',
        'modelos',
    }
)


def normalize_ptbr_title(raw_title: str) -> str:
    """Limpa pontuação/ruído e traduz títulos genéricos acidentais em inglês para pt-BR."""
    if not isinstance(raw_title, str):
        return ''
    title = raw_title.strip()
    title = re.sub(r'^```(?:json)?\s*|\s*```$', '', title, flags=re.IGNORECASE).strip()
    title = title.strip('"\'“”‘’`').strip()
    title = re.sub(r'\s+', ' ', title)
    title = title.rstrip('.').strip()
    if not title:
        return ''
    mapped = _EXACT_ENGLISH_TITLE_MAP.get(title.lower())
    if mapped:
        return mapped
    return title


def looks_english_title(title: str) -> bool:
    """Detecta títulos curtos que escaparam em inglês para acionar reescrita garantida em pt-BR."""
    clean = normalize_ptbr_title(title)
    if not clean:
        return False
    # Acentuação típica do português já indica pt-BR
    if re.search(r'[áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ]', clean):
        return False
    tokens = re.findall(r"[a-zA-ZÀ-ÿ]+", clean.lower())
    if not tokens:
        return False
    if any(tok in _PTBR_SIGNAL_WORDS for tok in tokens):
        return False
    eng_hits = sum(1 for tok in tokens if tok in _ENGLISH_TITLE_STRONG_WORDS)
    if eng_hits == 0:
        return False
    # Qualquer título curto contendo termos caracteristicamente ingleses sem sinais de pt-BR
    return eng_hits >= 1 and (eng_hits / len(tokens)) >= 0.33


def extract_title_from_response(response_message: dict | None) -> str:
    """Extrai o campo title do JSON retornado pelo modelo sem vazar raciocínio bruto."""
    if not isinstance(response_message, dict):
        return ''
    candidates: list[tuple[str, str]] = []
    content = response_message.get('content')
    if isinstance(content, str) and content.strip():
        candidates.append(('content', content.strip()))
    reasoning = response_message.get('reasoning_content')
    if isinstance(reasoning, str) and reasoning.strip():
        candidates.append(('reasoning', reasoning.strip()))

    for source_kind, text in candidates:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end > start:
            snippet = text[start : end + 1]
            try:
                parsed = JSONCodec.loads(snippet)
                if isinstance(parsed, dict) and isinstance(parsed.get('title'), str):
                    cleaned = normalize_ptbr_title(parsed['title'])
                    if cleaned:
                        return cleaned
            except Exception:
                # Tenta extrair via regex caso haja aspas simples ou texto extra no JSON
                m = re.search(r'["\']title["\']\s*:\s*["\']([^"\']+)["\']', snippet)
                if m:
                    cleaned = normalize_ptbr_title(m.group(1))
                    if cleaned:
                        return cleaned
        # Só aceita texto plano direto do campo content (nunca do reasoning_content)
        if source_kind == 'content' and '\n' not in text and len(text) <= 80 and '{' not in text:
            cleaned = normalize_ptbr_title(text)
            if cleaned:
                return cleaned
    return ''


async def follow_up_generation_template(
    template: str, messages: list[dict], user: Optional[Any] = None, *, use_default: bool = False
) -> str:
    if use_default:
        start = max(0, len(messages) - 4)
        first_user = next((i for i, message in enumerate(messages) if message.get('role') == 'user'), None)
        messages = ([messages[first_user]] if first_user is not None and first_user < start else []) + messages[start:]

    normalized = []
    for message in messages:
        content = message.get('content')
        if isinstance(content, list):
            content = '\n'.join(
                item['text']
                for item in content
                if isinstance(item, dict) and item.get('type') == 'text' and isinstance(item.get('text'), str)
            )
        else:
            content = get_content_from_message(message) or ''
        if use_default and len(content) > 1000:
            # truncate_content adds three characters for the omission marker.
            content = truncate_content(content, 997)
        normalized.append({**message, 'content': content})
    messages = normalized

    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = await prompt_template(template, user)
    return template


def parse_follow_ups(content: str, max_count: int = 5) -> list[str]:
    if not isinstance(content, str):
        return []
    content = content[content.find('{') : content.rfind('}') + 1]
    try:
        data = JSONCodec.loads(content)
    except (ValueError, TypeError):
        return []
    suggestions = data.get('follow_ups') if isinstance(data, dict) else None
    if not isinstance(suggestions, list) or any(not isinstance(item, str) for item in suggestions):
        return []

    result = []
    for item in suggestions:
        item = item.strip()
        if item and len(item) <= 400 and item not in result:
            result.append(item)
    return result[:max_count]


async def tags_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = await prompt_template(template, user)
    return template


async def image_prompt_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = await prompt_template(template, user)
    return template


async def emoji_generation_template(template: str, prompt: str, user: Optional[Any] = None) -> str:
    template = replace_prompt_variable(template, prompt)
    template = await prompt_template(template, user)

    return template


async def autocomplete_generation_template(
    template: str,
    prompt: str,
    messages: Optional[list[dict]] = None,
    type: Optional[str] = None,
    user: Optional[Any] = None,
) -> str:
    template = template.replace('{{TYPE}}', type if type else '')
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = await prompt_template(template, user)
    return template


async def query_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = await prompt_template(template, user)
    return template


def moa_response_generation_template(template: str, prompt: str, responses: list[str]) -> str:
    def replacement_function(match):
        full_match = match.group(0)
        start_length = match.group(1)
        end_length = match.group(2)
        middle_length = match.group(3)

        if full_match == '{{prompt}}':
            return prompt
        elif start_length is not None:
            return prompt[: int(start_length)]
        elif end_length is not None:
            return prompt[-int(end_length) :]
        elif middle_length is not None:
            middle_length = int(middle_length)
            if len(prompt) <= middle_length:
                return prompt
            start = prompt[: math.ceil(middle_length / 2)]
            end = prompt[-math.floor(middle_length / 2) :]
            return f'{start}...{end}'
        return ''

    template = re.sub(
        r'{{prompt}}|{{prompt:start:(\d+)}}|{{prompt:end:(\d+)}}|{{prompt:middletruncate:(\d+)}}',
        replacement_function,
        template,
    )

    responses = [f'"""{response}"""' for response in responses]
    responses = '\n\n'.join(responses)

    template = template.replace('{{responses}}', responses)
    return template


def tools_function_calling_generation_template(template: str, tools_specs: str) -> str:
    template = template.replace('{{TOOLS}}', tools_specs)
    return template
