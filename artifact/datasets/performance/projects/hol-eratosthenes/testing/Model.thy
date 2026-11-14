theory Model imports Sieve_Entry begin
definition observe :: "nat list => nat list" where "observe input = primes_upto (hd input)"
end
