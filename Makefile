.PHONY: open open_test build build_silent code gen opt test targeted hol-gcd hol-stress loc kloc clippy clippy-case-studies-prepare clippy-case-studies clippy-all macro_sbpf micro_sbpf micro_sbpf_gen x64 x64-rust-export x64-gen x64-test x64-performance x64_gen x64_test clean help

#### Configuration ####

DEFAULT_FILE := $(CURDIR)/Rust_Base_Setup.thy
PROJECT_SESSION := Rust
TEST_SESSION    := Rust
TEST_ROOT_DIR   := test-root
TEST_ROOT_FILE  := $(TEST_ROOT_DIR)/ROOT
TEST_TIMEOUT    ?= 300
HOL_DIR         ?= test/HOL_Codegenerator
HOL_GCD_THEORY ?= Code_Test_Rust
HOL_STRESS_SESSION ?= Rust-HOL-Codegenerator_Test

CARGO                  ?= cargo +stable
ISABELLE_CARGO         ?= $(HOME)/.cargo/bin/cargo
OCAMLC                 ?= ocamlc
OCAMLFIND              ?= ocamlfind
ISABELLE_EXPORTED_LOCK := $(CURDIR)/scripts/isabelle-exported.Cargo.lock
CARGO_LOCK_HELPER      := $(CURDIR)/scripts/ensure-cargo-lock.py
OPTIMIZE_DIR           := $(CURDIR)/optimize
OPT_STACK_KB            ?= 65536
EXPORT_ITEM_COUNTER    := $(CURDIR)/scripts/count-rust-export-items.pl
TEST_RUST_METRICS      := $(CURDIR)/scripts/test-rust-metrics.py
IMPLEMENTATION_LOC     := $(CURDIR)/scripts/count-implementation-loc.py
CLIPPY_PROCESSES       ?= 4
CLIPPY_CARGO_JOBS      ?= 1
SBPF_CLIPPY_PROGRAM_S1 := tests_sbpf/theory/stage1/bpf_generator_word_checked_interp/interp_test
SBPF_CLIPPY_PROGRAM_S2 := tests_sbpf/theory/stage2/bpf_generator_word_checked_interp/interp_test
SBPF_CLIPPY_STEP_S1    := tests_sbpf/theory/stage1/bpf_generator_word_checked/step_test
SBPF_CLIPPY_STEP_S2    := tests_sbpf/theory/stage2/bpf_generator_word_checked/step_test
X64_CLIPPY_STEPPER_S1  := tests_x64/theory/stage1/x64StepRustPerformanceGenerator/x64_step_test
X64_CLIPPY_STEPPER_S2  := tests_x64/theory/stage2/x64StepRustPerformanceGenerator/x64_step_test
ISABELLE_BUILD_LOCK    := $(CURDIR)/.isabelle-build.lock
ISABELLE_PROJECT_BUILD := isabelle build -v -e -d . $(PROJECT_SESSION)
ISABELLE_TEST_VERBOSE  := isabelle build -v -e -d $(TEST_ROOT_DIR) $(TEST_SESSION)
ISABELLE_TEST_SILENT   := isabelle build -e -d $(TEST_ROOT_DIR) $(TEST_SESSION)

export ISABELLE_CARGO
unexport RUSTC_BOOTSTRAP

WRITE_TEST_ROOT = mkdir -p $(TEST_ROOT_DIR); { printf '%s\n' 'session $(TEST_SESSION) in ".." = Main +' '  description "$(TEST_THEORY) test session"' '  options [timeout = $(TEST_TIMEOUT)]' '  sessions' '    "HOL-Library"' '    "Word_Lib"' '  directories' '    "$(TEST_DIR)"' '  theories [document = false]' '    Rust_Base_Setup' '    Rust_Integer_BigInt_Layer' '    Rust_BigInt_Setup' '    Rust_Checked128_Setup' '    Rust_BigInt_WordU128_Setup' '    Rust_Checked128_WordU128_Setup' '    "$(TEST_DIR)/$(TEST_THEORY)"' '  export_files (in "$(TEST_DIR)/stage1/$(TEST_THEORY)") [2]' '    "*:**.rs"' '    "*:**.toml"' '    "*:**.ocaml"'; } > $(TEST_ROOT_FILE)

#### Targets ####

open:
	isabelle jedit -n -d . -R $(PROJECT_SESSION) $(DEFAULT_FILE)

open_test:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make open_test TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  echo "Example: make open_test TEST_DIR=test/unit/types TEST_THEORY=Tuple_Test"; \
	  exit 1; \
	fi
	@$(WRITE_TEST_ROOT)
	isabelle jedit -n -d $(TEST_ROOT_DIR) -R $(TEST_SESSION) "$(TEST_DIR)/$(TEST_THEORY).thy"

# build one theory (verbose)
build:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make build TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  echo "Example: make build TEST_DIR=test/unit/mapping TEST_THEORY=Lists_Test"; \
	  exit 1; \
	fi
	@{ \
	  flock 9; \
	  rm -rf "$(TEST_DIR)/stage1/$(TEST_THEORY)"; \
	  echo ">> $(TEST_ROOT_FILE) for $(TEST_DIR)/$(TEST_THEORY).thy"; \
	  $(WRITE_TEST_ROOT); \
	  echo ">> isabelle build (verbose)..."; \
	  $(ISABELLE_TEST_VERBOSE); \
	} 9>$(ISABELLE_BUILD_LOCK)

# build one theory (quiet, for gen/test)
build_silent:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make build_silent TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  exit 1; \
	fi
	@{ \
	  flock 9; \
	  rm -rf "$(TEST_DIR)/stage1/$(TEST_THEORY)"; \
	  $(WRITE_TEST_ROOT); \
	  $(ISABELLE_TEST_SILENT); \
	} 9>$(ISABELLE_BUILD_LOCK)

code:
	@{ flock 9; $(ISABELLE_PROJECT_BUILD); } 9>$(ISABELLE_BUILD_LOCK)

# gen: Isabelle build → stage1 + cargo build on stage1
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
	    CARGO="$(CARGO)" python3 "$(CARGO_LOCK_HELPER)" "$$m" "$(ISABELLE_EXPORTED_LOCK)" || return 1; \
	    env -u RUSTC_BOOTSTRAP RUSTFLAGS="-Awarnings" $(CARGO) build --locked --manifest-path "$$m" || return 1; \
	  done; \
	}; \
	if [ -n "$(DIR)" ] && [ -n "$(Name)" ]; then \
	  ITEMS=$$(perl "$(EXPORT_ITEM_COUNTER)" "$(DIR)/$(Name).thy"); \
	  echo ">>> [gen] $(Name) ($$ITEMS exported definitions)"; \
	  $(MAKE) build_silent TEST_DIR="$(DIR)" TEST_THEORY="$(Name)" || exit 1; \
	  _cargo_run_stage1 "$(DIR)" "$(Name)"; \
	elif [ -n "$(DIR)" ]; then \
	  HOL_FILE="$(HOL_DIR)/$(HOL_GCD_THEORY).thy"; \
	  if [ "$(DIR)" = "$(HOL_DIR)" ]; then \
	    FILES="$$HOL_FILE"; \
	  else \
	    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
	      FILES=$$(git ls-files -- "$(DIR)" | sed -n '/_Test\.thy$$/p' | while IFS= read -r f; do [ -f "$$f" ] && printf '%s\n' "$$f"; done | sort); \
	    else \
	      FILES=$$(find "$(DIR)" -name '*_Test.thy' -type f | sort); \
	    fi; \
	    case "$$HOL_FILE" in "$(DIR)"/*) FILES=$$(printf '%s\n%s\n' "$$FILES" "$$HOL_FILE" | sed '/^$$/d' | sort -u);; esac; \
	  fi; \
	  if [ -z "$$FILES" ]; then \
	    echo "No *_Test.thy found under $(DIR)"; exit 1; \
	  fi; \
	  SUCCESS=0; FAIL=0; SKIP=0; TOTAL=0; SUCCESS_ITEMS=0; FAIL_ITEMS=0; TOTAL_ITEMS=0; FAILED=""; \
	  for f in $$FILES; do \
	    D=$$(dirname "$$f"); T=$${f##*/}; T=$${T%.thy}; \
	    ITEMS=$$(perl "$(EXPORT_ITEM_COUNTER)" "$$f"); \
	    TOTAL=$$((TOTAL+1)); \
	    TOTAL_ITEMS=$$((TOTAL_ITEMS+ITEMS)); \
	    if [ "$$ITEMS" -eq 0 ]; then \
	      SKIP=$$((SKIP+1)); \
	      echo ">>> [gen $$TOTAL] $$T (0 exported definitions) -- skipped"; \
	      continue; \
	    fi; \
	    echo ">>> [gen $$TOTAL] $$T ($$ITEMS exported definitions)"; \
	    if $(MAKE) -s build_silent TEST_DIR="$$D" TEST_THEORY="$$T" && \
	       _cargo_run_stage1 "$$D" "$$T"; then \
	      SUCCESS=$$((SUCCESS+1)); \
	      SUCCESS_ITEMS=$$((SUCCESS_ITEMS+ITEMS)); \
	    else \
	      FAIL=$$((FAIL+1)); FAIL_ITEMS=$$((FAIL_ITEMS+ITEMS)); FAILED="$$FAILED $$T"; \
	    fi; \
	  done; \
	  echo "================================"; \
	  echo "gen summary ($(DIR)):"; \
	  echo "  Exported definitions: Passed: $$SUCCESS_ITEMS / Failed: $$FAIL_ITEMS / Total: $$TOTAL_ITEMS"; \
	  echo "  Theories:             Passed: $$SUCCESS / Failed: $$FAIL / Skipped: $$SKIP / Total: $$TOTAL"; \
	  if [ -n "$$FAILED" ]; then \
	    for T in $$FAILED; do echo "    - $$T"; done; \
	    exit 1; \
	  fi; \
	else \
	  echo "Usage:"; \
	  echo "  make gen DIR=<dir> Name=<theory>  # build Isabelle + cargo build stage1"; \
	  echo "  make gen DIR=<dir>                # all *_Test.thy under dir"; \
	  exit 1; \
	fi

# opt: optimize every stage1 Rust export into stage2/<theory>/<export>/, then build it
# (no Isabelle build)
# Usage: make opt DIR=<dir> Name=<theory>   (single)
#        make opt DIR=<dir>                 (all theories in dir/stage1/)
opt:
	@_run_opt() { \
	  local dir="$$1" name="$$2"; \
	  local s1_root="$$dir/stage1/$$name"; \
	  local s2_root="$$dir/stage2/$$name"; \
	  local manifests; \
	  local items=0; \
	  local item_label; \
	  if [ -f "$$dir/$$name.thy" ]; then items=$$(perl "$(EXPORT_ITEM_COUNTER)" "$$dir/$$name.thy"); fi; \
	  if [ -f "$$dir/$$name.thy" ] && grep -Eq '^[[:space:]]*export_code[[:space:]]+_[[:space:]]+in[[:space:]]+Rust' "$$dir/$$name.thy"; then \
	    item_label="wildcard export"; \
	  else \
	    item_label="$$items exported definitions"; \
	  fi; \
	  if [ ! -d "$$s1_root" ]; then \
	    echo "ERROR: stage1 not found at $$s1_root — run make gen first"; return 1; \
	  fi; \
	  manifests=$$(find "$$s1_root" -mindepth 2 -maxdepth 2 -type f -name Cargo.toml | sort -V); \
	  if [ -z "$$manifests" ]; then \
	    echo "ERROR: no Rust export found under $$s1_root"; return 1; \
	  fi; \
	  echo ">>> [opt] $$name ($$item_label)  stage1 -> stage2"; \
	  rm -rf "$$s2_root"; \
	  for manifest in $$manifests; do \
	    local s1=$$(dirname "$$manifest"); \
	    local export_name=$$(basename "$$s1"); \
	    local s2="$$s2_root/$$export_name"; \
	    echo ">>> [opt] optimizing Rust export: $$export_name"; \
	    (ulimit -s "$(OPT_STACK_KB)"; \
	      env -u RUSTC_BOOTSTRAP $(CARGO) run -q --manifest-path "$(OPTIMIZE_DIR)/Cargo.toml" --bin cargo-opt -- \
	        "$$s1" --out-dir "$$s2") || return 1; \
	    CARGO="$(CARGO)" python3 "$(CARGO_LOCK_HELPER)" "$$s2/Cargo.toml" \
	      "$(ISABELLE_EXPORTED_LOCK)" || return 1; \
	    echo ">>> [opt] cargo build stage2: $$name/$$export_name"; \
	    env -u RUSTC_BOOTSTRAP RUSTFLAGS="-Awarnings" $(CARGO) build --locked \
	      --manifest-path "$$s2/Cargo.toml" || return 1; \
	  done; \
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
	  SUCCESS=0; FAIL=0; SKIP=0; TOTAL=0; SUCCESS_ITEMS=0; FAIL_ITEMS=0; TOTAL_ITEMS=0; FAILED=""; \
	  for N in $$NAMES; do \
	    ITEMS=0; \
	    if [ -f "$(DIR)/$$N.thy" ]; then ITEMS=$$(perl "$(EXPORT_ITEM_COUNTER)" "$(DIR)/$$N.thy"); fi; \
	    TOTAL=$$((TOTAL+1)); \
	    TOTAL_ITEMS=$$((TOTAL_ITEMS+ITEMS)); \
	    if [ "$$ITEMS" -eq 0 ]; then \
	      SKIP=$$((SKIP+1)); \
	      echo ">>> [opt $$TOTAL] $$N (0 exported definitions) -- skipped"; \
	      continue; \
	    fi; \
	    if _run_opt "$(DIR)" "$$N"; then \
	      SUCCESS=$$((SUCCESS+1)); \
	      SUCCESS_ITEMS=$$((SUCCESS_ITEMS+ITEMS)); \
	    else \
	      FAIL=$$((FAIL+1)); FAIL_ITEMS=$$((FAIL_ITEMS+ITEMS)); FAILED="$$FAILED $$N"; \
	    fi; \
	  done; \
	  echo "================================"; \
	  echo "opt summary ($(DIR)):"; \
	  echo "  Exported definitions: Passed: $$SUCCESS_ITEMS / Failed: $$FAIL_ITEMS / Total: $$TOTAL_ITEMS"; \
	  echo "  Theories:             Passed: $$SUCCESS / Failed: $$FAIL / Skipped: $$SKIP / Total: $$TOTAL"; \
	  if [ -n "$$FAILED" ]; then \
	    for N in $$FAILED; do echo "    - $$N"; done; \
	    exit 1; \
	  fi; \
	else \
	  echo "Usage:"; \
	  echo "  make opt DIR=<dir> Name=<theory>  # optimize stage1 -> stage2 + cargo build"; \
	  echo "  make opt DIR=<dir>                # all theories in dir/stage1/"; \
	  exit 1; \
	fi

# test: full two-phase pipeline — stage1 + cargo build → "stage1 done" →
# stage2/<theory>/<export>/ + cargo build
# Usage: make test DIR=<dir> Name=<theory>   (single)
#        make test DIR=<dir>                 (all *_Test.thy under dir)
test:
	@_run_opt() { \
	  local dir="$$1" name="$$2"; \
	  local s1_root="$$dir/stage1/$$name"; \
	  local s2_root="$$dir/stage2/$$name"; \
	  local manifests; \
	  if [ ! -d "$$s1_root" ]; then \
	    echo "ERROR: stage1 not found at $$s1_root"; return 1; \
	  fi; \
	  manifests=$$(find "$$s1_root" -mindepth 2 -maxdepth 2 -type f -name Cargo.toml | sort -V); \
	  if [ -z "$$manifests" ]; then \
	    echo "ERROR: no Rust export found under $$s1_root"; return 1; \
	  fi; \
	  rm -rf "$$s2_root"; \
	  for manifest in $$manifests; do \
	    local s1=$$(dirname "$$manifest"); \
	    local export_name=$$(basename "$$s1"); \
	    local s2="$$s2_root/$$export_name"; \
	    CARGO="$(CARGO)" python3 "$(CARGO_LOCK_HELPER)" "$$manifest" \
	      "$(ISABELLE_EXPORTED_LOCK)" || return 1; \
	    echo ">>> [test] cargo build stage1: $$name/$$export_name"; \
	    env -u RUSTC_BOOTSTRAP RUSTFLAGS="-Awarnings" $(CARGO) build --locked \
	      --manifest-path "$$manifest" || return 1; \
	    echo ">>> [test] optimizing Rust export: $$export_name"; \
	    (ulimit -s "$(OPT_STACK_KB)"; \
	      env -u RUSTC_BOOTSTRAP $(CARGO) run -q --manifest-path "$(OPTIMIZE_DIR)/Cargo.toml" --bin cargo-opt -- \
	        "$$s1" --out-dir "$$s2") || return 1; \
	    CARGO="$(CARGO)" python3 "$(CARGO_LOCK_HELPER)" "$$s2/Cargo.toml" \
	      "$(ISABELLE_EXPORTED_LOCK)" || return 1; \
	    env -u RUSTC_BOOTSTRAP RUSTFLAGS="-Awarnings" $(CARGO) build --locked \
	      --manifest-path "$$s2/Cargo.toml" || return 1; \
	  done; \
	}; \
	if [ -n "$(DIR)" ] && [ -n "$(Name)" ]; then \
	  ITEMS=$$(perl "$(EXPORT_ITEM_COUNTER)" "$(DIR)/$(Name).thy"); \
	  echo ">>> [test] $(Name) ($$ITEMS exported definitions)"; \
	  $(MAKE) -s build_silent TEST_DIR="$(DIR)" TEST_THEORY="$(Name)" || exit 1; \
	  echo ">>> stage1 done: $(Name)"; \
	  _run_opt "$(DIR)" "$(Name)"; \
	elif [ -n "$(DIR)" ]; then \
	  HOL_FILE="$(HOL_DIR)/$(HOL_GCD_THEORY).thy"; \
	  if [ "$(DIR)" = "$(HOL_DIR)" ]; then \
	    FILES="$$HOL_FILE"; \
	  else \
	    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
	      FILES=$$(git ls-files -- "$(DIR)" | sed -n '/_Test\.thy$$/p' | while IFS= read -r f; do [ -f "$$f" ] && printf '%s\n' "$$f"; done | sort); \
	    else \
	      FILES=$$(find "$(DIR)" -name '*_Test.thy' -type f | sort); \
	    fi; \
	    case "$$HOL_FILE" in "$(DIR)"/*) FILES=$$(printf '%s\n%s\n' "$$FILES" "$$HOL_FILE" | sed '/^$$/d' | sort -u);; esac; \
	  fi; \
	  if [ -z "$$FILES" ]; then \
	    echo "No *_Test.thy found under $(DIR)"; exit 1; \
	  fi; \
	  SUCCESS=0; FAIL=0; SKIP=0; TOTAL=0; SUCCESS_ITEMS=0; FAIL_ITEMS=0; TOTAL_ITEMS=0; FAILED=""; \
	  for f in $$FILES; do \
	    D=$$(dirname "$$f"); T=$${f##*/}; T=$${T%.thy}; \
	    ITEMS=$$(perl "$(EXPORT_ITEM_COUNTER)" "$$f"); \
	    TOTAL=$$((TOTAL+1)); \
	    TOTAL_ITEMS=$$((TOTAL_ITEMS+ITEMS)); \
	    if [ "$$ITEMS" -eq 0 ]; then \
	      SKIP=$$((SKIP+1)); \
	      echo ">>> [test $$TOTAL] $$T (0 exported definitions) -- skipped"; \
	      continue; \
	    fi; \
	    echo ">>> [test $$TOTAL] $$T ($$ITEMS exported definitions)"; \
	    if $(MAKE) -s build_silent TEST_DIR="$$D" TEST_THEORY="$$T"; then \
	      echo ">>> stage1 done: $$T"; \
	      if _run_opt "$$D" "$$T"; then \
	        SUCCESS=$$((SUCCESS+1)); \
	        SUCCESS_ITEMS=$$((SUCCESS_ITEMS+ITEMS)); \
	      else \
	        FAIL=$$((FAIL+1)); FAIL_ITEMS=$$((FAIL_ITEMS+ITEMS)); FAILED="$$FAILED $$T"; \
	      fi; \
	    else \
	      FAIL=$$((FAIL+1)); FAIL_ITEMS=$$((FAIL_ITEMS+ITEMS)); FAILED="$$FAILED $$T"; \
	    fi; \
	  done; \
	  echo "================================"; \
	  echo "test summary ($(DIR)):"; \
	  echo "  Exported definitions: Passed: $$SUCCESS_ITEMS / Failed: $$FAIL_ITEMS / Total: $$TOTAL_ITEMS"; \
	  echo "  Theories:             Passed: $$SUCCESS / Failed: $$FAIL / Skipped: $$SKIP / Total: $$TOTAL"; \
	  if [ -n "$$FAILED" ]; then \
	    for T in $$FAILED; do echo "    - $$T"; done; \
	    exit 1; \
	  fi; \
	else \
	  echo "Usage:"; \
	  echo "  make test DIR=<dir> Name=<theory>  # stage1 -> stage2 + cargo build (single)"; \
	  echo "  make test DIR=<dir>                # all *_Test.thy under dir"; \
	  exit 1; \
	fi

hol-gcd:
	@echo ">>> Building HOL gcd smoke test ($(HOL_GCD_THEORY))..."
	$(MAKE) build TEST_DIR=$(HOL_DIR) TEST_THEORY=$(HOL_GCD_THEORY)

	@OUT_DIR="$(HOL_DIR)/stage1/$(HOL_GCD_THEORY)/export1/src"; \
	if [ ! -d "$$OUT_DIR" ]; then \
	  echo "ERROR: $$OUT_DIR does not exist. Build may have failed."; \
	  exit 1; \
	fi; \
	echo ">>> Replacing main.rs with template..."; \
	cp "$(HOL_DIR)/template/main.rs" "$$OUT_DIR/main.rs"

	@echo ">>> Running cargo..."
	@CARGO_TOML="$(HOL_DIR)/stage1/$(HOL_GCD_THEORY)/export1/Cargo.toml"; \
	if [ ! -f "$$CARGO_TOML" ]; then \
	  echo "ERROR: Cargo.toml not found at $$CARGO_TOML"; \
	  exit 1; \
	fi; \
	CARGO="$(CARGO)" python3 "$(CARGO_LOCK_HELPER)" "$$CARGO_TOML" "$(ISABELLE_EXPORTED_LOCK)" || exit 1; \
	env -u RUSTC_BOOTSTRAP RUSTFLAGS="-Awarnings" $(CARGO) run --locked --manifest-path "$$CARGO_TOML"

# Both stress theories use `export_code _ in Rust`.  The session exports the
# generated crates into persistent stage1 directories, after which this target
# compiles both stages with Cargo.  A clean build is required because an
# up-to-date session would otherwise bypass both wildcard exports.
hol-stress:
	@echo ">>> Building HOL stress export ($(HOL_STRESS_SESSION))..."
	rm -rf $(HOL_DIR)/stage1/Generate $(HOL_DIR)/stage1/Generate_Binary_Nat
	isabelle build -c -v -e -d . $(HOL_STRESS_SESSION)
	@for THEORY in Generate Generate_Binary_Nat; do \
	  ROOT="$(HOL_DIR)/stage1/$$THEORY"; \
	  MANIFEST=$$(find "$$ROOT" -mindepth 2 -maxdepth 2 -type f -name Cargo.toml -printf '%p\n' | sort -V | tail -n 1); \
	  if [ -z "$$MANIFEST" ]; then \
	    echo "ERROR: no exported Cargo.toml under $$ROOT"; \
	    exit 1; \
	  fi; \
	  CARGO="$(CARGO)" python3 "$(CARGO_LOCK_HELPER)" "$$MANIFEST" "$(ISABELLE_EXPORTED_LOCK)" || exit 1; \
	  echo ">>> Cargo-checking HOL stress export: $$THEORY"; \
	  env -u RUSTC_BOOTSTRAP RUSTFLAGS="-Awarnings" $(CARGO) build --locked --manifest-path "$$MANIFEST" || exit 1; \
	  $(MAKE) -s opt DIR="$(HOL_DIR)" Name="$$THEORY" || exit 1; \
	done

# Count physical lines in the current HOL, unit, and FPP generated Rust crates.
kloc:
	@python3 "$(TEST_RUST_METRICS)" kloc

# Count implementation lines for the architecture description.
loc:
	@python3 "$(IMPLEMENTATION_LOC)"

# Aggregate warning types across Stage 1 and Stage 2 generated Rust crates.
# Generate_Binary_Nat is intentionally excluded because it duplicates the
# Generate lint profile.
clippy:
	@CARGO="$(CARGO)" python3 "$(TEST_RUST_METRICS)" clippy \
	  --processes "$(CLIPPY_PROCESSES)" --cargo-jobs "$(CLIPPY_CARGO_JOBS)"

# Generate the pure Rust crates used by the SBPF and X64 case studies, then
# apply the same complete Stage-2 optimizer used by the test-suite workflow.
# REBUILD=1 forces all three Isabelle exports to be refreshed.
clippy-case-studies-prepare:
	@if [ "$(REBUILD)" = "1" ] || [ ! -f "$(SBPF_CLIPPY_PROGRAM_S1)/Cargo.toml" ]; then \
	  $(MAKE) -s build_silent TEST_DIR=tests_sbpf/theory TEST_THEORY=bpf_generator_word_checked_interp; \
	fi
	@if [ "$(REBUILD)" = "1" ] || [ ! -f "$(SBPF_CLIPPY_STEP_S1)/Cargo.toml" ]; then \
	  $(MAKE) -s build_silent TEST_DIR=tests_sbpf/theory TEST_THEORY=bpf_generator_word_checked; \
	fi
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" \
	  RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" python3 "$(X64_RUST_EXPORT)" performance
	@_opt_case_study() { \
	  local label="$$1" source="$$2" output="$$3"; \
	  echo ">>> [clippy] optimizing $$label"; \
	  (ulimit -s "$(OPT_STACK_KB)"; \
	    env -u RUSTC_BOOTSTRAP $(CARGO) run -q --release \
	      --manifest-path "$(OPTIMIZE_DIR)/Cargo.toml" --bin cargo-opt -- \
	      "$$source" --out-dir "$$output") || return 1; \
	  CARGO="$(CARGO)" python3 "$(CARGO_LOCK_HELPER)" "$$output/Cargo.toml" \
	    "$(ISABELLE_EXPORTED_LOCK)" || return 1; \
	}; \
	_opt_case_study SBPF-program "$(SBPF_CLIPPY_PROGRAM_S1)" "$(SBPF_CLIPPY_PROGRAM_S2)" && \
	_opt_case_study SBPF-instruction "$(SBPF_CLIPPY_STEP_S1)" "$(SBPF_CLIPPY_STEP_S2)" && \
	_opt_case_study X64-stepper "$(X64_CLIPPY_STEPPER_S1)" "$(X64_CLIPPY_STEPPER_S2)"

clippy-case-studies: clippy-case-studies-prepare
	@CARGO="$(CARGO)" python3 "$(TEST_RUST_METRICS)" clippy --scope case-studies \
	  --processes "$(CLIPPY_PROCESSES)" --cargo-jobs "$(CLIPPY_CARGO_JOBS)"

clippy-all: clippy-case-studies-prepare
	@CARGO="$(CARGO)" python3 "$(TEST_RUST_METRICS)" clippy --scope all \
	  --processes "$(CLIPPY_PROCESSES)" --cargo-jobs "$(CLIPPY_CARGO_JOBS)"


# sbpf macro validation:
#   shared orchestration lives under tests_sbpf/tests/exec_semantics;
#   language-specific glue and execution live under sbpf_ocaml / sbpf_rust.
SBPF_THEORY_DIR   := tests_sbpf/theory
SBPF_EXEC         := tests_sbpf/tests/exec_semantics
OCAML_VERSION     ?= 4.11.2
RUST_TOOLCHAIN    ?= stable

macro_sbpf:
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" DATA_REBUILD="$(DATA_REBUILD)" OCAML_REBUILD="$(OCAML_REBUILD)" OCAML_VERSION="$(OCAML_VERSION)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" SBPF_THEORY="$(SBPF_THEORY)" SBPF_EXPORT_DIR="$(SBPF_EXPORT_DIR)" python3 $(SBPF_EXEC)/run_macro_sbpf.py

micro_sbpf:
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" OCAML_REBUILD="$(OCAML_REBUILD)" OCAML_VERSION="$(OCAML_VERSION)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" SBPF_THEORY="$(SBPF_THEORY)" SBPF_EXPORT_DIR="$(SBPF_EXPORT_DIR)" SBPF_STEP_JSON="$(SBPF_STEP_JSON)" SBPF_STEP_SEED="$(SBPF_STEP_SEED)" python3 $(SBPF_EXEC)/run_micro_sbpf.py

micro_sbpf_gen:
	@PYTHONDONTWRITEBYTECODE=1 X="$(X)" SBPF_STEP_JSON="$(SBPF_STEP_JSON)" SBPF_STEP_SEED="$(SBPF_STEP_SEED)" python3 $(SBPF_EXEC)/run_micro_sbpf.py gen

# x64 validation:
#   x64_gen builds the random instruction/state data under tests_x64/x64-validation/0-data.
#   x64_test compares the real x64 CPU stepper against the Isabelle-exported OCaml semantics.
X64_VALIDATION      := tests_x64/x64-validation
X64_INS_GEN         := $(X64_VALIDATION)/1-x64-ins-gen
X64_ASSEMBLER       := $(X64_VALIDATION)/2-exec-assembler
X64_MAP_GEN         := $(X64_VALIDATION)/3-x64-map-gen
X64_STEPPER_C       := $(X64_VALIDATION)/4-x64-stepper-c
X64_SEMANTICS       := $(X64_VALIDATION)/5-exec-semantics
X64_RUST_EXPORT     := $(X64_VALIDATION)/run_rust_export.py
X64_RUST_VALIDATION := $(X64_VALIDATION)/run_rust_validation.py
X64_PERFORMANCE     := $(X64_SEMANTICS)/run.py
X64_COUNT           ?= 10000
X64_ISABELLE_THREADS ?= 1
X64_ISABELLE_TIMEOUT ?= 1200
X64_ISABELLE_MAX_HEAP ?= 3200
X64_ISABELLE_JAVA_HEAP ?= 768
X64_OCAML_PACKAGES  ?= yojson
X64_JANSSON_LIBS    ?= $(shell pkg-config --libs jansson 2>/dev/null || echo -ljansson)

# Compile both untouched stage1 Rust exports before any correctness harness is
# allowed to run.  The script builds Rust-only theories, so the fixed OCaml
# baseline is neither regenerated nor rewritten by this gate.
x64-rust-export:
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" X64_ISABELLE_THREADS="$(X64_ISABELLE_THREADS)" X64_ISABELLE_TIMEOUT="$(X64_ISABELLE_TIMEOUT)" X64_ISABELLE_MAX_HEAP="$(X64_ISABELLE_MAX_HEAP)" X64_ISABELLE_JAVA_HEAP="$(X64_ISABELLE_JAVA_HEAP)" python3 $(X64_RUST_EXPORT)

# The hyphenated target is the canonical stage-1 workflow.  Its prerequisite
# guarantees both raw Rust exports compile before random data or OCaml oracle
# output is changed.  The Rust adapter then checks each raw x64_encode result
# against the fixed OCaml encoder output.
x64-gen: x64-rust-export
	@echo ">>> [x64_gen] generating $(X64_COUNT) random x64 instructions"
	@env -u RUSTC_BOOTSTRAP $(CARGO) run --quiet --manifest-path $(X64_INS_GEN)/Cargo.toml -- $(X64_COUNT)
	@echo ">>> [x64_gen] encoding instructions with the existing OCaml x64 encoder"
	@cd "$(X64_ASSEMBLER)" && $(OCAMLC) -o exec x64_encode.ml && ./exec
	@echo ">>> [x64_gen] cross-checking the raw Rust x64 encoder against OCaml"
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" python3 $(X64_RUST_VALIDATION) encoder
	@echo ">>> [x64_gen] generating register and memory maps"
	@env -u RUSTC_BOOTSTRAP $(CARGO) run --quiet --manifest-path $(X64_MAP_GEN)/Cargo.toml

# Stage 2 retains the established CPU and fixed OCaml checks, then observes the
# raw Rust x64_step_test through glue installed only in an _build crate copy.
x64-test: x64-rust-export
	@echo ">>> [x64_test] running cases on the real x64 CPU stepper"
	@cd "$(X64_STEPPER_C)" && $(CC) -O2 -Wall -Wextra -o ptrace_exec ptrace_exec.c $(X64_JANSSON_LIBS) && ./ptrace_exec
	@echo ">>> [x64_test] running Isabelle-exported OCaml semantics and comparing results"
	@cd "$(X64_SEMANTICS)" && $(OCAMLFIND) ocamlc -package $(X64_OCAML_PACKAGES) -linkpkg -c x64_step_test.ml && $(OCAMLFIND) ocamlc -package $(X64_OCAML_PACKAGES) -linkpkg -o exec x64_step_test.cmo exec.ml && ./exec
	@echo ">>> [x64_test] running the raw Rust semantics observation against the CPU"
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" python3 $(X64_RUST_VALIDATION) stepper

# Keep the historical underscore entry points as compatibility aliases while
# documenting and composing the canonical hyphenated targets.
x64_gen: x64-gen

x64_test: x64-test

x64: x64-gen x64-test

# RQ3 performance matrix for the x64 semantics only.  It reuses the fixed
# OCaml stepper export and existing step4 CPU observations; the encoder is
# neither exported nor executed by this target.
x64-performance:
	@PYTHONDONTWRITEBYTECODE=1 RUST_TOOLCHAIN=stable python3 $(X64_PERFORMANCE)

clean:
	@echo "Cleaning temp files and generated output..."
	find . -name "*\.thy~" -exec rm {} \;
	find . -name "*\.cmi"  -exec rm {} \;
	find . -name "*\.cmo"  -exec rm {} \;
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find test -path "*/stage1" -type d -prune -exec rm -rf {} +
	find test -path "*/stage2" -type d -prune -exec rm -rf {} +
	find tests_targeted -path "*/stage1" -type d -prune -exec rm -rf {} +
	find tests_targeted -path "*/stage2" -type d -prune -exec rm -rf {} +
	find tests_targeted -path "*/Rust_Out" -type d -prune -exec rm -rf {} +
	find tests_HOL -path "*/stage1" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	find $(HOL_DIR) -path "*/stage1" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf tests_sbpf/theory/stage1 tests_sbpf/theory/stage2
	rm -rf evaluation/code_generation_quality/export
	rm -rf tests_sbpf/tests/exec_semantics/_build
	rm -rf tests_sbpf/tests/exec_semantics/sbpf_ocaml/_build
	rm -rf tests_sbpf/tests/exec_semantics/sbpf_rust/_build
	rm -f tests_x64/x64-validation/2-exec-assembler/exec tests_x64/x64-validation/2-exec-assembler/*.cmi tests_x64/x64-validation/2-exec-assembler/*.cmo
	rm -f tests_x64/x64-validation/4-x64-stepper-c/ptrace_exec
	rm -f tests_x64/x64-validation/5-exec-semantics/exec tests_x64/x64-validation/5-exec-semantics/*.cmi tests_x64/x64-validation/5-exec-semantics/*.cmo
	# Rust x64 stage1 exports and correctness copies are reproducible build
	# products.  Fixed OCaml files and 0-data vectors are intentionally retained.
	rm -rf tests_x64/theory/stage1/x64EncodeRustGenerator tests_x64/theory/stage1/x64StepRustGenerator
	rm -rf tests_x64/x64-validation/_build
	rm -rf tests_x64/theory/performance
	rm -rf tests_x64/x64-validation/1-x64-ins-gen/target tests_x64/x64-validation/3-x64-map-gen/target
	rm -rf optimize/tests/stage1 optimize/tests/stage2
	rm -rf tests_HOL/Hol_Test/target
	rm -rf $(HOL_DIR)/Hol_Test/target
	rm -rf $(TEST_ROOT_DIR)

help:
	@echo "Available targets:"
	@echo "  open"
	@echo "      Open $(DEFAULT_FILE) in Isabelle/jEdit."
	@echo "  open_test TEST_DIR=<dir> TEST_THEORY=<thy-name>"
	@echo "      Generate test-root/ROOT and open the test theory in Isabelle/jEdit."
	@echo "  x64-rust-export"
	@echo "      Export and compile the untouched Rust x64_encode/x64_step_test crates."
	@echo "  x64-gen / x64-test / x64"
	@echo "      Cross-check raw Rust exports against fixed OCaml output and the x64 CPU."
	@echo "  x64-performance"
	@echo "      Run the seven-implementation RQ3 x64-stepper performance matrix."
	@echo "      Reuses step4.json and does not regenerate or execute the encoder."
	@echo "  build TEST_DIR=<dir> TEST_THEORY=<thy-name>"
	@echo "      Generate test-root/ROOT and run isabelle build (verbose)."
	@echo "      Example: make build TEST_DIR=test/unit/mapping TEST_THEORY=Lists_Test"
	@echo "  code"
	@echo "      Build the project session from ROOT."
	@echo "  gen DIR=<dir> [Name=<theory>]"
	@echo "      Isabelle build -> stage1 + cargo build on stage1."
	@echo "      Example: make gen DIR=test/unit/optimization Name=Copy_Test"
	@echo "      Example: make gen DIR=test/unit/optimization"
	@echo "  opt DIR=<dir> [Name=<theory>]"
	@echo "      Optimize every Rust export into stage2/<theory>/<export>/ and build it."
	@echo "      Does not run an Isabelle build."
	@echo "      Example: make opt DIR=test/unit/optimization Name=Copy_Test"
	@echo "      Example: make opt DIR=test/unit/optimization"
	@echo "  test DIR=<dir> [Name=<theory>]"
	@echo "      Full pipeline: Isabelle -> stage1 -> stage2/<theory>/<export>/ + cargo build."
	@echo "      Example: make test DIR=test/unit/optimization Name=Copy_Test"
	@echo "      Example: make test DIR=test/unit/optimization"
	@echo "  targeted"
	@echo "      Build + cargo run stage1 for all *_Test.thy under tests_targeted."
	@echo "      Example: make targeted"
	@echo "  hol-gcd"
	@echo "      Build and run the HOL gcd smoke test. Default: HOL_GCD_THEORY=$(HOL_GCD_THEORY)."
	@echo "  hol-stress"
	@echo "      Run the Rust HOL-Codegenerator pressure test session."
	@echo "  kloc"
	@echo "      Count generated Rust LOC for HOL, unit, and FPP at both stages."
	@echo "  loc"
	@echo "      Count Stage-1, Stage-2, and RustLight LOC, excluding comments and tests."
	@echo "  clippy [CLIPPY_PROCESSES=4] [CLIPPY_CARGO_JOBS=1]"
	@echo "      Aggregate warning types from the HOL, Unit, and FPP Stage 1/2 crates."
	@echo "  clippy-case-studies [REBUILD=1]"
	@echo "      Generate, optimize, and audit the SBPF program/instruction and X64"
	@echo "      stepper crates. REBUILD=1 refreshes the Isabelle exports first."
	@echo "  clippy-all [REBUILD=1]"
	@echo "      Audit both the three test suites and the three case-study workloads."
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
	@echo "  x64_gen [X64_COUNT=10000]"
	@echo "      Generate x64 validation data under tests_x64/x64-validation/0-data"
	@echo "      without running the Isabelle export or the final comparison."
	@echo "  x64_test"
	@echo "      Run the real x64 CPU stepper, then compare it with the OCaml semantics."
	@echo "  x64"
	@echo "      Run x64_gen followed by x64_test."
	@echo "  clean"
	@echo "      Remove temp files and generated output under test and legacy suites."
