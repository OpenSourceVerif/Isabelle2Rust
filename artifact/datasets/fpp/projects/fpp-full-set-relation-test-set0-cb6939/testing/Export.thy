theory Export imports Kernel "I2R_Agent.Agent_Export" begin
export_code Model.observe Kernel.kernel_prepare Kernel.kernel_run Kernel.kernel_encode in Rust_Agent module_name Candidate
end
