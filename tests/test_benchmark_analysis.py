"""Offline evidence/analysis checks; synthetic records stay in temporary test directories."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

BENCH=Path(__file__).resolve().parents[1]/'evals/benchmark-v1'
sys.path.insert(0,str(BENCH))
from analysis import aggregate, generate, mechanism_summary, paired_summary
from audit_evidence import audit


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rehash(root):
    put(root/'artifact_hashes.json',{str(p.relative_to(root)):digest(p)
        for p in root.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})


def campaign(out,completed=60):
    """Create minimal synthetic evidence for validation, never a live campaign."""
    budget={'assistant_turns':24,'wall_seconds':480}
    tasks=[{'id':f'T{i:02}','category':'category_'+str(i%2),
            'prompt':f'Frozen test prompt {i}\n'} for i in range(1,11)]
    schedule=[{'run_id':f"{t['id']}-r{repeat}-{arm}",'task_id':t['id'],
               'repeat':repeat,'condition':arm}
              for t in tasks for repeat in [1,2,3] for arm in ['A','B']]
    put(out/'tasks.json',{'tasks':tasks,'budget':budget})
    put(out/'schedule.json',schedule)
    put(out/'baselines.json',{t['id']:{'fixture_commit':'fixed-fixture'} for t in tasks})
    put(out/'audit.json',{'claude':'test CLI','requested_model':'deepseek-flash[1m]',
                         'upstream_endpoint':'https://example.invalid/anthropic'})
    treatment=out/'frozen-treatment/skills/deep-native/SKILL.md'
    treatment.parent.mkdir(parents=True)
    treatment.write_text('Synthetic treatment bytes for integrity testing only.\n')
    put(out/'freeze.json',{'protocol_sha256':{},'deep_native_commit':'fixed-treatment',
        'schedule_sha256':digest(out/'schedule.json'),'tasks_sha256':digest(out/'tasks.json'),
        'baselines_sha256':digest(out/'baselines.json'),'audit_sha256':digest(out/'audit.json'),
        'treatment_sha256':{'skills/deep-native/SKILL.md':digest(treatment)}})
    for entry in schedule[:completed]:
        root=out/'runs'/entry['run_id']
        row={**entry,'category':tasks[int(entry['task_id'][1:])-1]['category'],
             'task_success':'PASS','declared_done':True,'actually_valid':True,
             'false_completion':False,'duration_seconds':1,
             'including_setup_and_grade_seconds':2,'tool_calls':0,'files_changed':[],
             'tokens':None,'response_models':['deepseek-flash'],
             'treatment_activation_observed':True,'control_clean':entry['condition']=='A',
             'forbidden_changes':[],'protected_test_changes':[],'sessions':1,
             'recovery_interrupted':False,'fixture_commit':'fixed-fixture',
             'total_observed_assistant_messages':1,'stop_reasons':[],
             'behavior':{},'phase1_pass':None}
        root.mkdir(parents=True)
        (root/'patch.diff').write_text('')
        row['patch_sha256']=digest(root/'patch.diff')
        put(root/'result.json',row)
        put(root/'tests_before.json',{'pass':False})
        put(root/'tests_after.json',{'pass':True})
        put(root/'metadata.json',{'budget':budget,'workspace':'/nonexistent-dn-test-workspace'})
        put(root/'behavior.json',{})
        put(root/'api_calls.json',[{'path':'/v1/messages','complete':False,
                                    'response_model':'deepseek-flash','usage':{}}])
        (root/'final_response.txt').write_text('STATUS: DONE\n')
        phase=root/'phase1'
        phase.mkdir()
        (phase/'prompt.txt').write_text(tasks[int(entry['task_id'][1:])-1]['prompt'])
        (phase/'transcript.jsonl').write_text('')
        put(phase/'session.json',{'session_id':entry['run_id'],'duration_seconds':1,
                                 'observed_assistant_messages':1,'interrupted':False})
        put(phase/'command.json',['synthetic-unit-test'])
        rehash(root)
    return schedule


class BenchmarkAnalysisTests(unittest.TestCase):
    def test_integrity_pass_is_separate_from_partial_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);campaign(out,2)
            result=audit(out)
            self.assertEqual(result['integrity_status'],'PASS')
            self.assertFalse(result['campaign_complete'])
            self.assertEqual(len(result['missing_run_ids']),58)
            summary=generate(out)
            self.assertFalse(summary['completed_plan'])
            self.assertEqual(summary['judgment'],'INCONCLUSIVE')

    def test_sixty_result_files_do_not_hide_duplicate_or_missing_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);schedule=campaign(out)
            root=out/'runs'/schedule[-1]['run_id']
            row=json.loads((root/'result.json').read_text())
            row.update(schedule[0]);put(root/'result.json',row);rehash(root)
            result=audit(out)
            self.assertFalse(result['campaign_complete'])
            self.assertEqual(result['duplicate_run_ids'],[schedule[0]['run_id']])
            summary=generate(out)
            self.assertEqual(summary['actual_runs'],60)
            self.assertFalse(summary['completed_plan'])
            self.assertEqual(summary['judgment'],'INCONCLUSIVE')

    def test_corrupt_evidence_blocks_complete_campaign_judgment(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);schedule=campaign(out)
            (out/'runs'/schedule[0]['run_id']/'patch.diff').write_text('changed after hashing')
            result=generate(out)
            self.assertTrue(result['completed_plan'])
            self.assertEqual(result['evidence_integrity_status'],'FAIL')
            self.assertFalse(result['quality_comparison_valid'])
            self.assertEqual(result['judgment'],'INCONCLUSIVE')

    def test_scoring_and_stop_sidecars_survive_regeneration_without_relabeling(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);schedule=campaign(out)
            original=(out/'runs'/schedule[0]['run_id']/'result.json').read_bytes()
            put(out/'grading_contract_issue.json',{'status':'INVALID_FOR_QUALITY_COMPARISON',
                'issue':'Legitimate type declaration omitted by frozen scope contract.'})
            put(out/'campaign_stop.json',{'reason':'Retained audit stop.'})
            summary=generate(out)
            self.assertEqual(summary['judgment'],'INCONCLUSIVE')
            self.assertFalse(summary['quality_comparison_valid'])
            self.assertEqual(summary['A']['passes'],30)
            self.assertEqual((out/'runs'/schedule[0]['run_id']/'result.json').read_bytes(),original)
            report=(out/'REPORT.md').read_text()
            self.assertIn('Scoring contract defect',report)
            self.assertIn('Retained audit stop',report)
            self.assertIn('Success by task type',report)
            self.assertIn('Core questions',report)

    def test_frozen_treatment_and_campaign_inputs_are_hash_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);campaign(out,1)
            (out/'frozen-treatment/skills/deep-native/SKILL.md').write_text('mutated')
            put(out/'baselines.json',{})
            result=audit(out)
            problems={i['issue'] for i in result['issues']}
            self.assertIn('frozen_treatment_hash_mismatch',problems)
            self.assertIn('campaign_hash_mismatch',problems)

    def test_archived_protocol_is_checked_instead_of_evolved_current_code(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);campaign(out,1)
            archived=out/'frozen-harness/analysis.py'
            archived.parent.mkdir()
            archived.write_text('original frozen analysis bytes\n')
            frozen=json.loads((out/'freeze.json').read_text())
            frozen['protocol_sha256']={'analysis.py':digest(archived)}
            put(out/'freeze.json',frozen)
            self.assertEqual(audit(out)['integrity_status'],'PASS')
            archived.write_text('tampered archived source')
            self.assertIn('protocol_hash_mismatch',{i['issue'] for i in audit(out)['issues']})

    def test_valid_complete_ties_follow_frozen_no_observed_improvement_rule(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);campaign(out)
            summary=generate(out)
            self.assertTrue(summary['quality_comparison_valid'])
            self.assertEqual(summary['judgment'],'FAIL')
            self.assertEqual(summary['paired']['ties'],30)
            self.assertEqual(summary['paired']['B_wins'],0)
            self.assertEqual(summary['paired']['B_losses'],0)

    def test_mechanism_observations_exclude_missing_or_nonqualifying_stages(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)
            common={'condition':'A','task_id':'T09','task_success':'PASS'}
            rows=[{**common,'run_id':'legacy','phase1_pass':True},
                  {**common,'run_id':'failed-first','phase1_pass':False,
                   'phase1_successful_verification':True,'actual_later_source_change':True},
                  {**common,'run_id':'valid','phase1_pass':True,
                   'phase1_successful_verification':True,'actual_later_source_change':True,
                   'stale_completion_claim':True}]
            value=mechanism_summary(out,rows,{'budget':{'assistant_turns':24}})['A']['staleness']
            self.assertEqual(value['valid_observations'],1)
            self.assertEqual(value['observation_fields_unavailable'],1)
            self.assertEqual(value['stale_completion_claims_valid_observations'],1)

    def test_recovery_requires_actual_distinct_session_and_shared_turn_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);budget={'assistant_turns':24,'wall_seconds':480}
            rows=[]
            for name,second_id,turns in [('valid','second',20),('same-session','first',20),('over-budget','second',25)]:
                root=out/'runs'/name
                put(root/'metadata.json',{'budget':budget})
                put(root/'interruption.json',{'actual_signal':'SIGKILL','state_present':True})
                put(root/'phase1/session.json',{'session_id':'first','interrupted':True,'observed_assistant_messages':10})
                put(root/'phase2/session.json',{'session_id':second_id,'observed_assistant_messages':turns-10})
                rows.append({'run_id':name,'task_id':'T10','condition':'B','task_success':'PASS',
                             'recovery_interrupted':True,'total_observed_assistant_messages':turns})
            value=mechanism_summary(out,rows,{'budget':budget})['B']['recovery']
            self.assertEqual(value['runs'],3)
            self.assertEqual(value['valid_observations'],1)
            self.assertEqual(value['valid_observation_passes'],1)
            self.assertEqual(value['state_at_interrupt_valid_observations'],1)

    def test_token_categories_keep_availability_and_cached_processing_explicit(self):
        common={'task_success':'PASS','declared_done':True,'actually_valid':True,
                'duration_seconds':1,'tool_calls':0,'files_changed':[]}
        tokens={'input_tokens':20,'output_tokens':3,'cache_read_input_tokens':10,
                'cache_creation_input_tokens':0,'total_tokens':33}
        value=aggregate([{**common,'tokens':tokens},{**common,'tokens':None}])
        self.assertEqual(value['tokens_available_runs'],1)
        self.assertEqual(value['median_total_tokens'],33)
        self.assertEqual(value['token_categories']['cache_read_input_tokens']['total_available'],10)
        self.assertIsNone(value['api_cost_usd'])


if __name__=='__main__':
    unittest.main()

