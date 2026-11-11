use isabelle_exported::SharedContainerChain::{witness_branch, witness_chain, Itself};
use std::marker::PhantomData;

fn witness<A>() -> Itself<A> {
    Itself::Type(PhantomData)
}

#[test]
fn ordinary_chain_keeps_the_witness_type() {
    let _: Itself<bool> = witness_chain(witness::<bool>());
    let _: Itself<Vec<bool>> = witness_chain(witness::<Vec<bool>>());
}

#[test]
fn ordinary_branch_keeps_the_witness_type() {
    let _: Itself<(bool, bool)> = witness_branch(witness(), witness());
    let _: Itself<Vec<bool>> = witness_branch(witness(), witness());
}
