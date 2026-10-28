"""Verify the fixed-state predicate expansion seen in PLTL set preprocessing.

This family is deliberately narrower than arbitrary higher-order unification:
F has type pltl(a) -> (a -> bool) -> a -> bool, where a is rigid, and the last
argument is one fixed Free. Native imitation of conj creates two fresh heads
with the same arguments. Full-state beta substitution is checked, including
uses of the still-undischarged predicate witness in earlier goals.
"""
from pathlib import Path
import json,re,xml.etree.ElementTree as ET
import afp_common as c
import frontend_fault as f

FAMILY='fixed_parameter_boolean_conjunction'

def typ(node):
    """Decode only rigid native types; schematic type variables are rejected."""
    if node.tag=='item':
        f.need(len(node)==1,'Malformed type wrapper')
        return typ(node[0])
    if node.tag=='v0':return ('Type',node.attrib['a0'],tuple(typ(child) for child in node))
    if node.tag=='v1':return ('TFree',node.attrib['a0'],tuple((node[0].text or '').split()) if len(node) else ())
    raise ValueError('Fixed-parameter invariant requires rigid types')

def type_xml(text):return typ(ET.fromstring(text))
def arrow(a,b):return ('Type','fun',(a,b))
BOOL=('Type','HOL.bool',())

def free_types(path):
    """Retain Free types omitted by the older generic term decoder."""
    raw=re.sub(r'<(/?)([0-9]+|:)(?=[\s/>])',lambda m:'<'+m[1]+('item' if m[2]==':' else 'v'+m[2]),path.read_text())
    raw=re.sub(r' (\d+)=',r' a\1=',raw)
    root=ET.fromstring(raw);result={}
    for node in root.iter('v1'):
        name=node.attrib['a0']
        # A term Free has its type as a v0/v1 child; a TFree's child is its sort.
        if len(node)==1 and node[0].tag in {'v0','v1'}:
            value=typ(node[0])
            f.need(name not in result or result[name]==value,'Conflicting fixed Free types')
            result[name]=value
    return result

def fixed_goal(term,types):
    parameters=[];assumptions=[]
    while True:
        universal=f.const(term,'Pure.all',1);implication=f.const(term,'Pure.imp',2)
        if universal is not None:
            f.need(universal[0][0]=='v4','Expected quantified parameter')
            parameters.append(type_xml(universal[0][2]));term=universal[0][3]
        elif implication is not None:
            assumptions.append(implication[0]);term=implication[1]
        else:break
    proposition=f.const(term,'HOL.Trueprop',1)
    f.need(proposition is not None,'No Boolean goal')
    head,args=f.app(proposition[0])
    f.need(head[0]=='v2','Goal is rigid')
    f.need(len(parameters)==2 and len(args)==3 and args[:2]==[('v3',1),('v3',0)] and args[2][0]=='v1',
           'Expected all distinct bound parameters followed by one fixed Free')
    name=args[2][1];state=types.get(name)
    f.need(state is not None and state[0]=='TFree' and state[2]==('HOL.type',),'Fixed state type is not rigid polymorphic a')
    expected=[('Type','LTL.pltl',(state,)),arrow(state,BOOL)]
    f.need(parameters==expected,'Wrong quantified formula/predicate types')
    expected_head=arrow(expected[0],arrow(expected[1],arrow(state,BOOL)))
    f.need(type_xml(head[3])==expected_head,'Wrong fixed-parameter schematic function type')
    # Rigid assumptions are carried through resolution. No earlier goal is
    # discharged before REPEAT_ALL_NEW recurses on the fresh rightmost goal.
    f.need(not any(variables(item) for item in assumptions),'Schematic variable in active goal assumptions')
    return {'head':head,'arguments':args,'parameters':parameters,'assumptions':assumptions,'fixed_name':name,'fixed_type':state}

def variables(term):
    if not isinstance(term,tuple):return []
    if term[0]=='v2':return [(term[1],term[2])]
    return [value for child in term[1:] if isinstance(child,tuple) for value in variables(child)]

def shift(term,amount,cutoff=0):
    if term[0]=='v3':return ('v3',term[1]+amount) if term[1]>=cutoff else term
    if term[0]=='v4':return (*term[:3],shift(term[3],amount,cutoff+1))
    if term[0]=='v5':return ('v5',shift(term[1],amount,cutoff),shift(term[2],amount,cutoff))
    return term

def beta(body,argument,depth=0):
    if body[0]=='v3':
        if body[1]==depth:return shift(argument,depth)
        return ('v3',body[1]-1) if body[1]>depth else body
    if body[0]=='v4':return (*body[:3],beta(body[3],argument,depth+1))
    if body[0]=='v5':return ('v5',beta(body[1],argument,depth),beta(body[2],argument,depth))
    return body

def normalize(term):
    if term[0]=='v4':return (*term[:3],normalize(term[3]))
    if term[0]=='v5':
        function,argument=normalize(term[1]),normalize(term[2])
        return normalize(beta(function[3],argument)) if function[0]=='v4' else ('v5',function,argument)
    return term

def substitute(term,old,replacement):
    if term[0]=='v2' and term[1:3]==old[1:3]:
        f.need(term[3]==old[3],'Changed type of original schematic head')
        return replacement
    if term[0]=='v4':return (*term[:3],substitute(term[3],old,replacement))
    if term[0]=='v5':return ('v5',substitute(term[1],old,replacement),substitute(term[2],old,replacement))
    return term

def alpha(term):
    if term[0]=='v4':return ('v4','_',type_xml(term[2]),alpha(term[3]))
    if term[0]=='v2':return (*term[:3],type_xml(term[3]))
    if term[0]=='v5':return ('v5',alpha(term[1]),alpha(term[2]))
    return term

def split_state(term):
    goals=[]
    while (args:=f.const(term,'Pure.imp',2)) is not None:
        goals.append(args[0]);term=args[1]
    return goals,term

def validate_step(before,after,types_before,types_after,index,max_before,max_after):
    """Check the entire native state under its exact conjunction substitution."""
    prior,conclusion=split_state(before);later,result=split_state(after)
    f.need(index==len(prior) and len(later)==index+1,'Residual constraints or different native goal count')
    old,left,right=[fixed_goal(term,types) for term,types in [
        (prior[-1],types_before),(later[-2],types_after),(later[-1],types_after)]]
    for key in ['arguments','parameters','assumptions','fixed_name','fixed_type']:
        f.need(old[key]==left[key]==right[key],'Changed fixed-parameter goal environment')
    lh,rh=left['head'],right['head']
    f.need(lh[1]=='P' and rh[1]=='Q' and max_before<min(lh[2],rh[2]) and max(lh[2],rh[2])==max_after,
           'Children are not globally fresh Boolean predicates')
    f.need(max((n for _,n in variables(before)),default=-1)<=max_before,'Incorrect native maxidx before')
    # Build lambda x p s. P x p s & Q x p s. Its body is closed, so replacing
    # the schematic head under arbitrary existing binders needs no lifting.
    def application(head):
        for n in [2,1,0]:head=('v5',head,('v3',n))
        return head
    body=('v5',('v5',('v0','HOL.conj',0,None),application(lh)),application(rh))
    head_type=ET.fromstring(old['head'][3]);domains=[]
    while head_type.tag=='v0' and head_type.attrib.get('a0')=='fun':
        domains.append(ET.tostring(head_type[0],encoding='unicode'));head_type=head_type[1][0]
    for domain in reversed(domains):body=('v4','_',domain,body)
    def changed(term):return alpha(normalize(substitute(term,old['head'],body)))
    f.need([changed(term) for term in prior[:-1]]==[alpha(term) for term in later[:-2]],
           'Earlier witness goals do not match the exact native substitution')
    f.need(changed(conclusion)==alpha(result),'Changed theorem conclusion')
    for child,head in [(later[-2],lh),(later[-1],rh)]:
        expected=normalize(substitute(prior[-1],old['head'],head))
        f.need(alpha(expected)==alpha(child),'New child is not the same quantified Boolean goal')
    return {'parameters':2,'fixed_parameter':old['fixed_name'],'fixed_type':json.loads(json.dumps(old['fixed_type'])),
            'full_state_substitution_checked':True,'residual_unification_constraints':0}


def conjunction(work,project,installed,serializer):
    """Recheck native source, every retained state, and the recursive branch."""
    metadata=f.input_files(work);command,log=f.natural_failure(work,serializer)
    f.need(command['min_available_mb']>3500,'Observation lost isolated resource margin')
    f.need((work/'scope.txt').read_text().splitlines()==['PLTL.characteristic_formula'],'Wrong fixed-parameter singleton')
    reference=c.isabelle_source_root(project)
    def source(name):return f.installed_source(name,installed,reference)
    text=source('HOL/Tools/set_comprehension_pointfree.ML')
    observed=f.undo((work/'set-comprehension-observe.ML').read_text(),metadata['proof_observer_adjustments'])
    observed=f.undo(observed,metadata['pointfree_additional_observation_edits'])
    ancestor=project/metadata['pointfree_source_observer']
    observed=f.undo(observed,c.read_json(ancestor.parent/'sources.json')['observation_edits'])
    f.need(observed==text,'Observer does not reverse exactly to installed algorithm')
    converter=source('Pure/Isar/code.ML')
    start=converter.index('fun eqn_conv conv ct =');end=converter.index('\nfun apply_functrans',start)
    f.need((work/'native-conversion.ML').read_text()==converter[start:end] and
           f.sha(installed/'Pure/Isar/code.ML')==metadata['native_source_sha256'],'Changed native equation conversion')
    requirements={
      'HOL/Tools/set_comprehension_pointfree.ML':["THEN' (TRY o REPEAT_ALL_NEW (resolve_tac ctxt @{thms conjI}))"],
      'Pure/tactical.ML':['tac THEN_ALL_NEW (TRY o (fn i => REPEAT_ALL_NEW tac i));'],
      'Pure/General/seq.ML':['else op THEN (f j, INTERVAL f i (j - 1)) x;'],
      'Pure/pattern.ML':['| ints_of _              = raise Pattern;'],
      'Pure/unify.ML':['| Pattern.Pattern => hounifiers [] params;',
        '| _ => raise CANTUNIFY)',
        'fun matchfun ((bvar,T,targ)::projs) =',
        '| matchfun [] = (*imitation last of all*)',
        'Const _ => Seq.map joinargs (copyargs uargs)',
        "val (env', newhd) = Envir.genvar (#1 w) (env, Ts ---> base);"],
      'Pure/thm.ML':['val lift = lift_rule (cprem_of state i);',
        'case Seq.pull (Unify.unifiers (context, env, dpairs)) of',
        'Logic.list_implies (map Logic.mk_equals tpairs, prop);'],
      'HOL/HOL.thy':['lemma conjI: "\\<lbrakk>P; Q\\<rbrakk> \\<Longrightarrow> P \\<and> Q"']}
    for name,fragments in requirements.items():
        code=source(name)
        f.need(all(fragment in code for fragment in fragments),'Changed native recursion/unification branch: '+name)
    subset=text[text.index('    val subset_tac2 ='):text.index('    val subset_tac2 =')+850]
    f.need(subset.index('@{thms exI}')<subset.index('REPEAT_ALL_NEW')<subset.index('hyp_subst_tac'),'Changed witness ordering')
    certificate=c.read_json(work/'fixed-parameter-nontermination-analysis.json')
    f.need(certificate.get('family')==FAMILY,'Wrong fixed-parameter certificate family')
    entries={};returns={}
    for line in log.splitlines():
        match=re.match(r'DIAGNOSTIC tactic (enter|return) (\d+) (\S+) (.*)',line)
        if match:
            row=dict(re.findall(r'(\w+)=([^ ]+)',match[4]));row['label']=match[3]
            (entries if match[1]=='enter' else returns)[int(match[2])]=row
    checked=[]
    for pair in certificate['state_pairs']:
        step=pair['step'];before=work/pair['before'];after=work/pair['after']
        for path,key in [(before,'before_sha256'),(after,'after_sha256')]:
            f.need(path.resolve().parent==work.resolve() and f.sha(path)==pair[key],'Changed or foreign native proof state')
        ba,bt=f.decode(before);aa,at=f.decode(after);enter,returned=entries[step],returns[step]
        f.need(ba['label']==aa['label']==enter['label']==returned['label']=='subset2.conjI.step','Different native tactic')
        index=int(ba['goal_index'])
        f.need(int(aa['goal_index'])==int(enter['goal_index'])==int(returned['goal_index'])==int(enter['goals'])==index
               and int(returned['goals'])==index+1,'Native event/state index mismatch')
        proof=validate_step(bt,at,free_types(before),free_types(after),index,int(returned['maxidx_before']),int(returned['maxidx_after']))
        checked.append({'step':step,**proof,'before_sha256':f.sha(before),'after_sha256':f.sha(after)})
    f.need(checked,'No actual full-state substitution proof')
    for step in range(min(row['step'] for row in checked),max(entries)+1):
        enter,returned=entries[step],returns[step]
        f.need(enter['label']==returned['label']=='subset2.conjI.step' and
            int(enter['goal_index'])==int(enter['goals']) and int(returned['goals'])==int(enter['goals'])+1,
            'Later source trajectory is not recursive rightmost expansion')
    return {'family':FAMILY,'typed_state_pairs':checked,'native_observation':command,
      'source_observer_reverses_exactly':True,'full_state_substitution_checked':True,
      'native_source_sha256':{name:f.sha(installed/name) for name in requirements},
      'basis':'Rigid type a blocks x/s projections; projecting predicate p has a bound head incompatible with conj. Native imitation creates fresh P/Q on the same x,p,s arguments. REPEAT_ALL_NEW visits the fresh rightmost goal before witness substitution.'}