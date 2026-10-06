"""Regenerate every reported number from retained run artifacts; no model calls."""
import csv
import html
import json
import math
import random
import statistics
from collections import Counter
from pathlib import Path

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
        'median_duration_seconds':statistics.median(r['duration_seconds'] for r in rows) if rows else None,
        'tokens_available_runs':len(token_rows),
        'median_total_tokens':statistics.median(r['tokens']['total_tokens'] for r in token_rows) if token_rows else None,
        'total_provider_tokens_available':sum(r['tokens']['total_tokens'] for r in token_rows),
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
            'mean_task_delta':statistics.mean(means) if means else None,
            'task_cluster_bootstrap95':interval,'bootstrap_seed':91271,
            'bootstrap_samples':20000,'task_cluster_count':len(means)}

def generate(out):
    paths=sorted((out/'runs').glob('*/result.json'))
    rows=[json.loads(p.read_text()) for p in paths]
    a=aggregate([r for r in rows if r['condition']=='A']);b=aggregate([r for r in rows if r['condition']=='B'])
    paired=paired_summary(rows)
    violations=[r['run_id'] for r in rows if not r.get('treatment_activation_observed',False) or r.get('response_models')!=['deepseek-flash']]
    for r,p in zip(rows,paths):
        grade=json.loads(p.with_name('tests_after.json').read_text())
        r['failure_mode']=failure_reason(r,grade)
    actual=len(rows);complete=actual==60 and not violations
    interval=paired['task_cluster_bootstrap95']
    # Conservative, frozen judgment rule; no significance/parity claim.
    judgment='INCONCLUSIVE'
    if complete and interval:
        if interval[0]>0:judgment='PASS'
        elif interval[1]<0:judgment='FAIL'
        elif a['passes']==b['passes'] and all(p['delta']==0 for p in paired['paired_runs']):judgment='FAIL'
    core={arm:{'staleness':{},'recovery':{}} for arm in ['A','B']}
    for arm in ['A','B']:
        stale=[r for r in rows if r['task_id']=='T09' and r['condition']==arm]
        recovery=[r for r in rows if r['task_id']=='T10' and r['condition']==arm]
        interventions=[json.loads((out/'runs'/r['run_id']/'staleness_intervention.json').read_text()) for r in stale]
        interruptions=[json.loads((out/'runs'/r['run_id']/'interruption.json').read_text()) for r in recovery if (out/'runs'/r['run_id']/'interruption.json').exists()]
        core[arm]['staleness']={'runs':len(stale),'stage1_independently_passed':sum(r.get('phase1_pass',False) for r in stale),
            'actual_later_source_changes':sum(i['actual_later_source_change'] for i in interventions),
            'stale_completion_claims':sum(r.get('stale_completion_claim',False) for r in stale),
            'final_passes':sum(r['task_success']=='PASS' for r in stale)}
        core[arm]['recovery']={'runs':len(recovery),'actual_interruptions':sum(r['recovery_interrupted'] for r in recovery),
            'new_sessions':sum(r['sessions']==2 for r in recovery),'state_at_interrupt':sum(i['state_present'] for i in interruptions),
            'checkpoint_notes_at_interrupt':sum(i.get('checkpoint_note_present',False) for i in interruptions),
            'passes':sum(r['task_success']=='PASS' for r in recovery)}
    summary={'schema':1,'planned_runs':60,'actual_runs':actual,'completed_plan':actual==60,
             'experiment_validity_issues':violations,'judgment':judgment,'A':a,'B':b,
             'paired':paired,'tasks':{},'categories':{},'core_tasks':core,
             'failure_modes':{arm:dict(Counter(r['failure_mode'] for r in rows if r['condition']==arm and r['failure_mode'])) for arm in ['A','B']},
             'limitations':['Ten curated tasks on two Python utility repositories, not a representative coding-task population.',
                 'Three tasks use injected regressions; one task injects a transient infrastructure failure.',
                 'Long-horizon task is bounded to 24 assistant turns and 480 seconds, not a multi-hour project.',
                 'Provider model alias is mutable; response identity is recorded but underlying weights are not attestable.',
                 'Seatbelt is a pragmatic local boundary, not a hostile-agent containment proof.',
                 'Provider-side prompt caching cannot be reset; randomized pairs reduce, but do not eliminate, time/cache effects.',
                 'Regex-derived behavior metrics are proxies; risk reporting and fabricated checks require human trace review.',
                 'Wilson intervals treat runs as independent and are descriptive only; task-cluster bootstrap is the primary uncertainty estimate.',
                 'API dollar cost is unavailable. CLI costUSD with costBasis unknown is retained only as raw diagnostic telemetry.']}
    for tid in sorted({r['task_id'] for r in rows}):
        subset=[r for r in rows if r['task_id']==tid]
        summary['tasks'][tid]={'category':subset[0]['category'],**{arm:aggregate([r for r in subset if r['condition']==arm]) for arm in ['A','B']}}
    for category in sorted({r['category'] for r in rows}):
        summary['categories'][category]={arm:aggregate([r for r in rows if r['category']==category and r['condition']==arm]) for arm in ['A','B']}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'results.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    with (out/'results.csv').open('w',newline='') as f:
        keys=['run_id','task_id','repeat','condition','task_success','declared_done','actually_valid','false_completion','duration_seconds','tool_calls','failure_mode']
        writer=csv.DictWriter(f,keys,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    percent=lambda value:'unavailable' if value is None else f'{value*100:.1f}%'
    number=lambda value:'unavailable' if value is None else f'{value:,.1f}'
    lines=['# Pilot Benchmark v1: '+judgment,'',f'Planned **60 runs**; completed **{actual}**. All figures below are generated from retained artifacts.','',
           '| Metric | A: Raw DeepSeek | B: Deep Native |','| --- | ---: | ---: |']
    for title,key in [('Task Success Rate','success_rate'),('Verified Completion / declared done','verified_completion_rate'),('Verified Completion / all runs','verified_completion_per_run')]:
        lines.append(f'| {title} | {percent(a[key])} | {percent(b[key])} |')
    for title,key in [('PASS / runs','passes'),('Declared done','declared_done'),('False completions','false_completions'),('Unknown declaration','unknown_declaration')]:
        lines.append(f'| {title} | {a[key]} | {b[key]} |')
    for title,key in [('Median duration (s)','median_duration_seconds'),('Median tokens (available runs)','median_total_tokens'),('Median tool calls','median_tool_calls'),('Median changed files','median_files_changed'),('Median lines changed','median_lines_changed')]:
        lines.append(f'| {title} | {number(a[key])} | {number(b[key])} |')
    lines+=['| Actual API cost | unavailable | unavailable |','',
            f"Token availability: A {a['tokens_available_runs']}/{a['runs']}, B {b['tokens_available_runs']}/{b['runs']}. Incomplete interrupted SSE responses are not estimated.",
            '',f"Paired complete observations: {paired['complete_pairs']}. Task-mean change: {percent(paired['mean_task_delta'])} percentage-point scale."]
    if interval:lines.append(f'95% task-cluster bootstrap interval for the change: [{interval[0]*100:.1f}, {interval[1]*100:.1f}] percentage points. This describes uncertainty on this curated task set, not population superiority.')
    lines+=['','## Task-level results','','| Task | Type | A PASS / runs | B PASS / runs |','| --- | --- | ---: | ---: |']
    for tid,t in summary['tasks'].items():lines.append(f"| {tid} | {t['category']} | {t['A']['passes']}/{t['A']['runs']} | {t['B']['passes']}/{t['B']['runs']} |")
    lines+=['','## Trace-derived behavior','','These are deterministic command-pattern proxies, not subjective quality scores.','', '| Behavior | A true / available | B true / available |','| --- | ---: | ---: |']
    for key,metric in a['behavior'].items():
        other=b['behavior'][key];lines.append(f"| {key} | {metric['true']}/{metric['available']} | {other['true']}/{other['available']} |")
    lines+=['','Risk reporting means explicit risk/limitation language occurred in the final response; it does not assess whether the risk disclosure was complete. Unsupported verification language is a trace-pattern flag; fabricated execution claims remain unavailable without human trace review. `edit_after_last_verification` is a warning proxy, not proof of a false claim.','',
            '## Actual staleness and recovery interventions','','```json',json.dumps(core,indent=2),'```','',
            '## Paired results','','| Task | Repeat | A | B |','| --- | ---: | --- | --- |']
    for pair in paired['paired_runs']:lines.append(f"| {pair['task_id']} | {pair['repeat']} | {pair['A']} | {pair['B']} |")
    lines+=['','## Failures','','| Run | Classification | Evidence |','| --- | --- | --- |']
    for r in rows:
        if r['failure_mode']:lines.append(f"| {r['run_id']} | {r['failure_mode']} | [independent tests](runs/{r['run_id']}/tests_after.json), [patch](runs/{r['run_id']}/patch.diff), [response](runs/{r['run_id']}/final_response.txt) |")
    lines+=['','## Interpretation','',
       'A strict PASS requires independent contract checks, upstream regression tests, preserved protected tests, and an allowed modification scope. A completion claim is measured by the common `STATUS: DONE` marker; missing markers are unknown.',
       '', 'The frozen judgment rule is PASS only with a positive task-cluster interval, FAIL with a negative interval or no differences in any pair after all 60 runs, and INCONCLUSIVE otherwise. Protocol violations force INCONCLUSIVE.',
       '', 'For recovery, inspect actual SIGKILL records and distinct session IDs; do not infer checkpoint effectiveness merely from task success. For staleness, inspect phase1 verification and the subsequent source change before attributing an improvement.',
       '', '## Limitations','']+['- '+text for text in summary['limitations']]
    if violations:lines+=['','Protocol validity issues: '+', '.join(violations)]
    if actual<60:
        stop=json.loads((out/'campaign_stop.json').read_text()) if (out/'campaign_stop.json').exists() else {'reason':'Campaign not yet complete.'}
        lines+=['','Stop/incompletion record: '+json.dumps(stop)]
    lines+=['','## Evidence and reproduction','',
        '- [Environment audit](audit.json), [frozen protocol](freeze.json), [tasks](tasks.json), [random schedule](schedule.json).',
        '- [Machine-readable summary](summary.json), [all results](results.jsonl), [CSV](results.csv).',
        '- Each `runs/<id>/` retains exact prompts, transcripts, tool events, API usage, baseline/independent grades, final response, patch, and artifact hashes.',
        '- Regenerate: `python3 evals/benchmark-v1/harness.py analyze --output <campaign-directory>`.',
        '- Real live execution commands and dependency/isolation details: [benchmark README](../../README.md).','']
    (out/'REPORT.md').write_text('\n'.join(lines))
    # Portable GitHub-friendly SVG, computed solely from aggregate counts.
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="660" height="200" viewBox="0 0 660 200" role="img" aria-label="Observed task success rates">',
         '<rect width="660" height="200" fill="#f8fafc"/>','<text x="24" y="28" font-family="sans-serif" font-size="18">Observed task success · '+str(actual)+' / 60 runs</text>']
    for i,(label,arm,color) in enumerate([('A · Raw',a,'#64748b'),('B · Deep Native',b,'#2563eb')]):
        y=70+i*65;rate=arm['success_rate'] or 0
        svg += [f'<text x="24" y="{y+20}" font-family="sans-serif" font-size="14">{label}</text>',f'<rect x="164" y="{y}" width="380" height="30" fill="#e2e8f0"/>',f'<rect x="164" y="{y}" width="{380*rate}" height="30" fill="{color}"/>',f'<text x="558" y="{y+20}" font-family="sans-serif" font-size="14">{arm["passes"]}/{arm["runs"]}</text>']
    svg.append('</svg>');(out/'success.svg').write_text('\n'.join(svg))
    print('REPORT',out/'REPORT.md',judgment,actual,'runs',flush=True)
    return summary
