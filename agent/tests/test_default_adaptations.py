import unittest
from pathlib import Path
from copy import deepcopy
from i2r_agent.common import read,Failure
from i2r_agent.default_adaptations import proposals,apply,HASHES,operational_identity

class DefaultAdaptations(unittest.TestCase):
    def model(self):
        es=read(Path(__file__).parent/'fixtures/default-primitives.json')
        es['constant:Business.run']={'id':'constant:Business.run','name':'Business.run','kind':'constant','dependencies':list(es)}
        return {'entries':['constant:Business.run'],'entities':es}

    def test_exact_facts_only_numeric_mode_and_business_protection(self):
        m=self.model();rows=proposals(m,{'mode':'checked'})
        self.assertEqual({r['source'] for r in rows},set(HASHES))
        self.assertIn('I2R_NUMERIC_OVERFLOW',str(rows));self.assertIn('lazy',str(rows))
        altered=deepcopy(m);altered['entities']['constant:HOL.If']['execution_equations']=[{'rhs':'eager branches'}]
        self.assertNotIn('constant:HOL.If',{r['source'] for r in proposals(altered,{'mode':'checked'})})
        altered=deepcopy(m);altered['entities']['type:Nat.nat']['constructors'][0]['fields']=[{'kind':'type','name':'Nat.nat','args':[]}]
        self.assertNotIn('type:Nat.nat',{r['source'] for r in proposals(altered,{'mode':'checked'})})
        self.assertEqual(proposals(m,{'mode':'unknown'}),[])
        self.assertIn('dashu_int::UBig',str(proposals(m,{'mode':'arbitrary'})))
        # An entry is always mandatory, even if it is otherwise a known primitive.
        m['entries']=['constant:Nat.Suc'];self.assertNotIn('constant:Nat.Suc',{r['source'] for r in proposals(m,{'mode':'checked'})})

    def test_explicit_acceptance_override_and_revocation(self):
        rows=proposals(self.model(),{'mode':'checked'})
        self.assertEqual(apply({},rows)[0],[])
        accepted,record=apply({'use_default_adaptations':True},rows)
        self.assertEqual(len(accepted),7);self.assertTrue(record['explicitly_accepted'])
        override={'source':'type:Nat.nat','kind':'native','basis':'explicit source reason','conditions':['alternative checked representation']}
        result,record=apply({'use_default_adaptations':True,'boundaries':[override],'revoke_default_adaptations':['constant:Nat.Suc']},rows)
        self.assertNotIn('constant:Nat.Suc',{r['source'] for r in result})
        self.assertEqual(next(r for r in result if r['source']=='type:Nat.nat'),override)
        self.assertEqual(record['overridden'],['type:Nat.nat'])
        for bad in [{'use_default_adaptations':'true'},{'revoke_default_adaptations':['constant:Business.run']}]:
            with self.assertRaises(Failure):apply(bad,rows)
