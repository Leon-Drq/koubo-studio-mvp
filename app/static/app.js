const form = document.querySelector("#job-form");
const createButton = document.querySelector("#create-job");
const extractButton = document.querySelector("#extract-script-btn");
const rewriteButton = document.querySelector("#rewrite-script-btn");
const adoptButton = document.querySelector("#adopt-script-btn");
const rewriteState = document.querySelector("#rewrite-state");
const stepsEl = document.querySelector("#steps");
const previewVideo = document.querySelector("#preview-video");
const emptyPreview = document.querySelector("#empty-preview");
const titleOutput = document.querySelector("#title-output");
const topicsOutput = document.querySelector("#topics-output");
const scriptOutput = document.querySelector("#script-output");
const publishReport = document.querySelector("#publish-report");

const links = {
  audio: document.querySelector("#audio-link"),
  script: document.querySelector("#script-link"),
  subtitle: document.querySelector("#subtitle-link"),
  cover: document.querySelector("#cover-link"),
  video: document.querySelector("#video-link"),
};

let pollTimer = null;

function apiFile(path) {
  if (!path) return "";
  const parts = path.split("/");
  const jobIndex = parts.indexOf("jobs");
  if (jobIndex === -1) return "";
  const jobId = parts[jobIndex + 1];
  const section = parts[jobIndex + 2];
  const filename = parts.slice(jobIndex + 3).join("/");
  return `/api/files/${jobId}/${section}/${encodeURIComponent(filename)}`;
}

function setPill(id, enabled) {
  const el = document.querySelector(id);
  el.classList.toggle("on", enabled);
  const base = el.dataset.base || el.textContent.split(" ")[0];
  el.dataset.base = base;
  el.textContent = `${base} ${enabled ? "API" : "本地"}`;
}

async function loadHealth() {
  const res = await fetch("/api/health");
  const data = await res.json();
  document.querySelector("#service-state").textContent = data.ok ? "本地服务已启动" : "服务异常";
  setPill("#asr-pill", Boolean(data.adapters.asr.api));
  setPill("#tts-pill", Boolean(data.adapters.tts.api));
  setPill("#video-pill", Boolean(data.adapters.lipsync.api));

  const defaults = {
    asr_provider: data.adapters.asr.default,
    llm_provider: data.adapters.llm.default,
    tts_provider: data.adapters.tts.default,
    tts_model: data.adapters.tts_models?.default,
    lipsync_provider: data.adapters.lipsync.default,
  };
  for (const [name, value] of Object.entries(defaults)) {
    const select = document.querySelector(`[name="${name}"]`);
    if (select && value) select.value = value;
  }
  const batchInput = document.querySelector('[name="musetalk_batch_size"]');
  const shiftInput = document.querySelector('[name="musetalk_bbox_shift"]');
  if (batchInput && data.adapters.lipsync.musetalk_batch_size) {
    batchInput.value = data.adapters.lipsync.musetalk_batch_size;
  }
  if (shiftInput && Number.isFinite(Number(data.adapters.lipsync.musetalk_bbox_shift))) {
    shiftInput.value = data.adapters.lipsync.musetalk_bbox_shift;
  }
}

function renderSteps(steps) {
  stepsEl.innerHTML = "";
  for (const step of steps) {
    const row = document.createElement("div");
    row.className = `step ${step.status}`;
    row.innerHTML = `<i class="dot"></i><strong>${step.label}</strong><span>${step.message || step.status}</span>`;
    stepsEl.appendChild(row);
  }
}

async function readTextArtifact(path) {
  const url = apiFile(path);
  if (!url) return "";
  const res = await fetch(url);
  return res.ok ? res.text() : "";
}

function showLink(link, path, label) {
  const url = apiFile(path);
  link.hidden = !url;
  if (url) {
    link.href = url;
    link.textContent = label;
  }
}

async function renderJob(job) {
  renderSteps(job.steps);
  titleOutput.value = job.artifacts.title || "";
  topicsOutput.innerHTML = "";
  for (const topic of job.artifacts.topics || []) {
    const pill = document.createElement("span");
    pill.textContent = `#${topic}`;
    topicsOutput.appendChild(pill);
  }
  if (job.artifacts.rewritten_script) {
    scriptOutput.value = await readTextArtifact(job.artifacts.rewritten_script);
  }

  showLink(links.audio, job.artifacts.speech_audio, "下载音频");
  showLink(links.script, job.artifacts.rewritten_script, "下载文案");
  showLink(links.subtitle, job.artifacts.srt, "下载字幕");
  showLink(links.cover, job.artifacts.cover_image, "下载封面");
  showLink(links.video, job.artifacts.final_video, "下载成片");

  const videoUrl = apiFile(job.artifacts.final_video);
  if (videoUrl) {
    previewVideo.src = videoUrl;
    previewVideo.hidden = false;
    emptyPreview.hidden = true;
  }
  publishReport.textContent = job.meta.publish ? JSON.stringify(job.meta.publish, null, 2) : job.error || "";

  if (job.status === "completed" || job.status === "failed") {
    clearInterval(pollTimer);
    pollTimer = null;
    createButton.disabled = false;
    createButton.textContent = job.status === "completed" ? "重新生成口播视频" : "生成失败，重试";
  }
}

async function pollJob(id) {
  const res = await fetch(`/api/jobs/${id}`);
  if (!res.ok) return;
  await renderJob(await res.json());
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const avatarInput = document.querySelector("#avatar_video");
  const providerInput = document.querySelector('[name="llm_provider"]');
  const finalScript = scriptOutput.value.trim();
  if (!avatarInput.files.length) {
    avatarInput.focus();
    return;
  }
  if (providerInput.value === "skip" && finalScript) {
    data.set("source_text", finalScript);
  }
  const platforms = [...document.querySelectorAll(".platforms input:checked")].map((item) => item.value);
  data.set("platforms", platforms.length ? platforms.join(",") : "local");
  createButton.disabled = true;
  createButton.textContent = "生成中";
  publishReport.textContent = "";
  const res = await fetch("/api/jobs", { method: "POST", body: data });
  if (!res.ok) {
    createButton.disabled = false;
    createButton.textContent = "生成口播视频";
    publishReport.textContent = await res.text();
    return;
  }
  const job = await res.json();
  await pollJob(job.id);
  pollTimer = setInterval(() => pollJob(job.id), 1600);
});

extractButton.addEventListener("click", async (event) => {
  event.preventDefault();
  const urlInput = document.querySelector('input[name="competitor_url"]');
  const url = urlInput.value.trim();

  if (!url) {
    alert("请输入对标链接");
    urlInput.focus();
    return;
  }

  extractButton.disabled = true;
  const originalText = extractButton.textContent;
  extractButton.textContent = "提取中...";

  try {
    const response = await fetch("/api/extract-script", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }

    const result = await response.json();
    const textInput = document.querySelector('[name="source_text"]');
    if (textInput) {
      textInput.value = result.script;
    }
    alert("文案提取成功！");
  } catch (error) {
    alert("提取失败: " + error.message);
    console.error(error);
  } finally {
    extractButton.disabled = false;
    extractButton.textContent = originalText;
  }
});

rewriteButton.addEventListener("click", async (event) => {
  event.preventDefault();
  const sourceInput = document.querySelector('[name="source_text"]');
  const productInput = document.querySelector('[name="product_brief"]');
  const toneInput = document.querySelector('[name="tone"]');
  const providerInput = document.querySelector('[name="llm_provider"]');
  const sourceText = sourceInput.value.trim();

  if (!sourceText) {
    alert("请先输入或提取对标文案");
    sourceInput.focus();
    return;
  }

  rewriteButton.disabled = true;
  const originalText = rewriteButton.textContent;
  rewriteButton.textContent = "改写中...";
  rewriteState.textContent = "正在调用 AI 改写";

  try {
    const response = await fetch("/api/rewrite-script", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_text: sourceText,
        product_brief: productInput.value.trim(),
        tone: toneInput.value,
        provider: providerInput.value,
      }),
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }

    const result = await response.json();
    titleOutput.value = result.title || "";
    topicsOutput.innerHTML = "";
    for (const topic of result.topics || []) {
      const pill = document.createElement("span");
      pill.textContent = `#${topic}`;
      topicsOutput.appendChild(pill);
    }
    scriptOutput.value = result.script || "";
    rewriteState.textContent = result.provider ? `已改写：${result.provider}` : "已改写";
  } catch (error) {
    rewriteState.textContent = "改写失败";
    alert("改写失败: " + error.message);
    console.error(error);
  } finally {
    rewriteButton.disabled = false;
    rewriteButton.textContent = originalText;
  }
});

adoptButton.addEventListener("click", (event) => {
  event.preventDefault();
  const sourceInput = document.querySelector('[name="source_text"]');
  const providerInput = document.querySelector('[name="llm_provider"]');
  const rewritten = scriptOutput.value.trim();

  if (!rewritten) {
    alert("没有可采用的改写文案");
    scriptOutput.focus();
    return;
  }

  sourceInput.value = rewritten;
  providerInput.value = "skip";
  rewriteState.textContent = "已采用改写稿";
});

loadHealth();
