PYTHON ?= python3
UVICORN ?= uvicorn
NPM ?= npm

.PHONY: run-api run-ui lint-ui build-ui sync-extension-assets build-extension

run-api:
	$(UVICORN) src.server:app --reload --port 8000

run-ui:
	cd manga-overlay && $(NPM) run dev

run-ui-test:
	cd manga-overlay && VITE_APP_MODE=test $(NPM) run dev

lint-ui:
	cd manga-overlay && $(NPM) run lint

build-ui:
	cd manga-overlay && $(NPM) run build

sync-extension-assets:
	@set -e; \
	cd manga-overlay; \
	js_file=$$(ls -t dist/assets/index-*.js | head -n 1); \
	css_file=$$(ls -t dist/assets/index-*.css | head -n 1); \
	cp "$$js_file" ../manga-extension/overlay.js; \
	cp "$$css_file" ../manga-extension/overlay.css; \
	mkdir -p ../manga-extension/fonts; \
	cp -f public/fonts/* ../manga-extension/fonts/; \
	echo "Synced $$js_file -> manga-extension/overlay.js"; \
	echo "Synced $$css_file -> manga-extension/overlay.css"; \
	echo "Synced public/fonts/* -> manga-extension/fonts/"

build-extension: build-ui sync-extension-assets
