"""Final bounded checks after the ordered primary pass, never async resubmission."""
import argparse
from datetime import datetime
from pathlib import Path
import auren_remaining_probe as remaining

audit = remaining.audit
SYNCHRONOUS = {'text', 'code', 'documents', 'vision', 'pdf', 'json', 'tools', 'embeddings', 'rerank'}


def candidates(run):
    rows = audit.read(run / 'matrix.json')['rows']; selected = []
    for row in rows:
        provider, operation = row['provider'], row['operation']
        if provider == 'groq' and operation == 'speech' and row.get('blocker') == 'model_terms_required':
            selected.append({'key': row['key'], 'provider': provider,
                'reason': 'New requested continuation: one current short speech permission check. No terms are accepted by the harness.',
                'fresh_prerequisite_check': True})
        if row.get('blocker') != 'prior_interrupted_request_unknown' or operation not in SYNCHRONOUS or provider not in ['zai', 'cohere', 'mistral', 'nvidia']:
            continue
        previous = row.get('prior_evidence', {})
        journal = audit.read(audit.ROOT / 'reports' / previous['source'] / 'results.json')['records'].get(row['key'], {})
        if any(sample.get('remote_id') for sample in journal.get('samples', [])): continue
        intents = journal.get('interruptions', []) + ([journal['in_flight']] if journal.get('in_flight') else [])
        dates = [datetime.fromisoformat(intent['at']) for intent in intents if intent.get('at')]
        if not dates or (datetime.fromisoformat(audit.now())-max(dates)).total_seconds() < 3600: continue
        selected.append({'key': row['key'], 'provider': provider,
            'reason': 'Reviewed old synchronous interrupted request, older than one hour, no async job ID, bounded output of 512 tokens. Current user request authorizes a new small test. The previous unknown outcome/cost remains in historical evidence.'})
    return selected


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--run', required=True, type=Path)
    args = parser.parse_args(); run = args.run; plan_path = run / 'final-followups.json'
    plan = audit.read(plan_path)
    if not plan:
        order = audit.read(run / 'order.json')
        if any(order['stages'].get(provider, {}).get('status') != 'reconciled' for provider in remaining.ORDER):
            raise SystemExit('Finish the ordered primary pass before final follow-ups.')
        plan = {'at': audit.now(), 'primary_pass_complete': True, 'rows': candidates(run), 'prepared': [], 'complete': []}
        audit.atomic(plan_path, plan)
    for provider in remaining.ORDER:
        choices = [item for item in plan['rows'] if item['provider'] == provider]
        if not choices or provider in plan['complete']: continue
        if provider not in plan['prepared']:
            matrix = audit.read(run / 'matrix.json'); journal = remaining.merge_provider_journals(run)
            by_key = {row['key']: row for row in matrix['rows']}
            for item in choices:
                row = by_key[item['key']]
                row.update(blocker=None, pending=item['reason'], bounded_final_followup=item['reason'])
                if item.get('fresh_prerequisite_check'): row['fresh_prerequisite_check'] = True
                record = journal['records'][item['key']]
                record.pop('terminal', None); record.pop('blocker', None); record.pop('pending', None)
            audit.atomic(run / 'matrix.json', matrix); audit.atomic(run / 'results.json', journal)
            checkpoint = run / 'journals' / (provider+'.json')
            if checkpoint.exists():
                part = audit.read(checkpoint)
                for item in choices: part['records'][item['key']] = journal['records'][item['key']]
                audit.atomic(checkpoint, part)
            order = audit.read(run / 'order.json'); stage = order['stages'][provider]
            stage['primary_reconciled_at'] = stage['updated_at']; stage['status'] = 'bounded_final_followup_pending'
            audit.atomic(run / 'order.json', order)
            plan['prepared'].append(provider); audit.atomic(plan_path, plan)
        remaining.execute_provider(run, provider, 180)
        if audit.read(run / 'order.json')['stages'][provider]['status'] != 'reconciled':
            raise SystemExit('Follow-up window ended; resume this same script without resetting evidence.')
        plan['complete'].append(provider); audit.atomic(plan_path, plan)
    plan['finished_at'] = audit.now(); audit.atomic(plan_path, plan)
    remaining.export_report(run)


if __name__ == '__main__': main()
