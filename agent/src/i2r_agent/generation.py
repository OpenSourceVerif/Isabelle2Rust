"""Lossless source graph encoding shared by the context reader."""
import json


def intern_program(programs):
    """Lossless structural sharing, especially for repeated Thingol case primitives."""
    table=[];index={}
    def intern(value):
        if isinstance(value,dict):node={k:intern(v) for k,v in value.items()}
        elif isinstance(value,list):node=[intern(v) for v in value]
        else:return value
        key=json.dumps(node,sort_keys=True,separators=(',',':'))
        if key not in index:index[key]=len(table);table.append(node)
        return {'$ref':index[key]}
    root=intern(programs)
    return {'encoding':'lossless DAG: {$ref:N} means table[N]; recursively expand references', 'root':root,'table':table}
