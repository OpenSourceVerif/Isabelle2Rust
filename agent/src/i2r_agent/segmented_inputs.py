"""Freeze disjoint development/final inputs before exposing any to the model."""
from .suites import scoped_inputs


def split(case, fixed, regressions, count, final_count, seed, bits):
    known={tuple(x) for x in fixed}|{tuple(x['input']) for x in regressions}
    pool={};stagnant=0
    for i in range(32):
        before=len(pool)
        for x in scoped_inputs(case,max(count+final_count,100),seed+i*1000003,bits):
            if tuple(x) not in known:pool.setdefault(tuple(x),x)
        if len(pool)>=count+final_count:break
        stagnant=stagnant+1 if len(pool)==before else 0
        if stagnant>=4:break
    values=list(pool.values())
    # When generators have a small unique domain, reserve an actual nonempty
    # holdout instead of exhausting all unique samples during development.
    dev_count=min(count,max(0,len(values)//3)) if len(values)<count+final_count else count
    dev=values[:dev_count];final=values[dev_count:dev_count+final_count]
    return dev,final,{'development_unique':len(dev),'final_unique':len(final),
        'fixed_regression_excluded':len(known),'requested_development':count,'requested_final':final_count,
        'overlap_unique':0,'generator_unique_shortfall':len(values)<count+final_count,
        'notice':'Finite sampled unique pool, not a proof of exhaustive domain enumeration.'}
