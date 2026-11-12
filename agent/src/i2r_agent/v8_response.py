"""Validate the v8 response envelope before phase-specific semantic checks."""
from copy import deepcopy
from .common import Failure
from .task_context import validate_source_requests

OBJECTS={'files','rust_config','reading_notes','review_checks','repair_hypothesis',
         'performance_analysis','optimization_hypothesis'}
ARRAYS={'strategy_updates','edits','mapping','remove_files','remove_mapping','decisions','boundaries',
        'request_pages','request_code_pages','request_entities','request_files',
        'request_sources','request_references','request_nodes','request_graphs','request_materials',
        'reviewed_sources','reviewed_pages','reviewed_code_pages','quality_resolutions',
        'algorithm_routes','unit_tests','obligations','semantic_obligations','analysis_coverage',
        'interface_guidance','opportunities','components'}
NULLABLE=OBJECTS|ARRAYS|{'numeric_representation','quality_review','reason','notes',
                       'unit_complete','action','test_source'}
STRING_ARRAYS={'remove_files','remove_mapping','request_pages','request_code_pages',
               'request_references','request_graphs','request_materials','reviewed_sources',
               'reviewed_pages','reviewed_code_pages','analysis_coverage'}
RECORD_ARRAYS={'strategy_updates','edits','mapping','boundaries','request_files','request_sources',
               'quality_resolutions','algorithm_routes','unit_tests','obligations',
               'semantic_obligations','interface_guidance','opportunities','components'}
RECORD_FIELDS={'strategy_updates':('id','reason'),'edits':('file','old','new'),'mapping':('source','rust'),
               'boundaries':('source','kind'),'request_files':('path',),'request_sources':('path',),
               'quality_resolutions':('id',),'algorithm_routes':('source',),
               'unit_tests':('file','source'),'obligations':('source',),
               'semantic_obligations':('source',)}


def normalize(reply):
    if not isinstance(reply,dict):raise Failure('invalid_model_response','Return one JSON object')
    result=deepcopy(reply);omitted=sorted(k for k in NULLABLE if k in result and result[k] is None)
    for key in omitted:del result[key]
    # Provider validates this envelope before material dispatch. Give malformed
    # source requests the same actionable protocol feedback at this first boundary.
    validate_source_requests(result)
    def reject(field,expected):
        raise Failure('invalid_model_response','Response field has the wrong shape',
                      {'field':field,'expected':expected,'instruction':'Return a corrected JSON response; no edit has been applied.'})
    for key in OBJECTS:
        if key in result and not isinstance(result[key],dict):reject(key,'object or omitted/null')
    for key in ARRAYS:
        if key in result and not isinstance(result[key],list):reject(key,'array or omitted/null')
    for key in STRING_ARRAYS:
        if any(not isinstance(x,str) for x in result.get(key,[])):reject(key,'array of strings')
    for key in RECORD_ARRAYS:
        for i,row in enumerate(result.get(key,[])):
            if not isinstance(row,dict):reject(f'{key}[{i}]','object')
            fields=('kind','old','new') if key=='edits' and result.get('action') in {'binding_fix','test_wrong'} else RECORD_FIELDS.get(key,())
            for field in fields:
                if not isinstance(row.get(field),str):reject(f'{key}[{i}].{field}','string')
    if result.get('action') in {'binding_fix','test_wrong'}:
        if any(k in result for k in ['files','rust_config','mapping','remove_files','remove_mapping','strategy_updates']):reject('binding_fix','test-only edits; no production fields')
        for i,row in enumerate(result.get('edits',[])):
            if row['kind'] not in {'integration','unit'}:reject(f'edits[{i}].kind','integration or unit')
            if type(row.get('index')) is not int or row['index']<0:reject(f'edits[{i}].index','nonnegative integer')
            if 'file' in row:reject(f'edits[{i}].file','test index only, no production file')
    for key in ['request_entities','request_nodes']:
        for i,row in enumerate(result.get(key,[])):
            if not isinstance(row,str) and not (isinstance(row,dict) and isinstance(row.get('id'),str)):
                reject(f'{key}[{i}]','source ID string or object with string id')
    for i,row in enumerate(result.get('mapping',[])):
        for field,kind in [('rust_item',str),('kind',str),('type_parameters',dict)]:
            if field in row and row[field] is not None and not isinstance(row[field],kind):reject(f'mapping[{i}].{field}',kind.__name__)
    if 'strategy_version' in result and not isinstance(result['strategy_version'],str):reject('strategy_version','string')
    for i,row in enumerate(result.get('strategy_updates',[])):
        if type(row.get('expected_revision')) is not int or row['expected_revision']<0:reject(f'strategy_updates[{i}].expected_revision','nonnegative integer')
    if 'action' in result and not isinstance(result['action'],str):reject('action','string')
    if 'test_source' in result and not isinstance(result['test_source'],str):reject('test_source','Rust source string')
    if 'unit_complete' in result and type(result['unit_complete']) is not bool:reject('unit_complete','boolean')
    analysis=result.get('performance_analysis',{})
    if 'classification' in analysis and not isinstance(analysis['classification'],str):reject('performance_analysis.classification','string')
    # Only optional TOP-LEVEL nulls mean omission. Nested Rust configuration,
    # code strings, source equations and test expectations are never rewritten.
    return result,{'omitted_optional_null_fields':omitted}
