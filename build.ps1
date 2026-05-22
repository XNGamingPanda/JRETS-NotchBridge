$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m PyInstaller `
  --noconfirm `
  --clean `
  --noconsole `
  --name "JRETS_Controller" `
  --add-data "vehicles.json;." `
  main.py
