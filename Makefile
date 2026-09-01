# Convenience targets. Everything here is also runnable by hand — see CONTRIBUTING.md.
# CI runs the same checks, so a green `make check` means a green pipeline.

.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: test
test: ## Run both reference servers' tests
	cd mcp/vault-mcp && pytest tests/ -v
	cd mcp/sqlite-mcp && pytest tests/ -v

.PHONY: links
links: ## Verify every relative Markdown link resolves
	python3 .github/scripts/check-links.py

.PHONY: shell
shell: ## Syntax-check every shell script and verify its executable bit is committed
	@fail=0; while IFS= read -r -d '' f; do bash -n "$$f" || fail=1; done \
		< <(find . -name '*.sh' -not -path './.git/*' -print0); \
	bad=$$(git ls-files -s -- '*.sh' | awk '$$1 != "100755" { print $$4 }'); \
	if [ -n "$$bad" ]; then \
		echo "Not executable in git (fix: git update-index --chmod=+x <file>):"; \
		echo "$$bad"; fail=1; \
	fi; \
	exit $$fail

.PHONY: vault
vault: ## Assert the vault template passes the rules it teaches
	python3 .github/scripts/check-vault.py

.PHONY: check
check: test links shell vault ## Run everything CI runs

.PHONY: demo
demo: ## Lay the stack down in a throwaway location and show what it produces
	@rm -rf /tmp/mem-stack-demo
	@./setup/bootstrap.sh --vault /tmp/mem-stack-demo/vault --claude-dir /tmp/mem-stack-demo/claude
