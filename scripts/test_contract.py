import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from check_contract import inspect_plan

class ContractTests(unittest.TestCase):
    def plan(self):
        return json.loads((Path(__file__).resolve().parents[1]/'examples/contract.json').read_text(encoding='utf-8'))
    def test_valid_example_is_not_modified(self):
        d=self.plan();before=copy.deepcopy(d)
        self.assertTrue(inspect_plan(d)['contract_valid'])
        self.assertEqual(d,before)
    def test_foreign_role_and_malformed_input_are_rejected(self):
        d=self.plan();d['skill']='foreign-skill'
        self.assertFalse(inspect_plan(d)['contract_valid'])
        for bad in [None,[],{},'text',{'skill':self.plan()['skill']}]:
            self.assertFalse(inspect_plan(bad)['contract_valid'])

    def test_loud_audio_is_not_verified_gameplay_and_unverified_edit_is_rejected(self):
        d=self.plan();d['events'][0]['evidence']=[{'kind':'audio','description':'player screams'}]
        self.assertFalse(inspect_plan(d)['contract_valid'])
        d['events'][0]['type']='reaction'
        self.assertTrue(inspect_plan(d)['contract_valid'])
        d=self.plan();d['events'][0]['verified']=False
        self.assertFalse(inspect_plan(d)['contract_valid'])
    def test_cutting_the_result_and_unlabeled_replay_are_rejected(self):
        d=self.plan();d['events'][0]['source_out']=45
        self.assertFalse(inspect_plan(d)['contract_valid'])
        d=self.plan();d['output_duration']=40;replay=copy.deepcopy(d['clips'][0]);replay.update(start=20,end=40);d['clips'].append(replay)
        self.assertFalse(inspect_plan(d)['contract_valid'])
        d['clips'][1]['replay']=True
        self.assertTrue(inspect_plan(d)['contract_valid'])


if __name__=='__main__': unittest.main()
