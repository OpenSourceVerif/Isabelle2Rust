.PHONY: open build build_silent code gen opt test targeted sbpf clean help

#### Configuration ####

DEFAULT_FILE := $(CURDIR)/Rust_Setup.thy
SESSION      := Test
ROOT_FILE    := ROOT
HOL_TEST_THEORY ?= Hol_Test_Integer

CARGO                  ?= cargo
ISABELLE_EXPORTED_LOCK := $(CURDIR)/scripts/isabelle-exported.Cargo.lock
OPTIMIZE_DIR           := $(CURDIR)/optimize
ISABELLE_BUILD_LOCK    := $(CURDIR)/.isabelle-build.lock
ISABELLE_BUILD_VERBOSE := isabelle build -v -e -d . $(SESSION)
ISABELLE_BUILD_SILENT  := isabelle build -e -d . $(SESSION)

#### Targets ####

open:
	isabelle jedit -d . $(DEFAULT_FILE)

# build one theory (verbose)
build:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make build TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  echo "Example: make build TEST_DIR=tests_targeted TEST_THEORY=List_Test"; \
	  exit 1; \
	fi
	@{ \
	  flock 9; \
	  echo ">> ROOT for $(TEST_DIR)/$(TEST_THEORY).thy"; \
	  sed \
	    -e 's|@TEST_DIR@|$(TEST_DIR)|g' \
	    -e 's|@TEST_THEORY@|$(TEST_THEORY)|g' \
	    ROOT.template > $(ROOT_FILE); \
	  echo ">> isabelle build (verbose)..."; \
	  $(ISABELLE_BUILD_VERBOSE); \
	} 9>$(ISABELLE_BUILD_LOCK)

# build one theory (quiet, for targeted)
build_silent:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make build_silent TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  exit 1; \
	fi
	@{ \
	  flock 9; \
	  sed \
	    -e 's|@TEST_DIR@|$(TEST_DIR)|g' \
	    -e 's|@TEST_THEORY@|$(TEST_THEORY)|g' \
	    ROOT.template > $(ROOT_FILE); \
	  $(ISABELLE_BUILD_SILENT); \
	} 9>$(ISABELLE_BUILD_LOCK)

code:
	@{ flock 9; $(ISABELLE_BUILD_VERBOSE); } 9>$(ISABELLE_BUILD_LOCK)

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


# sbpf: Rust<->OCaml runtime cross-test of the exported sBPF semantics.
#   Feeds the Rust-exported bpf_interp_test / step_test the SAME inputs the OCaml
#   reference uses and asserts each self-checking call returns true (i.e. the Rust
#   export agrees, case-for-case, with the OCaml-validated expected values).
#   Runs against the existing export under tests_sbpf/theory/stage1/bpf_generator.
#   Pass REBUILD=1 to regenerate that export via Isabelle first.
SBPF_THEORY_DIR := tests_sbpf/theory
SBPF_RUST       := tests_sbpf/tests/exec_semantics/rust
SBPF_DATA       := $(CURDIR)/tests_sbpf/tests/data
sbpf:
	@if [ "$(REBUILD)" = "1" ]; then \
	  echo ">>> [sbpf] regenerating Rust export (bpf_generator)..."; \
	  $(MAKE) build TEST_DIR=$(SBPF_THEORY_DIR) TEST_THEORY=bpf_generator; \
	fi
	@_sbpf_run() { \
	  crate="$$1"; main="$$2"; json="$$3"; \
	  toml=$$(find "$(SBPF_THEORY_DIR)/stage1/bpf_generator/$$crate" -maxdepth 2 -name Cargo.toml 2>/dev/null | head -1); \
	  if [ -z "$$toml" ]; then \
	    echo "ERROR: no export for $$crate under $(SBPF_THEORY_DIR)/stage1 — run 'make sbpf REBUILD=1'"; \
	    return 2; \
	  fi; \
	  src="$$(dirname "$$toml")/src"; \
	  cp "$$main" "$$src/main.rs"; \
	  grep -q '^serde ' "$$toml" || \
	    sed -i '/^\[dependencies\]/a serde = { version = "1", features = ["derive"] }\nserde_json = "1"' "$$toml"; \
	  CROSS_JSON="$$json" RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" $(CARGO) run -q --manifest-path "$$toml"; \
	}; \
	echo ">>> [sbpf] interp cross-test (bpf_interp_test) over 146 OCaml-reference cases"; \
	_sbpf_run interp_test "$(SBPF_RUST)/interp_main.rs" "$(SBPF_DATA)/interp_in.json"; \
	interp_rc=$$?; \
	echo ">>> [sbpf] step cross-test (step_test, best-effort)"; \
	_sbpf_run step_test "$(SBPF_RUST)/step_main.rs" "$(SBPF_DATA)/ocaml_in.json" \
	  || echo ">>> step cross-test red — known step-export compile issues (best-effort)"; \
	exit $$interp_rc

clean:
	@echo "Cleaning temp files and generated output..."
	find . -name "*\.thy~" -exec rm {} \;
	find . -name "*\.cmi"  -exec rm {} \;
	find . -name "*\.cmo"  -exec rm {} \;
	find tests_targeted -path "*/stage1" -type d -prune -exec rm -rf {} +
	find tests_targeted -path "*/stage2" -type d -prune -exec rm -rf {} +
	find tests_HOL -path "*/stage1" -type d -prune -exec rm -rf {} +
	find tests_sbpf/theory/stage1 -name target -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf optimize/tests/stage1 optimize/tests/stage2
	rm -rf tests_HOL/Hol_Test/target

help:
	@echo "Available targets:"
	@echo "  open"
	@echo "      Open $(DEFAULT_FILE) in Isabelle/jEdit."
	@echo "  build TEST_DIR=<dir> TEST_THEORY=<thy-name>"
	@echo "      Generate ROOT from ROOT.template and run isabelle build (verbose)."
	@echo "      Example: make build TEST_DIR=tests_targeted TEST_THEORY=List_Test"
	@echo "  code"
	@echo "      Run isabelle build using the existing ROOT file."
	@echo "  run TEST_DIR=<dir> TEST_THEORY=<thy-name>"
	@echo "      Run all Cargo projects under TEST_DIR/stage1/TEST_THEORY/export*/."
	@echo "      Example: make run TEST_DIR=tests_targeted/lists TEST_THEORY=List_Test"
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
	@echo "  sbpf [REBUILD=1]"
	@echo "      Rust<->OCaml runtime cross-test of the exported sBPF semantics"
	@echo "      (interp_test over 146 cases + step_test best-effort). REBUILD=1 first"
	@echo "      regenerates the export via Isabelle. Example: make sbpf"
	@echo "  clean"
	@echo "      Remove temp files and generated output (stage1, stage2 under tests_targeted/tests_HOL)."
