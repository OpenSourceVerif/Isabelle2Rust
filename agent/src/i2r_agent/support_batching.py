"""Measured author size failures preserve genuine source atoms and SCCs."""
import re
from copy import deepcopy
from .common import read,save,Failure
from .task_context import fingerprint
from .program_model import components

POLICY='measured-author-split-atoms-bounded-indivisible-retry-v2'

def apply(plan,directory):
    p=directory/'batch-splits.json';ledger=read(p) if p.exists() else {};out=deepcopy(plan)
    base=fingerprint([POLICY,plan['identity']]);queue=list(plan['groups']);groups=[]
    while queue:
        group=queue.pop(0);record=ledger.get(fingerprint([base,sorted(group)]))
        if record:
            parts=record['parts']
            if record.get('policy')!=POLICY or sorted(n for g in parts for n in g)!=sorted(group):
                raise Failure('invalid_support_partition','Saved split changed policy or source ownership')
            queue=parts+queue
        else:groups.append(group)
    out['groups']=groups;out['source_owner']={n:i for i,g in enumerate(groups) for n in g}
    out['split_policy']=POLICY;out['base_identity']=base;out['identity']=fingerprint([base,groups]);return out

def size_failure(error):
    if error.code=='incomplete_response' and (error.evidence or {}).get('finish_reason')=='length':return True
    if error.code=='support_output_budget_exhausted':return True
    return error.code=='provider_error' and (error.evidence or {}).get('http_status') in {400,413} and bool(re.search(r'context[_ ]length|context window|maximum context|too many tokens',str(error),re.I))

def source_atoms(partition,selected,model):
    """Undo only an automatic whole-program batch, never a semantic component.

    Original graph SCCs protect recursion even through non-owned dependencies;
    adapted type/class edges and original atomic-unit membership also stay intact.
    All unowned dependencies remain available through the normal source-page scope.
    """
    if partition.get('grouping_decision',{}).get('method')!='program_single_group' or len(partition.get('units',{}))!=1:return None
    original=partition.get('original_graph',{}).get('edges',{});adapted=partition.get('source_edges',{})
    graph={n:sorted(set(original.get(n,[]))|set(adapted.get(n,[]))) for n in set(original)|set(adapted)}
    if not selected<=graph.keys():return None # No invented atom for an unknown source.
    groups=[set(g)&selected for g in components(graph)];groups=[g for g in groups if g]
    for unit in partition.get('atomic_units',{}).values():
        atom=set(unit['members'])&selected
        touched=[g for g in groups if g&atom]
        if touched:
            groups=[g for g in groups if not g&atom]+[set().union(*touched)]
    # Signature/constructor-only atoms retain an owner but do not create an
    # otherwise empty author call; attach them to an executable responsibility.
    ordered=sorted((sorted(g) for g in groups),key=lambda g:tuple(g));parts=[];pending=[]
    for atom in ordered:
        pending+=atom
        if any(n in model['entries'] or model['entities'][n].get('execution_equations') for n in atom):
            parts.append(sorted(pending));pending=[]
    if pending:
        if parts:parts[-1]=sorted(parts[-1]+pending)
        else:parts=[sorted(pending)]
    return parts

def split(plan,group,state,error,directory):
    if not size_failure(error):return False
    selected=set(group);parts=[];seen=set();partition=state.get('partition',{})
    for uid in partition.get('order',[]):
        part=sorted(set(partition['units'][uid]['members'])&selected)
        if part:parts.append(part);seen.update(part)
    parts.extend([[n] for n in sorted(selected-seen)])
    basis='validated_components'
    if len(parts)<2:
        atoms=source_atoms(partition,selected,state['bundle']['source_model'])
        if atoms is not None:parts=atoms;basis='automatic_whole_program_to_original_atoms_and_sccs'
    if len(parts)<2:return False
    pivot=len(parts)//2;halves=[sorted(n for p in parts[:pivot] for n in p),sorted(n for p in parts[pivot:] for n in p)]
    if sorted(n for g in halves for n in g)!=sorted(group):raise Failure('invalid_support_partition','Split changed source ownership')
    p=directory/'batch-splits.json';ledger=read(p) if p.exists() else {};key=fingerprint([plan['base_identity'],sorted(group)])
    if key in ledger:return False
    ledger[key]={'policy':POLICY,'basis':basis,'atomic_parts':parts,'partition_identity':fingerprint(partition),'parts':halves,
        'failure':{'code':error.code,'message':str(error),'evidence':error.evidence},'original_group':group,
        'candidate_unchanged':True,'obligations_preserved':True};save(p,ledger);return True
