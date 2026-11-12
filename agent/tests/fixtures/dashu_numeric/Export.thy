theory Export
  imports "I2R_Agent.Agent_Export"
begin

definition signed_wire :: "int \<Rightarrow> nat" where
  "signed_wire z = 2 * nat (abs z) + (if z < 0 then 1 else 0)"

definition observe :: "nat list \<Rightarrow> nat list" where
  "observe xs = (let n = hd xs; z = int n in
    [n + 1, n - (n + 1), (n + 1) - n, n div 0, n mod 0,
     signed_wire (z div (-7)), signed_wire (z mod (-7)),
     signed_wire ((-z) div 7), signed_wire ((-z) mod 7),
     signed_wire ((-z) div (-7)), signed_wire ((-z) mod (-7)),
     signed_wire (z div 0), signed_wire ((-z) mod 0),
     nat_of_integer (integer_of_nat n), nat_of_integer (- integer_of_nat n),
     signed_wire (int_of_integer (integer_of_nat n)),
     nat_of_integer (integer_of_int (-z)),
     1606938044258990275541962092341162602522202993782792835301376,
     signed_wire (-1606938044258990275541962092341162602522202993782792835301376)])"

definition kernel_prepare :: "nat list \<Rightarrow> nat list" where "kernel_prepare xs = xs"
definition kernel_run :: "nat list \<Rightarrow> nat list" where "kernel_run xs = observe xs"
definition kernel_encode :: "nat list \<Rightarrow> nat list" where "kernel_encode xs = xs"
export_code observe kernel_prepare kernel_run kernel_encode in Rust_Agent module_name Candidate
end
