theory Model imports GCD_Entry begin
definition decode :: "nat => integer" where
 "decode w = (if even w then integer_of_nat (w div 2) else - integer_of_nat ((w+1) div 2))"
definition observe :: "nat list => nat list" where
 "observe input = [nat_of_integer (GCD_Entry.gcd_entry (decode (input!0)) (decode (input!1)))]"
end
