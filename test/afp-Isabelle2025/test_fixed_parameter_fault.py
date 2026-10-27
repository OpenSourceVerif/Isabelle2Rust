"""Counterexamples for the fixed-state PLTL source certificate; no native runs."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path.cwd()/'test/afp-Isabelle2025'))
import frontend_fault as generic
import frontend_fixed_parameter as fixed

A='<v1 a0="a"><item>HOL.type</item></v1>'
BOOL='<v0 a0="HOL.bool" />'
def function(a,b):return '<v0 a0="fun"><item>'+a+'</item><item>'+b+'</item></v0>'
FORMULA='<v0 a0="LTL.pltl"><item>'+A+'</item></v0>'
PREDICATE=function(A,BOOL)
HEAD=function(FORMULA,function(PREDICATE,function(A,BOOL)))
TYPES={'s':fixed.type_xml(A)}
def const(name):return ('v0',name,0,None)
def app(fn,arg):return ('v5',fn,arg)
def trueprop(term):return app(const('HOL.Trueprop'),term)
def expression(name,index,args=None,head_type=HEAD):
    term=('v2',name,index,head_type)
    for arg in args if args is not None else [('v3',1),('v3',0),('v1','s',0,None)]:term=app(term,arg)
    return term
def quantify(term):
    for name,typ in [('p',PREDICATE),('x',FORMULA)]:
        term=app(const('Pure.all'),('v4',name,'<item>'+typ+'</item>',term))
    return term
def goal(name,index,args=None,head_type=HEAD):return quantify(trueprop(expression(name,index,args,head_type)))
def conjunction(p,q):return app(app(const('HOL.conj'),p),q)
def witness(value):return quantify(trueprop(app(app(const('HOL.eq'),value),value)))
def state(goals):
    term=const('Pure.prop')
    for item in reversed(goals):term=app(app(const('Pure.imp'),item),term)
    return term

def example(left_index=14):
    # The earlier equality shares the unchosen predicate with the final Boolean
    # goal. Native imitation must substitute this earlier occurrence as well.
    before=state([witness(expression('Q',10)),goal('Q',10)])
    replacement=conjunction(expression('P',left_index),expression('Q',13))
    after=state([witness(replacement),goal('P',left_index),goal('Q',13)])
    return before,after

class FixedParameterCounterexamples(unittest.TestCase):
    def test_exact_fixed_state_shape_is_separate_from_bound_only_certificate(self):
        # A fixed Free argument is part of the actual native predicate. The old
        # family must still reject it while this separately typed family accepts.
        term=goal('Q',10)
        self.assertEqual(fixed.fixed_goal(term,TYPES)['fixed_name'],'s')
        with self.assertRaisesRegex(ValueError,'distinct quantified parameters'):generic.flexible(term)

    def test_entire_shared_witness_substitution_is_verified(self):
        # Valid children alone are insufficient: the unchosen predicate also
        # occurs in earlier goals, whose full substitution must be checked.
        before,after=example()
        result=fixed.validate_step(before,after,TYPES,TYPES,2,11,14)
        self.assertTrue(result['full_state_substitution_checked'])
        self.assertEqual(result['residual_unification_constraints'],0)

    def test_unchanged_earlier_witness_cannot_certify_native_substitution(self):
        # This fabricated result has fresh final children but leaves the shared
        # earlier predicate untouched; it cannot be a native resolution result.
        before,_=example()
        bad=state([witness(expression('Q',10)),goal('P',14),goal('Q',13)])
        with self.assertRaisesRegex(ValueError,'Earlier witness goals'):
            fixed.validate_step(before,bad,TYPES,TYPES,2,11,14)

    def test_reused_child_variable_is_not_globally_fresh(self):
        # Reusing an existing head invalidates the induction even when goal and
        # parameter counts agree with an expanding conjunction step.
        before,after=example(left_index=10)
        with self.assertRaisesRegex(ValueError,'globally fresh'):
            fixed.validate_step(before,after,TYPES,TYPES,2,11,13)

    def test_duplicate_bound_argument_is_rejected(self):
        # The source proof relies on the exact x,p,s argument vector. Repeating
        # p changes unification and cannot reuse this narrow invariant.
        args=[('v3',0),('v3',0),('v1','s',0,None)]
        with self.assertRaisesRegex(ValueError,'distinct bound parameters'):fixed.fixed_goal(goal('Q',10,args),TYPES)

    def test_compound_fixed_argument_is_rejected(self):
        # A compound term can introduce different imitation/projection choices.
        # This certificate only covers one genuinely fixed Free state argument.
        args=[('v3',1),('v3',0),app(const('other'),('v1','s',0,None))]
        with self.assertRaisesRegex(ValueError,'fixed Free'):fixed.fixed_goal(goal('Q',10,args),TYPES)

    def test_boolean_state_type_cannot_reuse_rigid_polymorphic_projection_argument(self):
        # A Boolean argument admits projections that the rigid type a excludes.
        # It must not be accepted merely because application arity is three.
        with self.assertRaisesRegex(ValueError,'rigid polymorphic'):
            fixed.fixed_goal(goal('Q',10),{'s':fixed.BOOL})

    def test_wrong_schematic_function_result_is_rejected(self):
        # conjI requires a Boolean result; a similarly shaped nat-valued head
        # cannot support the source argument about Boolean imitation.
        head=function(FORMULA,function(PREDICATE,function(A,'<v0 a0="Nat.nat" />')))
        with self.assertRaisesRegex(ValueError,'schematic function type'):
            fixed.fixed_goal(goal('Q',10,head_type=head),TYPES)

    def test_extra_full_state_constraint_is_rejected(self):
        # Thm.full_prop_of prepends residual flex-flex constraints. A certificate
        # must not confuse those extra premises with the native tactic's goals.
        before,after=example()
        extra=app(app(const('Pure.eq'),const('A')),const('B'))
        before=app(app(const('Pure.imp'),extra),before)
        with self.assertRaisesRegex(ValueError,'Residual constraints'):
            fixed.validate_step(before,after,TYPES,TYPES,2,11,14)

    def test_beta_substitution_does_not_capture_outer_bound_argument(self):
        # The full-state checker substitutes under existing lambdas. The outer
        # Bound must be lifted past the inner binder instead of becoming Bound 0.
        body=('v4','inner','<item>'+A+'</item>',('v3',1))
        result=fixed.beta(body,('v3',0))
        self.assertEqual(result[3],('v3',1))

if __name__=='__main__':unittest.main()