#!/usr/bin/env python3
"""Offline review of completed v4 artifacts; never inspect active-run traces."""
import argparse
import datetime
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--expected-count', type=int, required=True)
    parser.add_argument('--output-prefix', type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve(); bench = repo / 'evals/benchmark-v1'
    out = bench / 'results/2026-10-06-pilot-v4'
    sys.path.insert(0, str(bench))
    import harness
    import isolation
    from transport import provider_tokens
    read = lambda path: json.loads(Path(path).read_text())
    hash_cache = {}
    def sha(path):
        path = Path(path)
        key = (str(path.resolve()), path.stat().st_size, path.stat().st_mtime_ns)
        if key not in hash_cache:
            hash_cache[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        return hash_cache[key]
    freeze = read(out / 'freeze.json'); audit = read(out / 'audit.json')
    schedule = read(out / 'schedule.json'); tasks = read(out / 'tasks.json')
    baselines = read(out / 'baselines.json')
    paths = sorted((out / 'runs').glob('*/result.json'))
    if len(paths) != args.expected_count:
        raise SystemExit(f'Expected {args.expected_count} completed result files, observed {len(paths)}; no review written.')
    for path in paths:
        if not (path.parent / 'artifact_hashes.json').is_file():
            raise SystemExit('Run has not fully finalized: ' + path.parent.name)
    issues = []; observations = []; protocol = {}; frozen_skill = {}; records = []; bases = {}
    def issue(name, run=None, detail=None):
        issues.append({'issue': name, **({'run_id': run} if run else {}),
                       **({'detail': detail} if detail is not None else {})})
    for name, expected in freeze['protocol_sha256'].items():
        current = sha(bench / name); archived = sha(out / 'frozen-harness' / name)
        protocol[name] = {'expected': expected, 'current': current, 'archived': archived,
                          'match': expected == current == archived}
        if not protocol[name]['match']: issue('protocol_changed', detail=name)
    for name, key in [('audit.json', 'audit_sha256'), ('baselines.json', 'baselines_sha256'),
                      ('tasks.json', 'tasks_sha256'), ('schedule.json', 'schedule_sha256')]:
        if sha(out / name) != freeze[key]: issue('campaign_input_changed', detail=name)
    for name, expected in freeze['treatment_sha256'].items():
        frozen = sha(out / 'frozen-treatment' / name)
        blob = subprocess.run(['git', '-C', str(repo), 'show', freeze['deep_native_commit'] + ':' + name],
                              check=True, capture_output=True).stdout
        original = hashlib.sha256(blob).hexdigest()
        current = sha(repo / name)
        frozen_skill[name] = {'expected': expected, 'frozen': frozen, 'fixed_commit': original,
                             'current_repository': current, 'match': expected == frozen == original == current}
        if not frozen_skill[name]['match']: issue('skill_changed', detail=name)
    completed_ids = {read(path)['run_id'] for path in paths}
    expected_ids = {entry['run_id'] for entry in schedule[:args.expected_count]}
    if completed_ids != expected_ids: issue('completed_schedule_prefix', detail=sorted(completed_ids ^ expected_ids))
    task_index = {task['id']: task for task in tasks['tasks']}
    schedule_index = {entry['run_id']: entry for entry in schedule}
    completed_workspaces = {read(path.parent / 'metadata.json')['workspace']: read(path)['run_id'] for path in paths}
    settings_variants = set(); native_warning_count = 0; api_incomplete = 0; artifacts_checked = 0
    expected_environment_checked = False
    for path in paths:
        folder = path.parent; result = read(path); rid = result['run_id']; meta = read(folder / 'metadata.json')
        workspace = Path(meta['workspace']); base = workspace.parent; bases[str(base)] = rid
        env = meta['environment']; local = []
        def check(condition, name, detail=None):
            if not condition:
                local.append(name); issue(name, rid, detail)
        check(folder.name == rid and all(result.get(key) == value for key, value in schedule_index[rid].items()), 'run_identity')
        check(meta['task'] == task_index[result['task_id']], 'exact_task_definition')
        check(result['fixture_commit'] == baselines[result['task_id']]['fixture_commit'], 'fixture_identity')
        check(meta['deep_native_commit'] == freeze['deep_native_commit'], 'treatment_commit_identity')
        check((folder / 'phase1/prompt.txt').read_text() == task_index[result['task_id']]['prompt'], 'exact_user_prompt')
        check(meta['budget'] == tasks['budget'], 'common_budget')
        required = ['metadata.json', 'result.json', 'tests_before.json', 'tests_after.json', 'api_calls.json',
                    'final_response.txt', 'behavior.json', 'patch.diff', 'local_workspace.txt', 'artifact_hashes.json']
        for name in required: check((folder / name).is_file(), 'missing_artifact', name)
        manifest = read(folder / 'artifact_hashes.json')
        actual_names = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name != 'artifact_hashes.json'}
        check(set(manifest) == actual_names, 'artifact_manifest_complete', sorted(set(manifest) ^ actual_names))
        for name, expected in manifest.items():
            check((folder / name).is_file() and sha(folder / name) == expected, 'artifact_hash_mismatch', name)
            artifacts_checked += 1
        check(sha(folder / 'patch.diff') == result['patch_sha256'], 'patch_hash')
        check(Path((folder / 'local_workspace.txt').read_text().strip()) == base, 'retained_workspace_pointer')
        check(workspace.is_dir(), 'retained_workspace_missing')
        python_dir = Path(env['PATH'].split(':')[0]); python = python_dir / 'python'
        resolved = {tool: shutil.which(tool, path=env['PATH']) for tool in ['git', 'python3', 'claude']}
        for tool, key in [('git', 'native_git_binary_sha256'), ('python3', 'python_binary_sha256'), ('claude', 'claude_binary_sha256')]:
            check(bool(resolved[tool]) and sha(Path(resolved[tool]).resolve()) == audit[key], 'resolved_binary_hash', tool)
        check(str(Path(resolved['git']).resolve()) == audit['native_git_path'], 'native_git_path')
        if not expected_environment_checked:
            harness.validate_environment(out, python); expected_environment_checked = True
        relay = type('RecordedRelay', (), {'url': env['ANTHROPIC_BASE_URL']})()
        check(env == harness.agent_env(Path(env['HOME']), base / 'tmp', python, relay, audit['requested_model']), 'exact_sanitized_environment')
        check(env.get('HOME') == str(base / 'home') and env.get('TMPDIR') == env.get('CLAUDE_CODE_TMPDIR') == str(base / 'tmp'), 'fresh_environment_paths')
        with patch('isolation.sys.base_prefix', audit['python_base_prefix']):
            expected_profile = isolation.sandbox_profile(workspace, Path(env['HOME']), python_dir.parent,
                                                        urlparse(env['ANTHROPIC_BASE_URL']).port)
        check((base / 'sandbox.sb').read_text() == expected_profile, 'exact_sandbox_profile')
        installed = {}; project_settings = sorted(str(p.relative_to(workspace)) for p in (workspace / '.claude').glob('*.json'))
        if result['condition'] == 'B':
            check(read(folder / 'installation.json')['exit_code'] == 0, 'treatment_installation_exit')
            target = workspace / '.claude/skills/deep-native'
            expected_relative = {str(Path(name).relative_to('skills/deep-native')) for name in freeze['treatment_sha256']}
            actual_relative = {str(p.relative_to(target)) for p in target.rglob('*') if p.is_file()}
            check(expected_relative == actual_relative, 'installed_treatment_file_set', sorted(expected_relative ^ actual_relative))
            for name, expected in freeze['treatment_sha256'].items():
                relative = Path(name).relative_to('skills/deep-native'); p = target / relative
                actual = sha(p) if p.is_file() else None; installed[str(relative)] = {'sha256': actual, 'matches_frozen': actual == expected}
                check(actual == expected, 'installed_treatment_hash', str(relative))
            hook_command = shlex.join([str(python), str(target / 'scripts/deep_native.py'), '--project', str(workspace), 'hook'])
            expected_settings = {'hooks': {event: [{'hooks': [{'command': hook_command, 'timeout': 15, 'type': 'command'}]}]
                                           for event in ['SessionStart', 'Stop']}}
            check(project_settings == ['.claude/settings.local.json'], 'treatment_project_settings_files', project_settings)
            check(read(workspace / '.claude/settings.local.json') == expected_settings, 'treatment_hook_configuration')
            check(result['treatment_activation_observed'] is True, 'native_skill_activation')
        else:
            check(not project_settings and not (workspace / '.claude/skills/deep-native').exists(), 'control_has_native_configuration')
            check(result['control_clean'] is True, 'control_clean_init')
        sessions = []; cleanup = []; initializations = []; warnings = []; external_attempts = []; tool_inputs = {}; tool_results = {}
        for phase in sorted(p for p in folder.glob('phase*') if p.is_dir()):
            for name in ['command.json', 'prompt.txt', 'transcript.jsonl', 'stderr.txt', 'final_response.txt',
                         'session.json', 'source_observations.json', 'process_cleanup.json']:
                check((phase / name).is_file(), 'missing_phase_artifact', phase.name + '/' + name)
            session = read(phase / 'session.json'); sessions.append(session)
            cleanup.append({'phase': phase.name, **read(phase / 'process_cleanup.json')})
            argv = read(phase / 'command.json')
            check(argv[:2] == ['/bin/sh', '-c'] and 'CLI_PID=$$' in argv[2] and str(base / 'sandbox.sb') in argv, 'actual_sandbox_launcher', phase.name)
            if result['condition'] == 'B':
                check('--append-system-prompt' in argv and argv[argv.index('--append-system-prompt') + 1] == tasks['treatment_activation'], 'minimal_treatment_activation_append')
            else: check('--append-system-prompt' not in argv, 'control_extra_system_append')
            events = []
            for line in (phase / 'transcript.jsonl').read_text().splitlines():
                try: event = json.loads(line)
                except ValueError:
                    observations.append({'run_id': rid, 'observation': 'non_json_transcript_line', 'phase': phase.name}); continue
                events.append(event)
                if event.get('subtype') == 'init':
                    init = {key: event.get(key) for key in ['cwd', 'model', 'permissionMode', 'mcp_servers', 'tools', 'skills', 'claude_code_version', 'session_id', 'messaging_socket_path']}
                    initializations.append(init)
                    check(init['cwd'] == str(workspace) and init['model'] == audit['requested_model'] and init['permissionMode'] == 'dontAsk' and init['mcp_servers'] == [] and set(init['tools'] or []) == set(audit['allowed_tools']), 'actual_cli_configuration')
                    check(init['session_id'] == session['session_id'], 'actual_session_identity')
                    check(init['messaging_socket_path'].startswith(str(base / 'tmp/cc-socks') + '/'), 'native_ipc_is_in_current_run')
                    if result['condition'] == 'A': check('deep-native' not in (init['skills'] or []), 'control_skill_present')
                for block in event.get('message', {}).get('content', []):
                    if not isinstance(block, dict): continue
                    if block.get('type') == 'tool_use': tool_inputs[block['id']] = block
                    if block.get('type') == 'tool_result':
                        tool_results[block['tool_use_id']] = block
                        text = block.get('content', ''); text = text if isinstance(text, str) else json.dumps(text)
                        if re.search(r'operation not permitted[^\n]*claude-[^\n]*-cwd|couldn.t create cache file[^\n]*xcrun_db', text, re.I):
                            warnings.append({'phase': phase.name, 'tool_use_id': block['tool_use_id']})
            assistant_ids = {event.get('message', {}).get('id') for event in events if event.get('type') == 'assistant'}
            check(len(assistant_ids) == session['observed_assistant_messages'], 'observed_message_accounting', phase.name)
            check((phase / 'final_response.txt').read_text() == session['final_response'], 'phase_response_matches_session')
            stderr = (phase / 'stderr.txt').read_text()
            if re.search(r'operation not permitted[^\n]*claude-[^\n]*-cwd|couldn.t create cache file[^\n]*xcrun_db', stderr, re.I):
                warnings.append({'phase': phase.name, 'source': 'stderr.txt'})
        check(bool(initializations), 'missing_cli_initialization')
        check(len(sessions) == result['sessions'] and abs(sum(s['duration_seconds'] for s in sessions) - result['duration_seconds']) < .001,
              'session_duration_accounting')
        check(sum(s['observed_assistant_messages'] for s in sessions) == result['total_observed_assistant_messages'] <= tasks['budget']['assistant_turns'], 'shared_assistant_budget')
        check(harness.source_fingerprint(workspace, None) == sessions[-1]['final_source_hash'], 'retained_final_source_fingerprint')
        check(not warnings, 'native_wrapper_warning_recurrence', warnings)
        native_warning_count += len(warnings)
        check((folder / 'final_response.txt').read_text() == sessions[-1]['final_response'], 'final_response_identity')
        calls = read(folder / 'api_calls.json'); configs = set(); incomplete = 0; provider_errors = []
        for call in calls:
            if '/messages' not in call['path'] or 'count_tokens' in call['path']: continue
            config = {key: call.get(key) for key in ['requested_model', 'max_tokens', 'thinking', 'output_config', 'temperature']}
            configs.add(json.dumps(config, sort_keys=True)); settings_variants.add(json.dumps(config, sort_keys=True))
            check(call.get('requested_model') == 'deepseek-flash' and (call.get('response_model') in [None, 'deepseek-flash']), 'actual_provider_model_identity')
            check(call.get('output_config', {}).get('effort') == audit['effort'], 'actual_provider_effort')
            if not call.get('complete'): incomplete += 1
            if call.get('http_status') not in [None, 200]: provider_errors.append({'http_status': call['http_status'], 'transport_error': call.get('transport_error')})
        check(provider_tokens(calls) == result['tokens'], 'provider_usage_aggregation')
        api_incomplete += incomplete
        if incomplete or provider_errors:
            observations.append({'run_id': rid, 'observation': 'provider_calls_not_all_complete', 'incomplete_calls': incomplete,
                                 'non_200_responses': provider_errors, 'token_aggregate_available': result['tokens'] is not None})
        if result['task_id'] == 'T10':
            check((folder / 'interruption.json').is_file(), 'actual_recovery_record')
            interruption = read(folder / 'interruption.json')
            check(interruption['actual_signal'] == 'SIGKILL' and sessions[0]['interrupted'] and len(sessions) == 2 and sessions[0]['session_id'] != sessions[1]['session_id'], 'actual_recovery_sessions')
        if result['task_id'] == 'T09':
            check((folder / 'phase1_independent_grade.json').is_file() and (folder / 'staleness_intervention.json').is_file(), 'staleness_intervention_artifacts')
            check(len(sessions) == 2 and sessions[0]['session_id'] == sessions[1]['session_id'], 'resumed_staleness_session')
        for tool_id, tool in tool_inputs.items():
            text = json.dumps(tool.get('input', {}))
            other_runs = [other_id for other_workspace, other_id in completed_workspaces.items()
                          if other_id != rid and str(Path(other_workspace).parent) in text]
            benchmark_paths = [str(bench / name) for name in ['reference.py', 'acceptance.py']]
            protected = [name for name in benchmark_paths if name in text]
            if other_runs or protected:
                returned = tool_results.get(tool_id, {})
                blocked = returned.get('is_error', False)
                external_attempts.append({'tool_use_id': tool_id, 'tool_name': tool.get('name'),
                                          'other_completed_runs_referenced': other_runs,
                                          'external_benchmark_files_referenced': protected,
                                          'tool_result_error': blocked})
                observations.append({'run_id': rid, 'observation': 'external_protected_path_referenced',
                                     **external_attempts[-1]})
                if not blocked:
                    issue('external_protected_path_requires_trace_review', rid, tool_id)
        records.append({'run_id': rid, 'condition': result['condition'], 'issues': local,
                        'artifact_files_verified': len(manifest), 'environment_matches': not any(x in local for x in ['exact_sanitized_environment', 'actual_cli_configuration', 'exact_sandbox_profile', 'resolved_binary_hash']),
                        'resolved_programs': resolved, 'workspace': str(workspace), 'sandbox_profile_sha256': sha(base / 'sandbox.sb'),
                        'installed_skill_files': installed, 'project_configuration_files': project_settings,
                        'actual_cli_initializations': initializations, 'process_cleanup': cleanup, 'native_wrapper_warnings': warnings,
                        'provider_configuration_variants': [json.loads(value) for value in sorted(configs)],
                        'incomplete_provider_calls': incomplete, 'non_200_provider_responses': provider_errors,
                        'observed_assistant_messages': result['total_observed_assistant_messages'], 'sessions': len(sessions),
                        'external_read_attempts': external_attempts})
    if len(settings_variants) != 1: issue('provider_configuration_varies_across_runs', detail=[json.loads(x) for x in sorted(settings_variants)])
    check_processes = subprocess.run(['/usr/sbin/lsof', '-a', '-d', 'cwd', '-Fpn'], capture_output=True, text=True, timeout=20).stdout
    leftovers = []; pid = None
    for line in check_processes.splitlines():
        if line.startswith('p') and line[1:].isdigit(): pid = int(line[1:])
        elif line.startswith('n'):
            cwd = Path(line[1:])
            for name, rid in bases.items():
                base = Path(name)
                if cwd == base or base in cwd.parents:
                    leftovers.append({'run_id': rid, 'pid': pid, 'cwd': str(cwd)}); issue('completed_workspace_process_remains', rid, pid)
    report = {'schema': 1, 'campaign': out.name, 'snapshot_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'review_status': 'PASS' if not issues else 'FAIL', 'planned_runs': len(schedule), 'completed_runs_reviewed': len(records),
              'completed_schedule_prefix_matches': completed_ids == expected_ids, 'campaign_complete': len(records) == len(schedule),
              'scope': 'Runtime/configuration and artifact integrity of completed runs; no active-run trace inspection, model/API calls, or task/Skill changes. A partial campaign remains insufficient for the complete 60-run A/B judgment.',
              'protocol_hashes': protocol, 'fixed_skill_commit': freeze['deep_native_commit'], 'skill_hashes': frozen_skill,
              'audit_sha256': sha(out / 'audit.json'), 'freeze_sha256': sha(out / 'freeze.json'),
              'artifact_files_verified': artifacts_checked, 'native_wrapper_warning_recurrences': native_warning_count,
              'provider_configuration_variants': [json.loads(value) for value in sorted(settings_variants)],
              'incomplete_provider_calls': api_incomplete, 'issues': issues, 'observations': observations,
              'completed_workspace_process_cwds': leftovers, 'runs': records,
              'limits': ['No hidden model-weight or backend prompt-cache attestation is possible from these local artifacts.',
                        'Process ownership covers observed descendants; the final process check is a current cwd snapshot.',
                        'Sandbox read guarantees apply to the recorded Documents/temp deployment and declared runtime exceptions.']}
    next_entry = schedule[args.expected_count] if args.expected_count < len(schedule) else None
    next_folder = out / 'runs' / next_entry['run_id'] if next_entry else None
    report['stage_stop'] = {'next_scheduled_entry': next_entry,
                            'next_run_artifact_directory_exists': next_folder.exists() if next_folder else None,
                            'partial_run_directories': [p.parent.name for p in (out / 'runs').glob('*/metadata.json')
                                                       if not (p.parent / 'result.json').exists()],
                            'operator_pause': read(out / 'user_pause.json') if (out / 'user_pause.json').exists() else None,
                            'controller_stop_record': read(out / 'campaign_stop.json') if (out / 'campaign_stop.json').exists() else None,
                            'interpretation': 'The completed current run was finalized. The next scheduled ID in the controller stop record identifies an environment-validation boundary, not an executed abnormal run, when its artifact directory is absent.'}
    prefix = args.output_prefix.resolve(); prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['# Preliminary v4 runtime audit', '',
             f'Runtime and artifact integrity: **{report["review_status"]}** for **{len(records)} / {len(schedule)}** planned runs.', '',
             'This is a stage-complete audit of retained runs, not a completed 60-run effectiveness experiment.', '',
             f'- Completed runs match the frozen schedule prefix: {report["completed_schedule_prefix_matches"]}.',
             f'- Current and archived protocol files checked: {len(protocol)}; fixed-commit Skill files checked: {len(frozen_skill)}.',
             f'- Per-run artifact files hash-verified: {artifacts_checked}.',
             '- Child environments, actual CLI initialization, provider model/effort/configuration, installed Skill bytes and hooks, and shared turn accounting were checked.',
             f'- Native cwd/Git wrapper warning recurrences: {native_warning_count}.',
             f'- Processes with cwd in completed workspaces at the final snapshot: {len(leftovers)}.', '',
             'Incomplete interrupted/retried provider calls are retained. Token totals stay unavailable whenever relevant responses are incomplete.', '',
             'The operator stopped after the current run finalized. A stop record naming the next scheduled entry does not mean that next run executed: its artifact directory is absent. This is an intentional stage boundary, not an abnormal completed run.', '',
             f'[Detailed machine-readable audit]({prefix.name}.json)', '', '## Findings', '']
    lines += ['No runtime/configuration or artifact-integrity issue was detected.'] if not issues else ['```json', json.dumps(issues, indent=2), '```']
    lines += ['', '## Observations', '', '```json', json.dumps(observations, indent=2), '```', '',
              '## Scope limits', ''] + ['- ' + value for value in report['limits']]
    prefix.with_suffix('.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'review_status': report['review_status'], 'completed_runs': len(records),
                      'issues': issues, 'observations': observations, 'artifact_files_verified': artifacts_checked,
                      'outputs': [str(prefix.with_suffix('.json')), str(prefix.with_suffix('.md'))]}, indent=2))


if __name__ == '__main__':
    main()
