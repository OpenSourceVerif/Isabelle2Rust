"""Preserve obligations while synchronizing explicitly judged wrong oracle prose."""
from copy import deepcopy
import re
from .common import Failure
from .task_context import fingerprint

def synchronize(original,updated,verdict,checks):
    edited={e['test_id'] for e in verdict['edits']};rows=deepcopy(updated['obligations']);proof=[]
    for oid,judgment in checks['obligations'].items():
        if judgment['verdict']!='wrong':continue
        names=judgment.get('tests',[])
        if len(names)!=1 or names[0] not in edited:continue
        if not re.fullmatch(r'o:\d+',oid):raise Failure('source_suite_review_unresolved','Invalid obligation identity')
        index=int(oid[2:]);old=original['obligations'][index]
        if old.get('test_name')!=names[0]:raise Failure('source_suite_review_unresolved','Wrong obligation does not uniquely bind the edited test')
        related=[e for e in verdict['edits'] if e['test_id']==names[0]]
        reason=judgment.get('reason','');new_literals=[re.sub(r'\s+','',e['new']) for e in related]
        # A denial alone is not a replacement basis. Preserve exact original
        # model reasoning only when it states the proposed corrected literal,
        # and cites the same real source responsibility, not interface facts alone.
        source_ids={e.get('source') for e in verdict['source_evidence'] if e.get('kind')=='source' and e.get('id') in judgment.get('basis',[])}
        affirmative=isinstance(reason,str) and all(re.search(r'(?:yielding|yields|produces|expectedis|resultis|requiredis)'+re.escape(x),re.sub(r'\s+','',reason),re.I) for x in new_literals)
        if not affirmative or re.search(r'\b(?:not|never)\s+(?:yield|produce|expect)',reason,re.I) or old.get('source') not in source_ids:
            raise Failure('source_suite_review_unresolved','Wrong obligation reason lacks explicit corrected expectation and exact source basis; do not invent prose',oid)
        if rows[index]!=old:raise Failure('source_suite_review_unresolved','Obligation already changed before protected synchronization')
        rows[index]={**old,'expected_basis':reason}
        proof.append({'obligation':oid,'test_id':names[0],'field':'expected_basis','old':old.get('expected_basis'),'new':reason,'old_sha256':fingerprint(old.get('expected_basis')),'new_sha256':fingerprint(reason),'verdict_row_sha256':fingerprint(judgment),'verbatim_checker_reason':True})
    if not proof:return updated
    revised=deepcopy(updated);revised['obligations']=rows
    revised['oracle_metadata_revision']={'policy':'verbatim-wrong-linked-oracle-basis-v1','validated_verdict_sha256':fingerprint(verdict),'changes':proof,'all_other_fields_and_rows_unchanged':True}
    revised['identity']=fingerprint({'parent_revision':updated['identity'],'obligations':rows,'oracle_metadata_revision':revised['oracle_metadata_revision']})
    return revised
