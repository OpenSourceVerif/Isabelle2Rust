"""Mechanical source-test context, without candidate bodies or generator prose."""
from copy import deepcopy
from .segmented_contract import interfaces

def bodyless_interfaces(state):
    result=deepcopy(interfaces(state['files']))
    for rows in result.values():
        for row in rows:
            if row['kind'] in {'const_item','static_item'}:row['signature']=row['signature'].split('=',1)[0].rstrip()+';'
            if row['kind']=='macro_definition':
                # The compiler already validates the exact calls. Do not expose
                # macro expansions as candidate behavior to the oracle checker.
                row['signature']=row['signature'].split('{',1)[0].rstrip()+' { /* expansion withheld */ }'
    return result

def canonical_mapping(state):
    # Mapping.rust/basis/conditions are generator-controlled prose and can contain
    # full implementation bodies. Only mechanical binding fields cross roles.
    return [{k:deepcopy(row[k]) for k in ['source','rust_item','kind','type_parameters'] if k in row}
            for row in state['mapping']]

