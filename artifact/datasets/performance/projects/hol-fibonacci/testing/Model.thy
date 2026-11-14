theory Model imports Fib_Entry begin
definition observe :: "nat list => nat list" where "observe input = [Fib.fib (hd input)]"
end
