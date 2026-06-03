.PHONY: setup-tests setup-test clean-test-configs

setup-tests:
	../scripts/setup-optimize-test-projects.sh

setup-test:
	@if [ -z "$(PROJECT)" ]; then \
		echo "usage: make setup-test PROJECT=tests/fixtures/Your_Project"; \
		exit 1; \
	fi
	../scripts/setup-optimize-test-projects.sh "$(PROJECT)"

clean-test-configs:
	../scripts/setup-optimize-test-projects.sh --clear-all
