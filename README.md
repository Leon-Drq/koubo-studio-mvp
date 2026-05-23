# Koubo Studio MVP

Koubo Studio 是一个本地部署的电商口播数字人生成平台 MVP。它把“对标链接/文案 -> AI 改写 -> 语音克隆 -> 真人视频口型同步 -> 字幕封面 -> 发布清单”串成一个可运行的工作流。

默认可以先用 fallback 跑通流程；有 NVIDIA GPU 后，可以接入本仓库已适配的本地开源模型。

## 功能

- FastAPI 后端和静态前端操作台
- 对标视频下载：`yt-dlp`
- 音视频处理：`ffmpeg` / `ffprobe`
- 文案提取：FunASR / SenseVoiceSmall，也支持自定义 ASR 命令或 API
- 文案改写：Ollama / Qwen2.5，也支持 OpenAI-compatible API
- 语音克隆：F5-TTS、IndexTTS2、CosyVoice，可在页面选择
- 口型同步：LatentSync 高质量、MuseTalk 标准、快速预览 fallback
- 任务状态、产物、字幕、封面、发布清单持久化到 `data/jobs`

## 模型栈

当前本地模型适配如下：

| 环节 | 默认/推荐模型 | 说明 |
| --- | --- | --- |
| ASR | `iic/SenseVoiceSmall` via FunASR | 从视频音频提取中文口播文案 |
| LLM | `qwen2.5:7b` via Ollama | 本地文案改写；也可选择“采用当前文案” |
| TTS | F5-TTS `F5TTS_v1_Base` | 零样本语音克隆，支持声音样本 |
| TTS | IndexTTS2 `IndexTeam/IndexTTS-2` | 另一种本地语音克隆模型，页面可选 |
| TTS | CosyVoice2 `iic/CosyVoice2-0.5B` | 多语种零样本/跨语种声音克隆，页面可选 |
| Lip-sync | LatentSync 1.5 | 高质量口型同步，适合 12GB 显存机器 |
| Lip-sync | MuseTalk 1.5 | 标准口型同步 fallback |

注意：模型权重不会提交到 GitHub。安装脚本会把模型和缓存放到本地 `models/`、`checkpoints/`、`.venv-*` 等目录，这些目录已被 `.gitignore` 排除。

## 环境要求

基础运行：

- Windows 10/11、macOS 或 Linux
- Python 3.11
- `ffmpeg`
- `git`

推荐本地模型运行：

- Windows 11
- NVIDIA GPU，建议 12GB+ VRAM
- NVIDIA 驱动支持 CUDA 12.x
- `uv`
- `git-lfs`
- Ollama

## 资源占用估算

下面是本项目当前适配模型的大致资源需求。实际占用会随驱动、PyTorch/CUDA 版本、输入视频长度、分辨率、batch size、缓存状态变化。

| 使用方式 | 建议显存 | 建议内存 | 建议可用磁盘 | 说明 |
| --- | ---: | ---: | ---: | --- |
| 只跑 Web + fallback | 不需要 GPU | 4-8GB | 1-2GB | 可打开页面、创建任务、用静音/快速预览 fallback 跑通流程 |
| ASR + LLM 文案 | 6-8GB | 16GB | 10-20GB | SenseVoiceSmall + Ollama `qwen2.5:7b`；Ollama 约占 5-6GB 显存 |
| F5-TTS | 8GB+ | 16GB | 15-25GB | 语音克隆；首次运行会下载 HF/ModelScope 依赖模型 |
| IndexTTS2 | 10-12GB+ | 24-32GB | 15-25GB | `IndexTeam/IndexTTS-2` 权重较大，加载阶段也吃系统内存 |
| CosyVoice2 | 8-12GB+ | 16-24GB | 10-20GB | `iic/CosyVoice2-0.5B`，支持 cross-lingual/zero-shot |
| MuseTalk 1.5 | 8-12GB+ | 16GB | 15-25GB | 标准口型同步，`MUSETALK_BATCH_SIZE` 越大越吃显存 |
| LatentSync 1.5 | 12GB+ | 24GB | 15-25GB | 高质量口型同步；12GB 显存机器建议关闭其他 GPU 程序 |
| 全量本地模型 | 12GB+ | 32GB | 80-120GB | 包含多个虚拟环境、PyTorch CUDA wheel、模型权重和缓存 |

推荐配置：

- 入门体验：16GB 内存，20GB 可用磁盘，不要求 GPU，使用 fallback/快速预览。
- 本地语音克隆：RTX 3060 12GB 或以上，24GB 内存，50GB 可用磁盘。
- 完整本地数字人流程：RTX 4080 12GB 或以上，32GB 内存，100GB 可用磁盘。

Windows 可用：

```powershell
winget install Gyan.FFmpeg
winget install Git.Git
winget install GitHub.GitLFS
winget install astral-sh.uv
winget install Ollama.Ollama
```

## 快速启动

### 1. 克隆项目

```powershell
git clone git@github.com:Leon-Drq/koubo-studio-mvp.git
cd koubo-studio-mvp
```

没有 SSH key 时也可以用 HTTPS：

```powershell
git clone https://github.com/Leon-Drq/koubo-studio-mvp.git
cd koubo-studio-mvp
```

### 2. 创建主服务环境

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### 3. 启动 Web 服务

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

开发时如果需要自动重载，可用：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

正式使用本地模型时建议不要加 `--reload`，因为模型缓存和虚拟环境文件变化会触发服务重启。

## 安装本地模型

仓库提供了 Windows PowerShell 安装脚本：

```powershell
.\scripts\setup_local_models.ps1
```

这一步会下载多个 PyTorch CUDA wheel、模型仓库和模型权重。建议先确认 D 盘或项目所在磁盘至少有 80GB 可用空间；如果同时安装 IndexTTS2 和 CosyVoice，建议预留 100GB 以上。

它会安装：

- `.venv-models`：FunASR、F5-TTS、共享模型环境
- Ollama `qwen2.5:7b`
- `.venv-musetalk` 和 `models/MuseTalk`
- MuseTalk 相关模型权重

如果只想安装 IndexTTS2：

```powershell
.\scripts\setup_local_models.ps1 -SkipOllama -SkipMuseTalk -WithIndexTTS
```

如果只想安装 CosyVoice：

```powershell
.\scripts\setup_local_models.ps1 -SkipOllama -SkipMuseTalk -WithCosyVoice
```

如果全部安装：

```powershell
.\scripts\setup_local_models.ps1 -WithIndexTTS -WithCosyVoice
```

脚本会尽量把 `uv`、Hugging Face、ModelScope、Torch 缓存放到 `models/cache`，减少 C 盘压力。

## `.env` 关键配置

复制 `.env.example` 后，按需调整：

```env
DEFAULT_ASR_PROVIDER=local
DEFAULT_LLM_PROVIDER=local
DEFAULT_TTS_PROVIDER=local
DEFAULT_LIPSYNC_PROVIDER=latentsync
DEFAULT_TTS_MODEL=f5

ASR_COMMAND=.venv-models/Scripts/python.exe scripts/adapters/funasr_asr.py --input {audio} --output {text}
LLM_COMMAND=python scripts/adapters/ollama_rewrite.py --input {input} --output {output}
F5_TTS_COMMAND=.venv-models/Scripts/python.exe scripts/adapters/f5_tts.py --input {input} --voice {voice} --voice-sample {voice_sample} --output {audio}
INDEXTTS_COMMAND=models/IndexTTS/.venv/Scripts/python.exe scripts/adapters/indextts2_tts.py --input {input} --voice-sample {voice_sample} --output {audio}
COSYVOICE_COMMAND=models/CosyVoice/.venv/Scripts/python.exe scripts/adapters/cosyvoice_tts.py --input {input} --voice-sample {voice_sample} --output {audio}
LATENTSYNC_COMMAND=.venv-latentsync/Scripts/python.exe scripts/adapters/latentsync_lipsync.py --video {video} --audio {audio} --output {output}
LIPSYNC_COMMAND=.venv-musetalk/Scripts/python.exe scripts/adapters/musetalk_lipsync.py --video {video} --audio {audio} --output {output}
```

页面上可以单独选择：

- 文案提取：自动 / 本地模型 / API
- AI 改写：自动 / 本地模型 / API / 采用当前文案
- 语音模型：F5-TTS / IndexTTS2 / CosyVoice
- 语音生成：自动 / 本地模型 / API
- 成片质量：自动 / 快速预览 / MuseTalk 标准 / LatentSync 高质量 / API 成片

CosyVoice 默认使用 `COSYVOICE_MODE=cross_lingual`，只需要上传声音样本即可生成克隆音色。如果要使用 zero-shot 模式，可设置：

```env
COSYVOICE_MODE=zero_shot
COSYVOICE_PROMPT_TEXT=声音样本中说的原文
COSYVOICE_FP16=true
```

## 显存说明

本项目会在语音克隆和口型同步前自动执行：

```text
ollama stop qwen2.5:7b
```

这是为了释放 Ollama 占用的 GPU 显存，避免 IndexTTS2、CosyVoice、LatentSync、MuseTalk 因显存不足失败。可在 `.env` 关闭：

```env
AUTO_UNLOAD_OLLAMA_BEFORE_MEDIA=false
```

如果显存仍不足：

- 选择“成片质量 -> 快速预览”
- 降低 `MUSETALK_BATCH_SIZE`
- 关闭浏览器、飞书、剪辑软件等占 GPU 的程序
- 使用“AI 改写 -> 采用当前文案”，减少 Ollama 使用

## API Provider

每个生成步骤都可以走 API。API provider 适合先用云服务跑通线上 SaaS，再逐步替换成本地 GPU。

### ASR API

`ASR_API_URL` 是 multipart endpoint，默认字段名为 `file`，返回值可以是 `{"text": "..."}` 或纯文本。

```env
ASR_API_URL=https://api.example.com/v1/audio/transcriptions
ASR_API_KEY=sk-...
ASR_API_MODEL=whisper-1
ASR_API_FILE_FIELD=file
```

### LLM API

`LLM_API_URL` 使用 OpenAI-compatible `/chat/completions` 格式。

```env
LLM_API_URL=https://api.example.com/v1/chat/completions
LLM_API_KEY=sk-...
LLM_API_MODEL=gpt-4o-mini
LLM_API_TEMPERATURE=0.7
```

### TTS API

JSON 模式适合 OpenAI-compatible `/audio/speech` 一类接口，接口可以直接返回音频二进制，也可以返回 `audio_url` 或 `audio_base64`。

```env
TTS_API_URL=https://api.example.com/v1/audio/speech
TTS_API_KEY=sk-...
TTS_API_MODEL=tts-1
TTS_API_VOICE=alloy
TTS_API_MODE=json
```

第三方语音克隆接口如需上传参考声音样本：

```env
TTS_API_MODE=multipart
TTS_API_TEXT_FIELD=input
TTS_API_VOICE_FIELD=voice
TTS_API_FILE_FIELD=voice_sample
```

### Lip-sync API

`LIPSYNC_API_URL` 接收真人静默视频和口播音频，返回视频二进制、`video_url` 或 `video_base64`。

```env
LIPSYNC_API_URL=https://api.example.com/v1/lipsync
LIPSYNC_API_KEY=sk-...
LIPSYNC_API_VIDEO_FIELD=video
LIPSYNC_API_AUDIO_FIELD=audio
```

## 常用命令

健康检查：

```powershell
curl.exe --noproxy "*" http://127.0.0.1:8000/api/health
```

烟测：

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

查看 GPU 占用：

```powershell
nvidia-smi
```

停止 Ollama 模型释放显存：

```powershell
ollama stop qwen2.5:7b
```

## API

- `GET /`：前端页面
- `GET /api/health`：服务和 provider 状态
- `POST /api/jobs`：创建生成任务，multipart 表单
- `GET /api/jobs`：任务列表
- `GET /api/jobs/{id}`：任务详情
- `GET /api/files/{job_id}/{inputs|outputs}/{filename}`：下载产物
- `POST /api/extract-script`：从链接提取口播文案
- `POST /api/rewrite-script`：改写口播文案

## 目录结构

```text
app/
  main.py              FastAPI 入口
  jobs.py              任务流水线
  services/            ASR/LLM/TTS/Lip-sync/媒体处理适配
  static/              前端页面
scripts/
  adapters/            本地模型 wrapper
  setup_local_models.ps1
data/
  jobs/                运行产物，本地生成，不提交
models/                本地模型仓库和权重，不提交
```

## 合规边界

- 对标视频、声音样本、真人形象必须获得授权。
- 语音克隆和数字人口型同步需要获得被克隆人的明确授权。
- 抖音、视频号、小红书、快手自动发布建议优先接官方开放平台。
- Wav2Lip 等部分开源项目存在商业使用限制，商业化前需单独确认许可证。
- 本项目是 MVP，不包含内容审核、版权检测和平台风控绕过能力。

## AI 部署指令

下面这段是给 AI coding agent / 运维 agent 看的。目标是让 AI 在一台新的 Windows 机器上，从零部署出和本仓库同等能力的本地 Koubo Studio。

### 目标

部署一个可本地访问的 Koubo Studio：

- Web 地址：`http://127.0.0.1:8000`
- 支持上传真人视频、声音样本、对标链接/文案
- 支持 F5-TTS、IndexTTS2、CosyVoice 三种语音模型选项
- 支持 LatentSync 高质量口型同步和 MuseTalk fallback
- 支持 Ollama/Qwen 本地文案改写
- 不把 `.env`、模型权重、任务产物、cookies、缓存提交到 Git

### 机器前提

先确认：

- Windows 11
- NVIDIA GPU，建议 12GB+ VRAM
- 32GB 内存更稳
- 项目所在磁盘至少 100GB 可用空间
- PowerShell 可运行脚本
- 网络可访问 GitHub、Hugging Face、ModelScope、PyPI、PyTorch wheel 源

如果没有 GPU，也要部署 Web 和 fallback，但不要承诺本地模型高质量生成一定可用。

### 安装系统依赖

在管理员或普通 PowerShell 中执行：

```powershell
winget install Git.Git
winget install GitHub.GitLFS
winget install Gyan.FFmpeg
winget install astral-sh.uv
winget install Ollama.Ollama
```

如果 `winget` 不可用，AI 需要改用官方安装包或包管理器安装等价工具。安装后验证：

```powershell
git --version
git-lfs --version
ffmpeg -version
ffprobe -version
uv --version
ollama --version
nvidia-smi
```

### 获取源码

```powershell
git clone https://github.com/Leon-Drq/koubo-studio-mvp.git
cd koubo-studio-mvp
```

如果使用 SSH：

```powershell
git clone git@github.com:Leon-Drq/koubo-studio-mvp.git
cd koubo-studio-mvp
```

### 安装主服务

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

如果系统没有 Python 3.11，先安装 Python 3.11，再重新执行。

### 安装本地模型

完整安装：

```powershell
.\scripts\setup_local_models.ps1 -WithIndexTTS -WithCosyVoice
```

如果机器资源有限，可以分阶段：

```powershell
.\scripts\setup_local_models.ps1 -SkipOllama -SkipMuseTalk -WithIndexTTS
.\scripts\setup_local_models.ps1 -SkipOllama -SkipMuseTalk -WithCosyVoice
```

安装脚本需要能完成这些结果：

- `.venv-models` 存在
- `.venv-musetalk` 存在
- `.venv-latentsync` 存在，如果当前仓库/机器已配置 LatentSync
- `models/MuseTalk` 存在
- `models/IndexTTS/.venv` 和 `models/IndexTTS/checkpoints` 存在
- `models/CosyVoice/.venv` 和 `models/CosyVoice/pretrained_models/CosyVoice2-0.5B` 存在
- Ollama 已拉取 `qwen2.5:7b`

如果 GitHub LFS 报配额或示例音频下载失败，保持 `GIT_LFS_SKIP_SMUDGE=1`，只拉源码，再通过 Hugging Face/ModelScope 下载真正需要的权重。

如果 C 盘空间不足，设置缓存到项目磁盘后重试：

```powershell
$env:UV_CACHE_DIR=(Resolve-Path "models\cache\uv")
$env:TEMP=(Resolve-Path "models\cache\tmp")
$env:TMP=$env:TEMP
```

### 配置 `.env`

AI 要检查 `.env` 至少包含这些本地命令。路径可以按实际安装位置调整：

```env
DEFAULT_ASR_PROVIDER=local
DEFAULT_LLM_PROVIDER=local
DEFAULT_TTS_PROVIDER=local
DEFAULT_LIPSYNC_PROVIDER=latentsync
DEFAULT_TTS_MODEL=f5

ASR_COMMAND=.venv-models/Scripts/python.exe scripts/adapters/funasr_asr.py --input {audio} --output {text}
LLM_COMMAND=python scripts/adapters/ollama_rewrite.py --input {input} --output {output}
F5_TTS_COMMAND=.venv-models/Scripts/python.exe scripts/adapters/f5_tts.py --input {input} --voice {voice} --voice-sample {voice_sample} --output {audio}
INDEXTTS_COMMAND=models/IndexTTS/.venv/Scripts/python.exe scripts/adapters/indextts2_tts.py --input {input} --voice-sample {voice_sample} --output {audio}
COSYVOICE_COMMAND=models/CosyVoice/.venv/Scripts/python.exe scripts/adapters/cosyvoice_tts.py --input {input} --voice-sample {voice_sample} --output {audio}
LATENTSYNC_COMMAND=.venv-latentsync/Scripts/python.exe scripts/adapters/latentsync_lipsync.py --video {video} --audio {audio} --output {output}
LIPSYNC_COMMAND=.venv-musetalk/Scripts/python.exe scripts/adapters/musetalk_lipsync.py --video {video} --audio {audio} --output {output}

OLLAMA_MODEL=qwen2.5:7b
AUTO_UNLOAD_OLLAMA_BEFORE_MEDIA=true
```

如果 LatentSync 没安装成功，设置：

```env
DEFAULT_LIPSYNC_PROVIDER=preview
```

这样至少能用原视频配音预览跑通闭环。

### 启动服务

生产式本地运行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

不要默认使用 `--reload` 跑本地模型，因为模型缓存、虚拟环境文件变化会触发重启。

### 验收标准

AI 完成部署后必须验证：

```powershell
.\.venv\Scripts\python.exe -m compileall app scripts
.\.venv\Scripts\python.exe scripts\smoke_test.py
curl.exe --noproxy "*" http://127.0.0.1:8000/api/health
```

`/api/health` 至少应返回：

```json
{
  "ok": true,
  "adapters": {
    "tts_models": {
      "f5": true
    }
  }
}
```

如果已安装 IndexTTS2 和 CosyVoice，应看到：

```json
"tts_models": {
  "f5": true,
  "indextts2": true,
  "cosyvoice": true
}
```

还要做一次端到端任务：

1. 打开 `http://127.0.0.1:8000`
2. 输入或粘贴一段 10-30 秒中文口播文案
3. 上传真人视频
4. 上传声音样本
5. 语音模型先选 `F5-TTS`，成片质量先选 `快速预览`
6. 确认任务完成，`final.mp4` 可播放且有音轨
7. 再分别测试 `IndexTTS2`、`CosyVoice`、`LatentSync 高质量`

### 常见故障处理

- `503` 或 curl 本地失败：检查 `HTTP_PROXY`/`HTTPS_PROXY`，用 `curl.exe --noproxy "*"` 测试。
- `CUDA out of memory`：执行 `ollama stop qwen2.5:7b`，关闭浏览器/飞书/剪辑软件，或选 `快速预览`。
- IndexTTS2 报系统内存不足：关闭其他程序，增加虚拟内存，确认机器至少 24-32GB 内存。
- CosyVoice 找不到模块：确认 `models/CosyVoice/.venv` 安装完成，并且 `models/CosyVoice/third_party/Matcha-TTS` 存在。
- MuseTalk 找不到模型：重新执行安装脚本，确认 `models/MuseTalk/models` 下权重完整。
- yt-dlp 下载抖音失败：导出 douyin.com Netscape cookies，设置 `YTDLP_COOKIES_FILE=D:/path/to/cookies.txt`。
- 生成视频没声音：检查浏览器播放器是否静音；再用 `ffprobe final.mp4` 确认是否有 audio stream。
- 成片很短：成片长度跟生成的口播音频长度走，不跟原真人视频长度走；需要更长成片就提供更长文案。

### AI 不要做的事

- 不要提交 `.env`
- 不要提交 `models/`
- 不要提交 `data/jobs/`
- 不要提交 `checkpoints/`
- 不要提交 cookies 或用户上传素材
- 不要删除用户已有任务产物，除非用户明确要求
- 不要把商业授权、肖像授权、声音授权问题略过
