"""Knowledge query result builder."""

from __future__ import annotations

from typing import Any, Optional


def build_knowledge_query_result_payload(
    topic: str,
    *,
    catalog: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("knowledge query dependencies are required")
    KNOWLEDGE_ATLAS_QUERY_FIELDS = dependencies["KNOWLEDGE_ATLAS_QUERY_FIELDS"]
    KNOWLEDGE_QUERY_FIELDS = dependencies["KNOWLEDGE_QUERY_FIELDS"]
    KNOWLEDGE_QUEUE_PRIORITY_RANK = dependencies["KNOWLEDGE_QUEUE_PRIORITY_RANK"]
    KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS = dependencies["KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS"]
    action_details_from_ui_actions = dependencies["action_details_from_ui_actions"]
    annotate_research_action_details = dependencies["annotate_research_action_details"]
    append_unique_action_detail = dependencies["append_unique_action_detail"]
    build_concept_query_result = dependencies["build_concept_query_result"]
    build_knowledge_catalog = dependencies["build_knowledge_catalog"]
    build_knowledge_review_queue = dependencies["build_knowledge_review_queue"]
    build_research_action_groups = dependencies["build_research_action_groups"]
    build_skill_inspect_command = dependencies["build_skill_inspect_command"]
    canonical_topic_narrative = dependencies["canonical_topic_narrative"]
    capability_reports_by_worknet_key = dependencies["capability_reports_by_worknet_key"]
    compact_preview_text = dependencies["compact_preview_text"]
    execution_state_payload = dependencies["execution_state_payload"]
    find_concept_match = dependencies["find_concept_match"]
    find_topic_directory_entry = dependencies["find_topic_directory_entry"]
    frontload_user_action_labels = dependencies["frontload_user_action_labels"]
    humanize_knowledge_source_label = dependencies["humanize_knowledge_source_label"]
    join_product_sentences = dependencies["join_product_sentences"]
    knowledge_display_changed_sources = dependencies["knowledge_display_changed_sources"]
    knowledge_display_citations = dependencies["knowledge_display_citations"]
    knowledge_display_dossier = dependencies["knowledge_display_dossier"]
    knowledge_display_evidence = dependencies["knowledge_display_evidence"]
    knowledge_display_freshness = dependencies["knowledge_display_freshness"]
    knowledge_display_review_queue_entries = dependencies["knowledge_display_review_queue_entries"]
    knowledge_display_source_fact = dependencies["knowledge_display_source_fact"]
    knowledge_display_source_impact = dependencies["knowledge_display_source_impact"]
    knowledge_display_topic_label = dependencies["knowledge_display_topic_label"]
    knowledge_display_worknet = dependencies["knowledge_display_worknet"]
    knowledge_focus_topics_payload = dependencies["knowledge_focus_topics_payload"]
    knowledge_related_reference_highlights = dependencies["knowledge_related_reference_highlights"]
    knowledge_related_source_highlights = dependencies["knowledge_related_source_highlights"]
    knowledge_resolved_topic_key = dependencies["knowledge_resolved_topic_key"]
    knowledge_review_queue_recommendation = dependencies["knowledge_review_queue_recommendation"]
    knowledge_review_queue_summary_text = dependencies["knowledge_review_queue_summary_text"]
    knowledge_runtime_probe_display_for_topic = dependencies["knowledge_runtime_probe_display_for_topic"]
    knowledge_runtime_probe_evidence_entries = dependencies["knowledge_runtime_probe_evidence_entries"]
    knowledge_source_action_description = dependencies["knowledge_source_action_description"]
    knowledge_source_records_from_catalog = dependencies["knowledge_source_records_from_catalog"]
    knowledge_topic_citations = dependencies["knowledge_topic_citations"]
    knowledge_topic_execution_state = dependencies["knowledge_topic_execution_state"]
    knowledge_topic_headline = dependencies["knowledge_topic_headline"]
    knowledge_topic_plain_language = dependencies["knowledge_topic_plain_language"]
    knowledge_topic_recommendations = dependencies["knowledge_topic_recommendations"]
    knowledge_topic_summary = dependencies["knowledge_topic_summary"]
    knowledge_topic_worknet_context = dependencies["knowledge_topic_worknet_context"]
    knowledge_worknet_metadata = dependencies["knowledge_worknet_metadata"]
    load_cached_capability_bundle = dependencies["load_cached_capability_bundle"]
    load_cached_knowledge_catalog = dependencies["load_cached_knowledge_catalog"]
    load_cached_knowledge_review_queue = dependencies["load_cached_knowledge_review_queue"]
    normalize_concept_payload = dependencies["normalize_concept_payload"]
    normalize_glossary_item_payload = dependencies["normalize_glossary_item_payload"]
    normalize_knowledge_atlas_gap_payload = dependencies["normalize_knowledge_atlas_gap_payload"]
    normalize_knowledge_directory_entry_payload = dependencies["normalize_knowledge_directory_entry_payload"]
    normalize_knowledge_overview_payload = dependencies["normalize_knowledge_overview_payload"]
    normalize_knowledge_review_queue_summary = dependencies["normalize_knowledge_review_queue_summary"]
    normalize_query_payload = dependencies["normalize_query_payload"]
    normalize_source_directory_entry_payload = dependencies["normalize_source_directory_entry_payload"]
    preferred_worknet_source_keys_for_runtime_state = dependencies["preferred_worknet_source_keys_for_runtime_state"]
    prioritize_action_entries = dependencies["prioritize_action_entries"]
    query_knowledge_command = dependencies["query_knowledge_command"]
    query_source_command = dependencies["query_source_command"]
    ranked_knowledge_review_queue_entries = dependencies["ranked_knowledge_review_queue_entries"]
    render_argv = dependencies["render_argv"]
    scan_worknets_command = dependencies["scan_worknets_command"]
    state_context = dependencies["state_context"]
    summarize_knowledge_review_queue = dependencies["summarize_knowledge_review_queue"]

    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    topic = str(topic or "").strip().lower()
    source_drift = catalog.get("sourceDrift", {}) if isinstance(catalog.get("sourceDrift"), dict) else {}
    source_impact = catalog.get("sourceImpact", {}) if isinstance(catalog.get("sourceImpact"), dict) else {}
    topic_freshness_catalog = catalog.get("topicFreshness", {}) if isinstance(catalog.get("topicFreshness"), dict) else {}
    knowledge_review_queue = catalog.get("knowledgeReviewQueue", {}) if isinstance(catalog.get("knowledgeReviewQueue"), dict) else {}
    if not knowledge_review_queue:
        knowledge_review_queue = load_cached_knowledge_review_queue() or build_knowledge_review_queue()

    if topic in {"atlas", "overview", "knowledge-atlas", "encyclopedia", "network-map"}:
        state = state_context()
        knowledge_overview = (
            catalog.get("knowledgeOverview", {})
            if isinstance(catalog.get("knowledgeOverview"), dict)
            else {}
        )
        queue_summary = summarize_knowledge_review_queue(knowledge_review_queue)
        focus_topics = knowledge_overview.get("focusTopics") if isinstance(knowledge_overview.get("focusTopics"), list) else knowledge_focus_topics_payload(catalog, limit=6)
        topic_directory = [
            normalize_knowledge_directory_entry_payload(item)
            for item in catalog.get("topicDirectory", [])
            if isinstance(item, dict)
        ] if isinstance(catalog.get("topicDirectory"), list) else []
        worknet_directory = [
            item
            for item in topic_directory
            if isinstance(item, dict)
            and (
                str(item.get("worknetKey") or "").strip()
                or str(item.get("kind") or "").strip() in {"worknet", "worknet-service", "testnet"}
            )
        ]
        reference_directory = [
            normalize_knowledge_directory_entry_payload(item)
            for item in catalog.get("referenceIndex", [])
            if isinstance(item, dict)
        ] if isinstance(catalog.get("referenceIndex"), list) else []
        source_directory = [
            normalize_source_directory_entry_payload(item)
            for item in catalog.get("sourceDirectory", [])
            if isinstance(item, dict)
        ] if isinstance(catalog.get("sourceDirectory"), list) else []
        concept_directory = [
            normalize_concept_payload(item)
            for item in catalog.get("conceptDirectory", catalog.get("concepts", []))
            if isinstance(item, dict)
        ] if isinstance(catalog.get("conceptDirectory", catalog.get("concepts", [])), list) else []
        glossary_directory = [
            normalize_glossary_item_payload(item)
            for item in catalog.get("glossary", [])
            if isinstance(item, dict)
        ] if isinstance(catalog.get("glossary"), list) else []

        capability_reports = capability_reports_by_worknet_key(
            state=state,
            bundle=load_cached_capability_bundle(state),
        )
        skill_registry = {
            str(item.get("key") or "").strip(): item
            for item in catalog.get("skills", [])
            if isinstance(item, dict) and str(item.get("key") or "").strip()
        } if isinstance(catalog.get("skills"), list) else {}
        source_records = knowledge_source_records_from_catalog(catalog)
        atlas_gaps: list[dict[str, Any]] = []

        def add_gap(
            *,
            key: str,
            label: str,
            category: str,
            status: str,
            summary: str,
            worknet_key: Optional[str],
            worknet_name: Optional[str],
            source_key: Optional[str],
            recommended_action_label: Optional[str],
            recommended_action_command: Optional[str],
        ) -> None:
            atlas_gaps.append(
                normalize_knowledge_atlas_gap_payload(
                    {
                        "key": key,
                        "label": label,
                        "category": category,
                        "status": status,
                        "summary": summary,
                        "worknetKey": worknet_key,
                        "worknetName": worknet_name,
                        "sourceKey": source_key,
                        "sourceName": (
                            source_records.get(source_key, {}).get("name")
                            if isinstance(source_records.get(source_key), dict)
                            else source_key
                        ) if source_key else None,
                        "recommendedActionLabel": recommended_action_label,
                        "recommendedActionCommand": recommended_action_command,
                    }
                )
            )

        for worknet_item in catalog.get("worknets", []) if isinstance(catalog.get("worknets"), list) else []:
            if not isinstance(worknet_item, dict):
                continue
            worknet_key = str(worknet_item.get("key") or "").strip()
            if not worknet_key:
                continue
            worknet_name = str(worknet_item.get("name") or worknet_key).strip()
            skill_record = skill_registry.get(worknet_key, {})
            capability = capability_reports.get(worknet_key, {})
            worknet_metadata = knowledge_worknet_metadata(
                worknet_key=worknet_key,
                worknet_id=worknet_item.get("worknetId"),
                source_keys=worknet_item.get("sourceKeys", []),
                install_uri=worknet_item.get("installUri"),
                capability_report=capability,
            )
            runtime_spec_state = str(worknet_metadata.get("runtimeSpecState") or "").strip()
            runtime_spec_state_display = str(worknet_metadata.get("runtimeSpecStateDisplay") or "").strip()
            source_keys = [
                str(value).strip()
                for value in worknet_item.get("sourceKeys", [])
                if str(value).strip()
            ]
            preferred_source_keys = preferred_worknet_source_keys_for_runtime_state(
                source_keys,
                runtime_spec_state=runtime_spec_state or None,
                source_records=source_records,
            )
            preferred_source_key = next(
                (
                    key_name
                    for key_name in preferred_source_keys
                ),
                (
                    next((key_name for key_name in source_keys if key_name not in {"awp-live-query"}), None)
                    or (source_keys[0] if source_keys else None)
                ),
            )
            cli_status = str(capability.get("cliStatus") or "").strip()
            registry_status = str(skill_record.get("status") or "").strip()
            if runtime_spec_state in {"thin-repo-only", "thin-repo-plus-hub"}:
                summary = "Live WorkNet ID and skill URI are known, but public runtime operator details are still thin."
                if runtime_spec_state == "thin-repo-plus-hub":
                    summary = "Live WorkNet ID, skill URI, and community hub context are known, but runtime details remain thin."
                add_gap(
                    key=f"{worknet_key}-{runtime_spec_state or 'thin-public-sources'}",
                    label=f"{worknet_name} source coverage",
                    category="thin-public-sources",
                    status=runtime_spec_state or "thin",
                    summary=join_product_sentences(
                        [
                            summary,
                            f"Runtime spec state: {runtime_spec_state_display}." if runtime_spec_state_display else None,
                            (
                                f"Canonical ID: {worknet_metadata.get('canonicalWorknetId')}. "
                                f"minStake hint: {worknet_metadata.get('minStakeHintDisplay')}."
                                if worknet_metadata.get("canonicalWorknetId") or worknet_metadata.get("minStakeHintDisplay")
                                else None
                            ),
                        ]
                    ) or summary,
                    worknet_key=worknet_key,
                    worknet_name=worknet_name,
                    source_key=preferred_source_key,
                    recommended_action_label=f"Review source {humanize_knowledge_source_label(preferred_source_key)}" if preferred_source_key else "Review WorkNet options",
                    recommended_action_command=query_source_command(preferred_source_key) if preferred_source_key else scan_worknets_command(),
                )
                continue
            if runtime_spec_state == "runtime-doc-available" and registry_status in {"official-remote", "missing"}:
                inspect_command = build_skill_inspect_command(worknet_key)
                add_gap(
                    key=f"{worknet_key}-runtime-doc-available",
                    label=f"{worknet_name} runtime evidence",
                    category="runtime-evidence",
                    status=runtime_spec_state,
                    summary=join_product_sentences(
                        [
                            "WorkNet live ID and skill URI are available.",
                            f"Runtime spec state: {runtime_spec_state_display}." if runtime_spec_state_display else None,
                            (
                                f"Canonical ID: {worknet_metadata.get('canonicalWorknetId')}. "
                                f"minStake hint: {worknet_metadata.get('minStakeHintDisplay')}."
                                if worknet_metadata.get("canonicalWorknetId") or worknet_metadata.get("minStakeHintDisplay")
                                else None
                            ),
                            "Runtime checkout still needs local inspection.",
                        ]
                    ),
                    worknet_key=worknet_key,
                    worknet_name=worknet_name,
                    source_key=preferred_source_key,
                    recommended_action_label=f"Inspect {worknet_name} skill",
                    recommended_action_command=render_argv([str(part) for part in inspect_command.get('argv', [])]) if isinstance(inspect_command.get("argv"), list) else None,
                )
                continue
            if registry_status in {"official-remote", "missing"}:
                inspect_command = build_skill_inspect_command(worknet_key)
                add_gap(
                    key=f"{worknet_key}-runtime-install-gap",
                    label=f"{worknet_name} runtime install",
                    category="runtime-evidence",
                    status=registry_status,
                    summary="Runtime checkout and local inspection are still required before execution.",
                    worknet_key=worknet_key,
                    worknet_name=worknet_name,
                    source_key=preferred_source_key,
                    recommended_action_label=f"Inspect {worknet_name} skill",
                    recommended_action_command=render_argv([str(part) for part in inspect_command.get("argv", [])]) if isinstance(inspect_command.get("argv"), list) else None,
                )
                continue
            if cli_status in {"remote-profile-only", "empty-official-repo", "installed-needs-bootstrap", "runtime-error", "network-blocked"}:
                inspect_command = build_skill_inspect_command(worknet_key)
                add_gap(
                    key=f"{worknet_key}-{cli_status or 'runtime-gap'}",
                    label=f"{worknet_name} runtime status",
                    category="runtime-evidence",
                    status=cli_status or "runtime-gap",
                    summary="WorkNet runtime is not ready; inspect the runtime before executing live work.",
                    worknet_key=worknet_key,
                    worknet_name=worknet_name,
                    source_key=preferred_source_key,
                    recommended_action_label=f"Inspect {worknet_name} skill",
                    recommended_action_command=render_argv([str(part) for part in inspect_command.get("argv", [])]) if isinstance(inspect_command.get("argv"), list) else None,
                )

        status = "knowledge_review_needed" if atlas_gaps or queue_summary.get("hasPendingReviews") else "knowledge_ready"
        execution_payload = execution_state_payload(
            "review_required" if atlas_gaps or queue_summary.get("hasPendingReviews") else "knowledge_ready",
            headline=(
                "AWP knowledge atlas needs review before WorkNet execution."
                if atlas_gaps or queue_summary.get("hasPendingReviews")
                else "AWP knowledge atlas is ready."
            ),
        )
        summary = (
            f"Knowledge atlas includes {len(topic_directory)} topics, "
            f"{len(reference_directory)} references, "
            f"{len(source_directory)} sources, "
            f"{len(glossary_directory)} glossary terms, and {len(concept_directory)} concepts."
        )
        if atlas_gaps:
            summary += f" {len(atlas_gaps)} runtime or WorkNet coverage gap(s) need review."
        else:
            summary += " No runtime coverage gaps are currently flagged."

        recommendations: list[dict[str, Any]] = []
        for gap in atlas_gaps[:5]:
            if not isinstance(gap, dict):
                continue
            label = str(gap.get("recommendedActionLabel") or "").strip()
            command = str(gap.get("recommendedActionCommand") or "").strip()
            if not label or not command:
                continue
            recommendations.append(
                {
                    "label": label,
                    "description": str(gap.get("summary") or "Review this knowledge atlas gap.").strip(),
                    "command": command,
                }
            )
        recommendations.extend(
            [
                {
                    "label": "Review AWP Protocol Core",
                    "description": "Open protocol-level RootNet and WorkNet context.",
                    "command": query_knowledge_command("protocol-core"),
                },
                {
                    "label": "Review WorkNet options",
                    "description": "Scan WorkNet capability reports and selectable routes.",
                    "command": scan_worknets_command(),
                },
                {
                    "label": "Review pending knowledge updates",
                    "description": "Open the knowledge review queue.",
                    "command": query_knowledge_command("review-queue"),
                },
                {
                    "label": "Rebuild AWP Knowledge Atlas",
                    "description": "Rebuild the atlas from current local source and runtime cache data.",
                    "command": query_knowledge_command("atlas", rebuild=True),
                },
            ]
        )
        recommendations = prioritize_action_entries(
            recommendations,
            execution_state=execution_payload.get("executionState"),
            resume_status=None,
            worknet_key=None,
        )
        action_map = {
            str(item.get("label") or "").strip(): str(item.get("command") or "").strip()
            for item in recommendations
            if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("command") or "").strip()
        }
        user_action_details = action_details_from_ui_actions(recommendations, action_map)
        current_labels: list[str] = []
        worknet_labels: list[str] = []
        source_labels: list[str] = []
        control_labels: list[str] = []
        topic_labels: list[str] = []
        for index, item in enumerate(user_action_details):
            if not isinstance(item, dict):
                continue
            label_text = str(item.get("label") or "").strip()
            if not label_text:
                continue
            if index == 0 or label_text.startswith(("Review AWP", "Rebuild AWP", "Inspect ")):
                current_labels.append(label_text)
            elif label_text.startswith("Review source"):
                source_labels.append(label_text)
            elif label_text.startswith(("Review WorkNet", "Start ")):
                worknet_labels.append(label_text)
            elif label_text in {"Review pending knowledge updates", "Refresh knowledge review queue"}:
                control_labels.append(label_text)
            else:
                topic_labels.append(label_text)
        user_action_details = annotate_research_action_details(
            user_action_details,
            current_labels=current_labels,
            control_labels=control_labels,
            source_labels=source_labels,
            topic_labels=topic_labels,
            worknet_labels=worknet_labels,
            reference_labels=[],
            current_tier="current",
            control_tier="queued",
            source_tier="queued",
            topic_tier="overview",
            worknet_tier="overview",
        )
        research_action_groups = build_research_action_groups(
            user_action_details,
            current_labels=current_labels,
            control_labels=control_labels,
            source_labels=source_labels,
            topic_labels=topic_labels,
            worknet_labels=worknet_labels,
            reference_labels=[],
            control_first=False,
        )
        recommendations = annotate_research_action_details(
            recommendations,
            current_labels=current_labels,
            control_labels=control_labels,
            source_labels=source_labels,
            topic_labels=topic_labels,
            worknet_labels=worknet_labels,
            reference_labels=[],
            current_tier="current",
            control_tier="queued",
            source_tier="queued",
            topic_tier="overview",
            worknet_tier="overview",
        )
        return normalize_query_payload(
            {
                "topic": topic,
                "status": status,
                "resolvedTopicKey": "atlas",
                "resolvedTopicLabel": "AWP Knowledge Atlas",
                "progress": "[1/5] Knowledge Atlas",
                "headline": "AWP Knowledge Atlas",
                "summary": summary,
                "plainLanguage": "AWP Knowledge Atlas summarizes protocol, WorkNet, source, glossary, and runtime coverage.",
                "executionState": execution_payload.get("executionState"),
                "executionStateDisplay": execution_payload.get("executionStateDisplay"),
                "executionHeadline": execution_payload.get("executionHeadline"),
                "primaryCommand": user_action_details[0]["command"] if user_action_details else None,
                "primaryUserAction": user_action_details[0]["label"] if user_action_details else None,
                "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
                "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
                "userActionDetails": user_action_details,
                "researchActionGroups": research_action_groups,
                "recommendations": recommendations,
                "knowledgeOverview": normalize_knowledge_overview_payload(knowledge_overview),
                "reviewQueueSummary": normalize_knowledge_review_queue_summary(queue_summary),
                "focusTopics": focus_topics,
                "worknetDirectory": worknet_directory,
                "topicDirectory": topic_directory,
                "referenceDirectory": reference_directory,
                "sourceDirectory": source_directory,
                "glossaryDirectory": glossary_directory,
                "conceptDirectory": concept_directory,
                "atlasGaps": atlas_gaps,
            },
            KNOWLEDGE_ATLAS_QUERY_FIELDS,
        )

    if topic in {"upstream-drift", "source-drift", "source-impact", "stale", "outdated", "review-queue", "knowledge-review-queue", "stale-queue"}:
        source_records: dict[str, dict[str, Any]] = {}
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
        focus_entries = ranked_knowledge_review_queue_entries(knowledge_review_queue, limit=6)
        status = "stale_knowledge_pending" if review_queue_summary.get("hasPendingReviews") else "knowledge_ready"
        recommendations = [
            knowledge_review_queue_recommendation(item)
            for item in focus_entries
        ]
        recommendations = prioritize_action_entries(
            recommendations,
            execution_state=status,
            resume_status=None,
            worknet_key=None,
        )
        changed_sources_display = knowledge_display_changed_sources(changed_sources, source_records=source_records)
        impacts_display = knowledge_display_source_impact(
            {"affected": bool(impacts), "items": impacts},
            catalog=catalog,
        )
        review_queue_top_entries_display = knowledge_display_review_queue_entries(
            focus_entries,
            catalog=catalog,
        )
        citations: list[dict[str, Any]] = []
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
        action_map = {
            str(item.get("label") or "").strip(): str(item.get("command") or "").strip()
            for item in recommendations
            if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("command") or "").strip()
        }
        user_action_details = action_details_from_ui_actions(recommendations, action_map)
        refresh_label = str(review_queue_summary.get("refreshActionLabel") or "").strip()
        refresh_command = str(review_queue_summary.get("refreshActionCommand") or "").strip()
        if refresh_label and refresh_command:
            append_unique_action_detail(
                user_action_details,
                label=refresh_label,
                description="Refresh the knowledge review queue from the latest source drift data.",
                command=refresh_command,
            )
        current_labels: list[str] = []
        source_labels: list[str] = []
        topic_labels: list[str] = []
        control_labels: list[str] = []
        for index, item in enumerate(user_action_details):
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if not label:
                continue
            if index == 0:
                current_labels.append(label)
            elif label.startswith(("Review source", "Refresh source")):
                source_labels.append(label)
            elif label.startswith(("Review topic", "Refresh topic", "Research topic")):
                topic_labels.append(label)
            elif label in {refresh_label, "Review pending knowledge updates"}:
                control_labels.append(label)
        user_action_details = annotate_research_action_details(
            user_action_details,
            current_labels=current_labels,
            control_labels=control_labels,
            source_labels=source_labels,
            topic_labels=topic_labels,
            worknet_labels=[],
            reference_labels=[],
            current_tier="current",
            control_tier="queued",
            source_tier="queued",
            topic_tier="queued",
        )
        execution_payload = execution_state_payload(
            status,
            headline=str(review_queue_summary.get("headline") or "Knowledge review queue is ready."),
        )
        research_action_groups = build_research_action_groups(
            user_action_details,
            current_labels=current_labels,
            control_labels=control_labels,
            source_labels=source_labels,
            topic_labels=topic_labels,
            worknet_labels=[],
            reference_labels=[],
            control_first=False,
        )
        recommendations = annotate_research_action_details(
            recommendations,
            current_labels=current_labels,
            control_labels=control_labels,
            source_labels=source_labels,
            topic_labels=topic_labels,
            worknet_labels=[],
            reference_labels=[],
            current_tier="current",
            control_tier="queued",
            source_tier="queued",
            topic_tier="queued",
        )
        return normalize_query_payload({
            "topic": topic,
            "status": status,
            "progress": "[3/5] Knowledge Review Queue",
            "headline": str(review_queue_summary.get("headline") or "Knowledge review queue"),
            "summary": knowledge_review_queue_summary_text(review_queue_summary),
            "executionState": execution_payload.get("executionState"),
            "executionStateDisplay": execution_payload.get("executionStateDisplay"),
            "executionHeadline": execution_payload.get("executionHeadline"),
            "primaryCommand": primary_command,
            "primaryUserAction": user_action_details[0]["label"] if user_action_details else None,
            "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
            "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
            "userActionDetails": user_action_details,
            "researchActionGroups": research_action_groups,
            "recommendations": recommendations,
            "citations": citations,
            "reviewQueueSummary": review_queue_summary,
            "reviewQueueTopEntries": focus_entries,
            "reviewQueueTopEntriesDisplay": review_queue_top_entries_display,
            "sourceDriftSummary": source_drift.get("summary"),
            "sourceImpactSummary": source_impact.get("summary"),
            "changedSources": changed_sources,
            "changedSourcesDisplay": changed_sources_display,
            "impacts": impacts,
            "impactsDisplay": impacts_display,
            "reviewQueue": source_impact.get("reviewQueue"),
            "knowledgeReviewQueue": knowledge_review_queue,
        }, KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS)

    dossiers = catalog.get("topicDossiers", []) if isinstance(catalog.get("topicDossiers"), list) else []
    source_facts = list(catalog.get("sourceFacts", []))
    source_evidence = list(catalog.get("sourceEvidence", []))
    glossary_terms = list(catalog.get("glossary", []))
    concepts = list(catalog.get("conceptDirectory", catalog.get("concepts", []))) if isinstance(catalog.get("conceptDirectory", catalog.get("concepts", [])), list) else []
    worknets = catalog.get("worknets", []) if isinstance(catalog.get("worknets"), list) else []
    concept_match = find_concept_match(concepts, topic)
    if isinstance(concept_match, dict):
        return build_concept_query_result(
            topic,
            concept_match,
            catalog=catalog,
            source_impact=source_impact,
            topic_freshness_catalog=topic_freshness_catalog,
            knowledge_review_queue=knowledge_review_queue,
        )

    dossier = next((item for item in dossiers if item.get("key") == topic), None)
    source_fact = next((item for item in source_facts if item.get("key") == topic), None)
    worknet = next((item for item in worknets if item.get("key") == topic), None)
    direct_dossier_match = isinstance(dossier, dict)
    direct_source_fact_match = isinstance(source_fact, dict)
    direct_worknet_match = isinstance(worknet, dict)
    if source_fact is None:
        related_source_keys: set[str] = set()
        if isinstance(dossier, dict) and dossier.get("sourceKeys"):
            related_source_keys.update(dossier["sourceKeys"])
        if isinstance(worknet, dict) and worknet.get("sourceKeys"):
            related_source_keys.update(worknet["sourceKeys"])
        ranked: list[tuple[int, dict[str, Any]]] = []
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

    ranked_evidence: list[tuple[int, dict[str, Any]]] = []
    related_source_keys: set[str] = set()
    if isinstance(dossier, dict) and dossier.get("sourceKeys"):
        related_source_keys.update(dossier["sourceKeys"])
    if isinstance(worknet, dict) and worknet.get("sourceKeys"):
        related_source_keys.update(worknet["sourceKeys"])
    if isinstance(source_fact, dict) and source_fact.get("sourceKeys"):
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

    if isinstance(glossary_match, dict):
        related_topics = [str(item).strip().lower() for item in glossary_match.get("relatedTopics", [])]
        if dossier is None:
            dossier = next((item for item in dossiers if item.get("key") in related_topics), dossier)
        if worknet is None:
            worknet = next((item for item in worknets if item.get("key") in related_topics), worknet)
        ranked_source_facts: list[tuple[int, dict[str, Any]]] = []
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
    glossary_primary_match = (
        isinstance(glossary_match, dict)
        and not direct_dossier_match
        and not direct_source_fact_match
        and not direct_worknet_match
    )

    related_topic_keys = {topic}
    related_source_keys = set()
    if isinstance(glossary_match, dict):
        related_topic_keys.update(str(item).strip().lower() for item in glossary_match.get("relatedTopics", []))
        related_source_keys.update(glossary_match.get("sourceKeys", []))
    if isinstance(dossier, dict):
        related_topic_keys.add(str(dossier.get("key", "")).strip().lower())
        related_source_keys.update(dossier.get("sourceKeys", []))
    if isinstance(source_fact, dict):
        related_topic_keys.add(str(source_fact.get("key", "")).strip().lower())
        related_source_keys.update(source_fact.get("sourceKeys", []))
    if isinstance(worknet, dict):
        related_topic_keys.add(str(worknet.get("key", "")).strip().lower())
        related_source_keys.update(worknet.get("sourceKeys", []))

    impact_matches: list[dict[str, Any]] = []
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

    freshness_matches: list[dict[str, Any]] = []
    for bucket in ("topics", "facts", "worknets"):
        for item in topic_freshness_catalog.get(bucket, []):
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "")).strip().lower()
            if key in related_topic_keys:
                freshness_matches.append(item)
    freshness_status = "stable"
    highest_priority = "low"
    for item in freshness_matches:
        if item.get("status") == "affected":
            freshness_status = "affected"
        priority = str(item.get("highestPriority") or "low")
        if KNOWLEDGE_QUEUE_PRIORITY_RANK.get(priority, 0) > KNOWLEDGE_QUEUE_PRIORITY_RANK.get(highest_priority, 0):
            highest_priority = priority

    source_records: dict[str, dict[str, Any]] = {}
    sources = catalog.get("sources", {}) if isinstance(catalog.get("sources"), dict) else {}
    for bucket in ("officialWebSources", "localSources"):
        for item in sources.get(bucket, []):
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item

    worknet_context = knowledge_topic_worknet_context(topic, dossier=dossier, worknet=worknet)
    narrative = canonical_topic_narrative(
        topic,
        dossier_key=(
            None
            if glossary_primary_match
            else str(dossier.get("key") or "") if isinstance(dossier, dict) else None
        ),
        worknet_key=str(worknet_context.get("key") or "") if isinstance(worknet_context, dict) else None,
        glossary_term=str(glossary_match.get("term") or "") if isinstance(glossary_match, dict) else None,
    )
    label = (
        str(glossary_match.get("term") or topic).strip()
        if glossary_primary_match and isinstance(glossary_match, dict)
        else knowledge_display_topic_label(
            topic,
            glossary_match=glossary_match,
            dossier=dossier,
            source_fact=source_fact,
            worknet=worknet_context,
        )
    )
    capability_reports = capability_reports_by_worknet_key()
    capability_report = None
    if isinstance(worknet_context, dict) and str(worknet_context.get("key") or "").strip():
        capability_report = capability_reports.get(str(worknet_context.get("key") or "").strip())
    worknet_metadata = knowledge_worknet_metadata(
        worknet_key=worknet_context.get("key") if isinstance(worknet_context, dict) else None,
        worknet_id=worknet_context.get("worknetId") if isinstance(worknet_context, dict) else None,
        source_keys=(
            worknet_context.get("sourceKeys", [])
            if isinstance(worknet_context, dict)
            else (
                dossier.get("sourceKeys", [])
                if isinstance(dossier, dict)
                else (
                    source_fact.get("sourceKeys", [])
                    if isinstance(source_fact, dict)
                    else []
                )
            )
        ),
        install_uri=worknet_context.get("installUri") if isinstance(worknet_context, dict) else None,
        capability_report=capability_report,
    )
    freshness = {"status": freshness_status, "highestPriority": highest_priority, "items": freshness_matches}
    summary = knowledge_topic_summary(
        label,
        narrative=narrative,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet_context,
        freshness=freshness,
    )
    topic_execution_state = knowledge_topic_execution_state(
        label=label,
        affected=freshness_status == "affected",
        capability_report=capability_report if isinstance(capability_report, dict) else None,
    )
    recommendations = knowledge_topic_recommendations(
        topic,
        label,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet_context,
        capability_report=capability_report,
        freshness=freshness,
        impact_matches=impact_matches,
        source_records=source_records,
    )
    if glossary_primary_match:
        recommendations = frontload_user_action_labels(recommendations, [f"Refresh {label} knowledge"])
    status = "knowledge_review_needed" if freshness_status == "affected" else "knowledge_ready"
    citations = knowledge_topic_citations(
        evidence_matches,
        source_records=source_records,
        dossier=dossier,
    )
    evidence_display, evidence_display_index = knowledge_display_evidence(evidence_matches)
    citations_display = knowledge_display_citations(
        citations,
        evidence_display_index=evidence_display_index,
    )
    runtime_probe_display = knowledge_runtime_probe_display_for_topic(
        topic=topic,
        catalog=catalog,
        worknet_context=worknet_context,
        capability_report=capability_report,
    )
    runtime_probe_evidence = knowledge_runtime_probe_evidence_entries(
        runtime_probe_display,
        topic_key=str(worknet_context.get("key") or topic).strip() if isinstance(worknet_context, dict) else str(topic).strip() or None,
    )
    evidence_display = [*runtime_probe_evidence, *evidence_display]
    primary_command = None
    if recommendations and isinstance(recommendations[0].get("command"), str) and recommendations[0].get("command"):
        primary_command = recommendations[0]["command"]
    action_map = {
        str(item.get("label") or "").strip(): str(item.get("command") or "").strip()
        for item in recommendations
        if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("command") or "").strip()
    }
    user_action_details = action_details_from_ui_actions(recommendations, action_map)
    current_action_labels: list[str] = []
    worknet_action_labels: list[str] = []
    for index, item in enumerate(user_action_details):
        if not isinstance(item, dict):
            continue
        label_text = str(item.get("label") or "").strip()
        if not label_text:
            continue
        if index == 0 or label_text.startswith(("Refresh ", "Review ", "Inspect ", "Start ", "Build ")):
            current_action_labels.append(label_text)
        else:
            worknet_action_labels.append(label_text)

    plain_language = knowledge_topic_plain_language(
        narrative=narrative,
        glossary_match=glossary_match,
        dossier=dossier,
        source_fact=source_fact,
        worknet=worknet_context,
    )
    queue_summary = summarize_knowledge_review_queue(knowledge_review_queue)
    topic_directory = catalog.get("topicDirectory", []) if isinstance(catalog.get("topicDirectory"), list) else []
    resolved_topic_key = (
        str(glossary_match.get("term") or topic).strip()
        if glossary_primary_match and isinstance(glossary_match, dict)
        else knowledge_resolved_topic_key(
            topic,
            glossary_match=glossary_match,
            dossier=dossier,
            worknet=worknet_context,
        )
    )
    current_context = find_topic_directory_entry(
        topic_directory,
        key=str(resolved_topic_key or "").strip(),
        worknet_key=str(worknet_context.get("key") or "").strip() if isinstance(worknet_context, dict) else None,
    )
    if not isinstance(current_context, dict):
        current_context = {
            "key": resolved_topic_key,
            "label": label,
            "summary": summary,
            "summaryPreview": compact_preview_text(
                plain_language or summary,
                max_chars=140,
                max_sentences=2,
            ),
            "headline": knowledge_topic_headline(label, freshness),
            "queryCommand": query_knowledge_command(
                str(resolved_topic_key or topic).strip()
            ),
            "primaryCommand": primary_command,
            "freshnessStatus": freshness_status,
            "sourceKeys": list(related_source_keys),
            "worknetKey": worknet_context.get("key") if isinstance(worknet_context, dict) else None,
        }
    related_source_highlights = knowledge_related_source_highlights(
        catalog,
        current_context,
        limit=3,
    )
    related_reference_highlights = knowledge_related_reference_highlights(
        catalog,
        current_context,
        limit=2,
    )
    source_action_labels: list[str] = []
    for item in related_source_highlights[:2]:
        if not isinstance(item, dict):
            continue
        source_label = str(item.get("label") or item.get("key") or "").strip()
        command = str(item.get("queryCommand") or "").strip()
        if not source_label or not command:
            continue
        label_text = f"Review source {source_label}"
        source_action_labels.append(label_text)
        append_unique_action_detail(
            user_action_details,
            label=label_text,
            description=knowledge_source_action_description(item),
            command=command,
        )
    reference_action_labels: list[str] = []
    for item in related_reference_highlights[:2]:
        if not isinstance(item, dict):
            continue
        reference_label = str(item.get("label") or item.get("key") or "").strip()
        command = str(item.get("queryCommand") or "").strip()
        if not reference_label or not command:
            continue
        label_text = f"Review reference {reference_label}"
        reference_action_labels.append(label_text)
        append_unique_action_detail(
            user_action_details,
            label=label_text,
            description="Open the related reference highlight for source-backed context.",
            command=command,
        )
    control_action_labels: list[str] = []
    queue_label = str(queue_summary.get("primaryActionLabel") or "").strip()
    queue_command = str(queue_summary.get("primaryActionCommand") or "").strip()
    if queue_summary.get("hasPendingReviews") and queue_label and queue_command:
        control_action_labels.append(queue_label)
        append_unique_action_detail(
            user_action_details,
            label=queue_label,
            description="Review pending knowledge updates before trusting generated guidance.",
            command=queue_command,
        )
    research_action_groups = build_research_action_groups(
        user_action_details,
        current_labels=current_action_labels,
        control_labels=control_action_labels,
        source_labels=source_action_labels,
        topic_labels=[],
        worknet_labels=worknet_action_labels,
        reference_labels=reference_action_labels,
        control_first=False,
    )
    recommendations = annotate_research_action_details(
        recommendations,
        current_labels=current_action_labels,
        control_labels=control_action_labels,
        source_labels=source_action_labels,
        topic_labels=[],
        worknet_labels=worknet_action_labels,
        reference_labels=reference_action_labels,
        current_tier="current",
        control_tier="queued",
        source_tier="related",
        worknet_tier="related",
        reference_tier="related",
    )
    user_action_details = annotate_research_action_details(
        user_action_details,
        current_labels=current_action_labels,
        control_labels=control_action_labels,
        source_labels=source_action_labels,
        topic_labels=[],
        worknet_labels=worknet_action_labels,
        reference_labels=reference_action_labels,
        current_tier="current",
        control_tier="queued",
        source_tier="related",
        worknet_tier="related",
        reference_tier="related",
    )
    user_action_details = frontload_user_action_labels(
        user_action_details,
        [
            *current_action_labels,
            *source_action_labels,
            *worknet_action_labels,
            *control_action_labels,
            *reference_action_labels,
        ],
    )

    return normalize_query_payload({
        "topic": topic,
        "status": status,
        "resolvedTopicKey": resolved_topic_key,
        "resolvedTopicLabel": label,
        "progress": "[2/5] Knowledge Query",
        "headline": knowledge_topic_headline(label, freshness),
        "summary": summary,
        "plainLanguage": plain_language,
        "executionState": topic_execution_state.get("executionState"),
        "executionStateDisplay": topic_execution_state.get("executionStateDisplay"),
        "executionHeadline": topic_execution_state.get("executionHeadline"),
        "primaryCommand": primary_command,
        "primaryUserAction": user_action_details[0]["label"] if user_action_details else None,
        "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
        "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
        "userActionDetails": user_action_details,
        "researchActionGroups": research_action_groups,
        "recommendations": recommendations,
        "citations": citations,
        "citationsDisplay": citations_display,
        "glossary": glossary_match,
        "concept": None,
        "conceptDisplay": None,
        "dossier": dossier,
        "dossierDisplay": knowledge_display_dossier(
            dossier,
            summary=summary,
            why=(narrative or {}).get("why") if isinstance(narrative, dict) else None,
            worknet_metadata=worknet_metadata,
        ),
        "sourceFact": source_fact,
        "sourceFactDisplay": knowledge_display_source_fact(
            source_fact,
            summary=summary,
            runtime_probe_display=runtime_probe_display,
            worknet_metadata=worknet_metadata,
        ),
        "evidence": evidence_matches,
        "evidenceDisplay": evidence_display,
        "worknet": worknet,
        "worknetDisplay": knowledge_display_worknet(
            worknet,
            capability_report=capability_report if isinstance(capability_report, dict) else None,
            runtime_probe_display=runtime_probe_display,
        ),
        "runtimeProbeDisplay": runtime_probe_display,
        "runtimeProbeHighlights": runtime_probe_display.get("highlights", []) if isinstance(runtime_probe_display, dict) else [],
        "sourceImpact": {
            "affected": bool(impact_matches),
            "items": impact_matches,
        },
        "sourceImpactDisplay": knowledge_display_source_impact({
            "affected": bool(impact_matches),
            "items": impact_matches,
        }, catalog=catalog),
        "freshness": freshness,
        "freshnessDisplay": knowledge_display_freshness(freshness),
        "relatedSourceHighlights": related_source_highlights,
        "relatedReferenceHighlights": related_reference_highlights,
    }, KNOWLEDGE_QUERY_FIELDS)

def build_concept_query_result_payload(
    topic: str,
    concept_match: dict[str, Any],
    *,
    catalog: Optional[dict[str, Any]] = None,
    source_impact: Optional[dict[str, Any]] = None,
    topic_freshness_catalog: Optional[dict[str, Any]] = None,
    knowledge_review_queue: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build concept query result dependencies are required")
    KNOWLEDGE_QUERY_FIELDS = dependencies["KNOWLEDGE_QUERY_FIELDS"]
    KNOWLEDGE_QUEUE_PRIORITY_RANK = dependencies["KNOWLEDGE_QUEUE_PRIORITY_RANK"]
    action_details_from_ui_actions = dependencies["action_details_from_ui_actions"]
    annotate_research_action_details = dependencies["annotate_research_action_details"]
    build_knowledge_catalog = dependencies["build_knowledge_catalog"]
    build_knowledge_review_queue = dependencies["build_knowledge_review_queue"]
    build_research_action_groups = dependencies["build_research_action_groups"]
    compact_preview_text = dependencies["compact_preview_text"]
    execution_state_payload = dependencies["execution_state_payload"]
    find_topic_directory_entry = dependencies["find_topic_directory_entry"]
    frontload_user_action_labels = dependencies["frontload_user_action_labels"]
    knowledge_action_description = dependencies["knowledge_action_description"]
    knowledge_display_citations = dependencies["knowledge_display_citations"]
    knowledge_display_evidence = dependencies["knowledge_display_evidence"]
    knowledge_display_freshness = dependencies["knowledge_display_freshness"]
    knowledge_display_source_impact = dependencies["knowledge_display_source_impact"]
    knowledge_related_reference_highlights = dependencies["knowledge_related_reference_highlights"]
    knowledge_related_source_highlights = dependencies["knowledge_related_source_highlights"]
    knowledge_source_action_description = dependencies["knowledge_source_action_description"]
    knowledge_source_records_from_catalog = dependencies["knowledge_source_records_from_catalog"]
    knowledge_topic_citations = dependencies["knowledge_topic_citations"]
    load_cached_knowledge_catalog = dependencies["load_cached_knowledge_catalog"]
    load_cached_knowledge_review_queue = dependencies["load_cached_knowledge_review_queue"]
    normalize_concept_payload = dependencies["normalize_concept_payload"]
    normalize_query_payload = dependencies["normalize_query_payload"]
    query_knowledge_command = dependencies["query_knowledge_command"]
    summarize_knowledge_review_queue = dependencies["summarize_knowledge_review_queue"]

    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    source_impact = source_impact if isinstance(source_impact, dict) else (
        catalog.get("sourceImpact", {}) if isinstance(catalog.get("sourceImpact"), dict) else {}
    )
    topic_freshness_catalog = topic_freshness_catalog if isinstance(topic_freshness_catalog, dict) else (
        catalog.get("topicFreshness", {}) if isinstance(catalog.get("topicFreshness"), dict) else {}
    )
    knowledge_review_queue = knowledge_review_queue if isinstance(knowledge_review_queue, dict) else (
        catalog.get("knowledgeReviewQueue", {}) if isinstance(catalog.get("knowledgeReviewQueue"), dict) else {}
    )
    if not knowledge_review_queue:
        knowledge_review_queue = load_cached_knowledge_review_queue() or build_knowledge_review_queue()

    concept_key = str(concept_match.get("key") or topic).strip()
    concept_title = str(concept_match.get("title") or concept_key).strip()
    related_topics = [
        str(item).strip().lower()
        for item in concept_match.get("relatedTopics", [])
        if str(item).strip()
    ]
    related_worknets = [
        str(item).strip().lower()
        for item in concept_match.get("relatedWorknets", [])
        if str(item).strip()
    ]
    source_keys = [
        str(item).strip()
        for item in concept_match.get("sourceKeys", [])
        if str(item).strip()
    ]
    evidence_keys = {
        str(item).strip()
        for item in concept_match.get("evidenceKeys", [])
        if str(item).strip()
    }
    source_records = knowledge_source_records_from_catalog(catalog)
    source_evidence = list(catalog.get("sourceEvidence", []))
    topic_directory = catalog.get("topicDirectory", []) if isinstance(catalog.get("topicDirectory"), list) else []
    queue_summary = summarize_knowledge_review_queue(knowledge_review_queue)

    ranked_evidence: list[tuple[int, dict[str, Any]]] = []
    for item in source_evidence:
        if not isinstance(item, dict):
            continue
        score = 0
        item_key = str(item.get("key") or "").strip()
        topic_key = str(item.get("topicKey") or "").strip().lower()
        source_key = str(item.get("sourceKey") or "").strip()
        if item_key in evidence_keys:
            score += 100
        if topic_key in related_topics or topic_key in related_worknets:
            score += 40
        if source_key in source_keys:
            score += 20
        if score > 0:
            ranked_evidence.append((score, item))
    ranked_evidence.sort(key=lambda pair: pair[0], reverse=True)
    evidence_matches = [item for _, item in ranked_evidence]
    citations = knowledge_topic_citations(
        evidence_matches,
        source_records=source_records,
        dossier=None,
    )
    evidence_display, evidence_display_index = knowledge_display_evidence(evidence_matches)
    citations_display = knowledge_display_citations(
        citations,
        evidence_display_index=evidence_display_index,
    )

    related_topic_keys = {concept_key.lower(), *related_topics, *related_worknets}
    related_source_keys = set(source_keys)
    impact_matches: list[dict[str, Any]] = []
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
        source_key = str(item.get("sourceKey") or "").strip()
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

    freshness_matches: list[dict[str, Any]] = []
    for bucket in ("topics", "facts", "worknets"):
        for item in topic_freshness_catalog.get(bucket, []):
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "")).strip().lower()
            if key in related_topic_keys:
                freshness_matches.append(item)
    freshness_status = "stable"
    highest_priority = "low"
    for item in freshness_matches:
        if item.get("status") == "affected":
            freshness_status = "affected"
        priority = str(item.get("highestPriority") or "low")
        if KNOWLEDGE_QUEUE_PRIORITY_RANK.get(priority, 0) > KNOWLEDGE_QUEUE_PRIORITY_RANK.get(highest_priority, 0):
            highest_priority = priority
    freshness = {"status": freshness_status, "highestPriority": highest_priority, "items": freshness_matches}

    current_context = {
        "key": concept_key,
        "label": concept_title,
        "kind": "concept",
        "summary": concept_match.get("summary"),
        "summaryPreview": compact_preview_text(
            concept_match.get("plainLanguage") or concept_match.get("summary"),
            max_chars=140,
            max_sentences=2,
        ),
        "headline": f"{concept_title} ready" if freshness_status != "affected" else f"{concept_title} review required",
        "queryCommand": query_knowledge_command(concept_key),
        "primaryCommand": query_knowledge_command(concept_key, rebuild=True),
        "freshnessStatus": freshness_status,
        "sourceKeys": source_keys,
    }
    related_source_highlights = knowledge_related_source_highlights(catalog, current_context, limit=3)
    related_reference_highlights = knowledge_related_reference_highlights(catalog, current_context, limit=2)
    impact_display = knowledge_display_source_impact(
        {"affected": bool(impact_matches), "items": impact_matches},
        catalog=catalog,
    )
    freshness_display = knowledge_display_freshness(freshness)
    execution_payload = execution_state_payload(
        "review_required" if freshness_status == "affected" else "knowledge_ready",
        headline=(
            f"{concept_title} review required"
            if freshness_status == "affected"
            else f"{concept_title} ready"
        ),
    )

    recommendations: list[dict[str, Any]] = [
        {
            "label": f"Review concept: {concept_title}",
            "description": f"Refresh the knowledge record for {concept_title}.",
            "command": query_knowledge_command(concept_key, rebuild=True),
        }
    ]
    topic_action_labels: list[str] = []
    worknet_action_labels: list[str] = []
    for related_key in [*related_topics, *related_worknets]:
        topic_entry = find_topic_directory_entry(topic_directory, key=related_key, worknet_key=related_key)
        if not isinstance(topic_entry, dict):
            continue
        label_text = str(topic_entry.get("label") or topic_entry.get("key") or related_key).strip()
        command = str(topic_entry.get("queryCommand") or query_knowledge_command(related_key)).strip()
        if not label_text or not command:
            continue
        action_label = f"Review topic: {label_text}"
        description = knowledge_action_description(topic_entry)
        if any(str(item.get("label") or "").strip() == action_label for item in recommendations if isinstance(item, dict)):
            continue
        recommendations.append(
            {
                "label": action_label,
                "description": description,
                "command": command,
            }
        )
        if str(topic_entry.get("worknetKey") or "").strip():
            worknet_action_labels.append(action_label)
        else:
            topic_action_labels.append(action_label)
    source_action_labels: list[str] = []
    for item in related_source_highlights[:3]:
        if not isinstance(item, dict):
            continue
        source_label = str(item.get("label") or item.get("key") or "").strip()
        command = str(item.get("queryCommand") or "").strip()
        if not source_label or not command:
            continue
        label_text = f"Review source: {source_label}"
        if any(str(entry.get("label") or "").strip() == label_text for entry in recommendations if isinstance(entry, dict)):
            continue
        recommendations.append(
            {
                "label": label_text,
                "description": knowledge_source_action_description(item),
                "command": command,
            }
        )
        source_action_labels.append(label_text)
    reference_action_labels: list[str] = []
    for item in related_reference_highlights[:2]:
        if not isinstance(item, dict):
            continue
        reference_label = str(item.get("label") or item.get("key") or "").strip()
        command = str(item.get("queryCommand") or "").strip()
        if not reference_label or not command:
            continue
        label_text = f"Open reference: {reference_label}"
        if any(str(entry.get("label") or "").strip() == label_text for entry in recommendations if isinstance(entry, dict)):
            continue
        recommendations.append(
            {
                "label": label_text,
                "description": f"Open the related reference for {concept_title}.",
                "command": command,
            }
        )
        reference_action_labels.append(label_text)
    control_action_labels: list[str] = []
    queue_label = str(queue_summary.get("primaryActionLabel") or "").strip()
    queue_command = str(queue_summary.get("primaryActionCommand") or "").strip()
    if queue_summary.get("hasPendingReviews") and queue_label and queue_command:
        recommendations.append(
            {
                "label": queue_label,
                "description": "Review pending knowledge updates before continuing.",
                "command": queue_command,
            }
        )
        control_action_labels.append(queue_label)

    action_map = {
        str(item.get("label") or "").strip(): str(item.get("command") or "").strip()
        for item in recommendations
        if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("command") or "").strip()
    }
    user_action_details = action_details_from_ui_actions(recommendations, action_map)
    current_action_labels = [f"Review concept: {concept_title}"]
    research_action_groups = build_research_action_groups(
        user_action_details,
        current_labels=current_action_labels,
        control_labels=control_action_labels,
        source_labels=source_action_labels,
        topic_labels=topic_action_labels,
        worknet_labels=worknet_action_labels,
        reference_labels=reference_action_labels,
        control_first=False,
    )
    recommendations = annotate_research_action_details(
        recommendations,
        current_labels=current_action_labels,
        control_labels=control_action_labels,
        source_labels=source_action_labels,
        topic_labels=topic_action_labels,
        worknet_labels=worknet_action_labels,
        reference_labels=reference_action_labels,
        current_tier="current",
        control_tier="queued",
        source_tier="related",
        topic_tier="related",
        worknet_tier="related",
        reference_tier="related",
    )
    user_action_details = annotate_research_action_details(
        user_action_details,
        current_labels=current_action_labels,
        control_labels=control_action_labels,
        source_labels=source_action_labels,
        topic_labels=topic_action_labels,
        worknet_labels=worknet_action_labels,
        reference_labels=reference_action_labels,
        current_tier="current",
        control_tier="queued",
        source_tier="related",
        topic_tier="related",
        worknet_tier="related",
        reference_tier="related",
    )
    user_action_details = frontload_user_action_labels(
        user_action_details,
        [
            *current_action_labels,
            *source_action_labels,
            *topic_action_labels,
            *worknet_action_labels,
            *control_action_labels,
            *reference_action_labels,
        ],
    )

    return normalize_query_payload(
        {
            "topic": topic,
            "status": "knowledge_review_needed" if freshness_status == "affected" else "knowledge_ready",
            "resolvedTopicKey": concept_key,
            "resolvedTopicLabel": concept_title,
            "progress": "[2/5] Knowledge Query",
            "headline": execution_payload.get("executionHeadline"),
            "summary": str(concept_match.get("summary") or concept_match.get("plainLanguage") or "").strip() or None,
            "plainLanguage": concept_match.get("plainLanguage"),
            "executionState": execution_payload.get("executionState"),
            "executionStateDisplay": execution_payload.get("executionStateDisplay"),
            "executionHeadline": execution_payload.get("executionHeadline"),
            "primaryCommand": query_knowledge_command(concept_key, rebuild=True),
            "primaryUserAction": user_action_details[0]["label"] if user_action_details else None,
            "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
            "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
            "userActionDetails": user_action_details,
            "researchActionGroups": research_action_groups,
            "recommendations": recommendations,
            "citations": citations,
            "citationsDisplay": citations_display,
            "glossary": None,
            "concept": concept_match,
            "conceptDisplay": normalize_concept_payload(concept_match),
            "dossier": None,
            "dossierDisplay": None,
            "sourceFact": None,
            "sourceFactDisplay": None,
            "evidence": evidence_matches,
            "evidenceDisplay": evidence_display,
            "worknet": None,
            "worknetDisplay": None,
            "runtimeProbeDisplay": None,
            "runtimeProbeHighlights": [],
            "sourceImpact": {"affected": bool(impact_matches), "items": impact_matches},
            "sourceImpactDisplay": impact_display,
            "freshness": freshness,
            "freshnessDisplay": freshness_display,
            "relatedSourceHighlights": related_source_highlights,
            "relatedReferenceHighlights": related_reference_highlights,
        },
        KNOWLEDGE_QUERY_FIELDS,
    )


def build_source_query_result_payload(
    source_key: str,
    *,
    catalog: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build source query result dependencies are required")
    SOURCE_QUERY_FIELDS = dependencies["SOURCE_QUERY_FIELDS"]
    action_details_from_ui_actions = dependencies["action_details_from_ui_actions"]
    annotate_research_action_details = dependencies["annotate_research_action_details"]
    append_unique_action_detail = dependencies["append_unique_action_detail"]
    build_knowledge_catalog = dependencies["build_knowledge_catalog"]
    build_knowledge_query_result = dependencies["build_knowledge_query_result"]
    build_normalized_knowledge_highlight = dependencies["build_normalized_knowledge_highlight"]
    build_research_action_groups = dependencies["build_research_action_groups"]
    capability_reports_by_worknet_key = dependencies["capability_reports_by_worknet_key"]
    compact_preview_text = dependencies["compact_preview_text"]
    execution_state_payload = dependencies["execution_state_payload"]
    frontload_user_action_labels = dependencies["frontload_user_action_labels"]
    humanize_knowledge_source_label = dependencies["humanize_knowledge_source_label"]
    join_product_sentences = dependencies["join_product_sentences"]
    knowledge_action_description = dependencies["knowledge_action_description"]
    knowledge_display_citations = dependencies["knowledge_display_citations"]
    knowledge_display_drift_item = dependencies["knowledge_display_drift_item"]
    knowledge_display_evidence = dependencies["knowledge_display_evidence"]
    knowledge_display_glossary_items = dependencies["knowledge_display_glossary_items"]
    knowledge_display_source_impact = dependencies["knowledge_display_source_impact"]
    knowledge_display_source_record = dependencies["knowledge_display_source_record"]
    knowledge_display_worknet = dependencies["knowledge_display_worknet"]
    knowledge_runtime_probe_count = dependencies["knowledge_runtime_probe_count"]
    knowledge_runtime_probe_display = dependencies["knowledge_runtime_probe_display"]
    knowledge_runtime_probe_display_for_source = dependencies["knowledge_runtime_probe_display_for_source"]
    knowledge_runtime_probe_evidence_entries = dependencies["knowledge_runtime_probe_evidence_entries"]
    knowledge_runtime_probe_summary_sentence = dependencies["knowledge_runtime_probe_summary_sentence"]
    load_cached_knowledge_catalog = dependencies["load_cached_knowledge_catalog"]
    normalize_query_payload = dependencies["normalize_query_payload"]
    normalize_review_scope_payload = dependencies["normalize_review_scope_payload"]
    prioritize_action_entries = dependencies["prioritize_action_entries"]
    query_knowledge_command = dependencies["query_knowledge_command"]
    query_source_command = dependencies["query_source_command"]

    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    source_key = str(source_key or "").strip()
    source_drift = catalog.get("sourceDrift", {}) if isinstance(catalog.get("sourceDrift"), dict) else {}
    source_impact = catalog.get("sourceImpact", {}) if isinstance(catalog.get("sourceImpact"), dict) else {}
    source_records: dict[str, dict[str, Any]] = {}
    sources = catalog.get("sources", {}) if isinstance(catalog.get("sources"), dict) else {}
    for bucket in ("officialWebSources", "localSources"):
        for item in sources.get(bucket, []):
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item
    capability_reports = capability_reports_by_worknet_key()
    source_record = source_records.get(source_key)
    drift_item = next(
        (
            item
            for item in source_drift.get("items", [])
            if isinstance(item, dict) and item.get("key") == source_key
        ),
        None,
    )
    impact_item = next(
        (
            item
            for item in source_impact.get("impacts", [])
            if isinstance(item, dict) and item.get("sourceKey") == source_key
        ),
        None,
    )
    facts = [item for item in catalog.get("sourceFacts", []) if source_key in item.get("sourceKeys", [])]
    evidence = [item for item in catalog.get("sourceEvidence", []) if item.get("sourceKey") == source_key]
    dossiers = [item for item in catalog.get("topicDossiers", []) if source_key in item.get("sourceKeys", [])]
    glossary = [item for item in catalog.get("glossary", []) if source_key in item.get("sourceKeys", [])]
    worknets = [item for item in catalog.get("worknets", []) if source_key in item.get("sourceKeys", [])]
    topic_cache: dict[str, dict[str, Any]] = {}

    def topic_result(topic_key: Any) -> Optional[dict[str, Any]]:
        normalized = str(topic_key or "").strip()
        if not normalized:
            return None
        if normalized not in topic_cache:
            topic_cache[normalized] = build_knowledge_query_result(normalized, catalog=catalog)
        return topic_cache[normalized]

    facts_display: list[dict[str, Any]] = []
    for item in facts:
        result = topic_result(item.get("key"))
        if isinstance(result, dict) and isinstance(result.get("sourceFactDisplay"), dict):
            facts_display.append(result["sourceFactDisplay"])
    dossiers_display: list[dict[str, Any]] = []
    for item in dossiers:
        result = topic_result(item.get("key"))
        if isinstance(result, dict) and isinstance(result.get("dossierDisplay"), dict):
            dossiers_display.append(result["dossierDisplay"])
    worknets_display: list[dict[str, Any]] = []
    for item in worknets:
        worknet_key = str(item.get("key") or "").strip()
        rendered = knowledge_display_worknet(
            item,
            capability_report=capability_reports.get(worknet_key) if worknet_key else None,
            runtime_probe_display=knowledge_runtime_probe_display(
                capability_reports.get(worknet_key, {}).get("skillInspection"),
                skill_key=worknet_key,
            ) if worknet_key and isinstance(capability_reports.get(worknet_key), dict) else None,
        )
        if isinstance(rendered, dict):
            worknets_display.append(rendered)
    evidence_display, evidence_display_index = knowledge_display_evidence(evidence)
    drift_display = knowledge_display_drift_item(
        drift_item,
        source_record=source_record,
    )
    impact_display = knowledge_display_source_impact(
        {"affected": bool(impact_item), "items": [impact_item] if isinstance(impact_item, dict) else []},
        catalog=catalog,
    )
    source_runtime_probe_display = knowledge_runtime_probe_display_for_source(
        source_key=source_key,
        source_record=source_record,
        catalog=catalog,
        capability_report=capability_reports.get(str(source_record.get("worknetKey") or "").strip()) if isinstance(source_record, dict) and str(source_record.get("worknetKey") or "").strip() else None,
    )
    runtime_probe_evidence = knowledge_runtime_probe_evidence_entries(
        source_runtime_probe_display,
        topic_key=str(source_record.get("worknetKey") or "").strip() if isinstance(source_record, dict) else None,
    )
    evidence_display = [*runtime_probe_evidence, *evidence_display]
    source_display = knowledge_display_source_record(
        source_record,
        drift_item=drift_item,
        impact_item=impact_item,
        runtime_probe_display=source_runtime_probe_display,
        capability_report=capability_reports.get(str(source_record.get("worknetKey") or "").strip()) if isinstance(source_record, dict) and str(source_record.get("worknetKey") or "").strip() else None,
    )
    if isinstance(source_display, dict):
        source_display = dict(source_display)
        source_display["summaryPreview"] = compact_preview_text(
            source_display.get("summaryDisplay") or source_display.get("summary"),
            max_chars=140,
            max_sentences=2,
        )
    headline = None
    if isinstance(source_display, dict):
        headline = source_display.get("headline")
    if not headline:
        name_display = humanize_knowledge_source_label(source_key)
        headline = f"Source: {name_display}"
    summary_parts: list[str] = []
    if source_record is None:
        headline = f"Source missing: {source_key}"
        summary_parts.append("This source is not present in the current knowledge catalog.")
    if isinstance(source_display, dict) and isinstance(source_display.get("summaryDisplay"), str):
        summary_parts.append(str(source_display["summaryDisplay"]).strip())
    if isinstance(drift_display, dict) and drift_display.get("statusDisplay"):
        changed_fields = drift_display.get("changedFieldsDisplay", [])
        drift_sentence = f"Source drift status: {drift_display['statusDisplay']}."
        if changed_fields:
            drift_sentence += f" Changed fields: {', '.join(changed_fields)}."
        if drift_display.get("note"):
            drift_sentence += f" {str(drift_display['note']).strip()}"
        summary_parts.append(drift_sentence.strip())
    if isinstance(impact_display, dict) and isinstance(impact_display.get("summary"), str):
        summary_parts.append(str(impact_display["summary"]).strip())
    if not summary_parts:
        summary_parts.append("No source summary is available yet.")
    summary_text = " ".join(part for part in summary_parts if part).strip()
    summary_preview = (
        source_display.get("summaryPreview")
        if isinstance(source_display, dict)
        else None
    ) or compact_preview_text(summary_text, max_chars=160, max_sentences=2)
    recommendations: list[dict[str, Any]] = []
    seen_labels: set[str] = set()

    def add_recommendation(label: str, description: str, command: Optional[str]) -> None:
        resolved_label = str(label or "").strip()
        resolved_command = str(command or "").strip()
        if not resolved_label or not resolved_command or resolved_label in seen_labels:
            return
        seen_labels.add(resolved_label)
        recommendations.append(
            {
                "label": resolved_label,
                "description": description,
                "command": resolved_command,
            }
        )

    add_recommendation(
        f"Refresh source {humanize_knowledge_source_label(source_record.get('name') if isinstance(source_record, dict) else source_key)}",
        "Rebuild this source view from current cached and generated data.",
        query_source_command(source_key, rebuild=True),
    )
    if isinstance(impact_item, dict):
        for topic in impact_item.get("impactedTopics", [])[:3]:
            topic_key = str(topic.get("key") if isinstance(topic, dict) else topic).strip()
            topic_label = str(topic.get("title") if isinstance(topic, dict) else "").strip()
            result = topic_result(topic_key)
            if isinstance(result, dict):
                topic_label = str(result.get("resolvedTopicLabel") or topic_label or topic_key).strip()
            add_recommendation(
                f"Review topic {topic_label}",
                "Review the impacted topic before trusting this source context.",
                query_knowledge_command(topic_key),
            )
    add_recommendation(
        "Review pending knowledge updates",
        "Open the knowledge review queue for changed source impacts.",
        query_knowledge_command("review-queue"),
    )
    review_needed = bool(
        source_record
        and (
            (
                isinstance(drift_display, dict)
                and str(drift_display.get("status") or "").strip()
                and str(drift_display.get("status") or "").strip() not in {"unchanged", "no-baseline"}
            )
            or (isinstance(impact_display, dict) and impact_display.get("affected"))
        )
    )
    status = "source_missing"
    if source_record is not None:
        status = "source_review_needed" if review_needed else "source_ready"
    execution_payload = execution_state_payload(status, headline=headline)
    recommendations = prioritize_action_entries(
        recommendations,
        execution_state=status,
        resume_status=None,
        worknet_key=str(source_record.get("worknetKey") or "").strip() if isinstance(source_record, dict) else None,
    )
    action_map = {
        str(item.get("label") or "").strip(): str(item.get("command") or "").strip()
        for item in recommendations
        if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("command") or "").strip()
    }
    user_action_details = action_details_from_ui_actions(recommendations, action_map)

    topic_highlights: list[dict[str, Any]] = []
    seen_topic_keys: set[str] = set()
    topic_candidates = []
    if isinstance(impact_item, dict) and isinstance(impact_item.get("impactedTopics"), list):
        topic_candidates.extend(impact_item.get("impactedTopics", []))
    topic_candidates.extend(dossiers)
    for item in topic_candidates:
        if isinstance(item, dict):
            topic_key = str(item.get("key") or "").strip()
        else:
            topic_key = str(item or "").strip()
        if not topic_key or topic_key in seen_topic_keys:
            continue
        seen_topic_keys.add(topic_key)
        result = topic_result(topic_key)
        if not isinstance(result, dict):
            continue
        freshness_display = result.get("freshnessDisplay", {}) if isinstance(result.get("freshnessDisplay"), dict) else {}
        topic_highlights.append(
            build_normalized_knowledge_highlight(
                kind="topic",
                key=str(result.get("resolvedTopicKey") or topic_key).strip(),
                label=str(result.get("resolvedTopicLabel") or topic_key).strip(),
                headline=result.get("headline"),
                preview=result.get("plainLanguage") or result.get("summary"),
                query_command=query_knowledge_command(str(result.get("resolvedTopicKey") or topic_key).strip()),
                primary_command=result.get("primaryCommand"),
                freshness_status=freshness_display.get("status"),
                research_tier="related",
                extra={
                    "summary": compact_preview_text(
                        result.get("plainLanguage") or result.get("summary"),
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "summaryPreview": compact_preview_text(
                        result.get("plainLanguage") or result.get("summary"),
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "summaryFull": result.get("summary"),
                    "status": freshness_display.get("status"),
                    "statusDisplay": freshness_display.get("statusDisplay"),
                },
            )
        )

    fact_highlights: list[dict[str, Any]] = []
    for item in facts_display:
        if not isinstance(item, dict):
            continue
        fact_key = str(item.get("key") or "").strip()
        fact_result = topic_result(fact_key) if fact_key else None
        fact_freshness_display = (
            fact_result.get("freshnessDisplay", {})
            if isinstance(fact_result, dict) and isinstance(fact_result.get("freshnessDisplay"), dict)
            else {}
        )
        fact_runtime_summary = str(item.get("runtimeSummary") or "").strip() or None
        if not fact_runtime_summary:
            source_keys = [str(value).strip() for value in item.get("sourceKeys", []) if str(value).strip()]
            if source_key in source_keys:
                fact_runtime_summary = knowledge_runtime_probe_summary_sentence(source_runtime_probe_display)
        fact_summary_full = join_product_sentences(
            [
                item.get("summary"),
                fact_runtime_summary,
            ]
        ) or item.get("summary")
        fact_preview_text = join_product_sentences(
            [
                compact_preview_text(
                    " ".join(str(entry).strip() for entry in item.get("facts", [])[:2] if str(entry).strip()),
                    max_chars=160,
                    max_sentences=2,
                ),
                fact_runtime_summary,
            ]
        ) or fact_summary_full
        fact_highlights.append(
            build_normalized_knowledge_highlight(
                kind="fact",
                key=fact_key,
                label=item.get("topic") or fact_key,
                headline=(fact_result or {}).get("headline") if isinstance(fact_result, dict) else None,
                preview=fact_preview_text,
                query_command=query_knowledge_command(fact_key) if fact_key else None,
                primary_command=(fact_result or {}).get("primaryCommand") if isinstance(fact_result, dict) else None,
                freshness_status=fact_freshness_display.get("status"),
                research_tier="related",
                extra={
                    "topic": item.get("topic"),
                    "summary": compact_preview_text(
                        fact_summary_full,
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "summaryPreview": compact_preview_text(
                        fact_summary_full,
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "summaryFull": fact_summary_full,
                    "factsPreview": fact_preview_text,
                    "factCount": len(item.get("facts", [])) if isinstance(item.get("facts"), list) else 0,
                    "runtimeSummary": fact_runtime_summary,
                    "runtimeProbeCount": item.get("runtimeProbeCount") or (knowledge_runtime_probe_count(source_runtime_probe_display) or None),
                },
            )
        )

    worknet_highlights: list[dict[str, Any]] = []
    for item in worknets_display:
        if not isinstance(item, dict):
            continue
        worknet_key = str(item.get("key") or "").strip()
        worknet_result = topic_result(worknet_key) if worknet_key else None
        worknet_freshness_display = (
            worknet_result.get("freshnessDisplay", {})
            if isinstance(worknet_result, dict) and isinstance(worknet_result.get("freshnessDisplay"), dict)
            else {}
        )
        worknet_preview_text = join_product_sentences(
            [
                item.get("goalDisplay") or item.get("goal"),
                item.get("runtimeSummary"),
            ]
        ) or item.get("goalDisplay") or item.get("goal")
        worknet_highlights.append(
            build_normalized_knowledge_highlight(
                kind="worknet",
                key=worknet_key,
                label=item.get("name") or worknet_key,
                headline=(worknet_result or {}).get("headline") if isinstance(worknet_result, dict) else None,
                preview=worknet_preview_text,
                query_command=query_knowledge_command(worknet_key) if worknet_key else None,
                primary_command=(worknet_result or {}).get("primaryCommand") if isinstance(worknet_result, dict) else None,
                freshness_status=worknet_freshness_display.get("status"),
                research_tier="related",
                extra={
                    "name": item.get("name"),
                    "goal": compact_preview_text(
                        worknet_preview_text,
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "goalPreview": compact_preview_text(
                        worknet_preview_text,
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "goalFull": worknet_preview_text,
                    "cautionPreview": compact_preview_text(
                        item.get("cautionDisplay"),
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "statusDisplay": item.get("statusDisplay"),
                    "riskLevelDisplay": item.get("riskLevelDisplay"),
                    "recommendedRoleDisplay": item.get("recommendedRoleDisplay"),
                    "runtimeSummary": item.get("runtimeSummary"),
                    "runtimeProbeCount": item.get("runtimeProbeCount"),
                },
            )
        )

    evidence_highlights: list[dict[str, Any]] = []
    for item in evidence_display[:5]:
        if not isinstance(item, dict):
            continue
        evidence_topic_key = str(item.get("topicKey") or "").strip()
        evidence_preview = str(item.get("previewDisplay") or item.get("claimDisplay") or "").strip()
        evidence_highlights.append(
            build_normalized_knowledge_highlight(
                kind="evidence",
                key=item.get("key"),
                label=item.get("label") or item.get("sourceNameDisplay") or item.get("key"),
                headline=None,
                preview=evidence_preview,
                query_command=query_knowledge_command(evidence_topic_key) if evidence_topic_key else None,
                primary_command=None,
                freshness_status="affected" if review_needed else "stable",
                research_tier="related",
                extra={
                    "claim": compact_preview_text(
                        evidence_preview,
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "claimPreview": compact_preview_text(
                        evidence_preview,
                        max_chars=140,
                        max_sentences=2,
                    ),
                    "claimFull": item.get("claimDisplay"),
                    "claimDisplay": item.get("claimDisplay"),
                    "previewDisplay": item.get("previewDisplay"),
                    "locatorDisplay": item.get("locatorDisplay"),
                    "commandDisplay": item.get("commandDisplay"),
                    "stabilityDisplay": item.get("stabilityDisplay"),
                    "topicKey": evidence_topic_key or None,
                },
            )
        )
    for item in worknet_highlights[:2]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        command = str(item.get("queryCommand") or "").strip()
        if not label or not command:
            continue
        append_unique_action_detail(
            user_action_details,
            label=f"Review WorkNet {label}",
            description=knowledge_action_description(item),
            command=command,
        )

    current_labels: list[str] = []
    topic_labels: list[str] = []
    worknet_labels: list[str] = []
    control_labels: list[str] = []
    for index, item in enumerate(user_action_details):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        if index == 0:
            current_labels.append(label)
        elif label.startswith(("Review topic", "Refresh topic")):
            topic_labels.append(label)
        elif label.startswith("Review WorkNet"):
            worknet_labels.append(label)
        elif label in {"Review pending knowledge updates"}:
            control_labels.append(label)
    user_action_details = annotate_research_action_details(
        user_action_details,
        current_labels=current_labels,
        control_labels=control_labels,
        source_labels=[],
        topic_labels=topic_labels,
        worknet_labels=worknet_labels,
        reference_labels=[],
        current_tier="current",
        control_tier="queued",
        topic_tier="related",
        worknet_tier="related",
    )

    research_action_groups = build_research_action_groups(
        user_action_details,
        current_labels=current_labels,
        control_labels=control_labels,
        source_labels=[],
        topic_labels=topic_labels,
        worknet_labels=worknet_labels,
        reference_labels=[],
        control_first=False,
    )
    recommendations = annotate_research_action_details(
        recommendations,
        current_labels=current_labels,
        control_labels=control_labels,
        source_labels=[],
        topic_labels=topic_labels,
        worknet_labels=worknet_labels,
        reference_labels=[],
        current_tier="current",
        control_tier="queued",
        topic_tier="related",
        worknet_tier="related",
    )
    user_action_details = frontload_user_action_labels(
        user_action_details,
        [
            *current_labels,
            *topic_labels,
            *worknet_labels,
            *control_labels,
        ],
    )

    citations_display = knowledge_display_citations(
        [
            {
                "sourceKey": source_key,
                "sourceName": source_record.get("name") if isinstance(source_record, dict) else source_key,
                "url": source_record.get("url") if isinstance(source_record, dict) else None,
                "locator": None,
                "claim": None,
                "evidenceType": source_record.get("kind") if isinstance(source_record, dict) else None,
                "stability": None,
            }
        ],
        evidence_display_index=evidence_display_index,
    )
    return normalize_query_payload({
        "sourceKey": source_key,
        "sourceName": source_record.get("name") if isinstance(source_record, dict) else None,
        "sourceNameDisplay": source_display.get("nameDisplay") if isinstance(source_display, dict) else None,
        "status": status,
        "progress": "[1/5] Source Query",
        "headline": headline,
        "summary": summary_text,
        "summaryPreview": summary_preview,
        "summaryDisplay": source_display.get("summaryDisplay") if isinstance(source_display, dict) else None,
        "executionState": execution_payload.get("executionState"),
        "executionStateDisplay": execution_payload.get("executionStateDisplay"),
        "executionHeadline": execution_payload.get("executionHeadline"),
        "primaryCommand": query_source_command(source_key, rebuild=True),
        "primaryUserAction": user_action_details[0]["label"] if user_action_details else None,
        "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
        "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
        "userActionDetails": user_action_details,
        "researchActionGroups": research_action_groups,
        "recommendations": recommendations,
        "reviewScope": normalize_review_scope_payload({
            "topicCount": len(topic_highlights),
            "factCount": len(fact_highlights),
            "worknetCount": len(worknet_highlights),
            "evidenceCount": len(evidence_highlights),
        }),
        "topicHighlights": topic_highlights,
        "factHighlights": fact_highlights,
        "worknetHighlights": worknet_highlights,
        "evidenceHighlights": evidence_highlights,
        "source": source_record,
        "sourceDisplay": source_display,
        "drift": drift_item,
        "driftDisplay": drift_display,
        "impact": impact_item,
        "impactDisplay": impact_display,
        "facts": facts,
        "factsDisplay": facts_display,
        "evidence": evidence,
        "evidenceDisplay": evidence_display,
        "dossiers": dossiers,
        "dossiersDisplay": dossiers_display,
        "glossary": glossary,
        "glossaryDisplay": knowledge_display_glossary_items(glossary),
        "worknets": worknets,
        "worknetsDisplay": worknets_display,
        "runtimeProbeDisplay": source_runtime_probe_display,
        "runtimeProbeHighlights": source_runtime_probe_display.get("highlights", []) if isinstance(source_runtime_probe_display, dict) else [],
        "citationsDisplay": citations_display,
    }, SOURCE_QUERY_FIELDS)


def build_changed_sources_query_result_payload(
    *,
    catalog: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build changed sources query result dependencies are required")
    CHANGED_SOURCES_QUERY_FIELDS = dependencies["CHANGED_SOURCES_QUERY_FIELDS"]
    action_details_from_ui_actions = dependencies["action_details_from_ui_actions"]
    annotate_research_action_details = dependencies["annotate_research_action_details"]
    build_knowledge_catalog = dependencies["build_knowledge_catalog"]
    build_knowledge_review_queue = dependencies["build_knowledge_review_queue"]
    build_research_action_groups = dependencies["build_research_action_groups"]
    changed_source_highlight_entry = dependencies["changed_source_highlight_entry"]
    execution_state_payload = dependencies["execution_state_payload"]
    frontload_user_action_labels = dependencies["frontload_user_action_labels"]
    humanize_knowledge_source_label = dependencies["humanize_knowledge_source_label"]
    knowledge_display_changed_sources = dependencies["knowledge_display_changed_sources"]
    knowledge_display_review_queue_entries = dependencies["knowledge_display_review_queue_entries"]
    knowledge_display_source_impact = dependencies["knowledge_display_source_impact"]
    knowledge_review_queue_summary_text = dependencies["knowledge_review_queue_summary_text"]
    load_cached_knowledge_catalog = dependencies["load_cached_knowledge_catalog"]
    load_cached_knowledge_review_queue = dependencies["load_cached_knowledge_review_queue"]
    normalize_query_payload = dependencies["normalize_query_payload"]
    query_source_command = dependencies["query_source_command"]
    ranked_knowledge_review_queue_entries = dependencies["ranked_knowledge_review_queue_entries"]
    summarize_knowledge_review_queue = dependencies["summarize_knowledge_review_queue"]

    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    source_drift = catalog.get("sourceDrift", {}) if isinstance(catalog.get("sourceDrift"), dict) else {}
    source_impact = catalog.get("sourceImpact", {}) if isinstance(catalog.get("sourceImpact"), dict) else {}
    knowledge_review_queue = catalog.get("knowledgeReviewQueue", {}) if isinstance(catalog.get("knowledgeReviewQueue"), dict) else {}
    if not knowledge_review_queue:
        knowledge_review_queue = load_cached_knowledge_review_queue() or build_knowledge_review_queue()
    source_records: dict[str, dict[str, Any]] = {}
    sources = catalog.get("sources", {}) if isinstance(catalog.get("sources"), dict) else {}
    for bucket in ("officialWebSources", "localSources"):
        for item in sources.get(bucket, []):
            if isinstance(item, dict) and item.get("key"):
                source_records[str(item["key"])] = item
    changed_items = [
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
    impacted = [
        {
            "sourceKey": item.get("sourceKey"),
            "sourceName": item.get("sourceName"),
            "priority": item.get("priority"),
            "driftStatus": item.get("driftStatus"),
            "changedFields": item.get("changedFields", []),
            "note": item.get("note"),
            "impactedTopics": [entry.get("key") for entry in item.get("impactedTopics", []) if isinstance(entry, dict)],
            "impactedFacts": [entry.get("key") for entry in item.get("impactedFacts", []) if isinstance(entry, dict)],
            "impactedWorknets": list(item.get("impactedWorknets", [])),
            "reviewHint": item.get("reviewHint"),
            "reviewCommands": item.get("reviewCommands"),
        }
        for item in source_impact.get("impacts", [])
        if isinstance(item, dict)
    ]
    queue_summary = summarize_knowledge_review_queue(knowledge_review_queue)
    top_entries = ranked_knowledge_review_queue_entries(knowledge_review_queue, limit=8)
    recommendations: list[dict[str, Any]] = []
    if isinstance(queue_summary.get("primaryActionLabel"), str) and isinstance(queue_summary.get("primaryActionCommand"), str):
        recommendations.append(
            {
                "label": str(queue_summary["primaryActionLabel"]).strip(),
                "description": "Review the highest-priority source changes.",
                "command": str(queue_summary["primaryActionCommand"]).strip(),
            }
        )
    if isinstance(queue_summary.get("refreshActionLabel"), str) and isinstance(queue_summary.get("refreshActionCommand"), str):
        recommendations.append(
            {
                "label": str(queue_summary["refreshActionLabel"]).strip(),
                "description": "Refresh the source inventory and drift summary.",
                "command": str(queue_summary["refreshActionCommand"]).strip(),
            }
        )
    for item in changed_items[:3]:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        label = humanize_knowledge_source_label(item.get("name") or key)
        if not key or not label:
            continue
        recommendations.append(
            {
                "label": f"Review source: {label}",
                "description": f"Open source details for {label}.",
                "command": query_source_command(key),
            }
        )
    action_map = {
        str(item.get("label") or "").strip(): str(item.get("command") or "").strip()
        for item in recommendations
        if isinstance(item, dict) and str(item.get("label") or "").strip() and str(item.get("command") or "").strip()
    }
    user_action_details = action_details_from_ui_actions(recommendations, action_map)
    current_labels: list[str] = []
    source_labels: list[str] = []
    control_labels: list[str] = []
    for index, item in enumerate(user_action_details):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        if index == 0:
            current_labels.append(label)
        elif label.startswith("Review source: "):
            source_labels.append(label)
        elif label in {
            str(queue_summary.get("refreshActionLabel") or "").strip(),
            str(queue_summary.get("primaryActionLabel") or "").strip(),
        }:
            control_labels.append(label)
    user_action_details = annotate_research_action_details(
        user_action_details,
        current_labels=current_labels,
        control_labels=control_labels,
        source_labels=source_labels,
        topic_labels=[],
        worknet_labels=[],
        reference_labels=[],
        current_tier="current",
        control_tier="queued",
        source_tier="queued",
    )
    changed_source_highlights = [
        highlight
        for highlight in (
            changed_source_highlight_entry(item)
            for item in knowledge_display_changed_sources(changed_items, source_records=source_records)
        )
        if isinstance(highlight, dict)
    ]
    status = "source_review_needed" if changed_items else "source_ready"
    execution_payload = execution_state_payload(
        status,
        headline=str(queue_summary.get("headline") or "Source review ready"),
    )
    research_action_groups = build_research_action_groups(
        user_action_details,
        current_labels=current_labels,
        control_labels=control_labels,
        source_labels=source_labels,
        topic_labels=[],
        worknet_labels=[],
        reference_labels=[],
        control_first=False,
    )
    recommendations = annotate_research_action_details(
        recommendations,
        current_labels=current_labels,
        control_labels=control_labels,
        source_labels=source_labels,
        topic_labels=[],
        worknet_labels=[],
        reference_labels=[],
        current_tier="current",
        control_tier="queued",
        source_tier="queued",
    )
    user_action_details = frontload_user_action_labels(
        user_action_details,
        [
            *current_labels,
            *source_labels,
            *control_labels,
        ],
    )
    return normalize_query_payload({
        "query": "changed",
        "status": status,
        "progress": "[2/5] Source Drift",
        "headline": str(queue_summary.get("headline") or "Source review ready"),
        "summary": knowledge_review_queue_summary_text(queue_summary),
        "executionState": execution_payload.get("executionState"),
        "executionStateDisplay": execution_payload.get("executionStateDisplay"),
        "executionHeadline": execution_payload.get("executionHeadline"),
        "primaryCommand": queue_summary.get("primaryActionCommand"),
        "primaryUserAction": user_action_details[0]["label"] if user_action_details else None,
        "primaryUserActionDisplay": user_action_details[0]["displayLabel"] if user_action_details else None,
        "primaryUserActionCommand": user_action_details[0]["command"] if user_action_details else None,
        "userActionDetails": user_action_details,
        "researchActionGroups": research_action_groups,
        "recommendations": recommendations,
        "sourceDriftSummary": source_drift.get("summary"),
        "sourceImpactSummary": source_impact.get("summary"),
        "changedSources": changed_items,
        "changedSourcesDisplay": knowledge_display_changed_sources(changed_items, source_records=source_records),
        "changedSourceHighlights": changed_source_highlights,
        "impacts": impacted,
        "impactsDisplay": knowledge_display_source_impact(
            {"affected": bool(impacted), "items": impacted},
            catalog=catalog,
        ),
        "reviewQueue": source_impact.get("reviewQueue"),
        "knowledgeReviewQueueSummary": queue_summary,
        "reviewQueueTopEntriesDisplay": knowledge_display_review_queue_entries(top_entries, catalog=catalog),
    }, CHANGED_SOURCES_QUERY_FIELDS)


def build_glossary_query_result_payload(
    term: str,
    *,
    catalog: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build glossary query result dependencies are required")
    GLOSSARY_QUERY_FIELDS = dependencies["GLOSSARY_QUERY_FIELDS"]
    build_glossary_catalog = dependencies["build_glossary_catalog"]
    normalize_glossary_item_payload = dependencies["normalize_glossary_item_payload"]
    normalize_glossary_query_match_payload = dependencies["normalize_glossary_query_match_payload"]
    normalize_query_payload = dependencies["normalize_query_payload"]

    catalog = catalog if isinstance(catalog, dict) else build_glossary_catalog()
    query = str(term or "").strip().lower()
    match = None
    for item in catalog.get("terms", []):
        candidates = [str(item.get("term", "")).lower()]
        candidates.extend(str(alias).lower() for alias in item.get("aliases", []))
        if query in candidates:
            match = item
            break
    normalized_match = normalize_glossary_query_match_payload(match) if isinstance(match, dict) else None
    normalized_match_display = normalize_glossary_item_payload(match) if isinstance(match, dict) else None
    return normalize_query_payload(
        {
            "query": query,
            "match": normalized_match,
            "matchDisplay": normalized_match_display,
        },
        GLOSSARY_QUERY_FIELDS,
    )
