.PHONY: open open_test build build_silent code gen opt test targeted hol macro_sbpf micro_sbpf micro_sbpf_gen sbpf x64 x64_gen x64_test clean help

#### Configuration ####

DEFAULT_FILE := $(CURDIR)/Rust_Setup.thy
PROJECT_SESSION := Rust
TEST_SESSION    := Rust
TEST_ROOT_DIR   := test-root
TEST_ROOT_FILE  := $(TEST_ROOT_DIR)/ROOT
HOL_TEST_THEORY ?= Hol_Test_Integer

CARGO                  ?= cargo
OCAMLC                 ?= ocamlc
OCAMLFIND              ?= ocamlfind
ISABELLE_EXPORTED_LOCK := $(CURDIR)/scripts/isabelle-exported.Cargo.lock
OPTIMIZE_DIR           := $(CURDIR)/optimize
ISABELLE_BUILD_LOCK    := $(CURDIR)/.isabelle-build.lock
ISABELLE_PROJECT_BUILD := isabelle build -v -e -d . $(PROJECT_SESSION)
ISABELLE_TEST_VERBOSE  := isabelle build -v -e -d $(TEST_ROOT_DIR) $(TEST_SESSION)
ISABELLE_TEST_SILENT   := isabelle build -e -d $(TEST_ROOT_DIR) $(TEST_SESSION)

WRITE_TEST_ROOT = mkdir -p $(TEST_ROOT_DIR); { printf '%s\n' 'session $(TEST_SESSION) in ".." = Main +' '  description "$(TEST_THEORY) test session"' '  options [timeout = 300]' '  sessions' '    "HOL-Library"' '    "Word_Lib"' '  directories' '    "$(TEST_DIR)"' '  theories [document = false]' '    Rust_Setup' '    Rust_BigInt_Int_Setup' '    Rust_BigInt_Nat_Setup' '    "$(TEST_DIR)/$(TEST_THEORY)"' '  export_files (in "$(TEST_DIR)/stage1/$(TEST_THEORY)") [2]' '    "*:**.rs"' '    "*:**.toml"' '    "*:**.ocaml"'; } > $(TEST_ROOT_FILE)

#### Targets ####

open:
	isabelle jedit -n -d . -R $(PROJECT_SESSION) $(DEFAULT_FILE)

open_test:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make open_test TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  echo "Example: make open_test TEST_DIR=tests_targeted/types TEST_THEORY=Type_Tuple_Test"; \
	  exit 1; \
	fi
	@$(WRITE_TEST_ROOT)
	isabelle jedit -n -d $(TEST_ROOT_DIR) -R $(TEST_SESSION) "$(TEST_DIR)/$(TEST_THEORY).thy"

# build one theory (verbose)
build:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make build TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  echo "Example: make build TEST_DIR=tests_targeted TEST_THEORY=List_Test"; \
	  exit 1; \
	fi
	@{ \
	  flock 9; \
	  echo ">> $(TEST_ROOT_FILE) for $(TEST_DIR)/$(TEST_THEORY).thy"; \
	  $(WRITE_TEST_ROOT); \
	  echo ">> isabelle build (verbose)..."; \
	  $(ISABELLE_TEST_VERBOSE); \
	} 9>$(ISABELLE_BUILD_LOCK)

# build one theory (quiet, for targeted)
build_silent:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make build_silent TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  exit 1; \
	fi
	@{ \
	  flock 9; \
	  $(WRITE_TEST_ROOT); \
	  $(ISABELLE_TEST_SILENT); \
	} 9>$(ISABELLE_BUILD_LOCK)

code:
	@{ flock 9; $(ISABELLE_PROJECT_BUILD); } 9>$(ISABELLE_BUILD_LOCK)

# gen: Isabelle build → stage1 + cargo run on stage1
# Usage: make gen DIR=<dir> Name=<theory>   (single)
#        make gen DIR=<dir>                 (all *_Test.thy under dir)
gen:
	@_cargo_run_stage1() { \
	  local dir="$$1" name="$$2"; \
	  local out="$$dir/stage1/$$name"; \
	  if [ ! -d "$$out" ]; then echo "No stage1 dir: $$out"; return 1; fi; \
	  local manifests; \
	  manifests=$$(find "$$out" -maxdepth 2 -type f -name Cargo.toml | sort); \
	  if [ -z "$$manifests" ]; then echo "No Cargo.toml under $$out"; return 1; fi; \
	  for m in $$manifests; do \
	    local pkg_dir=$$(dirname "$$m"); \
	    if [ ! -f "$$pkg_dir/Cargo.lock" ] && [ -f "$(ISABELLE_EXPORTED_LOCK)" ]; then \
	      cp "$(ISABELLE_EXPORTED_LOCK)" "$$pkg_dir/Cargo.lock"; \
	    fi; \
	    RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" $(CARGO) run --locked --manifest-path "$$m" || return 1; \
	  done; \
	}; \
	if [ -n "$(DIR)" ] && [ -n "$(Name)" ]; then \
	  echo ">>> [gen] $(Name)"; \
	  $(MAKE) build_silent TEST_DIR="$(DIR)" TEST_THEORY="$(Name)"; \
	  _cargo_run_stage1 "$(DIR)" "$(Name)"; \
	elif [ -n "$(DIR)" ]; then \
	  FILES=$$(find "$(DIR)" -name '*_Test.thy' -type f | sort); \
	  if [ -z "$$FILES" ]; then \
	    echo "No *_Test.thy found under $(DIR)"; exit 1; \
	  fi; \
	  SUCCESS=0; FAIL=0; TOTAL=0; FAILED=""; \
	  for f in $$FILES; do \
	    D=$$(dirname "$$f"); T=$${f##*/}; T=$${T%.thy}; \
	    TOTAL=$$((TOTAL+1)); \
	    echo ">>> [gen $$TOTAL] $$T"; \
	    if $(MAKE) -s build_silent TEST_DIR="$$D" TEST_THEORY="$$T" && \
	       _cargo_run_stage1 "$$D" "$$T"; then \
	      SUCCESS=$$((SUCCESS+1)); \
	    else \
	      FAIL=$$((FAIL+1)); FAILED="$$FAILED $$T"; \
	    fi; \
	  done; \
	  echo "================================"; \
	  echo "gen summary ($(DIR)):"; \
	  echo "  Passed: $$SUCCESS / Failed: $$FAIL / Total: $$TOTAL"; \
	  if [ -n "$$FAILED" ]; then \
	    for T in $$FAILED; do echo "    - $$T"; done; \
	    exit 1; \
	  fi; \
	else \
	  echo "Usage:"; \
	  echo "  make gen DIR=<dir> Name=<theory>  # build Isabelle + cargo run stage1"; \
	  echo "  make gen DIR=<dir>                # all *_Test.thy under dir"; \
	  exit 1; \
	fi

# opt: optimizer stage1 -> stage2 + cargo run on stage2 (no Isabelle build)
# Usage: make opt DIR=<dir> Name=<theory>   (single)
#        make opt DIR=<dir>                 (all theories in dir/stage1/)
opt:
	@_run_opt() { \
	  local dir="$$1" name="$$2"; \
	  local s1="$$dir/stage1/$$name/export1"; \
	  local s2="$$dir/stage2/$$name"; \
	  if [ ! -d "$$s1" ]; then \
	    echo "ERROR: stage1 not found at $$s1 — run make gen first"; return 1; \
	  fi; \
	  echo ">>> [opt] $$name  stage1 -> stage2"; \
	  rm -rf "$$s2"; \
	  $(CARGO) run -q --manifest-path "$(OPTIMIZE_DIR)/Cargo.toml" --bin cargo-opt -- \
	    "$$s1" --out-dir "$$s2" || return 1; \
	  if [ ! -f "$$s2/Cargo.lock" ]; then \
	    if   [ -f "$$s1/Cargo.lock" ];           then cp "$$s1/Cargo.lock" "$$s2/Cargo.lock"; \
	    elif [ -f "$(ISABELLE_EXPORTED_LOCK)" ];  then cp "$(ISABELLE_EXPORTED_LOCK)" "$$s2/Cargo.lock"; \
	    fi; \
	  fi; \
	  echo ">>> [opt] cargo run stage2: $$name"; \
	  RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" $(CARGO) run --locked \
	    --manifest-path "$$s2/Cargo.toml" || return 1; \
	}; \
	if [ -n "$(DIR)" ] && [ -n "$(Name)" ]; then \
	  _run_opt "$(DIR)" "$(Name)"; \
	elif [ -n "$(DIR)" ]; then \
	  S1BASE="$(DIR)/stage1"; \
	  if [ ! -d "$$S1BASE" ]; then \
	    echo "No stage1 directory at $$S1BASE — run make gen first"; exit 1; \
	  fi; \
	  NAMES=$$(find "$$S1BASE" -mindepth 1 -maxdepth 1 -type d | xargs -r -n1 basename | sort); \
	  if [ -z "$$NAMES" ]; then \
	    echo "No theories found under $$S1BASE"; exit 1; \
	  fi; \
	  SUCCESS=0; FAIL=0; TOTAL=0; FAILED=""; \
	  for N in $$NAMES; do \
	    TOTAL=$$((TOTAL+1)); \
	    if _run_opt "$(DIR)" "$$N"; then \
	      SUCCESS=$$((SUCCESS+1)); \
	    else \
	      FAIL=$$((FAIL+1)); FAILED="$$FAILED $$N"; \
	    fi; \
	  done; \
	  echo "================================"; \
	  echo "opt summary ($(DIR)):"; \
	  echo "  Passed: $$SUCCESS / Failed: $$FAIL / Total: $$TOTAL"; \
	  if [ -n "$$FAILED" ]; then \
	    for N in $$FAILED; do echo "    - $$N"; done; \
	    exit 1; \
	  fi; \
	else \
	  echo "Usage:"; \
	  echo "  make opt DIR=<dir> Name=<theory>  # optimize stage1 -> stage2 + cargo run"; \
	  echo "  make opt DIR=<dir>                # all theories in dir/stage1/"; \
	  exit 1; \
	fi

# test: full two-phase pipeline — stage1 (no cargo run) → "stage1 done" → stage2 + cargo run
# Usage: make test DIR=<dir> Name=<theory>   (single)
#        make test DIR=<dir>                 (all *_Test.thy under dir)
test:
	@_run_opt() { \
	  local dir="$$1" name="$$2"; \
	  local s1="$$dir/stage1/$$name/export1"; \
	  local s2="$$dir/stage2/$$name"; \
	  rm -rf "$$s2"; \
	  $(CARGO) run -q --manifest-path "$(OPTIMIZE_DIR)/Cargo.toml" --bin cargo-opt -- \
	    "$$s1" --out-dir "$$s2" || return 1; \
	  if [ ! -f "$$s2/Cargo.lock" ]; then \
	    if   [ -f "$$s1/Cargo.lock" ];           then cp "$$s1/Cargo.lock" "$$s2/Cargo.lock"; \
	    elif [ -f "$(ISABELLE_EXPORTED_LOCK)" ];  then cp "$(ISABELLE_EXPORTED_LOCK)" "$$s2/Cargo.lock"; \
	    fi; \
	  fi; \
	  RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" $(CARGO) run --locked \
	    --manifest-path "$$s2/Cargo.toml" || return 1; \
	}; \
	if [ -n "$(DIR)" ] && [ -n "$(Name)" ]; then \
	  $(MAKE) -s build_silent TEST_DIR="$(DIR)" TEST_THEORY="$(Name)"; \
	  echo ">>> stage1 done: $(Name)"; \
	  _run_opt "$(DIR)" "$(Name)"; \
	elif [ -n "$(DIR)" ]; then \
	  FILES=$$(find "$(DIR)" -name '*_Test.thy' -type f | sort); \
	  if [ -z "$$FILES" ]; then \
	    echo "No *_Test.thy found under $(DIR)"; exit 1; \
	  fi; \
	  SUCCESS=0; FAIL=0; TOTAL=0; FAILED=""; \
	  for f in $$FILES; do \
	    D=$$(dirname "$$f"); T=$${f##*/}; T=$${T%.thy}; \
	    TOTAL=$$((TOTAL+1)); \
	    echo ">>> [test $$TOTAL] $$T"; \
	    if $(MAKE) -s build_silent TEST_DIR="$$D" TEST_THEORY="$$T"; then \
	      echo ">>> stage1 done: $$T"; \
	      if _run_opt "$$D" "$$T"; then \
	        SUCCESS=$$((SUCCESS+1)); \
	      else \
	        FAIL=$$((FAIL+1)); FAILED="$$FAILED $$T"; \
	      fi; \
	    else \
	      FAIL=$$((FAIL+1)); FAILED="$$FAILED $$T"; \
	    fi; \
	  done; \
	  echo "================================"; \
	  echo "test summary ($(DIR)):"; \
	  echo "  Passed: $$SUCCESS / Failed: $$FAIL / Total: $$TOTAL"; \
	  if [ -n "$$FAILED" ]; then \
	    for T in $$FAILED; do echo "    - $$T"; done; \
	    exit 1; \
	  fi; \
	else \
	  echo "Usage:"; \
	  echo "  make test DIR=<dir> Name=<theory>  # stage1 -> stage2 + cargo run (single)"; \
	  echo "  make test DIR=<dir>                # all *_Test.thy under dir"; \
	  exit 1; \
	fi

# targeted: build + cargo run stage1 for all *_Test.thy under tests_targeted
targeted:
	@_cargo_run_stage1() { \
	  local dir="$$1" name="$$2"; \
	  local out="$$dir/stage1/$$name"; \
	  if [ ! -d "$$out" ]; then echo "No stage1 dir: $$out"; return 1; fi; \
	  local manifests; \
	  manifests=$$(find "$$out" -maxdepth 2 -type f -name Cargo.toml | sort); \
	  if [ -z "$$manifests" ]; then echo "No Cargo.toml under $$out"; return 1; fi; \
	  for m in $$manifests; do \
	    local pkg_dir=$$(dirname "$$m"); \
	    if [ ! -f "$$pkg_dir/Cargo.lock" ] && [ -f "$(ISABELLE_EXPORTED_LOCK)" ]; then \
	      cp "$(ISABELLE_EXPORTED_LOCK)" "$$pkg_dir/Cargo.lock"; \
	    fi; \
	    RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" $(CARGO) run --locked --manifest-path "$$m" || return 1; \
	  done; \
	}; \
	TD="tests_targeted"; \
	FILES=$$(find "$$TD" -name '*_Test.thy' -type f | sort); \
	if [ -z "$$FILES" ]; then echo "No *_Test.thy under $$TD"; exit 0; fi; \
	SUCCESS=0; FAIL=0; TOTAL=0; FAILED=""; \
	for f in $$FILES; do \
	  D=$$(dirname "$$f"); T=$${f##*/}; T=$${T%.thy}; \
	  TOTAL=$$((TOTAL+1)); \
	  echo ">>> [$$TOTAL] $$D/$$T"; \
	  if $(MAKE) -s build_silent TEST_DIR="$$D" TEST_THEORY="$$T" && \
	     _cargo_run_stage1 "$$D" "$$T"; then \
	    SUCCESS=$$((SUCCESS+1)); \
	  else \
	    FAIL=$$((FAIL+1)); FAILED="$$FAILED $$D/$$T"; \
	  fi; \
	done; \
	echo "================================"; \
	echo "Targeted summary:"; \
	echo "  Passed: $$SUCCESS / Failed: $$FAIL / Total: $$TOTAL"; \
	if [ -n "$$FAILED" ]; then \
	  echo "  Failed tests:"; \
	  for T in $$FAILED; do echo "    - $$T"; done; \
	  exit 1; \
	fi

hol:
	@echo ">>> Building $(HOL_TEST_THEORY)..."
	$(MAKE) build TEST_DIR=tests_HOL TEST_THEORY=$(HOL_TEST_THEORY)

	@OUT_DIR="tests_HOL/stage1/$(HOL_TEST_THEORY)/export1/src"; \
	if [ ! -d "$$OUT_DIR" ]; then \
	  echo "ERROR: $$OUT_DIR does not exist. Build may have failed."; \
	  exit 1; \
	fi; \
	echo ">>> Replacing main.rs with template..."; \
	cp tests_HOL/template/main.rs "$$OUT_DIR/main.rs"

	@echo ">>> Running cargo..."
	@CARGO_TOML="tests_HOL/stage1/$(HOL_TEST_THEORY)/export1/Cargo.toml"; \
	if [ ! -f "$$CARGO_TOML" ]; then \
	  echo "ERROR: Cargo.toml not found at $$CARGO_TOML"; \
	  exit 1; \
	fi; \
	package_dir=$$(dirname "$$CARGO_TOML"); \
	if [ ! -f "$$package_dir/Cargo.lock" ] && [ -f "$(ISABELLE_EXPORTED_LOCK)" ]; then \
	  cp "$(ISABELLE_EXPORTED_LOCK)" "$$package_dir/Cargo.lock"; \
	fi; \
	RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" cargo run --locked --manifest-path "$$CARGO_TOML"


# sbpf macro validation:
#   shared orchestration lives under tests_sbpf/tests/exec_semantics;
#   language-specific glue and execution live under sbpf_ocaml / sbpf_rust.
SBPF_THEORY_DIR   := tests_sbpf/theory
SBPF_EXEC         := tests_sbpf/tests/exec_semantics
OCAML_VERSION     ?= 4.11.2
RUST_TOOLCHAIN    ?= nightly-2025-12-01

macro_sbpf:
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" DATA_REBUILD="$(DATA_REBUILD)" OCAML_REBUILD="$(OCAML_REBUILD)" OCAML_VERSION="$(OCAML_VERSION)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" python3 $(SBPF_EXEC)/run_macro_sbpf.py

micro_sbpf:
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" OCAML_REBUILD="$(OCAML_REBUILD)" OCAML_VERSION="$(OCAML_VERSION)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" python3 $(SBPF_EXEC)/run_micro_sbpf.py

micro_sbpf_gen:
	@PYTHONDONTWRITEBYTECODE=1 X="$(X)" python3 $(SBPF_EXEC)/run_micro_sbpf.py gen

sbpf: macro_sbpf

# x64 validation:
#   x64_gen builds the random instruction/state data under tests_x64/x64-validation/0-data.
#   x64_test compares the real x64 CPU stepper against the Isabelle-exported OCaml semantics.
X64_VALIDATION      := tests_x64/x64-validation
X64_INS_GEN         := $(X64_VALIDATION)/1-x64-ins-gen
X64_ASSEMBLER       := $(X64_VALIDATION)/2-exec-assembler
X64_MAP_GEN         := $(X64_VALIDATION)/3-x64-map-gen
X64_STEPPER_C       := $(X64_VALIDATION)/4-x64-stepper-c
X64_SEMANTICS       := $(X64_VALIDATION)/5-exec-semantics
X64_COUNT           ?= 10000
X64_OCAML_PACKAGES  ?= yojson
X64_JANSSON_LIBS    ?= $(shell pkg-config --libs jansson 2>/dev/null || echo -ljansson)

x64_gen:
	@echo ">>> [x64_gen] generating $(X64_COUNT) random x64 instructions"
	@$(CARGO) run --quiet --manifest-path $(X64_INS_GEN)/Cargo.toml -- $(X64_COUNT)
	@echo ">>> [x64_gen] encoding instructions with the existing OCaml x64 encoder"
	@cd "$(X64_ASSEMBLER)" && $(OCAMLC) -o exec x64_encode.ml && ./exec
	@echo ">>> [x64_gen] generating register and memory maps"
	@$(CARGO) run --quiet --manifest-path $(X64_MAP_GEN)/Cargo.toml

x64_test:
	@echo ">>> [x64_test] running cases on the real x64 CPU stepper"
	@cd "$(X64_STEPPER_C)" && $(CC) -O2 -Wall -Wextra -o ptrace_exec ptrace_exec.c $(X64_JANSSON_LIBS) && ./ptrace_exec
	@echo ">>> [x64_test] running Isabelle-exported OCaml semantics and comparing results"
	@cd "$(X64_SEMANTICS)" && $(OCAMLFIND) ocamlc -package $(X64_OCAML_PACKAGES) -linkpkg -c x64_step_test.ml && $(OCAMLFIND) ocamlc -package $(X64_OCAML_PACKAGES) -linkpkg -o exec x64_step_test.cmo exec.ml && ./exec

x64: x64_gen x64_test

clean:
	@echo "Cleaning temp files and generated output..."
	find . -name "*\.thy~" -exec rm {} \;
	find . -name "*\.cmi"  -exec rm {} \;
	find . -name "*\.cmo"  -exec rm {} \;
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find tests_targeted -path "*/stage1" -type d -prune -exec rm -rf {} +
	find tests_targeted -path "*/stage2" -type d -prune -exec rm -rf {} +
	find tests_HOL -path "*/stage1" -type d -prune -exec rm -rf {} +
	find tests_sbpf/theory/stage1 -name target -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf tests_sbpf/tests/exec_semantics/_build
	rm -rf tests_sbpf/tests/exec_semantics/sbpf_ocaml/_build
	rm -rf tests_sbpf/tests/exec_semantics/sbpf_rust/_build
	rm -f tests_x64/x64-validation/2-exec-assembler/exec tests_x64/x64-validation/2-exec-assembler/*.cmi tests_x64/x64-validation/2-exec-assembler/*.cmo
	rm -f tests_x64/x64-validation/4-x64-stepper-c/ptrace_exec
	rm -f tests_x64/x64-validation/5-exec-semantics/exec tests_x64/x64-validation/5-exec-semantics/*.cmi tests_x64/x64-validation/5-exec-semantics/*.cmo
	rm -rf optimize/tests/stage1 optimize/tests/stage2
	rm -rf tests_HOL/Hol_Test/target
	rm -rf $(TEST_ROOT_DIR)

help:
	@echo "Available targets:"
	@echo "  open"
	@echo "      Open $(DEFAULT_FILE) in Isabelle/jEdit."
	@echo "  open_test TEST_DIR=<dir> TEST_THEORY=<thy-name>"
	@echo "      Generate test-root/ROOT and open the test theory in Isabelle/jEdit."
	@echo "  build TEST_DIR=<dir> TEST_THEORY=<thy-name>"
	@echo "      Generate test-root/ROOT and run isabelle build (verbose)."
	@echo "      Example: make build TEST_DIR=tests_targeted TEST_THEORY=List_Test"
	@echo "  code"
	@echo "      Build the project session from ROOT."
	@echo "  gen DIR=<dir> [Name=<theory>]"
	@echo "      Isabelle build -> stage1 + cargo run on stage1."
	@echo "      Example: make gen DIR=tests_targeted/optimization/copy Name=Copy_Bool_Fields_Test"
	@echo "      Example: make gen DIR=tests_targeted/optimization/copy"
	@echo "  opt DIR=<dir> [Name=<theory>]"
	@echo "      Optimize stage1 -> stage2 + cargo run on stage2 (no Isabelle build)."
	@echo "      Example: make opt DIR=tests_targeted/optimization/copy Name=Copy_Bool_Fields_Test"
	@echo "      Example: make opt DIR=tests_targeted/optimization/copy"
	@echo "  test DIR=<dir> [Name=<theory>]"
	@echo "      Full pipeline: stage1 (no cargo run) -> 'stage1 done' -> stage2 + cargo run."
	@echo "      Example: make test DIR=tests_targeted/optimization/copy Name=Copy_Bool_Fields_Test"
	@echo "      Example: make test DIR=tests_targeted/optimization/copy"
	@echo "  targeted"
	@echo "      Build + cargo run stage1 for all *_Test.thy under tests_targeted."
	@echo "      Example: make targeted"
	@echo "  hol"
	@echo "      Build and run the HOL smoke test. Default: HOL_TEST_THEORY=$(HOL_TEST_THEORY)."
	@echo "  macro_sbpf [REBUILD=1]"
	@echo "      Run program-level sBPF validation over the Solana official macro cases"
	@echo "      from Isabelle-generated OCaml and Rust exports. REBUILD=1 regenerates"
	@echo "      bpf_generator exports first. DATA_REBUILD=1 refreshes shared JSON."
	@echo "      OCAML_REBUILD=1 rebuilds only OCaml glue/cache."
	@echo "      Example: make macro_sbpf"
	@echo "  micro_sbpf [REBUILD=1]"
	@echo "      Run instruction-level sBPF step validation over tests/data/ocaml_in.json"
	@echo "      from Isabelle-generated OCaml and Rust step_test exports."
	@echo "      Example: make micro_sbpf"
	@echo "  micro_sbpf_gen [X=100]"
	@echo "      Generate random instruction-level step test data without running tests."
	@echo "      Example: make micro_sbpf_gen X=100"
	@echo "  sbpf"
	@echo "      Alias for macro_sbpf."
	@echo "  x64_gen [X64_COUNT=10000]"
	@echo "      Generate x64 validation data under tests_x64/x64-validation/0-data"
	@echo "      without running the Isabelle export or the final comparison."
	@echo "  x64_test"
	@echo "      Run the real x64 CPU stepper, then compare it with the OCaml semantics."
	@echo "  x64"
	@echo "      Run x64_gen followed by x64_test."
	@echo "  clean"
	@echo "      Remove temp files and generated output (stage1, stage2 under tests_targeted/tests_HOL)."
