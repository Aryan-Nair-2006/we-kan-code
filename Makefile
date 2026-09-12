.PHONY: build test clean

build:
	@echo "Preparing SAM build context..."
	python scripts/prepare_sam_build.py
	@echo "Validating SAM template..."
	sam validate -t infrastructure/template.yaml
	@echo "Building SAM application..."
	sam build -t infrastructure/template.yaml

test:
	python -m pytest -q

clean:
	Remove-Item -Recurse -Force .aws-sam -ErrorAction SilentlyContinue
	Remove-Item -Recurse -Force .sam_build_context -ErrorAction SilentlyContinue
