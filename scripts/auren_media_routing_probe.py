"""Resume-safe real synthetic media checks through Auren admission and fallback.

Uses configured eligible free/trial routes and records only synthetic evidence.
Never clears cooldowns or authorizes billing; existing completed cases are skipped.
"""
import base64
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / 'cavren-nextchat/src'))
from integration.lunvri_bridge import prepare_job
from integration.lunvri_worker import normalize_messages
from integration.auren_fallback import run
from integration.auren_settings import atomic_json

FIXTURES = ROOT / 'reports/auren-gemini-groq-2026-10-14-r2/fixtures'
PATH = ROOT / 'reports/auren-media-routing-live-2026-10-14.json'


def main():
    saved = json.loads(PATH.read_text()) if PATH.exists() else {'cases': {}}
    cases = [
        ('image', 'vision.png', 'Leia o identificador na imagem e conte os círculos vermelhos e quadrados azuis. Responda somente identificador|círculos|quadrados.', 'chat'),
        ('pdf', 'document.pdf', 'Leia o PDF e responda apenas o identificador escrito nele.', 'auto'),
        ('audio', 'pt.wav', 'Transcreva o áudio exatamente, sem comentários.', 'chat'),
        ('video', 'video.mp4', 'Leia o identificador no vídeo e conte os círculos vermelhos e quadrados azuis. Responda somente identificador|círculos|quadrados.', 'chat'),
    ]
    for key, name, prompt, task in cases:
        if key in saved['cases']:
            continue
        data = base64.b64encode((FIXTURES/name).read_bytes()).decode()
        part = {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,'+data}} if key == 'image' else (
            {'type': 'input_audio', 'input_audio': {'format': 'wav', 'data': data}} if key == 'audio' else
            {'type': 'input_file', 'input_file': {'mime_type': 'application/pdf', 'data': data}} if key == 'pdf' else
            {'type': 'input_video', 'input_video': {'mime_type': 'video/mp4', 'data': data}})
        row = {'requested_model': 'cavren:groq:openai/gpt-oss-120b', 'input': key,
               'synthetic': True, 'max_tokens': 1024, 'billing_confirmed': False, 'started_at': time.time(), 'in_flight': True}
        saved['cases'][key] = row
        atomic_json(PATH, saved)
        events = []
        start = time.monotonic()
        try:
            job = prepare_job({'model': row['requested_model'], 'auren_task': task,
                               'cavren_mode_id': 'ether', 'auren_mode_manual': True, 'max_tokens': 1024,
                               'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': prompt}, part]}]}, 'synthetic-media-'+key)
            run(job, normalize_messages, output=events.append)
            final = next(e['response'] for e in reversed(events) if e['type'] == 'generation.completed')
            text = final['text']
            compact = ''.join(text.upper().split())
            ok = 'PIXEL-739|2|1' in compact if key in ('image', 'video') else 'PDF-628' in text if key == 'pdf' else all(word in text.lower() for word in ('auren', 'pronta', 'bom', 'dia'))
            row.update(ok=ok, effective_provider=final.get('provider'), effective_model=final.get('model'),
                       task=job['auren_task'], attachment_switch=job.get('auren_attachment_switch'),
                       input_modalities=final.get('auren_input_modalities'), usage=final.get('usage'),
                       fallback_index=final.get('fallback_index'), response_excerpt=text[:240],
                       statuses=[e.get('description') for e in events if e['type'] in ('generation.task_selected', 'generation.fallback')],
                       fallback_events=[{k:e.get(k) for k in ('attempt_id','provider','effective_model','failure_code')}
                                        for e in events if e['type']=='generation.fallback'],
                       cost_class='unknown_actual_cost')
        except Exception as error:
            row.update(ok=False, error=type(error).__name__, code=getattr(error, 'code', None),
                       http_status=getattr(error, 'http_status', None), cost_class='unknown_or_not_called')
        row.update(seconds=round(time.monotonic()-start, 3), in_flight=False)
        atomic_json(PATH, saved)
        print(key, row.get('ok'), row.get('effective_provider'), row.get('effective_model'), flush=True)


if __name__ == '__main__':
    main()
