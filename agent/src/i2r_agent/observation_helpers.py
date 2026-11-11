"""Explicit, source-bound observation helpers; never candidate replacements."""
from pathlib import Path
from .common import digest,read

MIRROR_SOURCE_HASHES = {'Model.thy': '3a2698e072d08c8cd47cb4f0c923d322b04e37988300a201623b394923c90c17', 'Kernel.thy': '2d99c4e0d60454140ef74d10d95a9ad18c60d54577bc31e41a4e93ec03a989d4', 'Tree_Test.thy': 'af0bbaaf7f6365e0b061de292a9e6dc96525aa55f75e0710bcf0d6e35cfa8e1b', 'Export.thy': '4c1fb1e7234d78a12fab6efd4609b16a80103c1ee51e43d49c95b0ac152bf90b'}
MIRROR_TARGETS = {'type:Tree_Test.tree','constant:Tree_Test.tree.Leaf',
                  'constant:Tree_Test.tree.Node','constant:Tree_Test.mirror'}
PREORDER_EQUATIONS = r'''fun preorder :: "'a tree \<Rightarrow> 'a list" where
"preorder \<langle>\<rangle> = []" |
"preorder \<langle>l, x, r\<rangle> = x # preorder l @ preorder r"'''


def scenario_identity(project):
    project=Path(project)
    names=['Model.thy','Kernel.thy']
    meta=read(project/'case.json') if (project/'case.json').exists() else {}
    if meta.get('id')=='fpp-mirror':names+=['Tree_Test.thy','Export.thy']
    return {n:digest(project/n) if (project/n).exists() else None for n in names}


def material(project,mapping):
    project=Path(project)
    meta=read(project/'case.json') if (project/'case.json').exists() else {}
    if meta.get('id')!='fpp-mirror':return {}
    # Exact admitted scenario and imported theory, not a guess from function names.
    # The export is mirror only, whose source closure is tree + constructors.
    hashes=scenario_identity(project)
    if hashes!=MIRROR_SOURCE_HASHES:return {}
    if {r.get('source') for r in mapping}!=MIRROR_TARGETS:return {}
    return {'schema':'mirror-observation-helpers-v1','source_hashes':hashes,
        'candidate_required_call':'constant:Tree_Test.mirror',
        'model_owned_helper':'Model.fixture (equations in Model.thy)',
        'external_observation_helpers':[{'source':'constant:Tree_Test.preorder',
            'equations':PREORDER_EQUATIONS,'role':'encode the actual returned tree, never replace mirror'}],
        'scope':'Only fixture construction and preorder observation may be implemented in the connector. Call the mapped candidate mirror once between them. Do not implement mirror or return input directly. Keep fixture and preorder inside kernel_run, matching Kernel.thy; kernel_prepare is identity.'}


def generate(project,files,mapping,cfg):
    """Only the admitted mirror scenario and one verified boxed-tree interface."""
    import re
    from .segmented_contract import interfaces
    from .support_framework import enum_layout_matches
    if cfg['preprocessing']['numeric_mode']!='checked' or cfg['testing']['transport']!='native-u128':return None
    facts=material(project,mapping)
    if not facts:return None
    paths={r['source']:r.get('rust_item','') for r in mapping}
    tree=paths['type:Tree_Test.tree'];entry=paths['constant:Tree_Test.mirror']
    if not all(re.fullmatch(r'crate(?:::[A-Za-z_]\w*)+',p) for p in (tree,entry)):return None
    if paths['constant:Tree_Test.tree.Leaf']!=tree+'::Leaf' or paths['constant:Tree_Test.tree.Node']!=tree+'::Node':return None
    api=interfaces(files);rows=api.get(tree,[]);functions=api.get(entry,[])
    if len(rows)!=1 or len(functions)!=1:return None
    name=tree.rsplit('::',1)[-1]
    decl=rows[0].get('declaration','');signature=functions[0].get('signature','')
    enum=enum_layout_matches(decl,name,'tree')
    fn=re.fullmatch(r'pub fn '+re.escape(entry.rsplit('::',1)[-1])+r'<([A-Za-z_]\w*)>\([A-Za-z_]\w*:\s*'+re.escape(name)+r'<\1>\)\s*->\s*'+re.escape(name)+r'<\1>\s*',signature)
    if not enum or not fn:return None
    rust_tree=tree.replace('crate::','i2r_candidate::',1);rust_entry=entry.replace('crate::','i2r_candidate::',1)
    code='''pub type WireInt=u128;
pub type Prepared=Vec<WireInt>;
pub type KernelResult=Vec<WireInt>;
fn fixture(input:&[WireInt])->TREE<WireInt> {
    match input.split_first() {
        None=>TREE::Leaf,
        Some((x,xs))=>TREE::Node(Box::new(fixture(xs)),*x,Box::new(TREE::Leaf)),
    }
}
fn preorder(tree:TREE<WireInt>)->Vec<WireInt> {
    match tree {
        TREE::Leaf=>Vec::new(),
        TREE::Node(l,x,r)=>{
            let mut out=vec![x];
            out.extend(preorder(*l));
            out.extend(preorder(*r));
            out
        }
    }
}
pub fn observe(input:&[WireInt])->Vec<WireInt>{preorder(ENTRY(fixture(input)))}
pub fn benchmark_prepare(input:&[WireInt])->Prepared{input.to_vec()}
pub fn benchmark_run(input:Prepared)->KernelResult{observe(&input)}
pub fn benchmark_encode(result:KernelResult)->Vec<WireInt>{result}
'''.replace('TREE',rust_tree).replace('ENTRY',rust_entry)
    return {'status':'generated','schema':'mirror-observation-helpers-v1','files':{'src/lib.rs':code},
        'source_helpers':facts,'scope':'Exact source fixture -> actual candidate mirror -> preorder of actual result; compilation and differential execution required.'}
