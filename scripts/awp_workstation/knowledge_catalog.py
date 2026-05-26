"""Knowledge catalog builders."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def build_knowledge_catalog_payload(
    *,
    rebuild_derived: bool = False,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build knowledge catalog dependencies are required")
    CONCEPT_DIRECTORY_ITEM_FIELDS = dependencies["CONCEPT_DIRECTORY_ITEM_FIELDS"]
    DEFAULT_RPC_URL = dependencies["DEFAULT_RPC_URL"]
    KNOWLEDGE_CATALOG_SCHEMA_VERSION = dependencies["KNOWLEDGE_CATALOG_SCHEMA_VERSION"]
    KNOWN_WORKNETS = dependencies["KNOWN_WORKNETS"]
    OFFICIAL_SKILL_ALLOWLIST_PREFIXES = dependencies["OFFICIAL_SKILL_ALLOWLIST_PREFIXES"]
    SAFETY_RULES = dependencies["SAFETY_RULES"]
    annotate_knowledge_catalog_runtime_summaries = dependencies["annotate_knowledge_catalog_runtime_summaries"]
    atomic_write_json = dependencies["atomic_write_json"]
    build_concept_catalog = dependencies["build_concept_catalog"]
    build_coverage_audit = dependencies["build_coverage_audit"]
    build_glossary_catalog = dependencies["build_glossary_catalog"]
    build_knowledge_overview = dependencies["build_knowledge_overview"]
    build_knowledge_reference_index = dependencies["build_knowledge_reference_index"]
    build_knowledge_review_queue = dependencies["build_knowledge_review_queue"]
    build_knowledge_source_directory = dependencies["build_knowledge_source_directory"]
    build_knowledge_topic_directory = dependencies["build_knowledge_topic_directory"]
    build_knowledge_topic_index = dependencies["build_knowledge_topic_index"]
    build_skill_inspection_catalog = dependencies["build_skill_inspection_catalog"]
    build_source_drift_impact_report = dependencies["build_source_drift_impact_report"]
    build_source_drift_report = dependencies["build_source_drift_report"]
    build_source_evidence_catalog = dependencies["build_source_evidence_catalog"]
    build_source_fact_catalog = dependencies["build_source_fact_catalog"]
    build_source_inventory = dependencies["build_source_inventory"]
    build_topic_dossier_catalog = dependencies["build_topic_dossier_catalog"]
    build_topic_freshness_catalog = dependencies["build_topic_freshness_catalog"]
    ensure_user_preferences = dependencies["ensure_user_preferences"]
    load_cached_knowledge_review_queue = dependencies["load_cached_knowledge_review_queue"]
    load_cached_source_drift = dependencies["load_cached_source_drift"]
    load_cached_source_impact = dependencies["load_cached_source_impact"]
    load_cached_topic_freshness = dependencies["load_cached_topic_freshness"]
    now_iso = dependencies["now_iso"]
    project_fields = dependencies["project_fields"]
    skill_registry_from_inventory = dependencies["skill_registry_from_inventory"]
    state_context = dependencies["state_context"]
    write_reference_export = dependencies["write_reference_export"]

    state = state_context()
    preferences = ensure_user_preferences(state)
    inventory = build_source_inventory()
    skill_registry = skill_registry_from_inventory(inventory, state=state)
    skill_inspections = build_skill_inspection_catalog(state=state, inventory=inventory)
    source_facts = build_source_fact_catalog()
    source_evidence = build_source_evidence_catalog()
    glossary = build_glossary_catalog()
    concept_catalog = build_concept_catalog()
    topic_dossiers = build_topic_dossier_catalog()
    coverage_audit = build_coverage_audit(
        state=state,
        inventory=inventory,
        source_facts=source_facts,
        source_evidence=source_evidence,
        topic_dossiers=topic_dossiers,
        glossary=glossary,
        concept_catalog=concept_catalog,
        skill_inspections=skill_inspections,
    )
    if rebuild_derived:
        source_drift = build_source_drift_report(state=state)
        source_impact = build_source_drift_impact_report(
            state=state,
            drift_report=source_drift,
            topic_dossiers=topic_dossiers,
            source_facts=source_facts,
            source_evidence=source_evidence,
        )
        topic_freshness = build_topic_freshness_catalog(
            state=state,
            source_impact=source_impact,
            topic_dossiers=topic_dossiers,
            source_facts=source_facts,
        )
        knowledge_review_queue = build_knowledge_review_queue(
            state=state,
            source_impact=source_impact,
            topic_freshness=topic_freshness,
            source_evidence=source_evidence,
        )
    else:
        source_drift = load_cached_source_drift(state) or build_source_drift_report(state=state)
        source_impact = load_cached_source_impact(state) or build_source_drift_impact_report(
            state=state,
            drift_report=source_drift,
            topic_dossiers=topic_dossiers,
            source_facts=source_facts,
            source_evidence=source_evidence,
        )
        topic_freshness = load_cached_topic_freshness(state) or build_topic_freshness_catalog(
            state=state,
            source_impact=source_impact,
            topic_dossiers=topic_dossiers,
            source_facts=source_facts,
        )
        knowledge_review_queue = load_cached_knowledge_review_queue(state) or build_knowledge_review_queue(
            state=state,
            source_impact=source_impact,
            topic_freshness=topic_freshness,
            source_evidence=source_evidence,
        )
    catalog = {
        "generatedAt": now_iso(),
        "schemaVersion": KNOWLEDGE_CATALOG_SCHEMA_VERSION,
        "protocolDefaults": {
            "stateRoot": state["root"],
            "rpcUrl": DEFAULT_RPC_URL,
            "allowlistedSkillPrefixes": list(OFFICIAL_SKILL_ALLOWLIST_PREFIXES),
        },
        "userPreferences": preferences,
        "safetyRules": SAFETY_RULES,
        "sources": inventory,
        "sourceDrift": source_drift,
        "sourceImpact": source_impact,
        "topicFreshness": topic_freshness,
        "knowledgeReviewQueue": knowledge_review_queue,
        "sourceFacts": source_facts["facts"],
        "sourceEvidence": source_evidence["records"],
        "glossary": glossary["terms"],
        "concepts": concept_catalog["concepts"],
        "topicDossiers": topic_dossiers["dossiers"],
        "coverageAudit": coverage_audit,
        "skills": skill_registry,
        "skillInspections": skill_inspections["inspections"],
        "worknets": [
            {
                "key": item["key"],
                "worknetId": item["worknet_id"],
                "name": item["name"],
                "status": item["status"],
                "symbol": item["symbol"],
                "installUri": item.get("install_uri"),
                "sourceKeys": item.get("source_keys", []),
                "goal": item["goal"],
                "loop": item["loop"],
                "automationLevel": item["automation_level"],
                "riskLevel": item["risk_level"],
                "recommendedRole": item["recommended_role"],
            }
            for item in KNOWN_WORKNETS
        ],
    }
    topic_index = build_knowledge_topic_index(catalog)
    topic_directory = build_knowledge_topic_directory(topic_index)
    reference_index = build_knowledge_reference_index(topic_index)
    source_directory = build_knowledge_source_directory(catalog)
    concept_directory = [
        project_fields(item, CONCEPT_DIRECTORY_ITEM_FIELDS)
        for item in catalog.get("concepts", [])
        if isinstance(item, dict)
    ]
    catalog["knowledgeOverview"] = build_knowledge_overview(
        catalog,
        topic_index=topic_index,
        topic_directory=topic_directory,
        reference_index=reference_index,
        source_directory=source_directory,
    )
    catalog["topicIndex"] = topic_index
    catalog["topicDirectory"] = topic_directory
    catalog["referenceIndex"] = reference_index
    catalog["sourceDirectory"] = source_directory
    catalog["conceptDirectory"] = concept_directory
    catalog = annotate_knowledge_catalog_runtime_summaries(catalog)
    atomic_write_json(Path(state["cache"]) / "knowledge-catalog.json", catalog)
    write_reference_export("knowledge-catalog.json", catalog)
    return catalog


def knowledge_topic_recommendations_payload(
    topic: str,
    label: str,
    *,
    glossary_match: Optional[dict[str, Any]],
    dossier: Optional[dict[str, Any]],
    source_fact: Optional[dict[str, Any]],
    worknet: Optional[dict[str, Any]],
    capability_report: Optional[dict[str, Any]],
    freshness: Any,
    impact_matches: list[dict[str, Any]],
    source_records: Optional[dict[str, dict[str, Any]]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    if dependencies is None:
        raise ValueError("knowledge topic recommendations dependencies are required")
    build_playbook_command = dependencies["build_playbook_command"]
    build_skill_inspect_command = dependencies["build_skill_inspect_command"]
    frontload_user_action_labels = dependencies["frontload_user_action_labels"]
    humanize_knowledge_source_label = dependencies["humanize_knowledge_source_label"]
    knowledge_freshness_affected_items = dependencies["knowledge_freshness_affected_items"]
    knowledge_resolved_topic_key = dependencies["knowledge_resolved_topic_key"]
    knowledge_topic_execution_state = dependencies["knowledge_topic_execution_state"]
    knowledge_worknet_metadata = dependencies["knowledge_worknet_metadata"]
    preferred_worknet_source_keys_for_runtime_state = dependencies["preferred_worknet_source_keys_for_runtime_state"]
    prioritize_action_entries = dependencies["prioritize_action_entries"]
    query_knowledge_command = dependencies["query_knowledge_command"]
    query_source_command = dependencies["query_source_command"]
    render_argv = dependencies["render_argv"]
    run_worknet_command = dependencies["run_worknet_command"]
    scan_worknets_command = dependencies["scan_worknets_command"]

    recommendations: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(label_text: Optional[str], description: str, command: Optional[str]) -> None:
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

    affected = knowledge_freshness_affected_items(freshness)
    capability_state = knowledge_topic_execution_state(
        label=label,
        affected=affected,
        capability_report=capability_report if isinstance(capability_report, dict) else None,
    )
    if affected:
        add(
            f"Refresh {label} knowledge",
            "Rebuild this knowledge topic because related source material changed.",
            query_knowledge_command(topic, rebuild=True),
        )
        for item in impact_matches[:2]:
            source_key = str(item.get("sourceKey") or "").strip()
            source_name = humanize_knowledge_source_label(item.get("sourceName") or source_key)
            if source_key:
                add(
                    f"Review source {source_name}",
                    "Review the changed source before trusting this topic.",
                    query_source_command(source_key, rebuild=True),
                )
    else:
        canonical_topic = knowledge_resolved_topic_key(
            topic,
            glossary_match=glossary_match,
            dossier=dossier,
            worknet=worknet,
        )
        add(
            f"Refresh {label} knowledge",
            "Rebuild this knowledge topic from current local source data.",
            query_knowledge_command(canonical_topic, rebuild=True),
        )

    if isinstance(worknet, dict) and worknet.get("key"):
        worknet_key = str(worknet["key"])
        worknet_source_keys = [
            str(source_key).strip()
            for source_key in worknet.get("sourceKeys", [])
            if str(source_key).strip()
        ] if isinstance(worknet.get("sourceKeys"), list) else []
        worknet_metadata = knowledge_worknet_metadata(
            worknet_key=worknet_key,
            worknet_id=worknet.get("worknetId") if isinstance(worknet, dict) else None,
            source_keys=worknet_source_keys,
            install_uri=worknet.get("installUri") if isinstance(worknet, dict) else None,
            capability_report=capability_report,
        )
        if not affected and isinstance(capability_report, dict):
            runnable = bool(capability_report.get("runnable"))
            cli_status = str(capability_report.get("cliStatus") or "").strip()
            automation = str(capability_report.get("automationLevel") or "").strip()
            role = str(capability_report.get("recommendedRole") or "").strip()
            can_start_without_stake = capability_report.get("canStartWithoutStake") is True
            if worknet_key == "predict" and runnable:
                add(
                    "Start Predict",
                    "Start the Predict route after current readiness checks.",
                    run_worknet_command(worknet_key, execute=True, auto_advance=True),
                )
            elif worknet_key == "gov" and cli_status == "ready":
                add(
                    "Start Gov",
                    "Start the Gov route after public and signed-action readiness checks.",
                    run_worknet_command(worknet_key, execute=True, auto_advance=True),
                )
            elif worknet_key == "ardi" and cli_status == "ready":
                add(
                    "Start Ardi",
                    "Start the Ardi route after gas and stake checks.",
                    run_worknet_command(worknet_key, execute=True, auto_advance=True),
                )
            elif role == "identity" or worknet_key == "kya":
                add(
                    "Start KYA",
                    "Start the KYA identity or delegated eligibility route.",
                    run_worknet_command(worknet_key, execute=True, auto_advance=True),
                )
            elif str(worknet_metadata.get("runtimeSpecState") or "").strip() == "runtime-doc-available":
                preferred_source_keys = preferred_worknet_source_keys_for_runtime_state(
                    worknet_source_keys,
                    runtime_spec_state=str(worknet_metadata.get("runtimeSpecState") or "").strip() or None,
                    source_records=source_records,
                )
                if not preferred_source_keys and worknet_source_keys:
                    preferred_source_keys = [key for key in worknet_source_keys if key != "awp-live-query"] or worknet_source_keys[:]
                for source_key in preferred_source_keys[:2]:
                    add(
                        f"Review source {humanize_knowledge_source_label(source_key)}",
                        f"Review {label} source evidence before runtime inspection.",
                        query_source_command(source_key),
                    )
                inspect_command = build_skill_inspect_command(worknet_key)
                add(
                    f"Inspect {label} skill",
                    f"Inspect the {label} checkout before runtime execution.",
                    render_argv([str(part) for part in inspect_command.get("argv", [])]) if isinstance(inspect_command.get("argv"), list) else None,
                )
                add(
                    "Review WorkNet options",
                    f"Review WorkNet options while {label} runtime evidence is incomplete.",
                    scan_worknets_command(),
                )
            elif role == "observer" or automation == "manual-only" or cli_status in {"remote-profile-only", "empty-official-repo"}:
                preferred_source_keys = preferred_worknet_source_keys_for_runtime_state(
                    worknet_source_keys,
                    runtime_spec_state=str(worknet_metadata.get("runtimeSpecState") or "").strip() or None,
                    source_records=source_records,
                )
                if not preferred_source_keys and worknet_source_keys:
                    preferred_source_keys = [key for key in worknet_source_keys if key != "awp-live-query"] or worknet_source_keys[:]
                for source_key in preferred_source_keys[:2]:
                    add(
                        f"Review source {humanize_knowledge_source_label(source_key)}",
                        f"Review {label} skill and source evidence before execution.",
                        query_source_command(source_key),
                    )
                add(
                    "Review WorkNet options",
                    f"Review WorkNet options because {label} is not directly runnable yet.",
                    scan_worknets_command(),
                )
            elif worknet_key == "mine" and runnable and can_start_without_stake:
                add(
                    f"Start {label}",
                    "Start this WorkNet route after current readiness checks.",
                    run_worknet_command(worknet_key, execute=True, auto_advance=True),
                )
            elif runnable:
                add(
                    f"Start {label}",
                    "Start this WorkNet route after current readiness checks.",
                    run_worknet_command(worknet_key, execute=True, auto_advance=True),
                )
        add(
            f"Build {label} playbook",
            "Build the WorkPlaybook without executing it.",
            build_playbook_command(worknet_key),
        )
        add(
            "Review WorkNet options",
            "Scan available WorkNets and capability reports.",
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
                f"Review source {humanize_knowledge_source_label(source_key)}",
                "Review this source for the selected knowledge topic.",
                query_source_command(source_key),
            )

    worknet_key = str(worknet.get("key") or "").strip() if isinstance(worknet, dict) else None
    recommendations = prioritize_action_entries(
        recommendations,
        execution_state=capability_state.get("executionState") or ("review_required" if affected else "knowledge_ready"),
        resume_status=None,
        worknet_key=worknet_key or None,
    )
    if worknet_key in {"tmr", "community"}:
        recommendations = frontload_user_action_labels(
            recommendations,
            [
                item.get("label")
                for item in recommendations
                if isinstance(item, dict) and str(item.get("label") or "").strip().startswith("Review source")
            ],
        )
    return recommendations[:5]


def build_knowledge_topic_index_payload(
    catalog: Optional[dict[str, Any]] = None,
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    if dependencies is None:
        raise ValueError("build knowledge topic index dependencies are required")
    KNOWLEDGE_DIRECTORY_FACT_KEYS = dependencies["KNOWLEDGE_DIRECTORY_FACT_KEYS"]
    build_knowledge_catalog = dependencies["build_knowledge_catalog"]
    build_knowledge_query_result = dependencies["build_knowledge_query_result"]
    capability_reports_by_worknet_key = dependencies["capability_reports_by_worknet_key"]
    join_product_sentences = dependencies["join_product_sentences"]
    knowledge_catalog_topic_keys = dependencies["knowledge_catalog_topic_keys"]
    knowledge_first_non_empty = dependencies["knowledge_first_non_empty"]
    knowledge_runtime_augmented_preview = dependencies["knowledge_runtime_augmented_preview"]
    knowledge_runtime_probe_count = dependencies["knowledge_runtime_probe_count"]
    knowledge_runtime_probe_display_from_catalog = dependencies["knowledge_runtime_probe_display_from_catalog"]
    knowledge_runtime_probe_summary_sentence = dependencies["knowledge_runtime_probe_summary_sentence"]
    load_cached_capability_bundle = dependencies["load_cached_capability_bundle"]
    load_cached_knowledge_catalog = dependencies["load_cached_knowledge_catalog"]
    query_knowledge_command = dependencies["query_knowledge_command"]
    state_context = dependencies["state_context"]

    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    capability_reports = capability_reports_by_worknet_key(bundle=load_cached_capability_bundle(state_context()))
    index: list[dict[str, Any]] = []
    for topic_key in knowledge_catalog_topic_keys(catalog):
        result = build_knowledge_query_result(topic_key, catalog=catalog)
        dossier = result.get("dossier") if isinstance(result.get("dossier"), dict) else {}
        source_fact = result.get("sourceFact") if isinstance(result.get("sourceFact"), dict) else {}
        worknet = result.get("worknet") if isinstance(result.get("worknet"), dict) else {}
        glossary = result.get("glossary") if isinstance(result.get("glossary"), dict) else {}
        freshness = result.get("freshness") if isinstance(result.get("freshness"), dict) else {}
        source_impact = result.get("sourceImpact") if isinstance(result.get("sourceImpact"), dict) else {}
        affected_source_keys: list[str] = []
        for item in source_impact.get("items", []):
            if not isinstance(item, dict):
                continue
            source_key = str(item.get("sourceKey") or "").strip()
            if source_key and source_key not in affected_source_keys:
                affected_source_keys.append(source_key)
        source_keys: list[str] = []
        for container in (dossier, source_fact, glossary, worknet):
            if not isinstance(container, dict):
                continue
            for source_key in container.get("sourceKeys", []):
                key = str(source_key).strip()
                if key and key not in source_keys:
                    source_keys.append(key)
        worknet_key = str(worknet.get("key") or "").strip()
        runtime_probe_display = (
            result.get("runtimeProbeDisplay")
            if isinstance(result.get("runtimeProbeDisplay"), dict)
            else knowledge_runtime_probe_display_from_catalog(
                catalog,
                source_keys=source_keys,
                worknet_key=worknet_key or None,
                capability_report=capability_reports.get(worknet_key) if worknet_key else None,
            )
        )
        runtime_summary = knowledge_runtime_probe_summary_sentence(runtime_probe_display)
        summary_text = join_product_sentences(
            [
                result.get("summary"),
                runtime_summary,
            ]
        ) or result.get("summary")
        metadata_source = next(
            (
                payload
                for payload in (
                    result.get("worknetDisplay"),
                    result.get("dossierDisplay"),
                    result.get("sourceFactDisplay"),
                )
                if isinstance(payload, dict)
            ),
            {},
        )
        kind = knowledge_first_non_empty(
            dossier.get("kind"),
            ("worknet" if worknet else None),
            ("glossary" if glossary else None),
            ("fact" if source_fact else None),
            "topic",
        )
        index.append(
            {
                "key": result.get("resolvedTopicKey") or topic_key,
                "rawKey": topic_key,
                "canonicalTopicKey": result.get("resolvedTopicKey") or topic_key,
                "label": result.get("resolvedTopicLabel") or topic_key,
                "kind": kind,
                "headline": result.get("headline"),
                "summary": summary_text,
                "summaryPreview": knowledge_runtime_augmented_preview(
                    result.get("plainLanguage") or result.get("summary") or summary_text,
                    runtime_summary,
                    headline=result.get("headline"),
                    max_chars=140,
                    max_sentences=2,
                ),
                "plainLanguage": result.get("plainLanguage"),
                "runtimeSummary": runtime_summary,
                "runtimeProbeCount": knowledge_runtime_probe_count(runtime_probe_display) or None,
                "canonicalWorknetId": metadata_source.get("canonicalWorknetId") if isinstance(metadata_source, dict) else None,
                "predecessorWorknetIds": metadata_source.get("predecessorWorknetIds", []) if isinstance(metadata_source, dict) else [],
                "officialSkillUri": metadata_source.get("officialSkillUri") if isinstance(metadata_source, dict) else None,
                "minStakeHint": metadata_source.get("minStakeHint") if isinstance(metadata_source, dict) else None,
                "minStakeHintDisplay": metadata_source.get("minStakeHintDisplay") if isinstance(metadata_source, dict) else None,
                "runtimeSpecState": metadata_source.get("runtimeSpecState") if isinstance(metadata_source, dict) else None,
                "runtimeSpecStateDisplay": metadata_source.get("runtimeSpecStateDisplay") if isinstance(metadata_source, dict) else None,
                "queryCommand": query_knowledge_command(topic_key),
                "primaryCommand": result.get("primaryCommand"),
                "freshnessStatus": freshness.get("status"),
                "highestPriority": freshness.get("highestPriority"),
                "affectedSourceKeys": affected_source_keys,
                "sourceKeys": source_keys,
                "officialUrls": dossier.get("officialUrls", []),
                "aliases": glossary.get("aliases", []),
                "worknetKey": worknet.get("key"),
                "worknetName": worknet.get("name"),
                "automationLevel": worknet.get("automationLevel"),
                "riskLevel": worknet.get("riskLevel"),
                "recommendedRole": worknet.get("recommendedRole"),
                "surfaceLevel": "topic" if str(kind) != "fact" else ("topic" if topic_key in KNOWLEDGE_DIRECTORY_FACT_KEYS else "reference"),
                "recommendations": [
                    {
                        "label": item.get("label"),
                        "command": item.get("command"),
                    }
                    for item in result.get("recommendations", [])[:3]
                    if isinstance(item, dict)
                ],
                "citations": result.get("citations", [])[:3] if isinstance(result.get("citations"), list) else [],
            }
        )
    return index


def build_knowledge_source_directory_payload(
    catalog: Optional[dict[str, Any]] = None,
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    if dependencies is None:
        raise ValueError("build knowledge source directory dependencies are required")
    build_knowledge_catalog = dependencies["build_knowledge_catalog"]
    capability_reports_by_worknet_key = dependencies["capability_reports_by_worknet_key"]
    compact_preview_text = dependencies["compact_preview_text"]
    humanize_knowledge_source_label = dependencies["humanize_knowledge_source_label"]
    knowledge_display_drift_item = dependencies["knowledge_display_drift_item"]
    knowledge_display_source_impact = dependencies["knowledge_display_source_impact"]
    knowledge_display_source_record = dependencies["knowledge_display_source_record"]
    knowledge_runtime_augmented_preview = dependencies["knowledge_runtime_augmented_preview"]
    knowledge_runtime_probe_display_from_catalog = dependencies["knowledge_runtime_probe_display_from_catalog"]
    knowledge_source_directory_sort_key = dependencies["knowledge_source_directory_sort_key"]
    knowledge_source_records_from_catalog = dependencies["knowledge_source_records_from_catalog"]
    load_cached_capability_bundle = dependencies["load_cached_capability_bundle"]
    load_cached_knowledge_catalog = dependencies["load_cached_knowledge_catalog"]
    query_source_command = dependencies["query_source_command"]
    state_context = dependencies["state_context"]

    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    capability_reports = capability_reports_by_worknet_key(bundle=load_cached_capability_bundle(state_context()))
    source_records = knowledge_source_records_from_catalog(catalog)
    source_drift = catalog.get("sourceDrift", {}) if isinstance(catalog.get("sourceDrift"), dict) else {}
    source_impact = catalog.get("sourceImpact", {}) if isinstance(catalog.get("sourceImpact"), dict) else {}
    drift_by_source = {
        str(item.get("key") or "").strip(): item
        for item in source_drift.get("items", [])
        if isinstance(item, dict) and str(item.get("key") or "").strip()
    }
    impact_by_source = {
        str(item.get("sourceKey") or "").strip(): item
        for item in source_impact.get("impacts", [])
        if isinstance(item, dict) and str(item.get("sourceKey") or "").strip()
    }
    directory: list[dict[str, Any]] = []
    for source_key, source_record in source_records.items():
        drift_item = drift_by_source.get(source_key)
        impact_item = impact_by_source.get(source_key)
        runtime_probe_display = knowledge_runtime_probe_display_from_catalog(
            catalog,
            source_keys=[source_key],
            worknet_key=str(source_record.get("worknetKey") or "").strip() if isinstance(source_record, dict) else None,
        )
        source_display = knowledge_display_source_record(
            source_record,
            drift_item=drift_item,
            impact_item=impact_item,
            runtime_probe_display=runtime_probe_display,
            capability_report=capability_reports.get(str(source_record.get("worknetKey") or "").strip()) if isinstance(source_record, dict) and str(source_record.get("worknetKey") or "").strip() else None,
        )
        drift_display = knowledge_display_drift_item(
            drift_item,
            source_record=source_record,
        )
        impact_display = knowledge_display_source_impact(
            {"affected": bool(impact_item), "items": [impact_item] if isinstance(impact_item, dict) else []},
            catalog=catalog,
        )
        summary_parts: list[str] = []
        display_summary = str(source_display.get("summaryDisplay") or "").strip() if isinstance(source_display, dict) else ""
        if display_summary:
            summary_parts.append(display_summary)
        impact_summary = str(impact_display.get("summary") or "").strip() if isinstance(impact_display, dict) else ""
        if impact_summary and impact_summary not in summary_parts:
            summary_parts.append(impact_summary)
        drift_note = str(drift_display.get("note") or "").strip() if isinstance(drift_display, dict) else ""
        if drift_note and drift_note not in summary_parts:
            summary_parts.append(drift_note)
        drift_status = str((drift_item or {}).get("status") or "").strip()
        if impact_item or drift_status not in {"", "unchanged"}:
            freshness_status = "affected" if drift_status != "no-baseline" else "unknown"
        else:
            freshness_status = "stable"
        highest_priority = str((impact_item or {}).get("priority") or "low").strip() or "low"
        directory.append(
            {
                "key": source_key,
                "label": str(source_display.get("nameDisplay") or humanize_knowledge_source_label(source_record.get("name") or source_key)).strip(),
                "name": source_record.get("name"),
                "headline": source_display.get("headline") if isinstance(source_display, dict) else None,
                "summary": " ".join(part for part in summary_parts if part).strip(),
                "summaryPreview": knowledge_runtime_augmented_preview(
                    (
                        source_display.get("summaryDisplay")
                        if isinstance(source_display, dict)
                        else " ".join(part for part in summary_parts if part).strip()
                    ),
                    source_display.get("runtimeSummary") if isinstance(source_display, dict) else None,
                    headline=source_display.get("headline") if isinstance(source_display, dict) else None,
                    max_chars=140,
                    max_sentences=2,
                )
                or (
                    source_display.get("summaryPreview")
                    if isinstance(source_display, dict)
                    else None
                )
                or compact_preview_text(
                    " ".join(part for part in summary_parts if part).strip(),
                    max_chars=140,
                    max_sentences=2,
                ),
                "queryCommand": query_source_command(source_key),
                "primaryCommand": query_source_command(source_key, rebuild=True),
                "url": source_record.get("url") if isinstance(source_record, dict) else None,
                "kind": source_record.get("kind") if isinstance(source_record, dict) else None,
                "kindDisplay": source_display.get("kindDisplay") if isinstance(source_display, dict) else None,
                "trustTier": source_record.get("trustTier") if isinstance(source_record, dict) else None,
                "trustTierDisplay": source_display.get("trustTierDisplay") if isinstance(source_display, dict) else None,
                "worknetKey": source_record.get("worknetKey") if isinstance(source_record, dict) else None,
                "canonicalWorknetId": source_display.get("canonicalWorknetId") if isinstance(source_display, dict) else None,
                "predecessorWorknetIds": source_display.get("predecessorWorknetIds", []) if isinstance(source_display, dict) else [],
                "officialSkillUri": source_display.get("officialSkillUri") if isinstance(source_display, dict) else None,
                "minStakeHint": source_display.get("minStakeHint") if isinstance(source_display, dict) else None,
                "minStakeHintDisplay": source_display.get("minStakeHintDisplay") if isinstance(source_display, dict) else None,
                "runtimeSpecState": source_display.get("runtimeSpecState") if isinstance(source_display, dict) else None,
                "runtimeSpecStateDisplay": source_display.get("runtimeSpecStateDisplay") if isinstance(source_display, dict) else None,
                "freshnessStatus": freshness_status,
                "highestPriority": highest_priority,
                "runtimeSummary": source_display.get("runtimeSummary") if isinstance(source_display, dict) else None,
                "runtimeProbeCount": source_display.get("runtimeProbeCount") if isinstance(source_display, dict) else None,
                "driftStatus": drift_status or None,
                "driftStatusDisplay": drift_display.get("statusDisplay") if isinstance(drift_display, dict) else None,
                "changedFieldsDisplay": drift_display.get("changedFieldsDisplay", []) if isinstance(drift_display, dict) else [],
                "impactedTopicsDisplay": impact_display.get("items", [{}])[0].get("impactedTopicsDisplay", []) if isinstance(impact_display, dict) and impact_display.get("items") else [],
                "impactedWorknetsDisplay": impact_display.get("items", [{}])[0].get("impactedWorknetsDisplay", []) if isinstance(impact_display, dict) and impact_display.get("items") else [],
                "reviewHint": impact_display.get("items", [{}])[0].get("reviewHint") if isinstance(impact_display, dict) and impact_display.get("items") else None,
            }
        )
    directory.sort(key=knowledge_source_directory_sort_key)
    return directory


def build_knowledge_overview_payload(
    catalog: Optional[dict[str, Any]] = None,
    *,
    topic_index: Optional[list[dict[str, Any]]] = None,
    topic_directory: Optional[list[dict[str, Any]]] = None,
    reference_index: Optional[list[dict[str, Any]]] = None,
    source_directory: Optional[list[dict[str, Any]]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build knowledge overview dependencies are required")
    build_knowledge_catalog = dependencies["build_knowledge_catalog"]
    build_knowledge_reference_index = dependencies["build_knowledge_reference_index"]
    build_knowledge_source_directory = dependencies["build_knowledge_source_directory"]
    build_knowledge_topic_directory = dependencies["build_knowledge_topic_directory"]
    build_knowledge_topic_index = dependencies["build_knowledge_topic_index"]
    build_normalized_knowledge_highlight = dependencies["build_normalized_knowledge_highlight"]
    knowledge_freshness_status_display = dependencies["knowledge_freshness_status_display"]
    knowledge_review_queue_summary_text = dependencies["knowledge_review_queue_summary_text"]
    knowledge_runtime_augmented_preview = dependencies["knowledge_runtime_augmented_preview"]
    knowledge_runtime_augmented_summary = dependencies["knowledge_runtime_augmented_summary"]
    load_cached_knowledge_catalog = dependencies["load_cached_knowledge_catalog"]
    normalize_affected_topic_payload = dependencies["normalize_affected_topic_payload"]
    now_iso = dependencies["now_iso"]
    summarize_knowledge_review_queue = dependencies["summarize_knowledge_review_queue"]

    catalog = catalog if isinstance(catalog, dict) else (load_cached_knowledge_catalog() or build_knowledge_catalog())
    topic_index = topic_index if isinstance(topic_index, list) else build_knowledge_topic_index(catalog)
    topic_directory = topic_directory if isinstance(topic_directory, list) else build_knowledge_topic_directory(topic_index)
    reference_index = reference_index if isinstance(reference_index, list) else build_knowledge_reference_index(topic_index)
    source_directory = source_directory if isinstance(source_directory, list) else build_knowledge_source_directory(catalog)
    queue = catalog.get("knowledgeReviewQueue", {}) if isinstance(catalog.get("knowledgeReviewQueue"), dict) else {}
    queue_summary = summarize_knowledge_review_queue(queue)
    affected_topics = [item for item in topic_directory if isinstance(item, dict) and item.get("freshnessStatus") == "affected"]
    stable_topics = [item for item in topic_directory if isinstance(item, dict) and item.get("freshnessStatus") != "affected"]
    worknet_topics = [item for item in topic_directory if isinstance(item, dict) and item.get("worknetKey")]
    affected_sources = [item for item in source_directory if isinstance(item, dict) and item.get("freshnessStatus") == "affected"]
    focus_topics = topic_directory[:6]
    summary = (
        f"{len(topic_directory)} topics, "
        f"{len(worknet_topics)} WorkNet topics, "
        f"{len(catalog.get('glossary', [])) if isinstance(catalog.get('glossary'), list) else 0} glossary terms, "
        f"and {len(reference_index)} references are indexed."
    )
    queue_text = knowledge_review_queue_summary_text(queue_summary)
    if queue_summary.get("hasPendingReviews"):
        summary = f"{summary} {queue_text}"
    else:
        summary += " No pending source reviews."
    headline = (
        str(queue_summary.get("headline") or "AWP knowledge ready")
        if queue_summary.get("hasPendingReviews")
        else "AWP knowledge ready"
    )
    primary_action_label = None
    primary_action_command = None
    if isinstance(queue_summary.get("primaryActionLabel"), str) and queue_summary.get("primaryActionLabel"):
        primary_action_label = queue_summary["primaryActionLabel"]
        primary_action_command = queue_summary.get("primaryActionCommand")
    elif focus_topics:
        primary_action_label = f"Review topic: {focus_topics[0].get('label')}"
        primary_action_command = focus_topics[0].get("queryCommand")
    return {
        "generatedAt": catalog.get("generatedAt") or now_iso(),
        "headline": headline,
        "summary": summary,
        "topicCount": len(topic_directory),
        "rawTopicIndexCount": len(topic_index),
        "referenceEntryCount": len(reference_index),
        "sourceDirectoryCount": len(source_directory),
        "affectedSourceDirectoryCount": len(affected_sources),
        "stableTopicCount": len(stable_topics),
        "affectedTopicCount": len(affected_topics),
        "worknetTopicCount": len(worknet_topics),
        "glossaryTermCount": len(catalog.get("glossary", [])) if isinstance(catalog.get("glossary"), list) else 0,
        "officialSourceCount": len(catalog.get("sources", {}).get("officialWebSources", [])) if isinstance(catalog.get("sources"), dict) else 0,
        "pendingReviewCount": int(queue_summary.get("pendingReviewCount", 0) or 0),
        "changedSourceCount": int(queue_summary.get("changedSourceCount", 0) or 0),
        "highestPriority": queue_summary.get("highestPriority"),
        "knowledgeReviewQueueSummary": queue_summary,
        "primaryActionLabel": primary_action_label,
        "primaryActionCommand": primary_action_command,
        "focusTopics": [
            build_normalized_knowledge_highlight(
                kind="topic",
                key=item.get("key"),
                label=item.get("label"),
                headline=item.get("headline"),
                preview=knowledge_runtime_augmented_preview(
                    item.get("summaryPreview") or item.get("summary"),
                    item.get("runtimeSummary"),
                    headline=item.get("headline"),
                ),
                query_command=item.get("queryCommand"),
                primary_command=item.get("primaryCommand"),
                freshness_status=item.get("freshnessStatus"),
                research_tier="overview",
                extra={
                    "summary": knowledge_runtime_augmented_preview(
                        item.get("summaryPreview") or item.get("summary"),
                        item.get("runtimeSummary"),
                        headline=item.get("headline"),
                    ),
                    "summaryPreview": knowledge_runtime_augmented_preview(
                        item.get("summaryPreview") or item.get("summary"),
                        item.get("runtimeSummary"),
                        headline=item.get("headline"),
                    ),
                    "summaryFull": knowledge_runtime_augmented_summary(
                        item.get("summary"),
                        item.get("runtimeSummary"),
                    ) or item.get("summary"),
                    "affectedSourceKeys": item.get("affectedSourceKeys", []),
                    "worknetKey": item.get("worknetKey"),
                    "worknetName": item.get("worknetName"),
                    "automationLevel": item.get("automationLevel"),
                    "riskLevel": item.get("riskLevel"),
                    "runtimeSummary": item.get("runtimeSummary"),
                    "runtimeProbeCount": item.get("runtimeProbeCount"),
                    "status": item.get("freshnessStatus"),
                    "statusDisplay": knowledge_freshness_status_display(item.get("freshnessStatus")),
                },
            )
            for item in focus_topics
            if isinstance(item, dict)
        ],
        "affectedTopics": [
            normalize_affected_topic_payload({
                "key": item.get("key"),
                "label": item.get("label"),
                "headline": item.get("headline"),
                "primaryCommand": item.get("primaryCommand"),
                "affectedSourceKeys": item.get("affectedSourceKeys", []),
            })
            for item in affected_topics[:6]
            if isinstance(item, dict)
        ],
        "referenceHighlights": [
            build_normalized_knowledge_highlight(
                kind="reference",
                key=item.get("key"),
                label=item.get("label"),
                headline=item.get("headline"),
                preview=knowledge_runtime_augmented_preview(
                    item.get("summaryPreview") or item.get("summary"),
                    item.get("runtimeSummary"),
                    headline=item.get("headline"),
                ),
                query_command=item.get("queryCommand"),
                primary_command=item.get("primaryCommand"),
                freshness_status=item.get("freshnessStatus"),
                research_tier="overview",
                extra={
                    "summaryPreview": knowledge_runtime_augmented_preview(
                        item.get("summaryPreview") or item.get("summary"),
                        item.get("runtimeSummary"),
                        headline=item.get("headline"),
                    ),
                    "runtimeSummary": item.get("runtimeSummary"),
                    "runtimeProbeCount": item.get("runtimeProbeCount"),
                },
            )
            for item in reference_index[:6]
            if isinstance(item, dict)
        ],
        "sourceHighlights": [
            build_normalized_knowledge_highlight(
                kind="source",
                key=item.get("key"),
                label=item.get("label"),
                headline=item.get("headline"),
                preview=knowledge_runtime_augmented_preview(
                    item.get("summaryPreview") or item.get("summary"),
                    item.get("runtimeSummary"),
                    headline=item.get("headline"),
                ),
                query_command=item.get("queryCommand"),
                primary_command=item.get("primaryCommand"),
                freshness_status=item.get("freshnessStatus"),
                research_tier="overview",
                extra={
                    "summaryPreview": knowledge_runtime_augmented_preview(
                        item.get("summaryPreview") or item.get("summary"),
                        item.get("runtimeSummary"),
                        headline=item.get("headline"),
                    ),
                    "runtimeSummary": item.get("runtimeSummary"),
                    "runtimeProbeCount": item.get("runtimeProbeCount"),
                },
            )
            for item in source_directory[:6]
            if isinstance(item, dict)
        ],
    }

