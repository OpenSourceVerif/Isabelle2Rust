import unittest
from i2r_agent import afp20_suites as a, suites


class AFP20SuitesTests(unittest.TestCase):
    def test_all_workloads_have_explicit_valid_checked_domains(self):
        self.assertEqual(len(a.KINDS),20)
        for case in a.KINDS:
            with self.subTest(case=case):
                rows=suites.fixed(case)+suites.generate(case,100,51)+[suites.performance_input(case)]+a.additional_workloads(case)
                self.assertTrue(all(suites.domain(case,x) and suites.in_numeric_domain(x,128) for x in rows))
                self.assertEqual(suites.generate(case,5,1),suites.generate(case,5,1))
                self.assertNotEqual(suites.generate(case,5,1),suites.generate(case,5,2))
        self.assertFalse(suites.domain('afp-stern-brocot-path',[0,1]))
        self.assertFalse(suites.domain('afp-catalan',[11]))
        self.assertFalse(suites.domain('afp-list-power',[17,1]))

    def test_independent_observations_and_mutations(self):
        examples={
            'afp-binary-exponentiation':([3,4],[81]),
            'afp-inversions':([3,1,2],[2,1,2,3]),
            'afp-maximum-segment-sum':([6,9,8,2],[5]),
            'afp-hood-melville-queue':([2,3,0,4],[2,3]),
            'afp-trie-map':([5,4,5,6],[1,5,0]),
            'afp-binary-search-tree':([2,3,2,1,2],[1,3,1,2,3,1,3]),
            'afp-avl-tree':([2,3,2,1,2],[1,3,1,2,3,1,3]),
            'afp-huffman':([1,2,3],[9,6,2]),
            'afp-list-power':([2,1,0],[1,0,1,0]),
            'afp-catalan':([0,1,2,3,4],[1,1,2,5,14]),
            'afp-stern-brocot-path':([2,3],[0,1]),
            'afp-digits-eval':([10,1,2,3],[321,123]),
            'afp-move-to-front':([2,1,2,3,2],[2,1,3,2]),
        }
        examples.update({case:([3,1,1,2],[1,1,2,3]) for case,kind in a.KINDS.items() if kind=='sort'})
        self.assertEqual(set(examples),set(a.KINDS))
        for case,(x,y) in examples.items():
            with self.subTest(case=case):
                self.assertIsNone(suites.property_error(case,x,y))
                self.assertIsNotNone(suites.property_error(case,x,[999]+y[1:]))

    def test_empty_absent_duplicate_and_zero_base_observations(self):
        for case in a.KINDS:
            if case=='afp-stern-brocot-path':continue
            expected=[0] if a.KINDS[case] in {'inversions','mss'} else []
            self.assertIsNone(suites.property_error(case,[],expected),case)
        for case in ['afp-trie-map','afp-move-to-front']:
            self.assertIsNone(suites.property_error(case,[9,1,2],[0,0] if case=='afp-trie-map' else [1,2]))
        self.assertIsNone(suites.property_error('afp-digits-eval',[0,4,5],[4,5]))
        self.assertIsNone(suites.property_error('afp-stern-brocot-path',[4,6],[0,1]))


if __name__=='__main__':unittest.main()
