param(
  [switch]$SkipOllama,
  [switch]$SkipMuseTalk,
  [switch]$WithIndexTTS,
  [switch]$WithCosyVoice
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
$env:KOUBO_MODEL_CACHE = (Join-Path $Root "models\cache")
$env:HF_HOME = (Join-Path $env:KOUBO_MODEL_CACHE "huggingface")
$env:HF_HUB_CACHE = (Join-Path $env:HF_HOME "hub")
$env:TORCH_HOME = (Join-Path $env:KOUBO_MODEL_CACHE "torch")
$env:XDG_CACHE_HOME = (Join-Path $env:KOUBO_MODEL_CACHE "xdg")
$env:CACHED_PATH_CACHE_ROOT = (Join-Path $env:KOUBO_MODEL_CACHE "cached_path")
$env:MODELSCOPE_CACHE = (Join-Path $env:KOUBO_MODEL_CACHE "modelscope")
$env:OLLAMA_MODELS = (Join-Path $Root "models\ollama")
$env:UV_CACHE_DIR = (Join-Path $Root "models\cache\uv")
$env:TEMP = (Join-Path $Root "models\cache\tmp")
$env:TMP = $env:TEMP

New-Item -ItemType Directory -Force -Path $env:KOUBO_MODEL_CACHE, $env:UV_CACHE_DIR, $env:TEMP | Out-Null

function Run($exe, [string[]]$argv) {
  Write-Host ">> $exe $($argv -join ' ')"
  & $exe @argv
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $exe $($argv -join ' ')"
  }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  throw "uv was not found. Install uv first, then rerun this script."
}

Write-Host "Creating shared model environment: .venv-models"
Run "uv" @("venv", ".venv-models", "--python", "3.11")
$ModelPython = Join-Path $Root ".venv-models\Scripts\python.exe"
Run "uv" @("pip", "install", "--python", $ModelPython, "-U", "pip", "setuptools", "wheel")
Run "uv" @("pip", "install", "--python", $ModelPython, "torch==2.8.0+cu128", "torchaudio==2.8.0+cu128", "--extra-index-url", "https://download.pytorch.org/whl/cu128")
Run "uv" @("pip", "install", "--python", $ModelPython, "funasr", "modelscope", "f5-tts", "socksio", "pysocks")

if (-not $SkipOllama) {
  if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
      throw "Ollama is not installed and winget was not found."
    }
    Run "winget" @("install", "--id", "Ollama.Ollama", "-e", "--accept-source-agreements", "--accept-package-agreements")
  }
  Run "ollama" @("pull", "qwen2.5:7b")
}

if (-not $SkipMuseTalk) {
  if (-not (Test-Path "models")) {
    New-Item -ItemType Directory -Path "models" | Out-Null
  }
  if (-not (Test-Path "models\MuseTalk")) {
    Run "git" @("clone", "https://github.com/TMElyralab/MuseTalk.git", "models\MuseTalk")
  }
  Run "uv" @("venv", ".venv-musetalk", "--python", "3.10")
  $MusePython = Join-Path $Root ".venv-musetalk\Scripts\python.exe"
  Run "uv" @("pip", "install", "--python", $MusePython, "-U", "pip", "setuptools", "wheel")
  Run "uv" @("pip", "install", "--python", $MusePython, "torch==2.0.1", "torchvision==0.15.2", "torchaudio==2.0.2", "--index-url", "https://download.pytorch.org/whl/cu118")
  Run "uv" @("pip", "install", "--python", $MusePython, "-r", "models\MuseTalk\requirements.txt")
  Run "uv" @("pip", "install", "--python", $MusePython, "socksio", "pysocks")
  Run "uv" @("pip", "install", "--python", $MusePython, "-U", "openmim")
  Run ".venv-musetalk\Scripts\mim.exe" @("install", "mmengine")
  Run ".venv-musetalk\Scripts\mim.exe" @("install", "mmcv==2.0.1")
  Run ".venv-musetalk\Scripts\mim.exe" @("install", "mmdet==3.1.0")
  Run $MusePython @("-m", "pip", "install", "chumpy==0.70", "--no-build-isolation")
  Run ".venv-musetalk\Scripts\mim.exe" @("install", "mmpose==1.1.0")
  Run "uv" @("pip", "install", "--python", $MusePython, "numpy==1.23.5")
  Run "uv" @("pip", "install", "--python", $MusePython, "huggingface_hub[hf_xet]")
  $HfCli = Join-Path $Root ".venv-musetalk\Scripts\huggingface-cli.exe"
  Push-Location "models\MuseTalk"
  try {
    Run $HfCli @("download", "TMElyralab/MuseTalk", "--local-dir", "models")
    Run $HfCli @("download", "stabilityai/sd-vae-ft-mse", "--local-dir", "models\sd-vae", "--include", "config.json", "diffusion_pytorch_model.bin")
    Run $HfCli @("download", "openai/whisper-tiny", "--local-dir", "models\whisper", "--include", "config.json", "pytorch_model.bin", "preprocessor_config.json")
    Run $HfCli @("download", "yzd-v/DWPose", "--local-dir", "models\dwpose", "--include", "dw-ll_ucoco_384.pth")
    Run $HfCli @("download", "ByteDance/LatentSync", "--local-dir", "models\syncnet", "--include", "latentsync_syncnet.pt")
    Run $HfCli @("download", "ManyOtherFunctions/face-parse-bisent", "--local-dir", "models\face-parse-bisent", "--include", "79999_iter.pth", "resnet18-5c106cde.pth")
  } finally {
    Pop-Location
  }
}

if ($WithIndexTTS) {
  if (-not (Test-Path "models")) {
    New-Item -ItemType Directory -Path "models" | Out-Null
  }
  if (-not (Test-Path "models\IndexTTS")) {
    $env:GIT_LFS_SKIP_SMUDGE = "1"
    try {
      Run "git" @("clone", "https://github.com/index-tts/index-tts.git", "models\IndexTTS")
    } finally {
      Remove-Item Env:\GIT_LFS_SKIP_SMUDGE -ErrorAction SilentlyContinue
    }
  }
  Push-Location "models\IndexTTS"
  try {
    Run "git" @("config", "filter.lfs.smudge", "git-lfs smudge --skip -- %f")
    Run "git" @("config", "filter.lfs.process", "git-lfs filter-process --skip")
    Run "git" @("checkout", "-f", "HEAD")
    Run "uv" @("sync")
    Run "uv" @("tool", "run", "--from", "huggingface-hub[hf_xet]", "hf", "download", "IndexTeam/IndexTTS-2", "--local-dir", "checkpoints")
  } finally {
    Pop-Location
  }
}

if ($WithCosyVoice) {
  if (-not (Test-Path "models")) {
    New-Item -ItemType Directory -Path "models" | Out-Null
  }
  if (-not (Test-Path "models\CosyVoice")) {
    Run "git" @("clone", "--recursive", "https://github.com/FunAudioLLM/CosyVoice.git", "models\CosyVoice")
  }
  Push-Location "models\CosyVoice"
  try {
    Run "git" @("submodule", "update", "--init", "--recursive")
    Run "uv" @("venv", ".venv", "--python", "3.10")
    $CosyPython = Join-Path (Resolve-Path ".") ".venv\Scripts\python.exe"
    Run "uv" @("pip", "install", "--python", $CosyPython, "-U", "pip", "setuptools", "wheel")
    Run "uv" @("pip", "install", "--python", $CosyPython, "-r", "requirements.txt")
    Run "uv" @("pip", "install", "--python", $CosyPython, "huggingface_hub[hf_xet]", "modelscope")
    Run $CosyPython @("-c", "from modelscope import snapshot_download; snapshot_download('iic/CosyVoice2-0.5B', local_dir='pretrained_models/CosyVoice2-0.5B')")
  } finally {
    Pop-Location
  }
}

Write-Host "Local model setup finished."
