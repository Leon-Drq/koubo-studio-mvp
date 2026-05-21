from __future__ import annotations

import subprocess
from pathlib import Path

from app.config import Settings
from app.services.command import CommandError, has_binary, run_template


def _rule_based_rewrite(source: str, product_brief: str, tone: str) -> str:
    brief = product_brief.strip() or "这款产品"
    hook = "你是不是也遇到过这种情况：看了很多推荐，最后还是不知道该选哪一个？"
    body = [
        hook,
        f"今天直接讲重点，{brief}适合想省时间、又希望效果稳定的人。",
        "第一，它解决的是日常使用里最容易被忽略的麻烦，不需要复杂操作，上手就能看到变化。",
        "第二，它不是只讲参数，而是把体验做得更顺：该省的步骤省掉，该保留的质感保留住。",
        "第三，如果你最近刚好在比较同类选择，可以先从这个版本试起，成本更可控，踩坑概率也更低。",
        "想要少走弯路，就先把这条收藏起来，按自己的需求对照一下。",
    ]
    if "情绪" in tone or "高兴" in tone:
        body[0] = "我真的建议你认真看完，因为这个细节很多人一开始都会忽略。"
    if source.strip():
        body.append("原文案里的核心信息已经保留，但表达会更适合电商口播转化。")
    return "\n".join(body)


def _title_and_topics(script: str, product_brief: str) -> tuple[str, list[str]]:
    title_seed = product_brief.strip().splitlines()[0] if product_brief.strip() else "好物口播"
    title = f"{title_seed[:18]}，选对真的省心"
    topics = ["好物推荐", "电商口播", "真实测评", "省心选择"]
    if "护肤" in product_brief:
        topics.append("护肤分享")
    if "家居" in product_brief:
        topics.append("家居好物")
    return title, topics[:5]


def rewrite_script(source: str, settings: Settings, output: Path, product_brief: str, tone: str) -> tuple[str, str, list[str], str]:
    input_path = output.with_suffix(".input.txt")
    input_path.write_text(
        f"风格：{tone}\n商品卖点：{product_brief}\n\n原文案：\n{source}",
        encoding="utf-8",
    )

    if settings.llm_command.strip():
        try:
            run_template(settings.llm_command, input=input_path, output=output)
            script = output.read_text(encoding="utf-8").strip()
            title, topics = _title_and_topics(script, product_brief)
            return script, title, topics, "LLM_COMMAND"
        except CommandError:
            pass

    if settings.ollama_model and has_binary("ollama"):
        prompt = input_path.read_text(encoding="utf-8") + "\n\n请改写成 60-90 秒中文电商口播，结构清晰，避免夸大承诺。"
        try:
            proc = subprocess.run(
                ["ollama", "run", settings.ollama_model, prompt],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            script = proc.stdout.strip()
            if script:
                output.write_text(script, encoding="utf-8")
                title, topics = _title_and_topics(script, product_brief)
                return script, title, topics, f"Ollama {settings.ollama_model}"
        except Exception:
            pass

    script = _rule_based_rewrite(source, product_brief, tone)
    output.write_text(script, encoding="utf-8")
    title, topics = _title_and_topics(script, product_brief)
    return script, title, topics, "规则改写 fallback"
