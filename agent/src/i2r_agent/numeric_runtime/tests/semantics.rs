use i2r_numeric::{Int, Nat};

#[test]
fn natural_source_semantics() {
    let a=Nat::from(7u8); let b=Nat::from(3u8); let z=Nat::zero();
    assert_eq!((&a+&b).to_string(),"10");
    assert_eq!((&a*&b).to_string(),"21");
    assert_eq!((&b-&a),z);
    assert_eq!((&a/&z),z); assert_eq!((&a%&z),a);
    assert_eq!((&a/&b).to_string(),"2"); assert_eq!((&a%&b).to_string(),"1");
    let mut owned=a.clone(); owned+=&b; owned*=b;
    assert_eq!(owned.to_string(),"30");
    assert_eq!(a.clamped_len(3),3); assert_eq!(a.clamped_len(10),7);
    assert_eq!(Nat::zero().try_pow(0).unwrap(),Nat::one());
    assert_eq!(Nat::from(3u8).try_pow(5).unwrap().to_string(),"243");
}

#[test]
fn signed_div_mod_follow_isabelle_floor_convention() {
    for a in -33i128..=33 { for b in -9i128..=9 {
        let x=Int::from(a); let y=Int::from(b);
        let q=&x/&y; let r=&x%&y;
        let expected_q=if b==0 {0} else {
            let q=a/b; if a%b!=0 && (a<0)!=(b<0) {q-1} else {q}
        };
        assert_eq!(q.to_string(),expected_q.to_string());
        assert_eq!(r.to_string(),(a-expected_q*b).to_string());
        assert_eq!(&q*&y+&r,x);
    }}
    assert_eq!(Int::from(-5).to_nat(),Nat::zero());
    assert_eq!(Int::from(8).to_nat(),Nat::from(8u8));
}

#[test]
fn common_domain_includes_full_machine_boundaries() {
    let n=Nat::from(u128::MAX); assert_eq!(n.try_to_u128().unwrap(),u128::MAX);
    assert_eq!((&n/&Nat::one()),n);
    let min=Int::from(i128::MIN); let max=Int::from(i128::MAX);
    assert_eq!(min.try_to_i128().unwrap(),i128::MIN);
    assert_eq!((&min%&Int::from(-1)),Int::zero());
    assert_eq!((&max+&min).to_string(),"-1");
    assert_eq!(Nat::zero().try_shl(129).unwrap(),Nat::zero());
    assert_eq!(Nat::one().shr(129),Nat::zero());
    assert_eq!("xyz".parse::<Nat>().unwrap_err(),i2r_numeric::NumericError::InvalidInteger);
}

#[cfg(feature="arbitrary")]
#[test]
fn arbitrary_is_unbounded() {
    let big=Nat::one().try_shl(256).unwrap();
    assert_eq!(big.to_string(),"115792089237316195423570985008687907853269984665640564039457584007913129639936");
    assert_eq!((&big*&big).shr(256),big);
    let signed=Int::try_from_nat(&big).unwrap(); assert_eq!((-&signed).to_nat(),Nat::zero());
    assert_eq!((&signed/&Int::from(-1)),-signed);
    assert_eq!((&Nat::from(u128::MAX)+Nat::one()).to_string(),"340282366920938463463374607431768211456");
}

#[cfg(feature="checked")]
#[test]
fn checked_reports_overflow_instead_of_wrapping_or_falling_back() {
    use i2r_numeric::NumericError::Overflow;
    assert_eq!(Nat::from(u128::MAX).try_add(&Nat::one()),Err(Overflow));
    assert_eq!(Nat::one().try_shl(128),Err(Overflow));
    assert_eq!(Nat::from(2u8).try_shl(127),Err(Overflow));
    assert_eq!(Nat::from(u128::MAX).try_mul(&Nat::from(2u8)),Err(Overflow));
    assert_eq!(Int::from(i128::MIN).try_neg(),Err(Overflow));
    assert_eq!(Int::from(i128::MIN).try_div_floor(&Int::from(-1)),Err(Overflow));
    assert_eq!(Int::try_from_nat(&Nat::from(u128::MAX)),Err(Overflow));
    assert_eq!("340282366920938463463374607431768211456".parse::<Nat>(),Err(Overflow));
    let error=std::panic::catch_unwind(||Nat::from(u128::MAX)+Nat::one()).unwrap_err();
    assert!(error.downcast_ref::<String>().unwrap().contains("I2R_NUMERIC_OVERFLOW"));
}
