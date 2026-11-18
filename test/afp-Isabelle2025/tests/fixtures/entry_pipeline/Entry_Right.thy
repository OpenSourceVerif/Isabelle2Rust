theory Entry_Right
  imports Entry_Base
begin

declare probe_def[code del]

lemma probe_code [code]: "probe P = (P 0 & P 1)"
  unfolding probe_def by (auto simp: less_Suc_eq numeral_eq_Suc)

end
