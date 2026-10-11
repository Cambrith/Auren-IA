"""Use the existing Cavren engine with a single leading system message.

This boundary normalization also works around providers that reject multiple
system messages. The source checkout and its generation logic stay intact.
"""

from dataclasses import replace

from cavren import desktop_worker
from cavren.models import Message
from cavren.prompt_adapter import OpenAIChatPromptAdapter


def normalize_messages(messages):
    systems = [m.content.replace("Cavren", "Lunvri") for m in messages if m.role == "system"]
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
    return _original_adapt(self, normalize_messages(messages), provider=provider)


OpenAIChatPromptAdapter.adapt = adapt_single_system

if __name__ == "__main__":
    raise SystemExit(desktop_worker.main())
