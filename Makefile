.PHONY: open build build_silent code run test optimize_test optimize_copy optimize_all copy_inference targeted targeted_run clean help

#### Configuration ####

DEFAULT_FILE := $(CURDIR)/Rust_Setup.thy
SESSION      := Test
ROOT_FILE    := ROOT
HOL_TEST_THEORY ?= Hol_Test_Integer

CARGO                  ?= cargo
ISABELLE_EXPORTED_LOCK := $(CURDIR)/scripts/isabelle-exported.Cargo.lock
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

# run all Cargo projects under TEST_DIR/Rust_Out/TEST_THEORY/export*/
run:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make run TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  echo "Example: make run TEST_DIR=tests_targeted TEST_THEORY=List_Test"; \
	  exit 1; \
	fi
	@OUT_DIR="$(TEST_DIR)/Rust_Out/$(TEST_THEORY)"; \
	if [ ! -d "$$OUT_DIR" ]; then \
	  echo "No such output dir: $$OUT_DIR"; \
	  exit 1; \
	fi; \
	MANIFESTS=$$(find "$$OUT_DIR" -maxdepth 2 -type f -name Cargo.toml | sort); \
	if [ -z "$$MANIFESTS" ]; then \
	  echo "No Cargo.toml under $$OUT_DIR"; \
	  exit 1; \
	fi; \
	for m in $$MANIFESTS; do \
	  echo "=== cargo run: $$m ==="; \
	  package_dir=$$(dirname "$$m"); \
	  if [ ! -f "$$package_dir/Cargo.lock" ] && [ -f "$(ISABELLE_EXPORTED_LOCK)" ]; then \
	    cp "$(ISABELLE_EXPORTED_LOCK)" "$$package_dir/Cargo.lock"; \
	  fi; \
	  RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" $(CARGO) run --locked --manifest-path "$$m" || exit 1; \
	  echo ""; \
	done

# build (verbose) + run for a single test
test:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make test TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  echo "Example: make test TEST_DIR=tests_targeted TEST_THEORY=List_Test"; \
	  exit 1; \
	fi
	@$(MAKE) build TEST_DIR="$(TEST_DIR)" TEST_THEORY="$(TEST_THEORY)"
	@$(MAKE) run   TEST_DIR="$(TEST_DIR)" TEST_THEORY="$(TEST_THEORY)"

optimize_test:
	@./scripts/run-optimization-tests.sh "$(or $(STAGE),copy)"

optimize_copy:
	@$(MAKE) optimize_test STAGE=copy

optimize_all:
	@$(MAKE) optimize_test STAGE=all

copy_inference: optimize_copy

# run all *_Test.thy in tests_targeted (quiet build)
targeted:
	@TD="tests_targeted"; \
	FILES=$$(find "$$TD" -name '*_Test.thy' -type f | sort); \
	if [ -z "$$FILES" ]; then \
	  echo "No *_Test.thy under $$TD"; \
	  exit 0; \
	fi; \
	SUCCESS=0; FAIL=0; TOTAL=0; FAILED_TESTS=""; \
	for f in $$FILES; do \
	  D=$$(dirname "$$f"); T=$${f##*/}; T=$${T%.thy}; \
	  TOTAL=$$((TOTAL+1)); \
	  echo ">>> [$$TOTAL] $$D/$$T"; \
	  if $(MAKE) -s build_silent TEST_DIR="$$D" TEST_THEORY="$$T" && \
	     $(MAKE) -s run TEST_DIR="$$D" TEST_THEORY="$$T"; then \
	    SUCCESS=$$((SUCCESS+1)); \
	  else \
	    FAIL=$$((FAIL+1)); \
	    FAILED_TESTS="$$FAILED_TESTS $$D/$$T"; \
	  fi; \
	done; \
	echo "================================"; \
	echo "Targeted summary:"; \
	echo "  Passed: $$SUCCESS"; \
	echo "  Failed: $$FAIL"; \
	echo "  Total:  $$TOTAL"; \
	if [ -n "$$FAILED_TESTS" ]; then \
	  echo "  Failed tests:"; \
	  for T in $$FAILED_TESTS; do echo "    - $$T"; done; \
	fi

# run all already-built Cargo projects under tests_targeted/Rust_Out (no Isabelle rebuild)
targeted_run:
	@TD="tests_targeted"; \
	OUT_DIRS=$$(find "$$TD" -path '*/Rust_Out' -type d | sort); \
	if [ -z "$$OUT_DIRS" ]; then \
	  echo "No Rust_Out directories under $$TD"; \
	  exit 1; \
	fi; \
	SUCCESS=0; FAIL=0; TOTAL=0; FAILED_TESTS=""; \
	for OUT_DIR in $$OUT_DIRS; do \
	  D=$$(dirname "$$OUT_DIR"); \
	  THEORIES=$$(ls -d "$$OUT_DIR"/*/ 2>/dev/null | xargs -r -n1 basename | sort); \
	  for T in $$THEORIES; do \
	    TOTAL=$$((TOTAL+1)); \
	    echo ">>> [$$TOTAL] $$D/$$T"; \
	    if $(MAKE) -s run TEST_DIR="$$D" TEST_THEORY="$$T"; then \
	      SUCCESS=$$((SUCCESS+1)); \
	    else \
	      FAIL=$$((FAIL+1)); \
	      FAILED_TESTS="$$FAILED_TESTS $$D/$$T"; \
	    fi; \
	  done; \
	done; \
	echo "================================"; \
	echo "Targeted_run summary:"; \
	echo "  Passed: $$SUCCESS"; \
	echo "  Failed: $$FAIL"; \
	echo "  Total:  $$TOTAL"; \
	if [ -n "$$FAILED_TESTS" ]; then \
	  echo "  Failed tests:"; \
	  for T in $$FAILED_TESTS; do echo "    - $$T"; done; \
	fi


hol:
	@echo ">>> Building $(HOL_TEST_THEORY)..."
	$(MAKE) build TEST_DIR=tests_HOL TEST_THEORY=$(HOL_TEST_THEORY)

	@OUT_DIR="tests_HOL/Rust_Out/$(HOL_TEST_THEORY)/export1/src"; \
	if [ ! -d "$$OUT_DIR" ]; then \
	  echo "ERROR: $$OUT_DIR does not exist. Build may have failed."; \
	  exit 1; \
	fi; \
	echo ">>> Replacing main.rs with template..."; \
	cp tests_HOL/template/main.rs "$$OUT_DIR/main.rs"

	@echo ">>> Running cargo..."
	@CARGO_TOML="tests_HOL/Rust_Out/$(HOL_TEST_THEORY)/export1/Cargo.toml"; \
	if [ ! -f "$$CARGO_TOML" ]; then \
	  echo "ERROR: Cargo.toml not found at $$CARGO_TOML"; \
	  exit 1; \
	fi; \
	package_dir=$$(dirname "$$CARGO_TOML"); \
	if [ ! -f "$$package_dir/Cargo.lock" ] && [ -f "$(ISABELLE_EXPORTED_LOCK)" ]; then \
	  cp "$(ISABELLE_EXPORTED_LOCK)" "$$package_dir/Cargo.lock"; \
	fi; \
	RUSTC_BOOTSTRAP=1 RUSTFLAGS="-Awarnings" cargo run --locked --manifest-path "$$CARGO_TOML"


clean:
	@echo "Cleaning temp files and Rust_Out..."
	find . -name "*\.thy~" -exec rm {} \;
	find . -name "*\.cmi"  -exec rm {} \;
	find . -name "*\.cmo"  -exec rm {} \;
	rm -rf tests_targeted/Rust_Out
	find tests_targeted -path "*/Rust_Out" -type d -prune -exec rm -rf {} +
	rm -rf optimize/tests/out
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
	@echo "      Run all Cargo projects under TEST_DIR/Rust_Out/TEST_THEORY/export*/."
	@echo "      Example: make run TEST_DIR=tests_targeted/lists TEST_THEORY=List_Test"
	@echo "  test TEST_DIR=<dir> TEST_THEORY=<thy-name>"
	@echo "      Build Isabelle session (with -v) and then run all exported Cargo projects."
	@echo "      Example: make test TEST_DIR=tests_targeted TEST_THEORY=List_Test"
	@echo "  targeted"
	@echo "      Recursively run all *_Test.thy under tests_targeted with quiet Isabelle build."
	@echo "      Example: make targeted"
	@echo "  optimize_test STAGE=<copy|borrow|copy-borrow|all>"
	@echo "      Run staged optimizer tests. Default: STAGE=copy."
	@echo "      Example: make optimize_test STAGE=copy"
	@echo "  optimize_copy"
	@echo "      Run only copy optimization tests."
	@echo "  optimize_all"
	@echo "      Run all configured optimization stages."
	@echo "  copy_inference"
	@echo "      Alias for optimize_copy."
	@echo "  hol"
	@echo "      Build and run the HOL smoke test. Default: HOL_TEST_THEORY=$(HOL_TEST_THEORY)."
	@echo "  clean"
	@echo "      Remove temporary and build artefacts, including tests_targeted/Rust_Out."
