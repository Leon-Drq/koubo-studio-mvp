# Koubo Studio MVP

一个本地部署的电商口播数字人生成平台 MVP。它把“对标视频/文案 -> AI 改写 -> 口播音频 -> 真人静默视频配音/口型同步 -> 字幕封面 -> 发布清单”串成一个可运行的工作流。

## 已实现

- FastAPI 后端和静态前端操作台
- 对标链接下载适配 `yt-dlp`
- 对标视频音频抽取适配 `ffmpeg`
- ASR、LLM、TTS、Lip-sync 命令模板适配层
- 无 GPU 的 fallback 流程，方便先跑通产品闭环
- 任务状态、产物、字幕、封面、发布清单持久化到 `data/jobs`
- GitHub 友好的项目结构和烟测脚本

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
bash scripts/dev.sh
```

打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

本机建议安装：

```bash
brew install ffmpeg yt-dlp
```

没有配置模型时，系统会使用 fallback：文案走演示/规则改写，音频在 macOS 上用 `say`，视频用原真人静默视频配音预览。接入模型后，fallback 会自动让位给配置的命令。

## 接入开源模型

复制 `.env.example` 到 `.env`，按你的部署方式设置命令模板。

### ASR

Whisper:

```env
ASR_COMMAND=python scripts/adapters/whisper_asr.py --input {audio} --output {text}
```

也可以把 `ASR_COMMAND` 指向 FunASR/SenseVoice 的自有 wrapper，只要读取 `{audio}` 并写入 `{text}`。

### 文案改写

Ollama:

```env
OLLAMA_MODEL=qwen2.5:7b
```

或显式命令：

```env
LLM_COMMAND=python scripts/adapters/ollama_rewrite.py --input {input} --output {output}
```

### 语音克隆

推荐把 CosyVoice、GPT-SoVITS、F5-TTS 作为独立服务或独立虚拟环境，再写一个 wrapper：

```env
TTS_COMMAND=python your_cosyvoice_wrapper.py --input {input} --voice {voice} --output {audio}
```

### 口型同步

推荐 MuseTalk / VideoReTalking / Wav2Lip 作为独立环境：

```env
LIPSYNC_COMMAND=python your_musetalk_wrapper.py --video {video} --audio {audio} --output {output}
```

注意：Wav2Lip 官方仓库对商业使用有限制，商业化前要确认许可证。

## API

- `POST /api/jobs`：创建生成任务，multipart 表单。
- `GET /api/jobs`：任务列表。
- `GET /api/jobs/{id}`：任务详情。
- `GET /api/files/{job_id}/{inputs|outputs}/{filename}`：下载产物。

## 验证

```bash
python scripts/smoke_test.py
```

## 合规边界

- 对标视频、声音样本、真人形象需要授权。
- 抖音/视频号/小红书/快手自动发布建议优先接官方开放平台。
- 浏览器自动发布可以作为可选模块，但更容易受风控和页面变更影响。
