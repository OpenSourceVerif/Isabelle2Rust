// Common runtime helper; append the Nat and/or Signed fragments as documented
// in the theory. Only the Boolean observations cross the test interface.
use isabelle_exported::MappedSubtraction as code;

fn check_observations(mut observations: code::List<bool>) {
    let mut count = 0;
    while let code::List::Cons(value, tail) = observations {
        assert!(value, "HOL subtraction observation {count} changed");
        count += 1;
        observations = *tail;
    }
    assert_eq!(count, 6);
}
