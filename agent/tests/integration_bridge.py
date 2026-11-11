"""Explicit local integration fixture. Synthetic evidence, never an AFP result."""
from pathlib import Path
from unittest.mock import Mock
from i2r_agent.common import *
from i2r_agent.preprocessing import preprocess
from i2r_agent.adapters import load_adapter, materialize_support
from i2r_agent.planning import manifest, candidate_contract
from i2r_agent.generation import generate
from i2r_agent.references import cargo

root=ROOT/'state/preprocessing-rebuild-20261031'/('bridge-integration-'+now().replace(':',''))
root.mkdir(exist_ok=True);cfg=config();ex=Executor(root/'commands')
bundle=preprocess(ROOT/'tests/fixtures/adapter-bridge',cfg,root/'source',ex)
plan={'adaptation':{'decisions':[]},'dependencies':{},'adapter':{'imports':['HOL-Library.Code_Target_Nat'],
 'declarations':r'''code_printing type_constructor bool \<rightharpoonup> (Rust) "bool"
 | constant Not \<rightharpoonup> (Rust) "!crate::Native::flip'(_')"
 | type_constructor integer \<rightharpoonup> (Rust) "u128"
 | constant Suc \<rightharpoonup> (Rust) "!crate::succ'(_')"
 code_printing code_module Native \<rightharpoonup> (Rust) \<open>
// This comment must not swallow the next line during Pretty export.
unsafe extern "C" { fn invert(x: u8) -> u8; }
pub fn flip(x: bool) -> bool { unsafe { invert(u8::from(x)) != 0 } }
\<close>
 setup \<open>Numeral.add_code \<^const_name>\<open>Code_Numeral.Pos\<close> I (fn _ => fn n => Int.toString n ^ "u128") "Rust"\<close>
''','rust_root':'pub fn succ(n: u128) -> u128 { n.checked_add(1).expect("I2R_NUMERIC_OVERFLOW") }','rust_files':{
 'native/invert.c':'unsigned char invert(unsigned char x) { return x ? 0 : 1; }\n',
 'build.rs':r'''use std::{env,path::PathBuf,process::Command};
fn main() {
 let out=PathBuf::from(env::var("OUT_DIR").unwrap());
 assert!(Command::new("cc").args(["-c","native/invert.c","-o"]).arg(out.join("invert.o")).status().unwrap().success());
 assert!(Command::new("ar").arg("crus").arg(out.join("libinvert.a")).arg(out.join("invert.o")).status().unwrap().success());
 println!("cargo:rustc-link-search=native={}",out.display());
 println!("cargo:rustc-link-lib=static=invert");
}'''
}}}
loaded=load_adapter(plan,bundle,cfg,root/'adapter',ex)
assert any(x['application'].get('rust')=='7u128' for x in loaded['bindings']['concrete_applications'])
assert any(x['application']['status']=='requires_concrete_application' for x in loaded['bindings']['operations'])
assert any(x['source']=='constant:Nat.Suc' and x['application']['status']=='rendered' for x in loaded['bindings']['operations'])
support=loaded['support'];code='\n'.join(support['files'].values())
assert '// This comment must not swallow the next line during Pretty export.\n' in code
crate=root/'ffi-execute'
entries=[e for p in bundle['programs'] for e in p['entries']]
plan.update(boundaries=[],architecture={'exports':[{'source':e} for e in entries]})
bundle.update(translation_plan=plan,loaded_adapter=loaded)
provider=Mock();provider.call.return_value={'files':{'src/lib.rs':'pub fn flip(x: bool) -> bool { Native::flip(x) }\npub fn literal() -> u128 { 7u128 }\npub fn successor(n: u128) -> u128 { succ(n) }'},
    'mapping':[{'source':e,'rust':e.rsplit('.',1)[-1]} for e in entries],'adaptation_usage':[]}
generated=generate(bundle,cfg,provider,crate)
candidate_contract(plan,generated['files'],generated['mapping'],generated['adaptation_usage'],bundle)
(crate/'src/main.rs').write_text('fn main() { assert!(i2r_candidate::flip(false)); assert!(!i2r_candidate::flip(true)); assert_eq!(i2r_candidate::literal(),7); assert_eq!(i2r_candidate::successor(6),7); println!("ffi passed"); }')
ran=ex.run(cargo(cfg,'run','--release','--manifest-path',crate/'Cargo.toml'),timeout=cfg['budgets']['build_seconds'])
save(root/'result.json',{'status':'passed','kind':'synthetic_integration','checks':['actual ML numeral printer','original source Suc printing queried alongside imported code equations','code-module newline preserved','generation materialization and candidate contract with build.rs/C sources','Rust/C FFI compile, link and execute'],'execution':ran})
print('bridge integration passed')
