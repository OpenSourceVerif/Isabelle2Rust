theory Export
 imports "I2R_Agent.Agent_Export" "HOL.Code_Numeral"
begin
 definition flip :: "bool \<Rightarrow> bool" where "flip b = (\<not> b)"
 definition literal :: integer where "literal = 7"
 definition successor :: "nat \<Rightarrow> nat" where "successor n = Suc n"
 export_code flip literal successor in Rust_Agent module_name Bridge
end
