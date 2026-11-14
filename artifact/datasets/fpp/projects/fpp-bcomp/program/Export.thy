theory Export imports Compiler_Test "I2R_Agent.Agent_Export" begin
export_code Compiler_Test.bcomp in Rust_Agent module_name Candidate
end
