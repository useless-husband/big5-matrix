# big5-matrix. Every target works with whatever runtimes are installed; missing ones are skipped.
PY ?= python3
RUSTPATH := $(shell [ -d /opt/homebrew/opt/rustup/bin ] && echo /opt/homebrew/opt/rustup/bin:)
export PATH := $(RUSTPATH)$(PATH)

.PHONY: all build run analyze report check test verify lint bench serve clean

all: run analyze report      ## re-run everything and refresh the documents

build:                       ## build every adapter whose runtime is installed
	$(PY) -m big5matrix build

run:                         ## run every available adapter over all cases, update data/
	$(PY) -m big5matrix run

analyze:                     ## compute report/summary.json from data/
	$(PY) -m big5matrix analyze

report:                      ## refresh the generated numbers and tables in the documents
	$(PY) -m big5matrix report

check:                       ## drift check: re-run what is available and compare with data/
	$(PY) -m big5matrix check

test:                        ## unit and integration tests
	$(PY) -m unittest discover -s tests -t .

verify:                      ## check the report's surprising claims a second way
	$(PY) tools/verify_claims.py

lint:                        ## syntax and style checks for every language in the repository
	$(PY) -m compileall -q big5matrix tools tests
	@if command -v go >/dev/null; then cd adapters/go && test -z "$$(gofmt -l .)" && go vet ./...; fi
	@if command -v cargo >/dev/null; then cd adapters/rust && cargo fmt --check && cargo clippy -q --release -j4 --target-dir ../../build/rust -- -D warnings; fi
	@if command -v node >/dev/null; then for f in adapters/node/adapter.mjs adapters/browser/adapter.mjs docs/assets/*.js tests/js/*.mjs; do node --check $$f || exit 1; done; fi
	@if command -v php >/dev/null; then php -l adapters/php/adapter.php >/dev/null; fi
	@if command -v ruby >/dev/null; then ruby -wc adapters/ruby/adapter.rb >/dev/null; fi
	@if command -v perl >/dev/null; then perl -wc adapters/perl/adapter.pl 2>/dev/null; fi
	cc -fsyntax-only -Wall -Wextra -Werror adapters/iconv/adapter.c
	@if [ -n "$$(pkg-config --cflags icu-uc 2>/dev/null)" ] || [ -d /opt/homebrew/opt/icu4c ]; then \
	  cc -fsyntax-only -Wall -Wextra -Werror $$(pkg-config --cflags icu-uc 2>/dev/null || echo -I/opt/homebrew/opt/icu4c/include) adapters/icu/adapter.c; fi
	@if command -v dotnet >/dev/null; then dotnet build adapters/dotnet -c Release -o build/dotnet -nologo -v q -warnaserror >/dev/null; fi

bench:                       ## time a full run and analysis on this machine
	@/usr/bin/time -p $(PY) -m big5matrix run >/dev/null
	@/usr/bin/time -p $(PY) -m big5matrix analyze >/dev/null

serve:                       ## serve the site on 127.0.0.1 (the URL is printed)
	$(PY) tools/serve.py

clean:
	rm -rf build adapters/dotnet/obj adapters/rust/target
