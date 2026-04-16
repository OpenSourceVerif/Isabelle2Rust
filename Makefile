.PHONY: open build build_silent code run test targeted clean help

#### Configuration ####

DEFAULT_FILE := $(CURDIR)/Rust_Setup.thy
SESSION      := Test
ROOT_FILE    := ROOT

CARGO                  ?= cargo
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
	@echo ">> ROOT for $(TEST_DIR)/$(TEST_THEORY).thy"
	@sed \
	  -e 's|@TEST_DIR@|$(TEST_DIR)|g' \
	  -e 's|@TEST_THEORY@|$(TEST_THEORY)|g' \
	  ROOT.template > $(ROOT_FILE)
	@echo ">> isabelle build (verbose)..."
	@$(ISABELLE_BUILD_VERBOSE)

# build one theory (quiet, for targeted)
build_silent:
	@if [ -z "$(TEST_DIR)" ] || [ -z "$(TEST_THEORY)" ]; then \
	  echo "Usage: make build_silent TEST_DIR=<dir> TEST_THEORY=<thy>"; \
	  exit 1; \
	fi
	@sed \
	  -e 's|@TEST_DIR@|$(TEST_DIR)|g' \
	  -e 's|@TEST_THEORY@|$(TEST_THEORY)|g' \
	  ROOT.template > $(ROOT_FILE)
	@$(ISABELLE_BUILD_SILENT)

code:
	@$(ISABELLE_BUILD_VERBOSE)

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
	  RUSTFLAGS="-Awarnings" $(CARGO) run --manifest-path "$$m" || exit 1; \
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

# run all *_Test.thy in tests_targeted (quiet build)
targeted:
	@TD="tests_targeted"; \
	FILES=$$(ls "$$TD"/*_Test.thy 2>/dev/null || true); \
	if [ -z "$$FILES" ]; then \
	  echo "No *_Test.thy under $$TD"; \
	  exit 0; \
	fi; \
	SUCCESS=0; FAIL=0; TOTAL=0; \
	for f in $$FILES; do \
	  T=$${f##*/}; T=$${T%.thy}; \
	  TOTAL=$$((TOTAL+1)); \
	  echo ">>> [$$TOTAL] $$T"; \
	  if $(MAKE) -s build_silent TEST_DIR="$$TD" TEST_THEORY="$$T" && \
	     $(MAKE) -s run TEST_DIR="$$TD" TEST_THEORY="$$T"; then \
	    SUCCESS=$$((SUCCESS+1)); \
	  else \
	    FAIL=$$((FAIL+1)); \
	  fi; \
	done; \
	echo "================================"; \
	echo "Targeted summary:"; \
	echo "  Passed: $$SUCCESS"; \
	echo "  Failed: $$FAIL"; \
	echo "  Total:  $$TOTAL"


hol:
	@echo ">>> Building Hol_Test..."
	$(MAKE) build TEST_DIR=tests_HOL TEST_THEORY=Hol_Test

	@OUT_DIR="tests_HOL/Rust_Out/Hol_Test/export1/src"; \
	if [ ! -d "$$OUT_DIR" ]; then \
	  echo "ERROR: $$OUT_DIR does not exist. Build may have failed."; \
	  exit 1; \
	fi; \
	echo ">>> Replacing main.rs with template..."; \
	cp tests_HOL/template/main.rs "$$OUT_DIR/main.rs"

	@echo ">>> Running cargo..."
	@CARGO_TOML="tests_HOL/Rust_Out/Hol_Test/export1/Cargo.toml"; \
	if [ ! -f "$$CARGO_TOML" ]; then \
	  echo "ERROR: Cargo.toml not found at $$CARGO_TOML"; \
	  exit 1; \
	fi; \
	RUSTFLAGS="-Awarnings" cargo run --manifest-path "$$CARGO_TOML"


clean:
	@echo "Cleaning temp files and Rust_Out..."
	find . -name "*\.thy~" -exec rm {} \;
	find . -name "*\.cmi"  -exec rm {} \;
	find . -name "*\.cmo"  -exec rm {} \;
	rm -rf tests_targeted/Rust_Out
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
	@echo "  run TEST_THEORY=<thy-name> RUST_OUT=<rust-out-root>"
	@echo "      Run all Cargo projects under RUST_OUT/TEST_THEORY/export*/."
	@echo "      Example: make run TEST_THEORY=List_Test RUST_OUT=tests_targeted/Rust_Out"
	@echo "  test TEST_DIR=<dir> TEST_THEORY=<thy-name>"
	@echo "      Build Isabelle session (with -v) and then run all exported Cargo projects."
	@echo "      Example: make test TEST_DIR=tests_targeted TEST_THEORY=List_Test"
	@echo "  targeted"
	@echo "      Run all *_Test.thy under tests_targeted with quiet Isabelle build."
	@echo "      Example: make targeted"
	@echo "  clean"
	@echo "      Remove temporary and build artefacts, including tests_targeted/Rust_Out."