import unittest
from i2r_agent.experiment_metrics import aggregate
class MetricTests(unittest.TestCase):
    def test_failures_keep_cost_and_denominator(self):
        rows=[{'frozen_identity':'a','status':s,'seconds':n,'model_calls':2,'usage':{'total_tokens':100},'first_compile':'passed','first_behavior':'passed' if s=='passed' else 'mismatch'} for s,n in [('passed',10),('task_timeout',20)]]
        a=aggregate(rows)
        self.assertEqual((a['completed'],a['passed'],a['failed_task_tokens'],a['tokens_all_tasks']),(2,1,100,200))
        self.assertEqual(a['first_behavior_attempted'],2)
    def test_mixed_freezes_are_rejected(self):
        with self.assertRaises(ValueError):aggregate([{'frozen_identity':'a'},{'frozen_identity':'b'}])
    def test_source_outcome_comes_from_executed_support_record(self):
        import tempfile
        from i2r_agent.experiment_metrics import summarize
        with tempfile.TemporaryDirectory() as d:
            row=summarize(d,{'status':'passed','attempts':[{'action_phase':'support','support':{'status':'passed'}}]},'a','example',1)
            self.assertEqual(row['first_source_test'],'passed')
