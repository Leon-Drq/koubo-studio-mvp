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
