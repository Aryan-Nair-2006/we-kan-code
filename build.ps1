Remove-Item -Recurse -Force .aws-sam -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .sam_build_context -ErrorAction SilentlyContinue
Write-Host "Preparing SAM build context..."
python scripts/prepare_sam_build.py
Write-Host "Validating SAM template..."
sam validate -t infrastructure/template.yaml
Write-Host "Building SAM application..."
sam build -t infrastructure/template.yaml
