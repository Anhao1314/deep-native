#!/usr/bin/env python3
"""Read-only preliminary prefix analysis. No model calls or frozen-artifact edits."""
import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import statistics
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def med(values):
    values=list(values)
    return statistics.median(values) if values else None


def wilson(p,n):
    if not n:return None
    z=1.959963984540054;rate=p/n;d=1+z*z/n
    center=(rate+z*z/(2*n))/d
    half=z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/d
    return [center-half,center+half]


def aggregate(rows):
    n=len(rows);p=sum(r['task_success']=='PASS' for r in rows)
    declared=[r for r in rows if r.get('declared_done') is True]
    verified=sum(r.get('actually_valid') is True for r in declared)
    usable=[r for r in rows if r.get('tokens') is not None]
    return {'runs':n,'passes':p,'success_rate':p/n if n else None,
        'success_wilson95_descriptive':wilson(p,n),'declared_done':len(declared),
        'declared_blocked':sum(r.get('declared_done') is False for r in rows),
        'unknown_declaration':sum(r.get('declared_done') is None for r in rows),
        'verified_completions':verified,
        'verified_completion_rate':verified/len(declared) if declared else None,
        'false_completions':len(declared)-verified,
        'median_agent_seconds':med(r['duration_seconds'] for r in rows),
        'median_including_setup_and_grade_seconds':med(r['including_setup_and_grade_seconds'] for r in rows if r.get('including_setup_and_grade_seconds') is not None),
        'median_tool_calls':med(r['tool_calls'] for r in rows),
        'median_files_changed':med(len(r.get('files_changed',[])) for r in rows),
        'median_lines_changed':med(r.get('lines_added',0)+r.get('lines_removed',0) for r in rows),
        'tokens_available_runs':len(usable),'median_total_tokens':med(r['tokens']['total_tokens'] for r in usable),
        'token_categories':{k:{'median':med(r['tokens'].get(k,0) for r in usable),
            'available_total':sum(r['tokens'].get(k,0) for r in usable)}
            for k in ['input_tokens','output_tokens','cache_read_input_tokens','cache_creation_input_tokens']},
        'actual_api_cost_usd':None}


def provider_tokens(calls):
    calls=[c for c in calls if '/messages' in c.get('path','') and 'count_tokens' not in c.get('path','')]
    if not calls or any(not c.get('complete') or not c.get('usage') for c in calls):return None
    totals={k:sum(c['usage'].get(k,0) for c in calls)
            for k in ['input_tokens','output_tokens','cache_read_input_tokens','cache_creation_input_tokens']}
    totals['total_tokens']=sum(totals.values())
    return totals


def paired(rows):
    index={(r['task_id'],r['repeat'],r['condition']):r for r in rows}
    pairs=[];clusters={}
    for tid,repeat in sorted({(r['task_id'],r['repeat']) for r in rows}):
        a=index.get((tid,repeat,'A'));b=index.get((tid,repeat,'B'))
        if not a or not b:continue
        delta=int(b['task_success']=='PASS')-int(a['task_success']=='PASS')
        pairs.append({'task_id':tid,'repeat':repeat,'A_run':a['run_id'],'B_run':b['run_id'],
                      'A':a['task_success'],'B':b['task_success'],'delta':delta})
        clusters.setdefault(tid,[]).append(delta)
    means=[statistics.mean(v) for v in clusters.values()];interval=None
    if len(means)>=2:
        rng=random.Random(91271)
        samples=sorted(statistics.mean(rng.choices(means,k=len(means))) for _ in range(20000))
        interval=[samples[500],samples[19499]]
    ids={p[k] for p in pairs for k in ['A_run','B_run']}
    efficiency={}
    for key,getter in [('agent_seconds',lambda r:r.get('duration_seconds')),
                       ('context_processing_tokens',lambda r:(r.get('tokens') or {}).get('total_tokens'))]:
        values=[(getter(index[(p['task_id'],p['repeat'],'A')]),getter(index[(p['task_id'],p['repeat'],'B')])) for p in pairs]
        values=[(a,b) for a,b in values if a is not None and b is not None]
        efficiency[key]={'available_pairs':len(values),'median_B_minus_A':med(b-a for a,b in values),
                         'median_B_over_A':med(b/a for a,b in values if a>0)}
    return {'complete_pairs':len(pairs),'paired_runs':pairs,
        'A':aggregate([r for r in rows if r['run_id'] in ids and r['condition']=='A']),
        'B':aggregate([r for r in rows if r['run_id'] in ids and r['condition']=='B']),
        'unpaired_runs':[r['run_id'] for r in rows if r['run_id'] not in ids],
        'B_wins':sum(p['delta']>0 for p in pairs),'B_losses':sum(p['delta']<0 for p in pairs),
        'ties':sum(p['delta']==0 for p in pairs),
        'mean_task_delta':statistics.mean(means) if means else None,
        'task_cluster_bootstrap95_descriptive':interval,'task_cluster_count':len(means),
        'bootstrap_seed':91271,'bootstrap_samples':20000,'paired_efficiency':efficiency}


def audit(campaign,paths,rows,expected_count):
    issues=[];schedule=read(campaign/'schedule.json');freeze=read(campaign/'freeze.json')
    tasks={t['id']:t for t in read(campaign/'tasks.json')['tasks']}
    budget=read(campaign/'tasks.json')['budget'];baselines=read(campaign/'baselines.json')
    expected={r['run_id']:r for r in schedule[:expected_count]};actual=[r['run_id'] for r in rows]
    prefix=set(actual)==set(expected) and len(actual)==len(set(actual))==expected_count
    if not prefix:issues.append({'issue':'not_exact_frozen_schedule_prefix'})
    for name,key in [('tasks.json','tasks_sha256'),('schedule.json','schedule_sha256'),
                     ('audit.json','audit_sha256'),('baselines.json','baselines_sha256')]:
        if key not in freeze or sha(campaign/name)!=freeze[key]:issues.append({'issue':'frozen_input_hash','file':name})
    for name,value in freeze['protocol_sha256'].items():
        p=campaign/'frozen-harness'/name
        if not p.is_file() or sha(p)!=value:issues.append({'issue':'frozen_protocol_snapshot','file':name})
    treatment=campaign/'frozen-treatment'
    actual_treatment={str(p.relative_to(treatment)):sha(p) for p in treatment.rglob('*') if p.is_file()}
    if actual_treatment!=freeze.get('treatment_sha256'):issues.append({'issue':'treatment_hashes'})
    for path,row in zip(paths,rows):
        root=path.parent;rid=row['run_id'];local=[]
        if root.name!=rid or rid not in expected or any(row.get(k)!=v for k,v in expected.get(rid,{}).items()):local.append('identity')
        hashes=read(root/'artifact_hashes.json')
        for name,value in hashes.items():
            if not (root/name).is_file() or sha(root/name)!=value:local.append('artifact_hash:'+name)
        for name in ['result.json','metadata.json','tests_after.json','final_response.txt','patch.diff',
                     'api_calls.json','phase1/prompt.txt','phase1/transcript.jsonl','phase1/session.json','phase1/command.json']:
            if name not in hashes:local.append('missing_required_hash:'+name)
        if row.get('sessions')==2:
            for name in ['phase2/prompt.txt','phase2/transcript.jsonl','phase2/session.json','phase2/command.json']:
                if name not in hashes:local.append('missing_required_hash:'+name)
        if (root/'phase1/prompt.txt').read_bytes()!=tasks[row['task_id']]['prompt'].encode():local.append('prompt')
        if row['fixture_commit']!=baselines[row['task_id']]['fixture_commit']:local.append('fixture')
        grade=read(root/'tests_after.json')
        valid=bool(grade.get('pass') and not row.get('forbidden_changes') and not row.get('protected_test_changes'))
        if valid!=row.get('actually_valid') or ('PASS' if valid else 'FAIL')!=row['task_success']:local.append('strict_grade')
        final=[s.strip() for s in (root/'final_response.txt').read_text().splitlines() if s.strip()]
        marker=re.fullmatch(r'STATUS:\s*(DONE|BLOCKED)',final[-1]) if final else None
        done=(marker.group(1)=='DONE') if marker else None
        if done!=row.get('declared_done'):local.append('final_marker')
        if row.get('false_completion')!=(done is True and not valid):local.append('false_completion')
        if read(root/'metadata.json').get('budget')!=budget:local.append('budget_configuration')
        sessions=[read(p) for p in sorted(root.glob('phase*/session.json'))]
        if len(sessions)!=row.get('sessions'):local.append('sessions')
        if abs(sum(s['duration_seconds'] for s in sessions)-row['duration_seconds'])>.001:local.append('duration_aggregate')
        if sum(s['observed_assistant_messages'] for s in sessions)>budget['assistant_turns']:local.append('shared_turn_ceiling')
        calls=read(root/'api_calls.json')
        if provider_tokens(calls)!=row.get('tokens'):local.append('provider_tokens')
        models=sorted({c['response_model'] for c in calls if c.get('response_model')})
        if models!=['deepseek-flash'] or models!=row.get('response_models'):local.append('model_identity')
        if not row.get('treatment_activation_observed'):local.append('arm_activation')
        if row['condition']=='A' and not row.get('control_clean'):local.append('control_clean')
        if local:issues.append({'run_id':rid,'issues':local})
    return {'integrity_status':'PASS' if not issues else 'FAIL','issues':issues,
            'exact_prefix':prefix,'missing_planned_run_ids':[s['run_id'] for s in schedule if s['run_id'] not in actual],
            'scope':'Read-only retained hashes/identities/prompts/strict grades/status/budgets/provider/model and activation consistency; hidden model weights and subjective behavior are not attested.'}


def analyze(campaign,output,expected_count,trace_review,runtime_review=None):
    campaign=campaign.resolve();output=output.resolve()
    if campaign==output or campaign in output.parents:raise ValueError('Output must be outside the frozen campaign.')
    if output.suffix!='.json':raise ValueError('Output must be .json.')
    for supplement in [trace_review,runtime_review]:
        if supplement is not None and not supplement.is_file():raise ValueError('Wait for finalized supplement: '+str(supplement))
    runtime=read(runtime_review) if runtime_review else None
    trace=read(trace_review) if trace_review else None
    if runtime is not None and 'sandbox_shell_anomalies' not in runtime:raise ValueError('Wait for expanded native-shell runtime audit.')
    paths=sorted((campaign/'runs').glob('*/result.json'));rows=[read(p) for p in paths]
    if len(rows)!=expected_count:raise ValueError(f'Wait for {expected_count} finalized results; found {len(rows)}.')
    for p in paths:
        if not (p.parent/'artifact_hashes.json').exists() or read(p.parent/'artifact_hashes.json').get('result.json')!=sha(p):
            raise ValueError('Wait for final hashes: '+p.parent.name)
    before={str(p.relative_to(campaign)):sha(p) for p in paths}
    integrity=audit(campaign,paths,rows,expected_count);all_rows={a:aggregate([r for r in rows if r['condition']==a]) for a in ['A','B']}
    matched=paired(rows);manifest=read(campaign/'tasks.json');environment=read(campaign/'audit.json');freeze=read(campaign/'freeze.json')
    tasks={t['id']:{'category':t['category'],**{a:aggregate([r for r in rows if r['task_id']==t['id'] and r['condition']==a]) for a in ['A','B']}} for t in manifest['tasks']}
    types={cat:{a:aggregate([r for r in rows if r['category']==cat and r['condition']==a]) for a in ['A','B']} for cat in sorted({t['category'] for t in manifest['tasks']})}
    failures=[]
    for path,row in zip(paths,rows):
        if row['task_success']=='PASS':continue
        grade=read(path.parent/'tests_after.json')
        failing=[key for key in ['contract','upstream_regression','new_regression_tests'] if grade.get(key,{}).get('exit_code')]
        if row.get('forbidden_changes'):failing.append('out_of_scope')
        if row.get('protected_test_changes'):failing.append('protected_tests_modified')
        failures.append({'run_id':row['run_id'],'failing_checks':failing,'declared_done':row.get('declared_done'),'stop_reasons':row.get('stop_reasons'),
                         'evidence':{k:os.path.relpath(path.parent/name,output.parent) for k,name in [('grade','tests_after.json'),('response','final_response.txt'),('trace','phase1/transcript.jsonl')]}})
    stop=read(campaign/'campaign_stop.json') if (campaign/'campaign_stop.json').exists() else None
    user_pause=read(campaign/'user_pause.json') if (campaign/'user_pause.json').exists() else None
    blockers={n:read(campaign/n) for n in ['grading_contract_issue.json','infrastructure_issue.json'] if (campaign/n).exists()}
    no_improvement_signal=matched['B_wins']==0 and matched['B_losses']>0
    decision='STOP' if integrity['issues'] or blockers or no_improvement_signal else 'ANALYZE'
    reason=('Resolve evidence or experiment-validity issues before further interpretation.' if integrity['issues'] or blockers
            else 'Stop expanding this campaign now: the matched prefix shows no B quality win and at least one B loss. Preserve the user-requested pause and continue offline trace analysis. This is not a population claim that the Skill is ineffective and does not authorize additional API calls.' if no_improvement_signal
            else 'Keep the user-requested pause and analyze the matched prefix, efficiency and trace limitations before deciding whether more runs are warranted. This does not authorize additional API calls.')
    report={'schema':1,'analysis_kind':'post_hoc_preliminary_user_stopped_prefix','campaign':str(campaign),
        'planned_runs':60,'actual_runs':len(rows),'all_retained_runs':all_rows,'matched_subset':matched,
        'tasks':tasks,'task_types':types,'failures':failures,'independent_integrity_audit':integrity,
        'operational_recommendation':decision,'operational_scope':'whether_to_expand_this_campaign_now','operational_reason':reason,'formal_frozen_judgment':'INCONCLUSIVE',
        'formal_plan_complete':False,'campaign_stop':stop,'user_pause':user_pause,'blocking_sidecars':blockers,
        'supplemental_trace_review_path':str(trace_review) if trace_review else None,
        'supplemental_runtime_review_path':str(runtime_review) if runtime_review else None,
        'supplemental_runtime_review':runtime,
        'runtime_environment_status':runtime.get('runtime_environment_status') if runtime else None,
        'environment_limitations':runtime.get('sandbox_shell_anomalies') if runtime else None,
        'supplemental_trace_review':trace,
        'supplement_source_sha256':{str(p):sha(p) for p in [trace_review,runtime_review] if p is not None},
        'provenance':{'deep_native_commit':freeze['deep_native_commit'],'claude':environment['claude'],
                      'requested_model':environment['requested_model'],'endpoint':environment['upstream_endpoint'],
                      'protocol_sha256':freeze['protocol_sha256']},
        'limitations':['The user-requested stop is not the preregistered endpoint; uncertainty is descriptive, not a sequentially valid statistical decision.',
            'All retained runs are reported; only complete pairs enter matched comparisons and the extra arm is disclosed.',
            'Ten curated tasks and few repeats cannot establish population superiority, equivalence or broad recovery benefits.',
            'Raw verification proxies include version/help probes; separate actual-execution review is needed. Original fields remain unchanged.',
            'Unknown completion declarations limit claim-conditional false-completion interpretation.',
            'Incomplete SSE usage is unavailable; cached context-processing tokens are not dollar billing.',
            'Independent strict grades and marker-based Verified Completion are never relabelled by this supplement.',
            'Configuration and artifact integrity PASS does not imply anomaly-free ordinary shell execution; native heredoc/temp failures limit clean Skill-effect interpretation.',
            'The bootstrap only resamples observed outcomes; an upper zero with no observed B wins does not exclude benefits on unobserved tasks or repeats.'],
        'raw_result_sha256_before':before}
    after={str(p.relative_to(campaign)):sha(p) for p in paths}
    if before!=after:raise ValueError('Campaign changed during read-only analysis.')
    report['raw_result_sha256_after']=after
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    pct=lambda v:'unavailable' if v is None else f'{100*v:.1f}%'
    num=lambda v:'unavailable' if v is None else f'{v:,}' if isinstance(v,int) else f'{v:,.1f}'
    ratio=lambda v:'unavailable' if v is None else f'{v:.2f}x'
    a=all_rows['A'];b=all_rows['B'];ma=matched['A'];mb=matched['B'];ci=matched['task_cluster_bootstrap95_descriptive']
    lines=['# Preliminary v4 analysis: '+decision,'',
        f'Planned 60 runs; retained **{len(rows)}** completed runs. Formal frozen judgment: **INCONCLUSIVE**. This operational recommendation is separate from the preregistered final judgment.','',
        reason,'',f"Read-only evidence integrity: **{integrity['integrity_status']}**; exact frozen prefix: **{integrity['exact_prefix']}**. Raw scores were unchanged.",'',
        '## All outcomes and matched comparison','','| Cohort | A PASS / runs | B PASS / runs |','| --- | ---: | ---: |',
        f"| All {len(rows)} retained | {a['passes']}/{a['runs']} ({pct(a['success_rate'])}) | {b['passes']}/{b['runs']} ({pct(b['success_rate'])}) |",
        f"| Matched subset | {ma['passes']}/{ma['runs']} ({pct(ma['success_rate'])}) | {mb['passes']}/{mb['runs']} ({pct(mb['success_rate'])}) |",'',
        'Unpaired retained runs: '+(', '.join(matched['unpaired_runs']) or 'none')+'.','',
        f"Matched pairs: {matched['complete_pairs']}; B wins {matched['B_wins']}, B losses {matched['B_losses']}, ties {matched['ties']}. Task-mean B minus A: "+('unavailable' if matched['mean_task_delta'] is None else f"{100*matched['mean_task_delta']:+.1f} percentage points")+'.']
    if runtime:
        shell=runtime['sandbox_shell_anomalies']['counts']
        total_denials=sum(v['denied_bash_tool_results'] for v in shell.values())
        heredocs=sum(v['categories'].get('heredoc_tempfile_denial',0) for v in shell.values())
        masked=sum(v['masked_compound_tool_results'] for v in shell.values())
        block=['## Runtime environment limitations','',
            'Artifact/configuration integrity is separate from shell compatibility. The expanded audit observed denied native heredoc/temp operations and masked compound-command errors. These can consume turns or alter verification behavior; passing hashes do not make this an anomaly-free measurement of Skill effects.',
            '', f'Across all retained runs there were **{total_denials} denied Bash results**: **{heredocs} heredoc temp failures**, **{total_denials-heredocs} outside-run/native temp-write denials**, and **{masked} masked compound results**. A had {shell["A"]["denied_bash_tool_results"]} denials across {shell["A"]["affected_runs"]}/{shell["A"]["runs_reviewed"]} runs; B had {shell["B"]["denied_bash_tool_results"]} across {shell["B"]["affected_runs"]}/{shell["B"]["runs_reviewed"]}.', '',
            'Observed counts from the independent runtime audit:', '```json', json.dumps(runtime['sandbox_shell_anomalies']['counts'],indent=2), '```','',
            'Later alternative/retry/check evidence is retained, with genuine program/test failures kept separate. Raw strict scores remain unchanged. Isolate these shell quirks offline before any newly authorized model calls.','']
        lines[8:8]=block
    if ci:lines.append(f'Descriptive task-cluster bootstrap range: [{100*ci[0]:.1f}, {100*ci[1]:.1f}] percentage points ({matched["task_cluster_count"]} tasks; 20,000 resamples, seed 91271). No formal statistical conclusion follows from this adaptively stopped snapshot.')
    lines+=['','## Completion and efficiency','','| Metric, all retained runs | A | B |','| --- | ---: | ---: |']
    for label,key in [('Declared DONE','declared_done'),('Declared BLOCKED','declared_blocked'),('Unknown declaration','unknown_declaration'),
        ('False completions','false_completions'),('Median agent seconds','median_agent_seconds'),
        ('Median including setup/grading seconds','median_including_setup_and_grade_seconds'),
        ('Median tool calls','median_tool_calls'),('Median files changed','median_files_changed'),
        ('Median lines changed','median_lines_changed'),('Median available tokens','median_total_tokens')]:
        lines.append(f'| {label} | {num(a[key])} | {num(b[key])} |')
    lines+=[f"| Verified Completion / declared DONE | {pct(a['verified_completion_rate'])} | {pct(b['verified_completion_rate'])} |",
        f"| Token availability | {a['tokens_available_runs']}/{a['runs']} | {b['tokens_available_runs']}/{b['runs']} |",
        '| Actual API dollars | unavailable | unavailable |','',
        '| Common-pair efficiency | Available pairs | Median B minus A | Median B / A |','| --- | ---: | ---: | ---: |']
    for key,value in matched['paired_efficiency'].items():lines.append(f"| {key} | {value['available_pairs']} | {num(value['median_B_minus_A'])} | {ratio(value['median_B_over_A'])} |")
    lines+=['','Tokens include cached context processing; unavailable interrupted usage is not estimated. These are not equal-cost billing tokens.','',
        '## Task breakdown','','| Task | Type | A PASS / runs | B PASS / runs |','| --- | --- | ---: | ---: |']
    for tid,t in tasks.items():lines.append(f"| {tid} | {t['category']} | {t['A']['passes']}/{t['A']['runs']} | {t['B']['passes']}/{t['B']['runs']} |")
    lines+=['','## Failure evidence','','| Run | Failed strict checks | Declaration | Evidence |','| --- | --- | --- | --- |']
    for f in failures:lines.append(f"| {f['run_id']} | {', '.join(f['failing_checks'])} | {f['declared_done']} | [grade](<{f['evidence']['grade']}>), [response](<{f['evidence']['response']}>), [trace](<{f['evidence']['trace']}>) |")
    lines+=['','## Verification and recovery interpretation','',
        'The frozen proxy can treat version/help probes as successful verification. Retain its raw counts and use separate actual-execution trace review. Missing regex matches and wrapper errors are not fabrication evidence.','',
        'T09 qualification requires independent phase-1 PASS, actual successful functional checking there, and actual later source change. T10 needs actual interruption and distinct sessions; state presence or final PASS alone does not demonstrate checkpoint benefit.','',
        'Supplemental trace review: '+('[JSON](<'+os.path.relpath(trace_review.resolve(),output.parent)+'>)' if trace_review else 'pending')+'.','',
        'Supplemental runtime audit: '+('[JSON](<'+os.path.relpath(runtime_review.resolve(),output.parent)+'>)' if runtime_review else 'pending')+'.','',
        '## Interpretation limits','']+['- '+v for v in report['limitations']]
    lines+=['','## Provenance','',
        f"Claude Code {environment['claude']}; model {environment['requested_model']}; endpoint {environment['upstream_endpoint']}; Deep Native commit {freeze['deep_native_commit']}.",'',
        'This preliminary stage does not replace the planned design or claim a completed 60-run experiment.']
    if trace:
        summary=trace['summary'];actual=summary['all_completed'];paired_actual=summary['matched_only']
        section=['','## Supplemental actual-execution review','',
            '| Review measure | All A | All B | Matched A | Matched B |','| --- | ---: | ---: | ---: | ---: |']
        for label,key in [('Actual functional check attempted','actual_check_attempt'),
                          ('Actual completed successful check','actual_completed_successful_check'),
                          ('Frozen successful-verification proxy','preregistered_successful_verification')]:
            values=[cohort[arm][key] for cohort,arm in [(actual,'A'),(actual,'B'),(paired_actual,'A'),(paired_actual,'B')]]
            section.append('| '+label+' | '+' | '.join(str(v['true'])+'/'+str(v['available']) for v in values)+' |')
        t09=summary['T09'];t10=summary['T10']
        section+=['',f"T09 raw qualifying observations were A {t09['A']['preregistered_qualifying']}, B {t09['B']['preregistered_qualifying']}; actual trace-validated observations were A {t09['A']['trace_validated_qualifying']}, B {t09['B']['trace_validated_qualifying']}. Version probes do not establish functional checking. This stage therefore supplies no qualifying verified-then-changed case for either arm.",'',
            f"T10 actual interruption/new-session observations: A {t10['A']['actual_SIGKILL_new_session']}, B {t10['B']['actual_SIGKILL_new_session']}. Both used the 90-second fallback before source progress; checkpoint notes were A {t10['A']['checkpoint_note_present']}, B {t10['B']['checkpoint_note_present']}. B consulted retained state, which does not demonstrate checkpoint benefit.",'',
            f"Final claim review found {summary['final_claim_contradictions_found']} contradictions in {summary['nonempty_final_reports_reviewed']} available final reports. This does not attest missing final reports or every intermediate assertion. Raw completion fields and scores remain unchanged.",'']
        # Put the supplementary findings immediately before the interpretation limits.
        where=lines.index('## Interpretation limits')
        lines[where:where]=section
    chart=output.with_suffix('.svg')
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="340" viewBox="0 0 760 340" role="img" aria-label="Preliminary observed success, all retained runs and matched pairs">',
         '<rect width="760" height="340" fill="#f8fafc"/>',
         f'<text x="24" y="29" font-family="sans-serif" font-size="18">Preliminary v4 · {len(rows)} / 60 runs · formal INCONCLUSIVE</text>']
    for section,(title,arms) in enumerate([('All retained outcomes',{'A':a,'B':b}),('Matched subset only',{'A':ma,'B':mb})]):
        y=67+section*128
        svg.append(f'<text x="24" y="{y}" font-family="sans-serif" font-size="14">{title}</text>')
        for i,(arm,color) in enumerate([('A','#64748b'),('B','#2563eb')]):
            yy=y+14+i*38;value=arms[arm];width=440*(value['success_rate'] or 0)
            svg.extend([f'<text x="24" y="{yy+20}" font-family="sans-serif" font-size="14">{arm}</text>',
                f'<rect x="72" y="{yy}" width="440" height="26" fill="#e2e8f0"/>',
                f'<rect x="72" y="{yy}" width="{width}" height="26" fill="{color}"/>',
                f'<text x="535" y="{yy+20}" font-family="sans-serif" font-size="14">{value["passes"]}/{value["runs"]} ({pct(value["success_rate"])})</text>'])
    svg.extend(['<text x="24" y="324" font-family="sans-serif" font-size="12">Unpaired observations remain in all-retained results; descriptive snapshot only.</text>','</svg>'])
    chart.write_text('\n'.join(svg)+'\n')
    lines[7:7]=['','![Observed retained and matched success rates](<'+chart.name+'>)','']
    output.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    with output.with_suffix('.csv').open('w',newline='') as handle:
        keys=['run_id','task_id','repeat','condition','task_success','declared_done','actually_valid','false_completion','duration_seconds','tool_calls']
        writer=csv.DictWriter(handle,keys,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    print(json.dumps({'actual_runs':len(rows),'A_passes':a['passes'],'B_passes':b['passes'],
        'matched_pairs':matched['complete_pairs'],'unpaired':matched['unpaired_runs'],
        'integrity':integrity['integrity_status'],'recommendation':decision},indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--expected-runs',type=int,default=21)
    parser.add_argument('--trace-review',type=Path)
    parser.add_argument('--runtime-review',type=Path)
    args=parser.parse_args()
    analyze(args.campaign,args.output,args.expected_runs,args.trace_review,args.runtime_review)

