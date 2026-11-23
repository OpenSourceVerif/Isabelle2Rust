theory Nested_Method_Result_Test
  imports Rust_Base_Setup
begin

text \<open>
  Substituting a function instance for Self must preserve arrow boundaries in
  a trait method's result, including below Option and a pair. An absent codec
  is enough to expose an invalid impl signature: bool list => Self must remain
  one function returning Self, rather than flattening Self's own arguments.
  Export the generic class parameter as well as its concrete uses so the trait
  and its reconstructed impl must coexist. The unit instance supplies a present
  codec as a control for its callbacks.
\<close>

class nested_codec =
  fixes nested_codec :: "(('a \<Rightarrow> bool list) \<times> (bool list \<Rightarrow> 'a)) option"

instantiation "fun" :: (type, type) nested_codec
begin
definition "nested_codec_fun = (None :: ((('a \<Rightarrow> 'b) \<Rightarrow> bool list) \<times> (bool list \<Rightarrow> ('a \<Rightarrow> 'b))) option)"
instance ..
end

instantiation unit :: nested_codec
begin
definition nested_codec_unit :: "((unit \<Rightarrow> bool list) \<times> (bool list \<Rightarrow> unit)) option"
  where "nested_codec_unit = Some (\<lambda>_. [], \<lambda>_. ())"
instance ..
end

definition function_codec ::
  "(((bool \<Rightarrow> bool) \<Rightarrow> bool list) \<times> (bool list \<Rightarrow> (bool \<Rightarrow> bool))) option"
  where "function_codec = nested_codec"

definition unit_codec ::
  "((unit \<Rightarrow> bool list) \<times> (bool list \<Rightarrow> unit)) option"
  where "unit_codec = nested_codec"

text \<open>
  A present callback in a newly constructed Some must receive the same result
  expectation through both branches of If. Its function instance yields a
  callback returning another unary function, so Rust callers can invoke the two
  layers independently. This exercises existing constructor and lambda adapters;
  it does not convert a pre-existing container of function values.
\<close>

class nested_factory =
  fixes make_callback :: "bool \<Rightarrow> 'a \<Rightarrow> (bool \<Rightarrow> 'a) option"

instantiation "fun" :: (type, type) nested_factory
begin
definition make_callback_fun :: "bool \<Rightarrow> ('a \<Rightarrow> 'b) \<Rightarrow> (bool \<Rightarrow> ('a \<Rightarrow> 'b)) option"
  where "make_callback_fun flag f = (if flag then Some (\<lambda>b a. f a) else None)"
instance ..
end

export_code nested_codec function_codec unit_codec make_callback nested_factory_fun_inst.make_callback_fun
  in Rust module_name NestedMethodResult

end
