const form = document.querySelector("#job-form");
const createButton = document.querySelector("#create-job");
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
  el.textContent = `${el.textContent.split(" ")[0]} ${enabled ? "已配置" : "fallback"}`;
}

async function loadHealth() {
  const res = await fetch("/api/health");
  const data = await res.json();
  document.querySelector("#service-state").textContent = data.ok ? "本地服务已启动" : "服务异常";
  setPill("#asr-pill", data.adapters.asr);
  setPill("#tts-pill", data.adapters.tts);
  setPill("#video-pill", data.adapters.lipsync);
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
  if (!avatarInput.files.length) {
    avatarInput.focus();
    return;
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

loadHealth();
