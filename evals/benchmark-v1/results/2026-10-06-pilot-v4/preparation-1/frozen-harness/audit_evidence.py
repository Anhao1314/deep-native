"""Cross-check retained campaign evidence without model calls or score changes."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from transport import provider_tokens


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(out):
    out = Path(out)
    issues = []
    checked = []

    def issue(problem, **context):
        issues.append({**context, 'issue': problem})

    def read(path, fallback=None):
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            issue('missing_or_invalid_json', file=str(path.relative_to(out)))
            return fallback

    schedule = read(out / 'schedule.json', [])
    baseline = read(out / 'baselines.json', {})
    freeze = read(out / 'freeze.json', {})
    manifest = read(out / 'tasks.json', {})
    tasks = {t['id']: t for t in manifest.get('tasks', [])}
    expected = {s['run_id']: s for s in schedule}
    schedule_counts = Counter(s['run_id'] for s in schedule)
    for rid, count in schedule_counts.items():
        if count != 1:
            issue('duplicate_scheduled_run', run_id=rid)
    identities = [(s.get('task_id'), s.get('repeat'), s.get('condition')) for s in schedule]
    if len(set(identities)) != len(identities):
        issue('duplicate_scheduled_identity')
    planned_identities = {(tid, repeat, arm) for tid in tasks for repeat in [1, 2, 3] for arm in ['A', 'B']}
    if len(tasks) != 10 or len(schedule) != 60 or set(identities) != planned_identities:
        issue('invalid_benchmark_v1_schedule_design')
    for name, key in [('schedule.json', 'schedule_sha256'), ('tasks.json', 'tasks_sha256'),
                      ('baselines.json', 'baselines_sha256'), ('audit.json', 'audit_sha256')]:
        if key in freeze and (not (out / name).is_file() or sha(out / name) != freeze[key]):
            issue('campaign_hash_mismatch', file=name)
    for name, value in freeze.get('protocol_sha256', {}).items():
        archived = out / 'frozen-harness' / name
        path = archived if archived.is_file() else Path(__file__).parent / name
        if not path.is_file() or sha(path) != value:
            issue('protocol_hash_mismatch', file=name)
    treatment_map = freeze.get('treatment_sha256')
    if treatment_map is not None:
        treatment = out / 'frozen-treatment'
        actual = {str(p.relative_to(treatment)): sha(p) for p in treatment.rglob('*') if p.is_file()}
        if actual != treatment_map:
            issue('frozen_treatment_hash_mismatch')
    observed = []
    for path in sorted((out / 'runs').glob('*/result.json')):
        root = path.parent
        r = read(path)
        if not isinstance(r, dict):
            continue
        rid = r.get('run_id', root.name)
        observed.append(rid)
        local = []
        entry = expected.get(rid)
        if root.name != rid or not entry or any(r.get(k) != v for k, v in entry.items()):
            local.append('schedule_identity')
        task = tasks.get(r.get('task_id'))
        if task is None:
            local.append('unknown_task')
        elif not (root / 'phase1/prompt.txt').exists() or (root / 'phase1/prompt.txt').read_bytes() != task['prompt'].encode():
            local.append('exact_prompt')
        if r.get('fixture_commit') != baseline.get(r.get('task_id'), {}).get('fixture_commit'):
            local.append('fixture_commit')
        if not (root / 'patch.diff').exists() or sha(root / 'patch.diff') != r.get('patch_sha256'):
            local.append('patch_hash')
        hashes = read(root / 'artifact_hashes.json', {})
        required = ['result.json', 'tests_before.json', 'tests_after.json', 'metadata.json',
                    'patch.diff', 'final_response.txt', 'behavior.json', 'api_calls.json',
                    'phase1/prompt.txt', 'phase1/transcript.jsonl', 'phase1/session.json',
                    'phase1/command.json']
        for name in required:
            if name not in hashes:
                local.append('missing_artifact_hash:' + name)
        for name, value in hashes.items():
            target = root / name
            if not target.is_file() or sha(target) != value:
                local.append('artifact_hash:' + name)
        calls = read(root / 'api_calls.json', [])
        if provider_tokens(calls) != r.get('tokens'):
            local.append('provider_token_aggregate')
        models = sorted({c['response_model'] for c in calls if c.get('response_model')})
        if models != r.get('response_models') or models != ['deepseek-flash']:
            local.append('response_model_identity')
        grade = read(root / 'tests_after.json', {})
        valid = bool(grade.get('pass') and not r.get('forbidden_changes') and not r.get('protected_test_changes'))
        if valid != r.get('actually_valid') or ('PASS' if valid else 'FAIL') != r.get('task_success'):
            local.append('independent_grade')
        if r.get('false_completion') != (r.get('declared_done') is True and not valid):
            local.append('false_completion_logic')
        sessions = [read(p, {}) for p in sorted(root.glob('phase*/session.json'))]
        if abs(sum(s.get('duration_seconds', 0) for s in sessions) - r.get('duration_seconds', 0)) > .001:
            local.append('duration_aggregate')
        if len(sessions) != r.get('sessions'):
            local.append('session_count')
        metadata = read(root / 'metadata.json', {})
        if metadata.get('budget') != manifest.get('budget'):
            local.append('shared_budget_configuration')
        if sessions and all('observed_assistant_messages' in s for s in sessions):
            turns = sum(s['observed_assistant_messages'] for s in sessions)
            if 'total_observed_assistant_messages' in r and turns != r['total_observed_assistant_messages']:
                local.append('assistant_turn_aggregate')
            if turns > manifest.get('budget', {}).get('assistant_turns', 0):
                local.append('assistant_turn_budget_exceeded')
        if r.get('condition') == 'A' and not r.get('control_clean'):
            local.append('control_customization')
        if r.get('condition') == 'B' and not r.get('treatment_activation_observed'):
            local.append('missing_native_skill_activation')
        if r.get('task_id') == 'T10' and r.get('recovery_interrupted'):
            if len(sessions) != 2 or sessions[0].get('session_id') == sessions[1].get('session_id'):
                local.append('recovery_session_identity')
            interrupt = read(root / 'interruption.json', {})
            if interrupt.get('actual_signal') != 'SIGKILL' or not sessions or not sessions[0].get('interrupted'):
                local.append('missing_actual_interruption')
        treatment_checked = False
        workspace = Path(metadata.get('workspace', '/nonexistent-dn-benchmark-workspace'))
        if workspace.exists() and r.get('condition') == 'B':
            treatment_checked = True
            frozen = out / 'frozen-treatment/skills/deep-native'
            for source in frozen.rglob('*'):
                if not source.is_file():
                    continue
                installed = workspace / '.claude/skills/deep-native' / source.relative_to(frozen)
                if not installed.is_file() or sha(installed) != sha(source):
                    local.append('installed_treatment_modified:' + str(source.relative_to(frozen)))
        checked.append({'run_id': rid, 'issues': local, 'local_treatment_bytes_checked': treatment_checked})
        issues.extend({'run_id': rid, 'issue': problem} for problem in local)
    duplicate = sorted(rid for rid, count in Counter(observed).items() if count != 1)
    for rid in duplicate:
        issue('duplicate_completed_run', run_id=rid)
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    for rid in extra:
        issue('unexpected_completed_run', run_id=rid)
    complete = not missing and not extra and not duplicate and len(observed) == len(schedule)
    integrity = 'PASS' if not issues else 'FAIL'
    report = {'schema': 2, 'planned_runs': len(schedule), 'audited_completed_runs': len(checked),
              'missing_run_ids': missing, 'extra_run_ids': extra, 'duplicate_run_ids': duplicate,
              'campaign_complete': complete, 'integrity_status': integrity, 'status': integrity,
              'treatment_hash_available': treatment_map is not None, 'issues': issues, 'checks': checked,
              'scope': 'Evidence integrity of retained runs is separate from campaign completion. Checks frozen campaign inputs, schedule identities, artifact hashes, independent grades, provider tokens/model, session durations, shared budget configuration and actual recovery sessions. Does not attest hidden model weights or subjective behavior.'}
    (out / 'evidence_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(integrity, len(checked), 'completed runs audited;', len(issues), 'integrity issues;',
          'campaign complete:', complete)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    audit(args.output)
