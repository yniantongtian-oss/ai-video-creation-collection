#!/usr/bin/env python3
"""Generate source summaries, outline, chapter scripts, and visual shot plans."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from longform_common import (
    LongformError,
    env_float,
    env_int,
    load_dotenv,
    load_project,
    read_json,
    update_chapter_stage,
    update_pipeline_stage,
    write_json,
)


SYSTEM_RULES = """你是一名严谨的长篇纪录片总编剧和事实核查编辑。
只能使用用户提供的研究资料进行事实陈述。每个事实必须绑定提供的来源标记。
资料不足时写 NEEDS_SOURCE，不得猜测数据、日期、引语、人物经历或因果关系。
输出必须符合请求的 JSON 结构，不要在 JSON 外添加解释。"""


class LLMClient:
    def __init__(self) -> None:
        load_dotenv()
        self.base_url = os.environ.get("LONGFORM_LLM_BASE_URL", "").strip().rstrip("/")
        self.api_key = os.environ.get("LONGFORM_LLM_API_KEY", "").strip()
        self.model = os.environ.get("LONGFORM_LLM_MODEL", "").strip()
        self.temperature = env_float("LONGFORM_LLM_TEMPERATURE", 0.3)
        self.timeout = env_int("LONGFORM_LLM_TIMEOUT_SECONDS", 180)
        self.max_retries = env_int("LONGFORM_LLM_MAX_RETRIES", 3)
        if not self.base_url or not self.api_key or not self.model:
            raise LongformError(
                "LONGFORM_LLM_BASE_URL, LONGFORM_LLM_API_KEY, and "
                "LONGFORM_LLM_MODEL must be configured in tools/longform/.env"
            )

    @property
    def endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return self.base_url + "/chat/completions"

    def json_call(
        self,
        user_prompt: str,
        *,
        system_prompt: str = SYSTEM_RULES,
        max_tokens: int = 12000,
    ) -> Any:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ai-video-creation-collection-longform/1.0",
            },
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    response_data = json.loads(response.read().decode("utf-8"))
                content = response_data["choices"][0]["message"]["content"]
                return parse_json_content(str(content))
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                delay = min(2 ** (attempt - 1), 8)
                print(f"LLM request failed; retrying in {delay}s: {exc}", file=sys.stderr)
                time.sleep(delay)
        raise LongformError(f"LLM request failed after {self.max_retries} attempts: {last_error}")


def parse_json_content(content: str) -> Any:
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        starts = [position for position in (text.find("{"), text.find("[")) if position >= 0]
        if not starts:
            raise
        start = min(starts)
        opening = text[start]
        closing = "}" if opening == "{" else "]"
        end = text.rfind(closing)
        if end <= start:
            raise
        return json.loads(text[start : end + 1])


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LongformError(f"invalid JSONL at {path}:{number}: {exc}") from exc
        if isinstance(item, dict):
            entries.append(item)
    return entries


def normalize_chapter_ids(project_data: dict[str, Any], requested: list[str] | None) -> list[str]:
    available = [str(item.get("id")) for item in project_data.get("chapters", [])]
    if not requested:
        return available
    normalized: list[str] = []
    for value in requested:
        try:
            chapter_id = f"{int(value):02d}"
        except ValueError as exc:
            raise LongformError(f"invalid chapter number: {value}") from exc
        if chapter_id not in available:
            raise LongformError(f"chapter does not exist: {chapter_id}")
        normalized.append(chapter_id)
    return list(dict.fromkeys(normalized))


def source_groups(project: Path) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chunk in read_jsonl(project / "research" / "chunks.jsonl"):
        groups[str(chunk.get("source_id") or "unknown")].append(chunk)
    return groups


def batched_chunks(chunks: list[dict[str, Any]], max_chars: int = 12000) -> Iterable[list[dict[str, Any]]]:
    current: list[dict[str, Any]] = []
    size = 0
    for chunk in chunks:
        text = str(chunk.get("text") or "")
        if current and size + len(text) > max_chars:
            yield current
            current = []
            size = 0
        current.append(chunk)
        size += len(text)
    if current:
        yield current


def context_block(chunks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for chunk in chunks:
        parts.append(
            f"SOURCE={chunk.get('citation')}\n{str(chunk.get('text') or '').strip()}"
        )
    return "\n\n---\n\n".join(parts)


def summarize_sources(project: Path, client: LLMClient, force: bool) -> None:
    groups = source_groups(project)
    if not groups:
        raise LongformError(
            "research corpus is empty; run scripts/ingest_longform_corpus.py first"
        )
    update_pipeline_stage(project, "summaries", "running", sources=len(groups))
    try:
        for source_id, chunks in groups.items():
            output = project / "research" / "summaries" / f"{source_id}.md"
            if output.exists() and output.stat().st_size > 100 and not force:
                print(f"Summary exists, skipping: {source_id}")
                continue
            partials: list[dict[str, Any]] = []
            for batch_number, batch in enumerate(batched_chunks(chunks), 1):
                prompt = f"""请整理以下来源的第 {batch_number} 批资料。

要求输出 JSON：
{{
  "summary": "准确摘要",
  "chronology": [{{"event":"事件","source_refs":["来源标记"]}}],
  "key_facts": [{{"fact":"事实","source_refs":["来源标记"]}}],
  "concepts": [{{"name":"概念","explanation":"解释","source_refs":["来源标记"]}}],
  "disputes": [{{"issue":"争议或不确定处","source_refs":["来源标记"]}}],
  "visual_leads": [{{"idea":"适合寻找的画面","source_refs":["来源标记"]}}]
}}

不得合并不同来源标记，不得补充资料外事实。

资料：
{context_block(batch)}
"""
                result = client.json_call(prompt, max_tokens=8000)
                if not isinstance(result, dict):
                    raise LongformError(f"invalid summary response for {source_id}")
                partials.append(result)
            if len(partials) == 1:
                merged = partials[0]
            else:
                prompt = f"""把同一来源的多批摘要合并成一个去重后的来源摘要。
保留每条事实原有的 source_refs，不得新增事实。
输出结构与输入单项一致。

输入：
{json.dumps(partials, ensure_ascii=False)}
"""
                merged = client.json_call(prompt, max_tokens=10000)
                if not isinstance(merged, dict):
                    raise LongformError(f"invalid merged summary for {source_id}")
            lines = [f"# 来源摘要：{source_id}", "", str(merged.get("summary") or ""), ""]
            for key, title in (
                ("chronology", "时间线"),
                ("key_facts", "关键事实"),
                ("concepts", "概念"),
                ("disputes", "争议与不确定项"),
                ("visual_leads", "视觉素材线索"),
            ):
                lines.extend([f"## {title}", ""])
                values = merged.get(key, [])
                if isinstance(values, list):
                    for item in values:
                        if isinstance(item, dict):
                            refs = ", ".join(str(value) for value in item.get("source_refs", []))
                            content = item.get("fact") or item.get("event") or item.get("name") or item.get("issue") or item.get("idea") or ""
                            explanation = item.get("explanation") or ""
                            suffix = f" — {explanation}" if explanation else ""
                            lines.append(f"- {content}{suffix} `[{refs}]`")
                lines.append("")
            output.write_text("\n".join(lines), encoding="utf-8")
            print(f"Summary written: {output}")
    except Exception:
        update_pipeline_stage(project, "summaries", "failed")
        raise
    update_pipeline_stage(project, "summaries", "completed", sources=len(groups))


def load_summary_context(project: Path, max_total_chars: int = 90000) -> str:
    parts: list[str] = []
    total = 0
    for path in sorted((project / "research" / "summaries").glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        remaining = max_total_chars - total
        if remaining <= 0:
            break
        excerpt = text[:remaining]
        parts.append(excerpt)
        total += len(excerpt)
    if not parts:
        raise LongformError("no source summaries found; run the summarize stage first")
    return "\n\n===== NEXT SOURCE =====\n\n".join(parts)


def plan_outline(project: Path, project_data: dict[str, Any], client: LLMClient, force: bool) -> dict[str, Any]:
    output = project / "outline" / "outline.json"
    if output.exists() and not force:
        existing = read_json(output)
        if isinstance(existing, dict) and existing.get("chapters"):
            print("Outline exists, skipping")
            return existing
    target = project_data["target"]
    chapter_count = int(target["chapters"])
    summaries = load_summary_context(project)
    prompt = f"""为以下长视频制定完整章节大纲。

项目：{project_data.get('name')}
主题：{project_data.get('topic')}
受众：{project_data.get('audience')}
风格：{project_data.get('style')}
目标时长：{target.get('minutes')} 分钟
必须正好包含：{chapter_count} 章
每章约：{target.get('chapter_minutes')} 分钟

输出 JSON：
{{
  "title": "总标题",
  "subtitle": "副标题",
  "thesis": "全片核心论点",
  "opening_hook": "开场钩子",
  "chapters": [
    {{
      "id": "01",
      "title": "章节标题",
      "objective": "本章要完成的叙事任务",
      "target_minutes": 7,
      "key_points": ["要点"],
      "research_queries": ["用于检索语料库和素材的关键词"],
      "source_ids": ["优先来源 ID"],
      "transition_in": "承接前文方式",
      "transition_out": "引向下一章方式"
    }}
  ],
  "ending": "结尾结构",
  "global_visual_style": "全片视觉风格",
  "risk_notes": ["事实、版权或叙事风险"]
}}

章节必须形成递进，不得重复；事实不足的部分应在 risk_notes 标记需要补充来源。

来源摘要：
{summaries}
"""
    result = client.json_call(prompt, max_tokens=14000)
    if not isinstance(result, dict) or not isinstance(result.get("chapters"), list):
        raise LongformError("outline response does not contain chapters")
    chapters = result["chapters"]
    if len(chapters) != chapter_count:
        correction = f"""上一次大纲包含 {len(chapters)} 章，但项目必须正好包含 {chapter_count} 章。
请在不丢失核心信息的前提下重新组织，输出完整 JSON，结构与上次相同。

上次大纲：
{json.dumps(result, ensure_ascii=False)}
"""
        result = client.json_call(correction, max_tokens=14000)
        chapters = result.get("chapters", []) if isinstance(result, dict) else []
    if not isinstance(chapters, list) or len(chapters) != chapter_count:
        raise LongformError(
            f"outline chapter count mismatch: expected {chapter_count}, got {len(chapters)}"
        )
    for index, chapter in enumerate(chapters, 1):
        if not isinstance(chapter, dict):
            raise LongformError("outline chapter entries must be objects")
        chapter["id"] = f"{index:02d}"
        chapter.setdefault("target_minutes", project_data["chapters"][index - 1]["target_minutes"])
    write_json(output, result)
    apply_outline_to_project(project, project_data, result)
    update_pipeline_stage(project, "outline", "completed", chapters=chapter_count)
    return result


def apply_outline_to_project(
    project: Path, project_data: dict[str, Any], outline: dict[str, Any]
) -> None:
    chapters = outline.get("chapters", [])
    with (project / "outline" / "chapter-map.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "chapter",
                "title",
                "target_minutes",
                "target_chars",
                "target_shots",
                "status",
            ]
        )
        for index, chapter in enumerate(chapters):
            chapter_id = f"{index + 1:02d}"
            minutes = int(chapter.get("target_minutes") or project_data["chapters"][index]["target_minutes"])
            project_data["chapters"][index].update(
                {
                    "id": chapter_id,
                    "title": chapter.get("title") or f"第 {index + 1} 章",
                    "target_minutes": minutes,
                    "objective": chapter.get("objective") or "",
                    "research_queries": chapter.get("research_queries") or [],
                }
            )
            target_chars = minutes * int(project_data["target"]["chars_per_minute"])
            target_shots = math.ceil(
                minutes * 60 / int(project_data["target"]["visual_seconds_per_shot"])
            )
            writer.writerow(
                [
                    chapter_id,
                    project_data["chapters"][index]["title"],
                    minutes,
                    target_chars,
                    target_shots,
                    "planned",
                ]
            )
            brief = f"""# {project_data['chapters'][index]['title']}

## 本章目标

{chapter.get('objective', '')}

## 关键要点

"""
            for point in chapter.get("key_points", []):
                brief += f"- {point}\n"
            brief += "\n## 研究检索词\n\n"
            for query in chapter.get("research_queries", []):
                brief += f"- {query}\n"
            brief += "\n## 优先来源\n\n"
            for source_id in chapter.get("source_ids", []):
                brief += f"- `{source_id}`\n"
            brief += f"\n## 转场\n\n- 进入：{chapter.get('transition_in', '')}\n- 退出：{chapter.get('transition_out', '')}\n"
            (project / "chapters" / chapter_id / "brief.md").write_text(brief, encoding="utf-8")
    write_json(project / "project.json", project_data)


def lexical_terms(text: str) -> set[str]:
    lowered = text.lower()
    terms = {token for token in re.findall(r"[a-z0-9][a-z0-9_-]{1,}", lowered)}
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        if len(sequence) <= 6:
            terms.add(sequence)
        for size in (2, 3):
            for index in range(0, max(0, len(sequence) - size + 1)):
                terms.add(sequence[index : index + size])
    return terms


def retrieve_chunks(project: Path, query: str, limit: int) -> list[dict[str, Any]]:
    chunks = read_jsonl(project / "research" / "chunks.jsonl")
    query_terms = lexical_terms(query)
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        text = str(chunk.get("text") or "")
        terms = lexical_terms(text[:8000])
        overlap = query_terms & terms
        if not overlap:
            continue
        score = sum(3.0 if len(term) >= 3 else 1.0 for term in overlap)
        score += min(len(text) / 5000, 1.0)
        scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    if scored:
        return [item[1] for item in scored[:limit]]
    return chunks[:limit]


def strip_source_markers(text: str) -> str:
    text = re.sub(r"\[S:[^\]]+\]", "", text)
    text = re.sub(r"\s+([，。！？；：,.!?;:])", r"\1", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def ensure_script_length(
    client: LLMClient,
    result: dict[str, Any],
    target_chars: int,
    context: str,
    chapter_title: str,
) -> dict[str, Any]:
    narration = str(result.get("narration") or "")
    if len(narration) >= int(target_chars * 0.72):
        return result
    prompt = f"""以下章节旁白过短。请扩展到约 {target_chars} 个中文字符，保持自然口语、叙事推进和事实准确。
不得加入资料外事实；新增事实必须带来源标记并写入 claims。
输出 JSON 结构保持为 script_markdown、narration、claims、open_questions。

章节：{chapter_title}
当前结果：
{json.dumps(result, ensure_ascii=False)}

可用资料：
{context}
"""
    expanded = client.json_call(prompt, max_tokens=16000)
    return expanded if isinstance(expanded, dict) else result


def write_chapters(
    project: Path,
    project_data: dict[str, Any],
    outline: dict[str, Any],
    client: LLMClient,
    chapter_ids: list[str],
    retrieval_limit: int,
    force: bool,
) -> None:
    outline_chapters = {str(item.get("id")): item for item in outline.get("chapters", []) if isinstance(item, dict)}
    update_pipeline_stage(project, "scripts", "running", chapters=chapter_ids)
    previous_ending = ""
    try:
        for chapter_id in chapter_ids:
            chapter_dir = project / "chapters" / chapter_id
            script_path = chapter_dir / "script.md"
            narration_path = chapter_dir / "narration.txt"
            if script_path.exists() and script_path.stat().st_size > 200 and not force:
                print(f"Script exists, skipping chapter {chapter_id}")
                previous_ending = narration_path.read_text(encoding="utf-8", errors="replace")[-500:]
                continue
            chapter = outline_chapters.get(chapter_id)
            if not chapter:
                raise LongformError(f"outline is missing chapter {chapter_id}")
            index = int(chapter_id) - 1
            minutes = int(chapter.get("target_minutes") or project_data["chapters"][index]["target_minutes"])
            target_chars = minutes * int(project_data["target"]["chars_per_minute"])
            query = " ".join(
                [
                    str(chapter.get("title") or ""),
                    str(chapter.get("objective") or ""),
                    " ".join(str(value) for value in chapter.get("research_queries", [])),
                    " ".join(str(value) for value in chapter.get("key_points", [])),
                ]
            )
            chunks = retrieve_chunks(project, query, retrieval_limit)
            context = context_block(chunks)
            next_chapter = outline_chapters.get(f"{int(chapter_id) + 1:02d}")
            prompt = f"""撰写长视频第 {chapter_id} 章完整文案。

总主题：{project_data.get('topic')}
章节标题：{chapter.get('title')}
章节目标：{chapter.get('objective')}
目标时长：{minutes} 分钟
目标旁白长度：约 {target_chars} 个中文字符
受众：{project_data.get('audience')}
风格：{project_data.get('style')}
上一章结尾：{previous_ending or '这是开篇章节'}
下一章目标：{next_chapter.get('objective') if isinstance(next_chapter, dict) else '这是最终章节'}

输出 JSON：
{{
  "script_markdown": "包含段落标题和 [S:来源标记] 的完整编辑稿",
  "narration": "不含来源标记、可直接配音的连续旁白",
  "claims": [{{"claim":"可核查事实","source_refs":["来源标记"],"confidence":"high|medium|needs-source"}}],
  "open_questions": ["仍需补充来源的问题"]
}}

要求：
1. 章节内部有开场承接、主体递进、段落转折和结尾悬念。
2. 编辑稿中的事实句后使用 [S:source_id#locator]。
3. narration 不朗读来源标记，但不能省略正文内容。
4. 资料不足处写 NEEDS_SOURCE，不得用常识补齐。
5. 避免重复其他章节的功能。

可用资料：
{context}
"""
            update_chapter_stage(project, chapter_id, "script", "running")
            result = client.json_call(prompt, max_tokens=18000)
            if not isinstance(result, dict):
                raise LongformError(f"invalid script response for chapter {chapter_id}")
            result = ensure_script_length(
                client, result, target_chars, context, str(chapter.get("title") or "")
            )
            script = str(result.get("script_markdown") or "").strip()
            narration = strip_source_markers(str(result.get("narration") or script))
            if len(narration) < int(target_chars * 0.55):
                raise LongformError(
                    f"chapter {chapter_id} remains too short: {len(narration)} / {target_chars} characters"
                )
            script_path.write_text(script + "\n", encoding="utf-8")
            narration_path.write_text(narration + "\n", encoding="utf-8")
            write_json(chapter_dir / "claims.json", result.get("claims", []))
            write_json(chapter_dir / "open-questions.json", result.get("open_questions", []))
            (chapter_dir / "research" / "retrieved-context.md").write_text(
                context + "\n", encoding="utf-8"
            )
            update_chapter_stage(
                project,
                chapter_id,
                "script",
                "completed",
                characters=len(narration),
                target_characters=target_chars,
                retrieved_chunks=len(chunks),
            )
            previous_ending = narration[-500:]
            print(f"Chapter script written: {chapter_id} ({len(narration)} chars)")
    except Exception:
        update_pipeline_stage(project, "scripts", "failed")
        raise
    update_pipeline_stage(project, "scripts", "completed", chapters=chapter_ids)


def split_sentences(text: str) -> list[str]:
    values = re.split(r"(?<=[。！？!?；;])\s*|\n+", text)
    return [value.strip() for value in values if value.strip()]


def narration_segments(text: str, target_count: int, total_seconds: float) -> list[dict[str, Any]]:
    sentences = split_sentences(text)
    if not sentences:
        return []
    target_count = max(1, min(target_count, len(sentences)))
    target_chars = max(1, math.ceil(len(text) / target_count))
    groups: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = sentence if not current else current + sentence
        if current and len(candidate) > target_chars and len(groups) < target_count - 1:
            groups.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        groups.append(current)
    while len(groups) > target_count:
        tail = groups.pop()
        groups[-1] += tail
    total_chars = sum(len(group) for group in groups) or 1
    segments: list[dict[str, Any]] = []
    for index, group in enumerate(groups, 1):
        duration = total_seconds * len(group) / total_chars
        segments.append(
            {
                "segment_id": index,
                "narration_excerpt": group,
                "duration_seconds": round(duration, 3),
            }
        )
    difference = total_seconds - sum(float(item["duration_seconds"]) for item in segments)
    if segments:
        segments[-1]["duration_seconds"] = round(
            float(segments[-1]["duration_seconds"]) + difference, 3
        )
    return segments


def batched(values: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def generate_shots(
    project: Path,
    project_data: dict[str, Any],
    outline: dict[str, Any],
    client: LLMClient,
    chapter_ids: list[str],
    force: bool,
) -> None:
    outline_chapters = {str(item.get("id")): item for item in outline.get("chapters", []) if isinstance(item, dict)}
    update_pipeline_stage(project, "shots", "running", chapters=chapter_ids)
    try:
        for chapter_id in chapter_ids:
            chapter_dir = project / "chapters" / chapter_id
            output = chapter_dir / "shots.json"
            if output.exists() and not force:
                existing = read_json(output)
                if isinstance(existing, list) and existing:
                    print(f"Shot plan exists, skipping chapter {chapter_id}")
                    continue
            narration = (chapter_dir / "narration.txt").read_text(
                encoding="utf-8", errors="replace"
            ).strip()
            if not narration:
                raise LongformError(f"chapter {chapter_id} has no narration")
            chapter = outline_chapters.get(chapter_id, {})
            index = int(chapter_id) - 1
            minutes = int(chapter.get("target_minutes") or project_data["chapters"][index]["target_minutes"])
            total_seconds = minutes * 60
            cadence = int(project_data["target"]["visual_seconds_per_shot"])
            target_count = max(1, math.ceil(total_seconds / cadence))
            segments = narration_segments(narration, target_count, total_seconds)
            suggestions: dict[int, dict[str, Any]] = {}
            update_chapter_stage(project, chapter_id, "shots", "running")
            for batch in batched(segments, 20):
                prompt = f"""为长视频章节中的旁白片段设计视觉镜头。
章节：{chapter.get('title')}
全片视觉风格：{outline.get('global_visual_style')}

对每个 segment_id 必须返回且只能返回一条建议。输出 JSON：
{{
  "items": [
    {{
      "segment_id": 1,
      "visual_type": "video|image|document|diagram|map|timeline|title-card",
      "visual_description": "画面内容和运动方式",
      "search_queries": ["中文检索词", "英文检索词"],
      "on_screen_text": "必要时显示的短文字",
      "source_refs": ["与该画面相关的研究来源标记"],
      "reuse_allowed": true
    }}
  ]
}}

不得建议侵权影视片段、未经许可的人像或无法核验的数据图。优先建议公共领域、开放许可、机构资料、地图、档案、实拍 B-roll、图表和自制示意图。

片段：
{json.dumps(batch, ensure_ascii=False)}
"""
                result = client.json_call(prompt, max_tokens=10000)
                items = result.get("items", []) if isinstance(result, dict) else []
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            try:
                                suggestions[int(item.get("segment_id"))] = item
                            except (TypeError, ValueError):
                                continue
            shots: list[dict[str, Any]] = []
            for segment in segments:
                segment_id = int(segment["segment_id"])
                suggestion = suggestions.get(segment_id, {})
                excerpt = str(segment["narration_excerpt"])
                queries = suggestion.get("search_queries")
                if not isinstance(queries, list) or not queries:
                    queries = [excerpt[:40]]
                shots.append(
                    {
                        "id": f"{chapter_id}-{segment_id:03d}",
                        "chapter": chapter_id,
                        "segment_id": segment_id,
                        "duration_seconds": segment["duration_seconds"],
                        "narration_excerpt": excerpt,
                        "visual_type": suggestion.get("visual_type", "image"),
                        "visual_description": suggestion.get(
                            "visual_description", "与旁白直接相关的开放授权素材"
                        ),
                        "search_queries": queries[:3],
                        "on_screen_text": suggestion.get("on_screen_text", ""),
                        "source_refs": suggestion.get("source_refs", []),
                        "reuse_allowed": bool(suggestion.get("reuse_allowed", True)),
                        "asset_id": "",
                        "asset_path": "",
                        "status": "needs-asset",
                    }
                )
            write_json(output, shots)
            update_chapter_stage(
                project,
                chapter_id,
                "shots",
                "completed",
                shots=len(shots),
                target_shots=target_count,
            )
            print(f"Shot plan written: chapter {chapter_id}, shots={len(shots)}")
    except Exception:
        update_pipeline_stage(project, "shots", "failed")
        raise
    update_pipeline_stage(project, "shots", "completed", chapters=chapter_ids)


def print_status(project: Path, project_data: dict[str, Any]) -> None:
    pipeline_path = project / "state" / "pipeline.json"
    pipeline = read_json(pipeline_path) if pipeline_path.exists() else {}
    print(f"Project: {project_data.get('name')}")
    print(f"Target: {project_data.get('target', {}).get('minutes')} minutes")
    print("Pipeline:")
    stages = pipeline.get("stages", {}) if isinstance(pipeline, dict) else {}
    if isinstance(stages, dict):
        for name, state in stages.items():
            print(f"  {name:20s} {state}")
    print("Chapters:")
    for chapter in project_data.get("chapters", []):
        chapter_id = str(chapter.get("id"))
        path = project / "chapters" / chapter_id / "status.json"
        status = read_json(path) if path.exists() else {}
        chapter_stages = status.get("stages", {}) if isinstance(status, dict) else {}
        values = ", ".join(f"{key}={value}" for key, value in chapter_stages.items())
        print(f"  {chapter_id} {chapter.get('title')}: {values}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument(
        "command",
        choices=["summarize", "plan", "write", "shots", "run", "status"],
    )
    parser.add_argument(
        "--chapter",
        action="append",
        help="One chapter number. May be repeated. Defaults to all chapters.",
    )
    parser.add_argument("--retrieval-chunks", type=int, default=12)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not 3 <= args.retrieval_chunks <= 50:
        parser.error("--retrieval-chunks must be between 3 and 50")
    return args


def main() -> int:
    args = parse_args()
    project, project_data = load_project(args.project)
    chapter_ids = normalize_chapter_ids(project_data, args.chapter)
    if args.command == "status":
        print_status(project, project_data)
        return 0

    client = LLMClient()
    if args.command in {"summarize", "run"}:
        summarize_sources(project, client, args.force)
    outline: dict[str, Any]
    if args.command in {"plan", "run"}:
        update_pipeline_stage(project, "outline", "running")
        outline = plan_outline(project, project_data, client, args.force)
        project_data = read_json(project / "project.json")
    else:
        loaded = read_json(project / "outline" / "outline.json")
        if not isinstance(loaded, dict) or not loaded.get("chapters"):
            raise LongformError("outline is missing; run the plan stage first")
        outline = loaded
    if args.command in {"write", "run"}:
        write_chapters(
            project,
            project_data,
            outline,
            client,
            chapter_ids,
            args.retrieval_chunks,
            args.force,
        )
    if args.command in {"shots", "run"}:
        generate_shots(
            project,
            project_data,
            outline,
            client,
            chapter_ids,
            args.force,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (LongformError, OSError, ValueError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
