.DEFAULT_GOAL := open

.PHONY: open open_test build build_silent _build _build_silent code gen opt test \
        hol-gcd hol-stress loc kloc rq1-timings \
        rq3-clippy rq3-sbpf rq3-x64 \
        macro_sbpf micro_sbpf micro_sbpf_gen \
        x64 x64-rust-export x64-gen x64-test \
        clean help

#### Configuration ####

DEFAULT_FILE := $(CURDIR)/translate/Rust_Base_Setup.thy
PROJECT_SESSION := Rust
TEST_SESSION    := Rust
TEST_ROOT_DIR   := test-root
TEST_ROOT_FILE  := $(TEST_ROOT_DIR)/ROOT
TEST_TIMEOUT    ?= 300
TEST_EXTRA_SESSIONS ?= Word_Lib
HOL_DIR         ?= test/HOL_Codegenerator
HOL_GCD_THEORY ?= Code_Test_Rust
HOL_STRESS_SESSION ?= Rust-HOL-Codegenerator_Test

ISABELLE               ?= isabelle
RUST_TOOLCHAIN         ?= 1.94.0
CARGO                  ?= cargo +$(RUST_TOOLCHAIN)
ISABELLE_CARGO         ?= $(HOME)/.cargo/bin/cargo
OCAMLC                 ?= ocamlc
OCAMLFIND              ?= ocamlfind
ISABELLE_EXPORTED_LOCK := $(CURDIR)/scripts/isabelle-exported.Cargo.lock
CARGO_LOCK_HELPER      := $(CURDIR)/scripts/ensure-cargo-lock.py
OPTIMIZE_DIR           := $(CURDIR)/optimize
OPT_STACK_KB            ?= 65536
EXPORT_ITEM_COUNTER    := $(CURDIR)/scripts/count-rust-export-items.pl
RQ1_GENERATED_LOC      := $(CURDIR)/evaluation/scripts/rq1/count-generated-loc.py
RQ1_TIMINGS            := $(CURDIR)/evaluation/scripts/rq1/run-timings.py
RQ3_CLIPPY             := $(CURDIR)/evaluation/scripts/rq3/run-clippy.py
RQ3_SBPF               := $(CURDIR)/evaluation/scripts/rq3/run-sbpf.py
RQ3_X64                := $(CURDIR)/evaluation/scripts/rq3/run-x64.py
IMPLEMENTATION_LOC     := $(CURDIR)/evaluation/scripts/count-implementation-loc.py
CLIPPY_PROCESSES       ?= 4
CLIPPY_CARGO_JOBS      ?= 1
RUN_WITH_LOCK          := python3 "$(CURDIR)/scripts/with-lock.py"
RUN_WITH_STACK         := sh "$(CURDIR)/scripts/with-stack.sh" $(OPT_STACK_KB)
ISABELLE_BUILD_LOCK    := $(CURDIR)/.isabelle-build.lock
ISABELLE_PROJECT_BUILD := "$(ISABELLE)" build -v -e -d . $(PROJECT_SESSION)
ISABELLE_TEST_VERBOSE  := "$(ISABELLE)" build -v -e -d $(TEST_ROOT_DIR) $(TEST_SESSION)
ISABELLE_TEST_SILENT   := "$(ISABELLE)" build -e -d $(TEST_ROOT_DIR) $(TEST_SESSION)

export ISABELLE_CARGO
unexport RUSTC_BOOTSTRAP

WRITE_TEST_ROOT = mkdir -p $(TEST_ROOT_DIR); { printf '%s\n' 'session $(TEST_SESSION) in ".." = Main +' '  description "$(TEST_THEORY) test session"' '  options [timeout = $(TEST_TIMEOUT)]' '  sessions' '    "HOL-Library"' $(foreach session,$(TEST_EXTRA_SESSIONS),'    "$(session)"') '  directories' '    "translate"' '    "$(TEST_DIR)"' '  theories [document = false]' '    "translate/Rust_Base_Setup"' '    "translate/Rust_Integer_BigInt_Layer"' '    "translate/Rust_BigInt_Setup"' '    "translate/Rust_Checked128_Setup"' '    "translate/Rust_BigInt_WordU128_Setup"' '    "translate/Rust_Checked128_WordU128_Setup"' '    "$(TEST_DIR)/$(TEST_THEORY)"' '  export_files (in "$(TEST_DIR)/stage1/$(TEST_THEORY)") [2]' '    "*:**.rs"' '    "*:**.toml"' '    "*:**.ocaml"'; } > $(TEST_ROOT_FILE)

#### Code generation ####

# `-R` uses a generated requirements heap; let jEdit build or refresh it.
open:
	"$(ISABELLE)" jedit -d . -R $(PROJECT_SESSION) $(DEFAULT_FILE)

open_test:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make open_test TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  echo "Example: make open_test TEST_DIR=test/unit/types TEST_THEORY=Tuple_Test"; \
	  exit 1; \
	fi
	@$(WRITE_TEST_ROOT)
	"$(ISABELLE)" jedit -d $(TEST_ROOT_DIR) -R $(TEST_SESSION) "$(TEST_DIR)/$(TEST_THEORY).thy"

# build one theory (verbose)
build:
	+@$(RUN_WITH_LOCK) "$(ISABELLE_BUILD_LOCK)" $(MAKE) --no-print-directory _build

_build:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make build TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  echo "Example: make build TEST_DIR=test/unit/mapping TEST_THEORY=Lists_Test"; \
	  exit 1; \
	fi
	@{ \
	  rm -rf "$(TEST_DIR)/stage1/$(TEST_THEORY)"; \
	  echo ">> $(TEST_ROOT_FILE) for $(TEST_DIR)/$(TEST_THEORY).thy"; \
	  $(WRITE_TEST_ROOT); \
	  echo ">> isabelle build (verbose)..."; \
	  $(ISABELLE_TEST_VERBOSE); \
	}

# build one theory (quiet, for gen/test)
build_silent:
	+@$(RUN_WITH_LOCK) "$(ISABELLE_BUILD_LOCK)" $(MAKE) --no-print-directory _build_silent

_build_silent:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make build_silent TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  exit 1; \
	fi
	@{ \
	  rm -rf "$(TEST_DIR)/stage1/$(TEST_THEORY)"; \
	  $(WRITE_TEST_ROOT); \
	  $(ISABELLE_TEST_SILENT); \
	}

code:
	@$(RUN_WITH_LOCK) "$(ISABELLE_BUILD_LOCK)" $(ISABELLE_PROJECT_BUILD)

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
	    $(RUN_WITH_STACK) env -u RUSTC_BOOTSTRAP $(CARGO) run -q --manifest-path "$(OPTIMIZE_DIR)/Cargo.toml" --bin cargo-opt -- \
	        "$$s1" --out-dir "$$s2" || return 1; \
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
	  NAMES=$$(find "$$S1BASE" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort); \
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
	    $(RUN_WITH_STACK) env -u RUSTC_BOOTSTRAP $(CARGO) run -q --manifest-path "$(OPTIMIZE_DIR)/Cargo.toml" --bin cargo-opt -- \
	        "$$s1" --out-dir "$$s2" || return 1; \
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
	"$(ISABELLE)" build -c -v -e -d . $(HOL_STRESS_SESSION)
	@for THEORY in Generate Generate_Binary_Nat; do \
	  ROOT="$(HOL_DIR)/stage1/$$THEORY"; \
	  MANIFEST=$$(find "$$ROOT" -mindepth 2 -maxdepth 2 -type f -name Cargo.toml -print | sort -V | tail -n 1); \
	  if [ -z "$$MANIFEST" ]; then \
	    echo "ERROR: no exported Cargo.toml under $$ROOT"; \
	    exit 1; \
	  fi; \
	  CARGO="$(CARGO)" python3 "$(CARGO_LOCK_HELPER)" "$$MANIFEST" "$(ISABELLE_EXPORTED_LOCK)" || exit 1; \
	  echo ">>> Cargo-checking HOL stress export: $$THEORY"; \
	  env -u RUSTC_BOOTSTRAP RUSTFLAGS="-Awarnings" $(CARGO) build --locked --manifest-path "$$MANIFEST" || exit 1; \
	  $(MAKE) -s opt DIR="$(HOL_DIR)" Name="$$THEORY" || exit 1; \
	done

#### Evaluation ####

# Count physical lines in the current HOL, unit, and FPP generated Rust crates.
kloc:
	@python3 "$(RQ1_GENERATED_LOC)"

# Three independent phase-only runs; excludes proof checking and Cargo builds.
rq1-timings:
	@python3 "$(RQ1_TIMINGS)"

# Count implementation lines for the architecture description.
loc:
	@python3 "$(IMPLEMENTATION_LOC)"

rq3-clippy:
	@python3 "$(RQ3_CLIPPY)" --scope all \
	  --processes "$(CLIPPY_PROCESSES)" --cargo-jobs "$(CLIPPY_CARGO_JOBS)"

rq3-sbpf:
	@PYTHONDONTWRITEBYTECODE=1 python3 "$(RQ3_SBPF)"

rq3-x64:
	@PYTHONDONTWRITEBYTECODE=1 python3 "$(RQ3_X64)"

#### Validation ####

# sbpf macro validation:
#   shared orchestration lives under test/sbpf/tests/exec_semantics;
#   language-specific glue and execution live under sbpf_ocaml / sbpf_rust.
SBPF_EXEC         := test/sbpf/tests/exec_semantics
OCAML_VERSION     ?= 4.11.2

macro_sbpf:
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" DATA_REBUILD="$(DATA_REBUILD)" OCAML_REBUILD="$(OCAML_REBUILD)" OCAML_VERSION="$(OCAML_VERSION)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" SBPF_THEORY="$(SBPF_THEORY)" SBPF_EXPORT_DIR="$(SBPF_EXPORT_DIR)" python3 $(SBPF_EXEC)/run_macro_sbpf.py

micro_sbpf:
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" X="$(X)" REBUILD="$(REBUILD)" OCAML_REBUILD="$(OCAML_REBUILD)" OCAML_VERSION="$(OCAML_VERSION)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" SBPF_THEORY="$(SBPF_THEORY)" SBPF_EXPORT_DIR="$(SBPF_EXPORT_DIR)" SBPF_STEP_JSON="$(SBPF_STEP_JSON)" SBPF_STEP_SEED="$(SBPF_STEP_SEED)" python3 $(SBPF_EXEC)/run_micro_sbpf.py

micro_sbpf_gen:
	@PYTHONDONTWRITEBYTECODE=1 X="$(X)" SBPF_STEP_JSON="$(SBPF_STEP_JSON)" SBPF_STEP_SEED="$(SBPF_STEP_SEED)" python3 $(SBPF_EXEC)/run_micro_sbpf.py gen

# x64 validation:
#   x64-gen builds random instruction/state data under test/x64/x64-validation/0-data.
#   x64-test compares the real x64 CPU stepper against the Isabelle-exported OCaml semantics.
X64_VALIDATION      := test/x64/x64-validation
X64_INS_GEN         := $(X64_VALIDATION)/1-x64-ins-gen
X64_ASSEMBLER       := $(X64_VALIDATION)/2-exec-assembler
X64_MAP_GEN         := $(X64_VALIDATION)/3-x64-map-gen
X64_STEPPER_C       := $(X64_VALIDATION)/4-x64-stepper-c
X64_SEMANTICS       := $(X64_VALIDATION)/5-exec-semantics
X64_RUST_EXPORT     := $(X64_VALIDATION)/run_rust_export.py
X64_RUST_VALIDATION := $(X64_VALIDATION)/run_rust_validation.py
X64_RUN             := $(X64_VALIDATION)/run_x64.py
X                   ?= 10000
SEED                ?= 5984326
X64_ISABELLE_THREADS ?= 1
X64_ISABELLE_TIMEOUT ?= 1200
X64_ISABELLE_MAX_HEAP ?= 3200
X64_ISABELLE_JAVA_HEAP ?= 768
X64_OCAML_PACKAGES  ?= yojson
X64_JANSSON_LIBS    ?= $(shell pkg-config --libs jansson 2>/dev/null || echo -ljansson)

# Generate or reuse both Rust stages and compile their untouched exports before
# any correctness harness is allowed to run.
x64-rust-export:
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" X64_ISABELLE_THREADS="$(X64_ISABELLE_THREADS)" X64_ISABELLE_TIMEOUT="$(X64_ISABELLE_TIMEOUT)" X64_ISABELLE_MAX_HEAP="$(X64_ISABELLE_MAX_HEAP)" X64_ISABELLE_JAVA_HEAP="$(X64_ISABELLE_JAVA_HEAP)" python3 $(X64_RUST_EXPORT) stage2

# Stage 1 compiles the raw Rust exports, then uses the Rust encoder to prepare
# the machine-code inputs consumed by the stepper validation.
x64-gen: x64-rust-export
	@echo ">>> [x64-gen] generating $(X) random x64 instructions with seed $(SEED)"
	@env -u RUSTC_BOOTSTRAP $(CARGO) run --quiet --manifest-path $(X64_INS_GEN)/Cargo.toml -- $(X) $(SEED)
	@echo ">>> [x64-gen] encoding instructions with the Rust x64 encoder"
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" python3 $(X64_RUST_VALIDATION) encode
	@echo ">>> [x64-gen] generating register and memory maps"
	@env -u RUSTC_BOOTSTRAP $(CARGO) run --quiet --manifest-path $(X64_MAP_GEN)/Cargo.toml -- $(SEED)

# Run the native, OCaml, and Stage-1 Rust steppers on the shared corpus.
x64-test: x64-rust-export
	@echo ">>> [x64-test] running cases on the real x64 CPU stepper"
	@cd "$(X64_STEPPER_C)" && $(CC) -O2 -Wall -Wextra -o ptrace_exec ptrace_exec.c $(X64_JANSSON_LIBS) && ./ptrace_exec
	@echo ">>> [x64-test] running Isabelle-exported OCaml semantics and comparing results"
	@cd "$(X64_SEMANTICS)" && $(OCAMLFIND) ocamlc -package $(X64_OCAML_PACKAGES) -linkpkg -c x64_step_test.ml && $(OCAMLFIND) ocamlc -package $(X64_OCAML_PACKAGES) -linkpkg -o exec x64_step_test.cmo exec.ml && ./exec
	@echo ">>> [x64-test] running the raw Rust semantics observation against the CPU"
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" python3 $(X64_RUST_VALIDATION) stepper

# Run the Stage-2 stepper on exactly the same corpus.
x64-stage2-test: x64-rust-export
	@echo ">>> [x64-test] running the Stage-2 Rust semantics observation against the CPU"
	@PYTHONDONTWRITEBYTECODE=1 CARGO="$(CARGO)" REBUILD="$(REBUILD)" RUST_TOOLCHAIN="$(RUST_TOOLCHAIN)" X64_RUST_EXPORT_ROOT="$(CURDIR)/test/x64/theory/stage2/x64_generator_bigint" X64_RUST_BUILD_DIR="$(CURDIR)/test/x64/x64-validation/_build/stage2-full" python3 $(X64_RUST_VALIDATION) stepper

x64:
	+@PYTHONDONTWRITEBYTECODE=1 MAKE="$(MAKE)" python3 $(X64_RUN)

#### Maintenance ####

clean:
	@echo "Cleaning temp files and generated output..."
	find . -type f \( -name '*.thy~' -o -name '*.cmi' -o -name '*.cmo' \) -delete
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find test -type d \( -name stage1 -o -name stage2 \) -prune -exec rm -rf {} +
	rm -rf evaluation/.work
	rm -rf $(SBPF_EXEC)/_build $(SBPF_EXEC)/sbpf_ocaml/_build $(SBPF_EXEC)/sbpf_rust/_build
	rm -f $(X64_ASSEMBLER)/exec $(X64_STEPPER_C)/ptrace_exec $(X64_SEMANTICS)/exec
	# x64 stage1/stage2 exports and correctness copies are reproducible build
	# products.  Fixed 0-data vectors are intentionally retained.
	rm -rf test/x64/theory/stage1 test/x64/theory/stage2
	rm -rf $(X64_VALIDATION)/_build
	rm -rf test/x64/theory/performance
	rm -rf $(X64_INS_GEN)/target $(X64_MAP_GEN)/target
	rm -rf optimize/tests/stage1 optimize/tests/stage2
	rm -rf $(HOL_DIR)/Hol_Test/target
	rm -rf $(TEST_ROOT_DIR)

help:
	@echo "Core:"
	@echo "  open                              Open the Rust setup in Isabelle/jEdit"
	@echo "  open_test TEST_DIR=<dir> TEST_THEORY=<thy>"
	@echo "                                    Open one test theory in Isabelle/jEdit"
	@echo "  code                              Build the project session"
	@echo "  build TEST_DIR=<dir> TEST_THEORY=<thy>"
	@echo "                                    Export one theory (verbose)"
	@echo "  gen DIR=<dir> [Name=<thy>]        Export and compile Stage 1"
	@echo "  opt DIR=<dir> [Name=<thy>]        Optimize and compile existing Stage 1"
	@echo "  test DIR=<dir> [Name=<thy>]       Run the complete Stage-1/Stage-2 pipeline"
	@echo "  hol-gcd                           Run the HOL gcd smoke test"
	@echo "  hol-stress                        Run the broad HOL code-generator export"
	@echo ""
	@echo "Validation:"
	@echo "  macro_sbpf [REBUILD=1]            Run program-level SBPF validation"
	@echo "  micro_sbpf [REBUILD=1]            Run instruction-level SBPF validation"
	@echo "  micro_sbpf_gen [X=10000]          Generate SBPF instruction test data"
	@echo "  x64-rust-export [REBUILD=1]       Export and compile both x64 Rust stages"
	@echo "  x64-gen [X=10000] [SEED=<n>]      Generate and cross-check x64 inputs"
	@echo "  x64-test                          Compare OCaml and Stage 1 with the CPU"
	@echo "  x64-stage2-test                   Compare Stage 2 with the CPU"
	@echo "  x64 [X=10000] [SEED=<n>]          Run complete x64 differential validation"
	@echo ""
	@echo "Evaluation:"
	@echo "  loc / kloc / rq1-timings"
	@echo "  rq3-clippy                        Run the RQ3 Clippy comparison"
	@echo "  rq3-sbpf                          Run the RQ3 SBPF performance experiment"
	@echo "  rq3-x64                           Run the RQ3 x64 performance experiment"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean                             Remove generated output"
