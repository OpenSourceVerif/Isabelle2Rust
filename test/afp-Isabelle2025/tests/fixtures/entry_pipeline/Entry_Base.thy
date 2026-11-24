theory Entry_Base
  imports Main "Rust.Rust_BigInt_Setup" "Go.Go_Setup"
begin

definition healthy :: "nat => nat" where
  "healthy n = Suc n"

definition probe :: "(nat => bool) => bool" where
  "probe P = (ALL n. n < 2 --> P n)"

end
