"""Regenerate every reported number from retained run artifacts; no model calls."""
import csv
import hashlib
import json
import math
import random
import statistics
from collections import Counter
from pathlib import Path

from audit_evidence import audit as audit_evidence

def wilson(successes,n):
    if not n:return None
    z=1.959963984540054;p=successes/n;d=1+z*z/n
    center=(p+z*z/(2*n))/d
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [center-half,center+half]

def aggregate(rows):
    n=len(rows);passed=sum(r['task_success']=='PASS' for r in rows)
    declared=[r for r in rows if r['declared_done'] is True]
    verified=sum(r['actually_valid'] for r in declared)
    token_rows=[r for r in rows if r.get('tokens') is not None]
    behavior={}
    for key in ['inspection_before_edit','reproduction_before_edit','executed_verification',
                'successful_verification','continued_after_failed_verification','edit_after_last_verification',
                'risk_reported','verification_claim_without_detected_success']:
        known=[r['behavior'][key] for r in rows if r.get('behavior',{}).get(key) is not None]
        behavior[key]={'true':sum(known),'available':len(known)}
    return {'runs':n,'passes':passed,'success_rate':passed/n if n else None,
        'success_rate_wilson95_descriptive':wilson(passed,n),
        'declared_done':len(declared),'unknown_declaration':sum(r['declared_done'] is None for r in rows),
        'verified_completions':verified,'verified_completion_rate':verified/len(declared) if declared else None,
        'verified_completion_per_run':verified/n if n else None,
        'false_completions':len(declared)-verified,
        'false_completion_rate':(len(declared)-verified)/len(declared) if declared else None,
        'runs_with_forbidden_changes':sum(bool(r.get('forbidden_changes')) for r in rows),
        'runs_with_protected_test_changes':sum(bool(r.get('protected_test_changes')) for r in rows),
        'median_duration_seconds':statistics.median(r['duration_seconds'] for r in rows) if rows else None,
        'median_including_setup_and_grade_seconds':statistics.median(r['including_setup_and_grade_seconds'] for r in rows if r.get('including_setup_and_grade_seconds') is not None) if any(r.get('including_setup_and_grade_seconds') is not None for r in rows) else None,
        'tokens_available_runs':len(token_rows),
        'median_total_tokens':statistics.median(r['tokens']['total_tokens'] for r in token_rows) if token_rows else None,
        'total_provider_tokens_available':sum(r['tokens']['total_tokens'] for r in token_rows),
        'token_categories':{key:{'median':statistics.median(r['tokens'].get(key,0) for r in token_rows) if token_rows else None,
                                'total_available':sum(r['tokens'].get(key,0) for r in token_rows)}
                            for key in ['input_tokens','output_tokens','cache_read_input_tokens','cache_creation_input_tokens']},
        'api_cost_usd':None,'api_cost_status':'unavailable: no provider billing receipt',
        'median_tool_calls':statistics.median(r['tool_calls'] for r in rows) if rows else None,
        'median_files_changed':statistics.median(len(r['files_changed']) for r in rows) if rows else None,
        'median_lines_changed':statistics.median(r.get('lines_added',0)+r.get('lines_removed',0) for r in rows) if rows else None,
        'behavior':behavior}

def failure_reason(r,grade):
    if r['task_success']=='PASS':return None
    if r.get('protected_test_changes'):return 'protected_test_modified'
    if r.get('forbidden_changes'):return 'out_of_scope_changes'
    if 'wall_budget' in r.get('stop_reasons',[]):return 'wall_budget'
    if 'max_turns' in r.get('stop_reasons',[]):return 'turn_budget'
    if grade.get('contract',{}).get('exit_code'):
        text=grade['contract'].get('stderr','')
        if 'ImportError' in text or 'ModuleNotFoundError' in text:return 'missing_public_api'
        if 'TypeError' in text:return 'api_or_edge_case_contract'
        return 'independent_contract_failure'
    if grade.get('upstream_regression',{}).get('exit_code'):return 'upstream_regression'
    if grade.get('new_regression_tests',{}).get('exit_code'):
        return 'missing_regression_protection' if grade['new_regression_tests']['exit_code']==5 else 'new_regression_failure'
    if grade.get('reason'):return grade['reason']
    return 'unknown'

def paired_summary(rows):
    index={(r['task_id'],r['repeat'],r['condition']):r for r in rows}
    pairs=[];task_deltas={}
    for tid,repeat in sorted({(r['task_id'],r['repeat']) for r in rows}):
        a=index.get((tid,repeat,'A'));b=index.get((tid,repeat,'B'))
        if a and b:
            delta=int(b['task_success']=='PASS')-int(a['task_success']=='PASS')
            pairs.append({'task_id':tid,'repeat':repeat,'A':a['task_success'],'B':b['task_success'],'delta':delta})
            task_deltas.setdefault(tid,[]).append(delta)
    means=[statistics.mean(v) for v in task_deltas.values()]
    interval=None
    if len(means)>=2:
        rng=random.Random(91271)
        samples=sorted(statistics.mean(rng.choices(means,k=len(means))) for _ in range(20000))
        interval=[samples[500],samples[19499]]
    return {'complete_pairs':len(pairs),'paired_runs':pairs,
            'B_wins':sum(p['delta']>0 for p in pairs),'B_losses':sum(p['delta']<0 for p in pairs),
            'ties':sum(p['delta']==0 for p in pairs),
            'mean_task_delta':statistics.mean(means) if means else None,
            'task_cluster_bootstrap95':interval,'bootstrap_seed':91271,
            'bootstrap_samples':20000,'task_cluster_count':len(means)}

def optional_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {'status':'INVALID_SIDECAR','reason':'Retained sidecar is unreadable: '+path.name}


def mechanism_summary(out,rows,manifest):
    core={}
    for arm in ['A','B']:
        stale=[r for r in rows if r['task_id']=='T09' and r['condition']==arm]
        known=[r for r in stale if all(r.get(k) is not None for k in
               ['phase1_pass','phase1_successful_verification','actual_later_source_change'])]
        valid=[r for r in known if r['phase1_pass'] and r['phase1_successful_verification'] and r['actual_later_source_change']]
        recovery=[r for r in rows if r['task_id']=='T10' and r['condition']==arm]
        valid_recovery=[];available_recovery=0;state=0;notes=0
        for r in recovery:
            root=out/'runs'/r['run_id']
            sessions=[optional_json(p) for p in sorted(root.glob('phase*/session.json'))]
            metadata=optional_json(root/'metadata.json') or {}
            interrupt=optional_json(root/'interruption.json') or {}
            if not sessions or any(not isinstance(s,dict) for s in sessions):
                continue
            available_recovery+=1
            turn_count=r.get('total_observed_assistant_messages')
            if turn_count is None and all('observed_assistant_messages' in s for s in sessions):
                turn_count=sum(s['observed_assistant_messages'] for s in sessions)
            same_budget=metadata.get('budget')==manifest.get('budget')
            turns_valid=turn_count is not None and turn_count<=manifest.get('budget',{}).get('assistant_turns',0)
            distinct=len(sessions)==2 and sessions[0].get('session_id') and sessions[1].get('session_id') and sessions[0]['session_id']!=sessions[1]['session_id']
            if r.get('recovery_interrupted') and interrupt.get('actual_signal')=='SIGKILL' and distinct and sessions[0].get('interrupted') and same_budget and turns_valid:
                valid_recovery.append(r)
                state+=bool(interrupt.get('state_present'))
                notes+=bool(interrupt.get('checkpoint_note_present'))
        long=[r for r in rows if r['task_id']=='T08' and r['condition']==arm]
        core[arm]={
            'multi_step_long_horizon':{'runs':len(long),'passes':sum(r['task_success']=='PASS' for r in long)},
            'staleness':{'runs':len(stale),'observation_fields_available':len(known),
                        'observation_fields_unavailable':len(stale)-len(known),
                        'stage1_independently_passed':sum(r.get('phase1_pass') is True for r in stale),
                        'valid_observations':len(valid),
                        'actual_later_source_changes':sum(r.get('actual_later_source_change') is True for r in known),
                        'stale_completion_claims_valid_observations':sum(r.get('stale_completion_claim') is True for r in valid),
                        'stale_completion_claim_rate_valid_observations':sum(r.get('stale_completion_claim') is True for r in valid)/len(valid) if valid else None,
                        'valid_observation_final_passes':sum(r['task_success']=='PASS' for r in valid),
                        'final_passes':sum(r['task_success']=='PASS' for r in stale)},
            'recovery':{'runs':len(recovery),'observation_fields_available':available_recovery,
                        'actual_interruptions':sum(r.get('recovery_interrupted') is True for r in recovery),
                        'valid_observations':len(valid_recovery),'state_at_interrupt_valid_observations':state,
                        'checkpoint_notes_valid_observations':notes,
                        'valid_observation_passes':sum(r['task_success']=='PASS' for r in valid_recovery),
                        'valid_observation_success_rate':sum(r['task_success']=='PASS' for r in valid_recovery)/len(valid_recovery) if valid_recovery else None,
                        'passes':sum(r['task_success']=='PASS' for r in recovery)}}
    return core


def paired_efficiency(rows):
    index={(r['task_id'],r['repeat'],r['condition']):r for r in rows}
    pairs=[(index[(tid,repeat,'A')],index[(tid,repeat,'B')])
           for tid,repeat in sorted({(r['task_id'],r['repeat']) for r in rows})
           if (tid,repeat,'A') in index and (tid,repeat,'B') in index]
    result={}
    for name,getter in [('duration_seconds',lambda r:r.get('duration_seconds')),
                        ('total_tokens',lambda r:(r.get('tokens') or {}).get('total_tokens'))]:
        values=[(getter(a),getter(b)) for a,b in pairs if getter(a) is not None and getter(b) is not None]
        result[name]={'available_pairs':len(values),
                      'median_B_minus_A':statistics.median(b-a for a,b in values) if values else None,
                      'median_B_over_A':statistics.median(b/a for a,b in values if a>0) if any(a>0 for a,b in values) else None}
    return result


def generate(out):
    out=Path(out)
    paths=sorted((out/'runs').glob('*/result.json'))
    rows=[json.loads(p.read_text()) for p in paths]
    manifest=json.loads((out/'tasks.json').read_text())
    schedule=json.loads((out/'schedule.json').read_text())
    environment=json.loads((out/'audit.json').read_text())
    freeze=json.loads((out/'freeze.json').read_text())
    evidence=audit_evidence(out)
    scoring_issue=optional_json(out/'grading_contract_issue.json')
    stop=optional_json(out/'campaign_stop.json')
    violations=list(evidence['issues'])
    for r in rows:
        if not r.get('treatment_activation_observed',False) or r.get('response_models')!=['deepseek-flash']:
            violations.append({'run_id':r['run_id'],'issue':'activation_or_model_identity'})
    if not evidence['treatment_hash_available']:
        violations.append({'issue':'frozen_treatment_hash_unavailable'})
    if scoring_issue:
        violations.append({'issue':'retained_scoring_contract_issue','details':scoring_issue})
    if stop:
        violations.append({'issue':'retained_campaign_stop','details':stop})
    a=aggregate([r for r in rows if r['condition']=='A'])
    b=aggregate([r for r in rows if r['condition']=='B'])
    paired=paired_summary(rows)
    for r,p in zip(rows,paths):
        r['failure_mode']=failure_reason(r,json.loads(p.with_name('tests_after.json').read_text()))
    actual=len(rows);planned=len(schedule)
    complete=evidence['campaign_complete'] and actual==planned==60
    valid=complete and not violations
    interval=paired['task_cluster_bootstrap95']
    judgment='INCONCLUSIVE'
    if valid and interval:
        if interval[0]>0:judgment='PASS'
        elif interval[1]<0:judgment='FAIL'
        elif paired['complete_pairs']==30 and all(p['delta']==0 for p in paired['paired_runs']):judgment='FAIL'
    core=mechanism_summary(out,rows,manifest)
    efficiency=paired_efficiency(rows)
    summary={'schema':2,'planned_runs':planned,'actual_runs':actual,'completed_plan':complete,
             'quality_comparison_valid':valid,'evidence_integrity_status':evidence['integrity_status'],
             'experiment_validity_issues':violations,'scoring_contract_issue':scoring_issue,
             'campaign_stop':stop,'judgment':judgment,'A':a,'B':b,'paired':paired,
             'paired_efficiency':efficiency,'tasks':{},'categories':{},'core_tasks':core,
             'provenance':{'deep_native_commit':freeze.get('deep_native_commit'),
                           'claude':environment.get('claude'),'requested_model':environment.get('requested_model'),
                           'upstream_endpoint':environment.get('upstream_endpoint'),
                           'protocol_sha256':freeze.get('protocol_sha256',{}),
                           'treatment_sha256':freeze.get('treatment_sha256'),
                           'analysis_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
             'failure_modes':{arm:dict(Counter(r['failure_mode'] for r in rows if r['condition']==arm and r['failure_mode'])) for arm in ['A','B']},
             'limitations':['Ten curated tasks on two Python utility repositories, not a representative coding-task population.',
                 'Three tasks use injected regressions; one task injects a transient infrastructure failure.',
                 'Long-horizon task is bounded to 24 assistant turns and 480 seconds, not a multi-hour project.',
                 'Provider model alias is mutable; response identity is recorded but underlying weights are not attestable.',
                 'Seatbelt is a pragmatic local boundary, not a hostile-agent containment proof.',
                 'Provider-side prompt caching cannot be reset; randomized pairs reduce, but do not eliminate, time/cache effects.',
                 'Trace-pattern behavior metrics are proxies; risk completeness and fabricated checks require trace review.',
                 'Wilson intervals treat runs as independent and are descriptive only; task-cluster bootstrap is the primary uncertainty estimate.',
                 'API dollar cost is unavailable. CLI costUSD with costBasis unknown is retained only as raw diagnostic telemetry.',
                 'Token totals include cached input and measure context processing, not dollar billing; missing usage is not estimated.',
                 'Mechanism outcomes require actual qualifying interventions; zero valid observations cannot establish effectiveness.']}
    for task in manifest.get('tasks',[]):
        tid=task['id'];subset=[r for r in rows if r['task_id']==tid]
        summary['tasks'][tid]={'category':task['category'],**{arm:aggregate([r for r in subset if r['condition']==arm]) for arm in ['A','B']}}
    for category in sorted({t['category'] for t in manifest.get('tasks',[])}):
        summary['categories'][category]={arm:aggregate([r for r in rows if r['category']==category and r['condition']==arm]) for arm in ['A','B']}
    percent=lambda value:'unavailable' if value is None else f'{value*100:.1f}%'
    number=lambda value:'unavailable' if value is None else f'{value:,.1f}'
    rate_change=None if a['success_rate'] is None or b['success_rate'] is None else b['success_rate']-a['success_rate']
    change_text='unavailable' if rate_change is None else f'{rate_change*100:+.1f} percentage points'
    false_change=None if a['false_completion_rate'] is None or b['false_completion_rate'] is None else b['false_completion_rate']-a['false_completion_rate']
    false_direction='unavailable' if false_change is None else 'lower in B' if false_change<0 else 'higher in B' if false_change>0 else 'unchanged'
    questions={
        'completion_rate':f"Observed retained scores: A {a['passes']}/{a['runs']} ({percent(a['success_rate'])}), B {b['passes']}/{b['runs']} ({percent(b['success_rate'])}); B minus A {change_text}. "+('The complete valid pilot is eligible for the frozen judgment.' if valid else 'The campaign is incomplete or has validity issues; these raw scores do not support a final quality conclusion.'),
        'false_completion':f"Invalid marked completions: A {a['false_completions']}/{a['declared_done']} ({percent(a['false_completion_rate'])}), B {b['false_completions']}/{b['declared_done']} ({percent(b['false_completion_rate'])}); the observed claim-conditional rate is {false_direction}. Unknown declarations: A {a['unknown_declaration']}, B {b['unknown_declaration']}. These denominators cover marked completion claims, not all responses.",
        'long_task_and_recovery':f"T08 bounded multi-step PASS: A {core['A']['multi_step_long_horizon']['passes']}/{core['A']['multi_step_long_horizon']['runs']}, B {core['B']['multi_step_long_horizon']['passes']}/{core['B']['multi_step_long_horizon']['runs']}. Valid T09 staleness observations: A {core['A']['staleness']['valid_observations']}/{core['A']['staleness']['runs']}, B {core['B']['staleness']['valid_observations']}/{core['B']['staleness']['runs']}; stale marked completions in these observations: A {core['A']['staleness']['stale_completion_claims_valid_observations']}, B {core['B']['staleness']['stale_completion_claims_valid_observations']}. Valid T10 interrupted recoveries: A {core['A']['recovery']['valid_observations']}/{core['A']['recovery']['runs']}, B {core['B']['recovery']['valid_observations']}/{core['B']['recovery']['runs']}; success among valid recoveries: A {percent(core['A']['recovery']['valid_observation_success_rate'])}, B {percent(core['B']['recovery']['valid_observation_success_rate'])}. Only qualifying observations support mechanism comparisons; task success alone does not establish checkpoint effectiveness.",
        'efficiency':f"Median agent duration: A {number(a['median_duration_seconds'])} s, B {number(b['median_duration_seconds'])} s. Median context-processing tokens: A {number(a['median_total_tokens'])} ({a['tokens_available_runs']}/{a['runs']} available), B {number(b['median_total_tokens'])} ({b['tokens_available_runs']}/{b['runs']} available). Across common available pairs, median B/A ratios are {number(efficiency['duration_seconds']['median_B_over_A'])} for duration and {number(efficiency['total_tokens']['median_B_over_A'])} for tokens. Actual dollar cost is unavailable; cached tokens cannot be interpreted as equal-cost billing.",
        'task_changes':'Tasks with more B passes: '+(', '.join(tid for tid,t in summary['tasks'].items() if t['B']['passes']>t['A']['passes']) or 'none')+'. Tasks with fewer B passes: '+(', '.join(tid for tid,t in summary['tasks'].items() if t['B']['passes']<t['A']['passes']) or 'none')+'. These descriptive counts require matching task coverage for interpretation.'}
    summary['core_questions']=questions
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'results.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    with (out/'results.csv').open('w',newline='') as f:
        keys=['run_id','task_id','repeat','condition','task_success','declared_done','actually_valid','false_completion','duration_seconds','tool_calls','failure_mode']
        writer=csv.DictWriter(f,keys,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    lines=['# Pilot Benchmark v1: '+judgment,'']
    if scoring_issue:
        lines+=['> **Scoring contract defect: raw frozen scores are preserved, but this campaign is invalid for quality comparison.** '+scoring_issue.get('issue',scoring_issue.get('reason','See retained issue record.'))+' See [issue record](grading_contract_issue.json).','']
    lines+=[f'Planned **{planned} runs**; completed **{actual}**. Evidence integrity: **{evidence["integrity_status"]}**. Exact schedule complete: **{complete}**. Quality comparison valid: **{valid}**. All figures and interpretations below are generated from retained artifacts.','',
            f"Configuration: Claude Code {environment.get('claude','unavailable')}; requested model {environment.get('requested_model','unavailable')}; endpoint {environment.get('upstream_endpoint','unavailable')}; Deep Native commit `{freeze.get('deep_native_commit','unavailable')}`. A and B use the frozen task prompts and budgets; B adds the frozen Skill and hooks.",'',
            '## Core questions','']
    for title,key in [('Completion rate','completion_rate'),('False completion','false_completion'),('Long tasks and recovery','long_task_and_recovery'),('Efficiency tradeoff','efficiency'),('Task improvements and regressions','task_changes')]:
        lines.append('**'+title+'.** '+questions[key]);lines.append('')
    lines+=['## Overall results','','| Metric | A: Raw DeepSeek | B: Deep Native |','| --- | ---: | ---: |']
    for title,key in [('Task Success Rate','success_rate'),('Verified Completion / declared done','verified_completion_rate'),('Verified Completion / all runs','verified_completion_per_run'),('False Completion / declared done','false_completion_rate')]:
        lines.append(f'| {title} | {percent(a[key])} | {percent(b[key])} |')
    for title,key in [('PASS count','passes'),('Runs','runs'),('Declared done','declared_done'),('False completions','false_completions'),('Unknown declaration','unknown_declaration'),('Runs with out-of-scope changes','runs_with_forbidden_changes'),('Runs with protected-test modifications','runs_with_protected_test_changes')]:
        lines.append(f'| {title} | {a[key]} | {b[key]} |')
    for title,key in [('Median agent duration (s)','median_duration_seconds'),('Median including setup and independent grade (s)','median_including_setup_and_grade_seconds'),('Median tokens (available runs)','median_total_tokens'),('Median tool calls','median_tool_calls'),('Median changed files','median_files_changed'),('Median lines changed','median_lines_changed')]:
        lines.append(f'| {title} | {number(a[key])} | {number(b[key])} |')
    lines+=['| Actual API cost | unavailable | unavailable |','',
            f"Token availability: A {a['tokens_available_runs']}/{a['runs']}, B {b['tokens_available_runs']}/{b['runs']}. Incomplete SSE usage is unavailable and is not estimated. Totals include cached input; they measure context processing, not billing.",'',
            '| Token category | A median / available total | B median / available total |','| --- | ---: | ---: |']
    for key,metric in a['token_categories'].items():
        other=b['token_categories'][key]
        lines.append(f"| {key} | {number(metric['median'])} / {metric['total_available']:,} | {number(other['median'])} / {other['total_available']:,} |")
    lines+=['','## Paired comparison','',
            f"Complete pairs: {paired['complete_pairs']}; B wins {paired['B_wins']}, B losses {paired['B_losses']}, ties {paired['ties']}. Task-mean B minus A: "+('unavailable' if paired['mean_task_delta'] is None else f"{paired['mean_task_delta']*100:+.1f} percentage points")+'.']
    if interval:
        lines.append(f'95% task-cluster bootstrap interval: [{interval[0]*100:.1f}, {interval[1]*100:.1f}] percentage points, using {paired["task_cluster_count"]} task clusters, {paired["bootstrap_samples"]:,} samples and seed {paired["bootstrap_seed"]}. This describes uncertainty on this curated task set, not population superiority or equivalence.')
    lines+=['','| Paired efficiency metric | Available pairs | Median B minus A | Median B / A |','| --- | ---: | ---: | ---: |']
    for name,metric in efficiency.items():
        lines.append(f"| {name} | {metric['available_pairs']} | {number(metric['median_B_minus_A'])} | {number(metric['median_B_over_A'])} |")
    lines+=['','## Success by task type','','| Type | A PASS / runs | B PASS / runs |','| --- | ---: | ---: |']
    for category,t in summary['categories'].items():
        lines.append(f"| {category} | {t['A']['passes']}/{t['A']['runs']} | {t['B']['passes']}/{t['B']['runs']} |")
    lines+=['','## Task-level results','','| Task | Type | A PASS / runs | B PASS / runs |','| --- | --- | ---: | ---: |']
    for tid,t in summary['tasks'].items():
        lines.append(f"| {tid} | {t['category']} | {t['A']['passes']}/{t['A']['runs']} | {t['B']['passes']}/{t['B']['runs']} |")
    lines+=['','## Trace-derived behavior','','These are deterministic command-pattern proxies, not subjective quality scores.','',
            '| Behavior | A true / available | B true / available |','| --- | ---: | ---: |']
    for key,metric in a['behavior'].items():
        other=b['behavior'][key];lines.append(f"| {key} | {metric['true']}/{metric['available']} | {other['true']}/{other['available']} |")
    lines+=['','Risk reporting records explicit risk/limitation language, not the completeness of disclosure. Continued-after-failure records a later detected successful verification. Unsupported verification language is a trace flag; fabricated execution claims remain unavailable without trace review. Source-edit and stale-verification flags are warnings, not independent proof of fabrication.','',
            '## Actual staleness and recovery interventions','',
            'A valid T09 observation requires independently passing phase 1, a detected successful agent verification in phase 1, and an actual later source change. Legacy missing fields are unavailable. A valid T10 observation requires actual SIGKILL interruption, two distinct session IDs, the same frozen budget configuration, and observed assistant turns within the shared ceiling. All final strict task scores still include nonqualifying runs.','',
            '```json',json.dumps(core,indent=2),'```','',
            '## Paired results','','| Task | Repeat | A | B |','| --- | ---: | --- | --- |']
    for pair in paired['paired_runs']:
        lines.append(f"| {pair['task_id']} | {pair['repeat']} | {pair['A']} | {pair['B']} |")
    lines+=['','## Failures','','| Run | Classification | Evidence |','| --- | --- | --- |']
    for r in rows:
        if r['failure_mode']:
            lines.append(f"| {r['run_id']} | {r['failure_mode']} | [independent tests](runs/{r['run_id']}/tests_after.json), [patch](runs/{r['run_id']}/patch.diff), [response](runs/{r['run_id']}/final_response.txt), [trace](runs/{r['run_id']}/phase1/transcript.jsonl) |")
    lines+=['','## Interpretation','',
            'Strict PASS requires independent contracts, upstream regressions, intact protected tests and an allowed modification scope. Verified completion uses explicit STATUS declarations; missing declarations are unknown. Frozen run scores are never relabelled by this analysis.','',
            'The frozen judgment rule is PASS with a positive task-cluster interval, FAIL with a negative interval or identical outcomes in all 30 pairs after a valid complete 60-run campaign, and INCONCLUSIVE otherwise. A FAIL for identical pairs means no observed improvement here; it does not prove population equivalence. Evidence problems, stop records or scoring-contract defects force INCONCLUSIVE.','',
            '## Validity and provenance','',
            '- [Evidence integrity audit](evidence_audit.json): exact schedule coverage, identities, retained hashes and grade/usage/session cross-checks.',
            '- [Frozen protocol and treatment hashes](freeze.json), [environment](audit.json), [baselines](baselines.json), [immutable tasks](tasks.json), [random schedule](schedule.json).']
    if violations:
        lines+=['','Retained validity issues:','```json',json.dumps(violations,indent=2),'```']
    if stop:
        lines+=['','Stop/incompletion record: '+json.dumps(stop)]
    elif not complete:
        lines+=['','Campaign not yet complete. Missing runs: '+', '.join(evidence['missing_run_ids'])]
    lines+=['','## Limitations','']+['- '+item for item in summary['limitations']]
    lines+=['','## Evidence and reproduction','',
            '- [Machine-readable summary](summary.json), [all results](results.jsonl), [CSV](results.csv), [observed success chart](success.svg).',
            '- Every runs/<id>/ retains prompts, transcripts, tool events, API usage, independent grades, response, patch and artifact hashes.',
            '- Regenerate: `python3 evals/benchmark-v1/harness.py analyze --output <campaign-directory>`.',
            '- Live execution commands and dependency/isolation details: [benchmark README](../../README.md).','']
    (out/'REPORT.md').write_text('\n'.join(lines))
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="660" height="225" viewBox="0 0 660 225" role="img" aria-label="Observed retained task success rates">',
         '<rect width="660" height="225" fill="#f8fafc"/>',
         f'<text x="24" y="28" font-family="sans-serif" font-size="18">Observed retained success · {actual} / {planned} runs</text>',
         '<text x="24" y="51" font-family="sans-serif" font-size="12">'+('Complete valid pilot' if valid else 'Incomplete or invalid campaign; raw scores only')+'</text>']
    for i,(label,arm,color) in enumerate([('A · Raw',a,'#64748b'),('B · Deep Native',b,'#2563eb')]):
        y=78+i*65;rate=arm['success_rate'] or 0
        svg += [f'<text x="24" y="{y+20}" font-family="sans-serif" font-size="14">{label}</text>',
                f'<rect x="164" y="{y}" width="380" height="30" fill="#e2e8f0"/>',
                f'<rect x="164" y="{y}" width="{380*rate}" height="30" fill="{color}"/>',
                f'<text x="558" y="{y+20}" font-family="sans-serif" font-size="14">{arm["passes"]}/{arm["runs"]}</text>']
    svg.append('</svg>');(out/'success.svg').write_text('\n'.join(svg))
    print('REPORT',out/'REPORT.md',judgment,actual,'runs',flush=True)
    return summary
