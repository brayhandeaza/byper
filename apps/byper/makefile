.PHONY: build

build:
	@rm -rf ./build
	@rm -rf ./byper.egg-info

	@echo "Installing byper globally"
	@pip install . --no-cache-dir

	@echo "Installing byper in the test project"
	@bash -c "source /Users/brayhandeaza/Documents/dev/python/turbo-demo/apps/test/Packages/bin/activate && pip install . --no-cache-dir"

	@echo "Successfully installed byper"
