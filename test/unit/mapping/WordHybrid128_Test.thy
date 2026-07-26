theory WordHybrid128_Test
  imports
    Word_Setup_Common
    "Rust.Rust_Hybrid128_WordU128_Setup"
begin

export_code
  word_arithmetic word_div_mod word_bits word_casts word_signed_compare word_mask
  in Rust

end
