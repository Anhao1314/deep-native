"""Read-only cross-check of published evidence; no model calls or score changes."""
import argparse
import hashlib
import json
from pathlib import Path

from fixtures import TASKS
from transport import provider_tokens

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audit(out):
    schedule=json.loads((out/'schedule.json').read_text())
    baseline=json.loads((out/'baselines.json').read_text())
    freeze=json.loads((out/'freeze.json').read_text())
    expected={s['run_id']:s for s in schedule}
    tasks={t['id']:t for t in TASKS}
    issues=[];checked=[]
    for name,key in [('schedule.json','schedule_sha256'),('tasks.json','tasks_sha256')]:
        if sha(out/name)!=freeze[key]:issues.append({'file':name,'issue':'campaign_hash_mismatch'})
    for path in sorted((out/'runs').glob('*/result.json')):
        root=path.parent;r=json.loads(path.read_text());rid=r['run_id']
        local=[]
        entry=expected.get(rid)
        if not entry or any(r[k]!=v for k,v in entry.items()):local.append('schedule_identity')
        if (root/'phase1/prompt.txt').read_bytes()!=tasks[r['task_id']]['prompt'].encode():local.append('exact_prompt')
        if r['fixture_commit']!=baseline[r['task_id']]['fixture_commit']:local.append('fixture_commit')
        if sha(root/'patch.diff')!=r['patch_sha256']:local.append('patch_hash')
        hashes=json.loads((root/'artifact_hashes.json').read_text())
        for name,value in hashes.items():
            if not (root/name).exists() or sha(root/name)!=value:local.append('artifact_hash:'+name)
        calls=json.loads((root/'api_calls.json').read_text())
        if provider_tokens(calls)!=r['tokens']:local.append('provider_token_aggregate')
        grade=json.loads((root/'tests_after.json').read_text())
        valid=grade['pass'] and not r['forbidden_changes'] and not r['protected_test_changes']
        if valid!=r['actually_valid'] or ('PASS' if valid else 'FAIL')!=r['task_success']:local.append('independent_grade')
        sessions=[json.loads(p.read_text()) for p in sorted(root.glob('phase*/session.json'))]
        if abs(sum(s['duration_seconds'] for s in sessions)-r['duration_seconds'])>.001:local.append('duration_aggregate')
        if len(sessions)!=r['sessions']:local.append('session_count')
        if r['condition']=='A' and not r.get('control_clean'):local.append('control_customization')
        if r['condition']=='B' and not r['treatment_activation_observed']:local.append('missing_native_skill_activation')
        if r['response_models']!=['deepseek-flash']:local.append('response_model_identity')
        if r['task_id']=='T10' and r['recovery_interrupted']:
            if len(sessions)!=2 or sessions[0]['session_id']==sessions[1]['session_id']:local.append('recovery_session_identity')
            if not (root/'interruption.json').exists():local.append('missing_actual_interruption')
        # Local forensic check; public consumers need not have these temporary paths.
        workspace=Path(json.loads((root/'metadata.json').read_text())['workspace'])
        treatment_checked=False
        if workspace.exists() and r['condition']=='B':
            treatment_checked=True
            frozen=out/'frozen-treatment/skills/deep-native'
            for source in frozen.rglob('*'):
                if not source.is_file():continue
                installed=workspace/'.claude/skills/deep-native'/source.relative_to(frozen)
                if not installed.exists() or sha(installed)!=sha(source):local.append('installed_treatment_modified:'+str(source.relative_to(frozen)))
        checked.append({'run_id':rid,'issues':local,'local_treatment_bytes_checked':treatment_checked})
        issues.extend({'run_id':rid,'issue':problem} for problem in local)
    report={'schema':1,'planned_runs':len(schedule),'audited_completed_runs':len(checked),
            'missing_run_ids':sorted(set(expected)-{r['run_id'] for r in checked}),
            'issues':issues,'checks':checked,'status':'PASS' if not issues else 'FAIL',
            'scope':'Artifact hashes, exact prompts, identities, token/duration aggregates, independent-grade logic, activation and actual recovery sessions. Does not independently attest hidden model weights or subjective behavior.'}
    (out/'evidence_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(checked),'completed runs audited;',len(issues),'issues')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();audit(args.output)
