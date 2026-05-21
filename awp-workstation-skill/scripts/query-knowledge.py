#!/usr/bin/env python3
"""Query the workstation knowledge catalog by topic, dossier, or source fact key."""

from __future__ import annotations

import argparse

from awp_workstation_lib import (
    build_playbook_command,
    build_knowledge_catalog,
    build_knowledge_review_queue,
    load_cached_knowledge_catalog,
    load_cached_knowledge_review_queue,
    print_json,
    query_knowledge_command,
    query_source_command,
    scan_worknets_command,
    summarize_knowledge_review_queue,
)

PRIORITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}
KIND_ORDER = {"source": 0, "topic": 1, "fact": 2, "worknet": 3, "evidence": 4}
AUTOMATION_LABELS = {
    "full": "适合长期自动运行",
    "supervised": "适合有人盯关键节点时运行",
    "manual-only": "目前更适合手动观察",
    "partial": "只有部分环节适合自动化",
}
RISK_LABELS = {
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
}
TOPIC_NARRATIVES = {
    "protocol-core": {
        "plain": "AWP 是一个让 agent 找工作、赚钱和协作的双层网络：RootNet 负责总控，WorkNet 负责具体工作。",
        "why": "Workstation 先要吃透这层结构，才能替用户屏蔽协议细节，只保留注册、选活、执行和复盘这些真正需要的动作。",
        "caution": "这里最关键的风险点是 recipient 路由、资产动作确认，以及上游 skill 变化不能直接改写本地工作站行为。",
    },
    "awp-skill": {
        "plain": "awp-skill 是 AWP 的官方 RootNet 技能，负责注册、staking、allocation、worknet 查询和核心协议读写。",
        "why": "它是 workstation 连接官方协议面的主入口，也是后续注册、资格判断和 live 查询的依赖层。",
        "caution": "一旦这个官方 skill 发生上游变化，protocol-core、注册流程和风险边界都要跟着复核。",
    },
    "mine": {
        "plain": "Mine 是 AWP 默认优先级最高的数据工作网，核心就是找网页、抓网页、清洗内容、抽结构化数据，再提交拿收益。",
        "why": "它通常不要求 miner 先 stake，最适合作为新用户进入 AWP 的第一条长期工作流。",
        "loop": "默认节奏是先发现 URL 和 dataset，再去重、crawl、clean、抽 schema，最后 submit 并维持 heartbeat。",
        "caution": "真正影响收益的是提交确认率、重复率、IP 衰减和 epoch 结束时的质量门槛。",
    },
    "predict": {
        "plain": "Predict 是 AWP 的推理型预测工作网，agent 通过读取市场上下文和外部信号形成观点，再提交方向、价格和仓位。",
        "why": "它更像把研究能力直接变成收益，但前提是控制重复推理、频率和风控，而不是无脑多跑。",
        "loop": "默认节奏是先读 context，再拉信号、形成 thesis、给出 order，之后持续 monitor 和复盘。",
        "caution": "它天然比 Mine 更偏高风险，因为判断失误、过度重复 reasoning 和 rate limit 都会直接伤害结果。",
    },
    "gov": {
        "plain": "GovNet 是按阶段运行的治理/交易型 WorkNet，核心动作是看 market、投票、下单、盯 phase，再等结算。",
        "why": "它承接的是对 WorkNet 价值和每周排放的判断，不只是读信息，还会碰到真正的资产动作。",
        "loop": "默认节奏是先初始化和看 phase，再 stake / allocate / vote / monitor，最后等 settle。",
        "caution": "所有投票、下单、stake 和其他不可逆动作都必须先进 confirmation queue，不能静默自动执行。",
    },
    "staking": {
        "plain": "Staking 就是把 AWP 锁起来，换成 veAWP 和 AWP Power，用来拿治理权、资格和某些 WorkNet 的优先级。",
        "why": "它是增强项，不是新用户上手前置；只有真的需要资格或优先级时才该考虑。",
        "caution": "Staking 天然是价值移动动作，会锁定流动性，所以必须明确提示期限、影响和确认步骤。",
    },
    "dao": {
        "plain": "DAO 是 AWP 的治理面，负责提案、投票和协议方向调整。",
        "why": "用户未必要天天碰 DAO，但 workstation 必须理解它，因为 staking、AWP Power 和 GovNet 都会跟它连起来。",
        "caution": "治理判断和投票不是纯观察动作，任何签名或有价值影响的步骤都必须单独确认。",
    },
    "ardi": {
        "plain": "Ardi 是按 epoch 解谜的 WorkNet，agent 要读题、挑高置信答案、先 commit，等窗口到再 reveal 和 inscribe。",
        "why": "它不是持续刷任务型循环，更像带时间窗口的事件驱动工作网。",
        "loop": "默认节奏是先读谜题和上下文，再选最多 5 个答案，commit 后等 reveal 窗口，最后 inscribe。",
        "caution": "它最怕错过 phase 或者偏离官方 `_internal.next_command`，所以 runtime guidance 必须被严格遵守。",
    },
    "kya": {
        "plain": "KYA 更像一次性的身份、认证和委托工具网，主要负责 attestation、recipient 路由和 delegated staking。",
        "why": "它不是拿来长期循环刷收益的，而是帮其他工作流解决身份和权限前置问题。",
        "caution": "凡是跟身份绑定、recipient 设置或 delegated staking 有关的动作，都要强调签名和确认边界。",
    },
    "tmr": {
        "plain": "TMR 是官方已激活但公开资料仍偏薄的 WorkNet，目前 workstation 主要把它当成已发现但不可贸然自动运行的目标。",
        "why": "这类 WorkNet 需要先补齐官方 skill、流程和风险资料，才能安全进入自动化层。",
        "caution": "在资料不足前，最稳妥的动作是继续整理来源、比对 live skill URI，而不是强行执行。",
    },
    "community": {
        "plain": "Community 是官方已激活但公开操作资料仍偏薄的 WorkNet，目前更适合观察、整理资料和等官方 runtime 信号。",
        "why": "它已经进入发现面，但还没达到 workstation 可以放心自动化的资料密度。",
        "caution": "只要官方 skill URI 或 README 再变，这条知识就要优先复核，避免工作站误判可运行性。",
    },
}


def ranked_review_queue_entries(queue: dict, limit: int = 5) -> list[dict]:
    entries = queue.get("entries", []) if isinstance(queue.get("entries"), list) else []
    ranked = []
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        if not label:
            continue
        ranked.append((index, item))
    ranked.sort(
        key=lambda pair: (
            -PRIORITY_RANK.get(str(pair[1].get("priority") or "low"), 0),
            KIND_ORDER.get(str(pair[1].get("kind") or ""), 99),
            pair[0],
        )
    )
    return [item for _, item in ranked[:limit]]


def review_queue_recommendation(entry: dict) -> dict:
    kind = str(entry.get("kind") or "").strip()
    label = str(entry.get("label") or entry.get("key") or "").strip()
    action_prefix = {
        "source": "重读来源",
        "topic": "重审主题",
        "fact": "复核事实",
        "worknet": "复核 WorkNet 档案",
        "evidence": "复核证据",
    }.get(kind, "检查条目")
    reason = str(entry.get("reason") or "").strip() or "重新核对这个受影响条目。"
    return {
        "label": f"{action_prefix} {label}",
        "kind": kind,
        "key": entry.get("key"),
        "priority": entry.get("priority"),
        "description": reason,
        "command": entry.get("command"),
    }


def review_queue_summary_text(summary: dict) -> str:
    if not summary.get("hasPendingReviews"):
        return "当前本地百科没有待重审条目。"
    text = str(summary.get("headline") or "").strip()
    highest_priority = str(summary.get("highestPriority") or "").strip()
    if highest_priority:
        text += f" 当前最高优先级是 {highest_priority}。"
    focus_sources = [str(item).strip() for item in summary.get("focusSources", []) if str(item).strip()]
    focus_topics = [str(item).strip() for item in summary.get("focusTopics", []) if str(item).strip()]
    if focus_sources:
        text += f" 优先来源：{'、'.join(focus_sources[:3])}。"
    if focus_topics:
        text += f" 优先主题：{'、'.join(focus_topics[:3])}。"
    return text.strip()


def topic_narrative(
    topic: str,
    *,
    glossary_match: dict | None,
    dossier: dict | None,
    worknet: dict | None,
) -> dict | None:
    candidate_keys = [
        topic,
        str(dossier.get("key") or "").strip().lower() if isinstance(dossier, dict) else "",
        str(worknet.get("key") or "").strip().lower() if isinstance(worknet, dict) else "",
        str(glossary_match.get("term") or "").strip().lower() if isinstance(glossary_match, dict) else "",
    ]
    for key in candidate_keys:
        if key and key in TOPIC_NARRATIVES:
            return TOPIC_NARRATIVES[key]
    return None


def first_non_empty(*values: object) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def first_sentence(text: object) -> str | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    for marker in (". ", "。", "! ", "? "):
        if marker in raw:
            head = raw.split(marker, 1)[0].strip()
            if head:
                return head + ("。" if marker == "。" and not head.endswith("。") else "")
    return raw


def display_topic_label(
    topic: str,
    *,
    glossary_match: dict | None,
    dossier: dict | None,
    source_fact: dict | None,
    worknet: dict | None,
) -> str:
    return first_non_empty(
        dossier.get("title") if isinstance(dossier, dict) else None,
        worknet.get("name") if isinstance(worknet, dict) else None,
        glossary_match.get("term") if isinstance(glossary_match, dict) else None,
        source_fact.get("topic") if isinstance(source_fact, dict) else None,
        topic,
    ) or topic


def topic_worknet_context(
    topic: str,
    *,
    dossier: dict | None,
    worknet: dict | None,
) -> dict | None:
    if not isinstance(worknet, dict) or not worknet.get("key"):
        return None
    worknet_key = str(worknet.get("key") or "").strip().lower()
    dossier_key = str(dossier.get("key") or "").strip().lower() if isinstance(dossier, dict) else ""
    if worknet_key == topic or (dossier_key and dossier_key == worknet_key):
        return worknet
    return None


def resolved_topic_key(
    topic: str,
    *,
    glossary_match: dict | None,
    dossier: dict | None,
    worknet: dict | None,
) -> str:
    return first_non_empty(
        worknet.get("key") if isinstance(worknet, dict) else None,
        dossier.get("key") if isinstance(dossier, dict) else None,
        glossary_match.get("term") if isinstance(glossary_match, dict) else None,
        topic,
    ) or topic


def topic_plain_language(
    *,
    narrative: dict | None,
    glossary_match: dict | None,
    dossier: dict | None,
    source_fact: dict | None,
    worknet: dict | None,
) -> str | None:
    source_facts = source_fact.get("facts", []) if isinstance(source_fact, dict) else []
    return first_non_empty(
        narrative.get("plain") if isinstance(narrative, dict) else None,
        glossary_match.get("plainLanguage") if isinstance(glossary_match, dict) else None,
        dossier.get("summary") if isinstance(dossier, dict) else None,
        source_facts[0] if isinstance(source_facts, list) and source_facts else None,
        glossary_match.get("definition") if isinstance(glossary_match, dict) else None,
        worknet.get("goal") if isinstance(worknet, dict) else None,
    )


def freshness_affected_items(freshness: dict | None) -> list[dict]:
    if not isinstance(freshness, dict):
        return []
    items = freshness.get("items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict) and item.get("status") == "affected"]


def topic_headline(label: str, freshness: dict | None) -> str:
    if freshness_affected_items(freshness):
        return f"{label} 当前有上游变更待复核。"
    return f"{label} 当前资料可直接参考。"


def topic_summary(
    label: str,
    *,
    narrative: dict | None,
    glossary_match: dict | None,
    dossier: dict | None,
    source_fact: dict | None,
    worknet: dict | None,
    freshness: dict | None,
) -> str:
    parts: list[str] = []
    plain = topic_plain_language(
        narrative=narrative,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet,
    )
    if plain:
        parts.append(plain)
    why_it_matters = first_non_empty(
        narrative.get("why") if isinstance(narrative, dict) else None,
        glossary_match.get("whyItMatters") if isinstance(glossary_match, dict) else None,
        dossier.get("whyItExists") if isinstance(dossier, dict) else None,
    )
    if why_it_matters:
        parts.append(why_it_matters)
    if isinstance(worknet, dict) and worknet:
        automation = AUTOMATION_LABELS.get(str(worknet.get("automationLevel") or "").strip())
        risk = RISK_LABELS.get(str(worknet.get("riskLevel") or "").strip())
        loop_text = first_non_empty(
            narrative.get("loop") if isinstance(narrative, dict) else None,
            (f"默认节奏是 {worknet.get('loop')}。" if first_non_empty(worknet.get("loop")) else None),
        )
        posture = None
        if automation and risk:
            posture = f"这个 WorkNet 目前{automation}，整体属于{risk}。"
        elif automation:
            posture = f"这个 WorkNet 目前{automation}。"
        elif risk:
            posture = f"这个 WorkNet 当前属于{risk}。"
        parts.extend([item for item in (loop_text, posture) if item])
    affected = freshness_affected_items(freshness)
    if affected:
        affected_labels: list[str] = []
        source_names: list[str] = []
        for item in affected:
            label_text = str(item.get("label") or item.get("key") or "").strip()
            if label_text and label_text not in affected_labels:
                affected_labels.append(label_text)
            for impact in item.get("impactItems", []):
                if not isinstance(impact, dict):
                    continue
                source_name = str(impact.get("sourceName") or impact.get("sourceKey") or "").strip()
                if source_name and source_name not in source_names:
                    source_names.append(source_name)
        detail = f"当前这条知识要连同 {'、'.join(affected_labels[:3])} 一起复核。"
        if source_names:
            detail += f" 直接触发它的上游来源是 {'、'.join(source_names[:3])}。"
        parts.append(detail)
    else:
        parts.append("当前没有发现直接影响这条知识的上游变更。")
    caution = first_non_empty(narrative.get("caution") if isinstance(narrative, dict) else None)
    if caution:
        parts.append(caution)
    return " ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())


def topic_citations(
    evidence_matches: list[dict],
    *,
    source_records: dict[str, dict],
    dossier: dict | None,
    limit: int = 5,
) -> list[dict]:
    citations: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in evidence_matches[:limit]:
        if not isinstance(item, dict):
            continue
        source_key = str(item.get("sourceKey") or "").strip()
        claim = str(item.get("claim") or "").strip()
        key = (source_key, claim)
        if not source_key or not claim or key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "sourceKey": source_key,
                "sourceName": item.get("sourceName"),
                "url": item.get("sourceUrl"),
                "locator": item.get("locator"),
                "claim": claim,
                "evidenceType": item.get("evidenceType"),
                "stability": item.get("stability"),
            }
        )
    if citations:
        return citations
    if isinstance(dossier, dict):
        for source_key in dossier.get("sourceKeys", [])[:limit]:
            source_record = source_records.get(str(source_key), {})
            citations.append(
                {
                    "sourceKey": source_key,
                    "sourceName": source_record.get("name"),
                    "url": source_record.get("url"),
                    "locator": None,
                    "claim": None,
                    "evidenceType": source_record.get("kind"),
                    "stability": None,
                }
            )
    return citations


def topic_recommendations(
    topic: str,
    label: str,
    *,
    glossary_match: dict | None,
    dossier: dict | None,
    source_fact: dict | None,
    worknet: dict | None,
    freshness: dict | None,
    impact_matches: list[dict],
) -> list[dict]:
    recommendations: list[dict] = []
    seen: set[str] = set()

    def add(label_text: str | None, description: str, command: str | None) -> None:
        resolved_label = str(label_text or "").strip()
        resolved_command = str(command or "").strip()
        if not resolved_label or not resolved_command or resolved_label in seen:
            return
        seen.add(resolved_label)
        recommendations.append(
            {
                "label": resolved_label,
                "description": description,
                "command": resolved_command,
            }
        )

    affected = freshness_affected_items(freshness)
    if affected:
        add(
            f"重审 {label}",
            "重新拉取当前主题，确认上游变更有没有影响这条知识。",
            query_knowledge_command(topic, rebuild=True),
        )
        for item in impact_matches[:2]:
            source_key = str(item.get("sourceKey") or "").strip()
            source_name = str(item.get("sourceName") or source_key).strip()
            if source_key:
                add(
                    f"重读来源 {source_name}",
                    "先回到触发变更的官方来源，再决定本地知识要不要改。",
                    query_source_command(source_key, rebuild=True),
                )
    else:
        canonical_topic = resolved_topic_key(topic, glossary_match=glossary_match, dossier=dossier, worknet=worknet)
        add(
            f"刷新 {label}",
            "重新生成这条主题的本地百科条目，确认缓存仍然一致。",
            query_knowledge_command(canonical_topic, rebuild=True),
        )

    if isinstance(worknet, dict) and worknet.get("key"):
        worknet_key = str(worknet["key"])
        add(
            f"生成 {label} playbook",
            "把这条知识直接转成 workstation 可执行的 WorkPlaybook。",
            build_playbook_command(worknet_key),
        )
        add(
            "查看 WorkNet 扫描",
            "回到所有 WorkNet 的当前可运行性和风险对比。",
            scan_worknets_command(),
        )
    else:
        source_keys: list[str] = []
        for container in (dossier, source_fact, glossary_match):
            if not isinstance(container, dict):
                continue
            for source_key in container.get("sourceKeys", []):
                key = str(source_key).strip()
                if key and key not in source_keys:
                    source_keys.append(key)
        for source_key in source_keys[:2]:
            add(
                f"查看来源 {source_key}",
                "直接查看这条知识依赖的官方来源。",
                query_source_command(source_key),
            )

    return recommendations[:5]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--topic",
        required=True,
        help="Topic key such as protocol-core, mine, predict, gov, ardi, kya, or awp-skill.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the knowledge catalog instead of using the cached copy.",
    )
    args = parser.parse_args()

    catalog = build_knowledge_catalog() if args.rebuild else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    topic = args.topic.strip().lower()
    source_drift = catalog.get("sourceDrift", {}) if isinstance(catalog.get("sourceDrift"), dict) else {}
    source_impact = catalog.get("sourceImpact", {}) if isinstance(catalog.get("sourceImpact"), dict) else {}
    topic_freshness_catalog = catalog.get("topicFreshness", {}) if isinstance(catalog.get("topicFreshness"), dict) else {}
    knowledge_review_queue = catalog.get("knowledgeReviewQueue", {}) if isinstance(catalog.get("knowledgeReviewQueue"), dict) else {}
    if not knowledge_review_queue:
        knowledge_review_queue = load_cached_knowledge_review_queue() or build_knowledge_review_queue()

    if topic in {"upstream-drift", "source-drift", "source-impact", "stale", "outdated", "review-queue", "knowledge-review-queue", "stale-queue"}:
        source_records = {}
        sources = catalog.get("sources", {}) if isinstance(catalog.get("sources"), dict) else {}
        for item in sources.get("officialWebSources", []):
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item
        changed_sources = [
            {
                "key": item.get("key"),
                "name": item.get("name"),
                "status": item.get("status"),
                "changedFields": item.get("changedFields", []),
                "note": item.get("note"),
            }
            for item in source_drift.get("items", [])
            if isinstance(item, dict) and item.get("status") not in {"unchanged", "no-baseline"}
        ]
        impacts = [
            {
                "sourceKey": item.get("sourceKey"),
                "sourceName": item.get("sourceName"),
                "priority": item.get("priority"),
                "impactedTopics": [entry.get("key") for entry in item.get("impactedTopics", []) if isinstance(entry, dict)],
                "impactedFacts": [entry.get("key") for entry in item.get("impactedFacts", []) if isinstance(entry, dict)],
                "impactedWorknets": list(item.get("impactedWorknets", [])),
                "reviewHint": item.get("reviewHint"),
                "reviewCommands": item.get("reviewCommands"),
            }
            for item in source_impact.get("impacts", [])
            if isinstance(item, dict)
        ]
        review_queue_summary = summarize_knowledge_review_queue(knowledge_review_queue)
        focus_entries = ranked_review_queue_entries(knowledge_review_queue, limit=6)
        recommendations = [review_queue_recommendation(item) for item in focus_entries]
        citations = []
        for item in changed_sources:
            source_key = str(item.get("key") or "").strip()
            source_record = source_records.get(source_key, {})
            citations.append(
                {
                    "sourceKey": source_key,
                    "sourceName": item.get("name"),
                    "url": source_record.get("url"),
                    "kind": source_record.get("kind"),
                    "status": item.get("status"),
                    "changedFields": item.get("changedFields", []),
                    "note": item.get("note"),
                }
            )
        primary_command = None
        if recommendations and isinstance(recommendations[0].get("command"), str) and recommendations[0].get("command"):
            primary_command = recommendations[0]["command"]
        elif isinstance(review_queue_summary.get("primaryActionCommand"), str) and review_queue_summary.get("primaryActionCommand"):
            primary_command = review_queue_summary["primaryActionCommand"]
        print_json(
            {
                "topic": topic,
                "progress": "[3/5] Knowledge Review Queue",
                "headline": str(review_queue_summary.get("headline") or "当前没有待重审的知识条目。"),
                "summary": review_queue_summary_text(review_queue_summary),
                "primaryCommand": primary_command,
                "recommendations": recommendations,
                "citations": citations,
                "reviewQueueSummary": review_queue_summary,
                "reviewQueueTopEntries": focus_entries,
                "sourceDriftSummary": source_drift.get("summary"),
                "sourceImpactSummary": source_impact.get("summary"),
                "changedSources": changed_sources,
                "impacts": impacts,
                "reviewQueue": source_impact.get("reviewQueue"),
                "knowledgeReviewQueue": knowledge_review_queue,
            }
        )
        return

    dossier = next(
        (item for item in catalog.get("topicDossiers", []) if item.get("key") == topic),
        None,
    )
    source_facts = list(catalog.get("sourceFacts", []))
    source_evidence = list(catalog.get("sourceEvidence", []))
    glossary_terms = list(catalog.get("glossary", []))
    source_fact = next(
        (item for item in source_facts if item.get("key") == topic),
        None,
    )
    worknet = next(
        (item for item in catalog.get("worknets", []) if item.get("key") == topic),
        None,
    )
    if source_fact is None:
        related_source_keys = set()
        if dossier and dossier.get("sourceKeys"):
            related_source_keys.update(dossier["sourceKeys"])
        if worknet and worknet.get("sourceKeys"):
            related_source_keys.update(worknet["sourceKeys"])
        ranked = []
        for item in source_facts:
            score = 0
            key = str(item.get("key", "")).strip().lower()
            fact_topic = str(item.get("topic", "")).strip().lower()
            keys = set(item.get("sourceKeys", []))
            if key == topic:
                score += 100
            if topic in key:
                score += 50
            if topic == fact_topic:
                score += 40
            if topic in fact_topic:
                score += 20
            score += 5 * len(related_source_keys.intersection(keys))
            if score > 0:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        source_fact = ranked[0][1] if ranked else None

    ranked_evidence = []
    related_source_keys = set()
    if dossier and dossier.get("sourceKeys"):
        related_source_keys.update(dossier["sourceKeys"])
    if worknet and worknet.get("sourceKeys"):
        related_source_keys.update(worknet["sourceKeys"])
    if source_fact and source_fact.get("sourceKeys"):
        related_source_keys.update(source_fact["sourceKeys"])
    for item in source_evidence:
        score = 0
        if item.get("topicKey") == topic:
            score += 100
        source_key = item.get("sourceKey")
        item_source_keys = source_key if isinstance(source_key, list) else [source_key]
        overlap = related_source_keys.intersection(item_source_keys)
        score += 10 * len(overlap)
        if score > 0:
            ranked_evidence.append((score, item))
    ranked_evidence.sort(key=lambda pair: pair[0], reverse=True)
    evidence_matches = [item for _, item in ranked_evidence]

    glossary_match = next(
        (
            item
            for item in glossary_terms
            if topic == str(item.get("term", "")).strip().lower()
            or topic in {str(alias).strip().lower() for alias in item.get("aliases", [])}
        ),
        None,
    )

    if glossary_match:
        related_topics = [str(item).strip().lower() for item in glossary_match.get("relatedTopics", [])]
        if dossier is None:
            dossier = next(
                (item for item in catalog.get("topicDossiers", []) if item.get("key") in related_topics),
                dossier,
            )
        if worknet is None:
            worknet = next(
                (item for item in catalog.get("worknets", []) if item.get("key") in related_topics),
                worknet,
            )
        ranked_source_facts = []
        for item in source_facts:
            score = 0
            key = str(item.get("key", "")).strip().lower()
            fact_topic = str(item.get("topic", "")).strip().lower()
            item_source_keys = {str(source_key).strip().lower() for source_key in item.get("sourceKeys", [])}
            if key in related_topics:
                score += 100
            score += 30 * sum(1 for rel in related_topics if rel in fact_topic)
            score += 5 * sum(1 for rel in related_topics if rel in item_source_keys)
            if score > 0:
                ranked_source_facts.append((score, item))
        ranked_source_facts.sort(key=lambda pair: pair[0], reverse=True)
        if ranked_source_facts:
            source_fact = ranked_source_facts[0][1]

    related_topic_keys = {topic}
    related_source_keys = set()
    if glossary_match:
        related_topic_keys.update(str(item).strip().lower() for item in glossary_match.get("relatedTopics", []))
        related_source_keys.update(glossary_match.get("sourceKeys", []))
    if dossier:
        related_topic_keys.add(str(dossier.get("key", "")).strip().lower())
        related_source_keys.update(dossier.get("sourceKeys", []))
    if source_fact:
        related_topic_keys.add(str(source_fact.get("key", "")).strip().lower())
        related_source_keys.update(source_fact.get("sourceKeys", []))
    if worknet:
        related_topic_keys.add(str(worknet.get("key", "")).strip().lower())
        related_source_keys.update(worknet.get("sourceKeys", []))

    impact_matches = []
    for item in source_impact.get("impacts", []):
        if not isinstance(item, dict):
            continue
        impacted_topics = {
            str(entry.get("key", "")).strip().lower()
            for entry in item.get("impactedTopics", [])
            if isinstance(entry, dict) and entry.get("key")
        }
        impacted_facts = {
            str(entry.get("key", "")).strip().lower()
            for entry in item.get("impactedFacts", [])
            if isinstance(entry, dict) and entry.get("key")
        }
        impacted_worknets = {
            str(entry).strip().lower()
            for entry in item.get("impactedWorknets", [])
            if str(entry).strip()
        }
        source_key = str(item.get("sourceKey", "")).strip()
        if (
            impacted_topics.intersection(related_topic_keys)
            or impacted_facts.intersection(related_topic_keys)
            or impacted_worknets.intersection(related_topic_keys)
            or source_key in related_source_keys
        ):
            impact_matches.append(
                {
                    "sourceKey": item.get("sourceKey"),
                    "sourceName": item.get("sourceName"),
                    "priority": item.get("priority"),
                    "driftStatus": item.get("driftStatus"),
                    "reviewHint": item.get("reviewHint"),
                    "reviewCommands": item.get("reviewCommands"),
                }
            )

    freshness_matches = []
    for bucket in ("topics", "facts", "worknets"):
        for item in topic_freshness_catalog.get(bucket, []):
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "")).strip().lower()
            if key in related_topic_keys:
                freshness_matches.append(item)
    freshness_status = "stable"
    highest_priority = "low"
    priority_rank = {"low": 0, "medium": 1, "high": 2}
    for item in freshness_matches:
        if item.get("status") == "affected":
            freshness_status = "affected"
        priority = str(item.get("highestPriority") or "low")
        if priority_rank.get(priority, 0) > priority_rank.get(highest_priority, 0):
            highest_priority = priority

    source_records = {}
    sources = catalog.get("sources", {}) if isinstance(catalog.get("sources"), dict) else {}
    for bucket in ("officialWebSources", "localSources"):
        for item in sources.get(bucket, []):
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item

    worknet_context = topic_worknet_context(
        topic,
        dossier=dossier,
        worknet=worknet,
    )
    narrative = topic_narrative(
        topic,
        glossary_match=glossary_match,
        dossier=dossier,
        worknet=worknet_context,
    )
    label = display_topic_label(
        topic,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet_context,
    )
    summary = topic_summary(
        label,
        narrative=narrative,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet_context,
        freshness={"status": freshness_status, "highestPriority": highest_priority, "items": freshness_matches},
    )
    recommendations = topic_recommendations(
        topic,
        label,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet_context,
        freshness={"status": freshness_status, "highestPriority": highest_priority, "items": freshness_matches},
        impact_matches=impact_matches,
    )
    citations = topic_citations(
        evidence_matches,
        source_records=source_records,
        dossier=dossier,
    )
    primary_command = None
    if recommendations and isinstance(recommendations[0].get("command"), str) and recommendations[0].get("command"):
        primary_command = recommendations[0]["command"]

    result = {
        "topic": topic,
        "resolvedTopicKey": resolved_topic_key(
            topic,
            glossary_match=glossary_match,
            dossier=dossier,
            worknet=worknet_context,
        ),
        "resolvedTopicLabel": label,
        "progress": "[2/5] Knowledge Query",
        "headline": topic_headline(
            label,
            {"status": freshness_status, "highestPriority": highest_priority, "items": freshness_matches},
        ),
        "summary": summary,
        "plainLanguage": topic_plain_language(
            narrative=narrative,
            glossary_match=glossary_match,
            dossier=dossier,
            source_fact=source_fact,
            worknet=worknet_context,
        ),
        "primaryCommand": primary_command,
        "recommendations": recommendations,
        "citations": citations,
        "glossary": glossary_match,
        "dossier": dossier,
        "sourceFact": source_fact,
        "evidence": evidence_matches,
        "worknet": worknet,
        "sourceImpact": {
            "affected": bool(impact_matches),
            "items": impact_matches,
        },
        "freshness": {
            "status": freshness_status,
            "highestPriority": highest_priority,
            "items": freshness_matches,
        },
    }
    print_json(result)


if __name__ == "__main__":
    main()
