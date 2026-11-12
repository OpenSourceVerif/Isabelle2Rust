"""Small, deterministic advisory selection; offline candidates are never loaded."""
import json
import re
from .common import ROOT, digest

CATALOG = 'references/rust-generation/references/repair-knowledge.json'
REFERENCE_PATHS = (CATALOG,
    'references/rust-generation/references/ownership-examples.md',
    'references/rust-generation/references/closures-and-generics.md',
    'references/semantic-adaptation/references/numeric-semantics.md',
    'references/semantic-adaptation/references/representation-conditions.md',
    'references/semantic-adaptation/references/dashu-int-0.6.2-api.md')
MAX_CHARACTERS = 5000
MAX_ENTRIES = 3


def manifest():
    return {name: digest(ROOT / name) for name in REFERENCE_PATHS}


def catalog():
    return json.loads((ROOT / CATALOG).read_text())


def bounded(rows, data, characters=MAX_CHARACTERS, limit=MAX_ENTRIES):
    result={'version':data['version'],'policy':data['policy'],'entries':[]}
    if len(json.dumps(result,ensure_ascii=False))>characters:return {}
    for row in rows:
        # Evidence hashes remain in the versioned catalog, not repeated per call.
        item={k:v for k,v in row.items() if k not in {'evidence','operations','types','modes','required_fact_prefix','diagnostic_terms','dependency','kind'}}
        candidate={**result,'entries':result['entries']+[item]}
        if len(json.dumps(candidate,ensure_ascii=False))<=characters:result=candidate
        if len(result['entries'])>=limit:break
    return result if result['entries'] else {}


def compiler(diagnostic, rust_config, characters=MAX_CHARACTERS):
    text=json.dumps(diagnostic,ensure_ascii=False)
    def actual_codes(value):
        if isinstance(value,dict):
            code=value.get('code')
            if value.get('level')=='error' and isinstance(code,dict) and re.fullmatch(r'E\d{4}',str(code.get('code',''))):return {code['code']}
            return set().union(*(actual_codes(v) for key,v in value.items() if key!='explanation'))
        if isinstance(value,list):return set().union(*(actual_codes(v) for v in value))
        return set()
    codes=actual_codes(diagnostic)
    if not codes:
        def without_explanations(value):
            if isinstance(value,dict):return {key:without_explanations(v) for key,v in value.items() if key!='explanation'}
            if isinstance(value,list):return [without_explanations(v) for v in value]
            return value
        codes=set(re.findall(r'\bE\d{4}\b',json.dumps(without_explanations(diagnostic))))
    data=catalog();rows=[]
    for row in data['entries']:
        if row['kind']!='compiler' or not codes.intersection(row['codes']):continue
        if any(term not in text for term in row.get('diagnostic_terms',[])):continue
        dep=row.get('dependency')
        if dep:
            actual=rust_config.get('dependencies',{}).get(dep['name'])
            if isinstance(actual,dict):actual=actual.get('version')
            if actual!=dep['version']:continue
        rows.append(row)
    return bounded(rows,data,characters)


def type_names(value):
    if isinstance(value,dict):
        found={value['name']} if value.get('kind')=='type' and 'name' in value else set()
        return found.union(*(type_names(v) for v in value.values()))
    if isinstance(value,list):return set().union(*(type_names(v) for v in value))
    return set()


def semantic(model, numeric_policy, characters=MAX_CHARACTERS):
    data=catalog();rows=[]
    for row in data['entries']:
        if row['kind']!='semantic' or numeric_policy.get('mode') not in row['modes']:continue
        matches=[]
        for key in row['operations']:
            entity=model.get('entities',{}).get(key)
            if not entity or not type_names(entity.get('source_type',{})).intersection(row['types']):continue
            prefix=row.get('required_fact_prefix')
            if prefix and not any(f.get('name','').startswith(prefix) and f.get('equational') and f.get('rules') for f in entity.get('specifications',[])):continue
            matches.append(key)
        if matches:rows.append({**row,'matched_source_entities':matches,'numeric_mode':numeric_policy['mode']})
    return bounded(rows,data,characters)
