"""Use the existing Cavren engine with a single leading system message.

This boundary normalization also works around providers that reject multiple
system messages. The source checkout and its generation logic stay intact.
"""

from dataclasses import replace
import json
from pathlib import Path
import sys
import signal
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cavren import desktop_worker
from cavren.models import Message
from cavren.prompt_adapter import OpenAIChatPromptAdapter
from cavren.errors import CavrenError
from integration.auren_fallback import run as run_manual


def normalize_messages(messages):
    systems = [m.content.replace("Cavren", "Auren").replace("Lunvri", "Auren") for m in messages if m.role == "system"]
    rest = [m for m in messages if m.role != "system"]
    return ([Message("system", "\n\n".join(systems))] if systems else []) + rest


def normalize_context(builder):
    def wrapped(*args, **kwargs):
        context = builder(*args, **kwargs)
        return replace(context, messages=tuple(normalize_messages(context.messages)))

    return wrapped


desktop_worker.build_generation_context = normalize_context(desktop_worker.build_generation_context)
desktop_worker.with_web_results = normalize_context(desktop_worker.with_web_results)

# Cavren adds route metadata after context assembly. Normalize at the final
# provider boundary too, so that metadata cannot introduce a second system turn.
_original_adapt = OpenAIChatPromptAdapter.adapt


def adapt_single_system(self, messages, *, provider=""):
    result = _original_adapt(self, normalize_messages(messages), provider=provider)
    if provider == 'openrouter':
        for message in result:
            if isinstance(message.get('content'), list):
                message['content'] = [
                    (
                        {
                            'type': 'video_url',
                            'video_url': {
                                'url': f'data:{part["input_video"]["mime_type"]};base64,{part["input_video"]["data"]}'
                            },
                        }
                        if part.get('type') == 'input_video'
                        else part
                    )
                    for part in message['content']
                ]
    return result


OpenAIChatPromptAdapter.adapt = adapt_single_system

if __name__ == "__main__":
    def cancel(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, cancel)
    # Dispatch manual catalog routes without adding them to automatic fallback.
    raw = sys.stdin.read()
    job = json.loads(raw)
    if job.get('lunvri_image_generation'):
        job['auren_deadline'] = time.monotonic() + 480
        def expired(signum, frame):
            raise CavrenError('deadline', 'O prazo global de geração foi atingido.')
        signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, 475)
    if job.get('auren_fallback', True):
        try:
            raise SystemExit(run_manual(job, normalize_messages))
        except CavrenError as error:
            print(
                json.dumps(
                    {
                        'type': 'generation.error',
                        'generation_id': job['generation_id'],
                        'code': error.code,
                        'message': str(error).replace('Cavren', 'Auren'),
                    }
                ),
                flush=True,
            )
            raise SystemExit(1)
        except Exception:
            print(
                json.dumps(
                    {
                        'type': 'generation.error',
                        'generation_id': job['generation_id'],
                        'code': 'provider',
                        'message': 'Não foi possível concluir a chamada ao provedor.',
                    }
                ),
                flush=True,
            )
            raise SystemExit(1)
    from io import StringIO

    sys.stdin = StringIO(raw)
    raise SystemExit(desktop_worker.main())
