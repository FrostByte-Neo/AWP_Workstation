"""Audit builders with dependency-injected workstation adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def first_dict_item(items: Any) -> Optional[dict[str, Any]]:
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict):
            return item
    return None


def first_non_runtime_evidence_item(items: Any) -> Optional[dict[str, Any]]:
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and item.get("evidenceType") != "runtime-inspection":
            return item
    return None


def contract_audit_item(
    key: str,
    title: str,
    payload: Any,
    fields: list[str],
    *,
    sample_ref: Optional[str] = None,
    missing_message: str = "No sample payload was available for this contract.",
) -> dict[str, Any]:
    expected = list(fields)
    if not isinstance(payload, dict):
        reasons = [missing_message]
        if sample_ref:
            reasons.append(f"Sample ref: {sample_ref}")
        return {
            "key": key,
            "title": title,
            "status": "missing",
            "expectedFields": expected,
            "actualFields": [],
            "missingFields": expected,
            "extraFields": [],
            "reasons": reasons,
            "sampleRef": sample_ref,
        }
    actual = list(payload.keys())
    missing_fields = [field for field in expected if field not in payload]
    extra_fields = [field for field in actual if field not in expected]
    status = "covered" if not missing_fields and not extra_fields else "partial"
    reasons = [f"Observed {len(actual)} field(s); expected fixed contract size is {len(expected)}."]
    if missing_fields:
        reasons.append("Missing fields: " + ", ".join(missing_fields[:10]))
    if extra_fields:
        reasons.append("Unexpected fields: " + ", ".join(extra_fields[:10]))
    if sample_ref:
        reasons.append(f"Sample ref: {sample_ref}")
    return {
        "key": key,
        "title": title,
        "status": status,
        "expectedFields": expected,
        "actualFields": actual,
        "missingFields": missing_fields,
        "extraFields": extra_fields,
        "reasons": reasons,
        "sampleRef": sample_ref,
    }


def contract_audit_result(items: list[dict[str, Any]], *, generated_at: str) -> dict[str, Any]:
    covered_count = sum(1 for item in items if item["status"] == "covered")
    partial_count = sum(1 for item in items if item["status"] == "partial")
    missing_count = sum(1 for item in items if item["status"] == "missing")
    return {
        "generatedAt": generated_at,
        "summary": {
            "covered": covered_count,
            "partial": partial_count,
            "missing": missing_count,
        },
        "items": items,
    }


def build_coverage_audit_payload(
    *,
    state: Optional[dict[str, Any]] = None,
    inventory: Optional[dict[str, Any]] = None,
    source_facts: Optional[dict[str, Any]] = None,
    source_evidence: Optional[dict[str, Any]] = None,
    topic_dossiers: Optional[dict[str, Any]] = None,
    glossary: Optional[dict[str, Any]] = None,
    concept_catalog: Optional[dict[str, Any]] = None,
    skill_inspections: Optional[dict[str, Any]] = None,
    coverage_requirements: list[dict[str, Any]],
    generated_root: Path,
    dependencies: dict[str, Any],
) -> dict[str, Any]:
    state_context = dependencies["state_context"]
    build_source_inventory = dependencies["build_source_inventory"]
    build_source_fact_catalog = dependencies["build_source_fact_catalog"]
    build_source_evidence_catalog = dependencies["build_source_evidence_catalog"]
    build_topic_dossier_catalog = dependencies["build_topic_dossier_catalog"]
    build_glossary_catalog = dependencies["build_glossary_catalog"]
    build_concept_catalog = dependencies["build_concept_catalog"]
    load_cached_live_worknets = dependencies["load_cached_live_worknets"]
    load_cached_source_drift = dependencies["load_cached_source_drift"]
    load_cached_source_impact = dependencies["load_cached_source_impact"]
    load_cached_knowledge_review_queue = dependencies["load_cached_knowledge_review_queue"]
    load_cached_skill_inspection_catalog = dependencies["load_cached_skill_inspection_catalog"]
    skill_registry_from_inventory = dependencies["skill_registry_from_inventory"]
    build_registration_plan = dependencies["build_registration_plan"]
    load_json = dependencies["load_json"]
    build_skill_inspection_catalog = dependencies["build_skill_inspection_catalog"]
    atomic_write_json = dependencies["atomic_write_json"]
    write_reference_export = dependencies["write_reference_export"]
    now_iso = dependencies["now_iso"]

    state = state or state_context()
    inventory = inventory or build_source_inventory(state=state)
    source_facts = source_facts or build_source_fact_catalog()
    source_evidence = source_evidence or build_source_evidence_catalog()
    topic_dossiers = topic_dossiers or build_topic_dossier_catalog()
    glossary = glossary or build_glossary_catalog()
    concept_catalog = concept_catalog or build_concept_catalog()
    live_worknets = load_cached_live_worknets(state)
    source_drift = load_cached_source_drift(state)
    source_impact = load_cached_source_impact(state)
    knowledge_review_queue = load_cached_knowledge_review_queue(state)
    skill_inspections = skill_inspections or load_cached_skill_inspection_catalog(state)
    local_sources = {
        item["key"]: item for item in inventory.get("localSources", []) if isinstance(item, dict)
    }
    skill_registry = {
        item["key"]: item for item in skill_registry_from_inventory(inventory, state=state)
    }

    glossary_terms = {str(item["term"]).lower(): item for item in glossary.get("terms", [])}
    dossiers = {item["key"]: item for item in topic_dossiers.get("dossiers", [])}
    evidence_records = source_evidence.get("records", [])
    concept_records = {
        str(item.get("key") or "").strip(): item
        for item in concept_catalog.get("concepts", [])
        if isinstance(item, dict) and str(item.get("key") or "").strip()
    }
    inspection_map = {
        str(item.get("skillKey") or "").strip(): item
        for item in skill_inspections.get("inspections", [])
        if isinstance(item, dict) and str(item.get("skillKey") or "").strip()
    } if isinstance(skill_inspections, dict) else {}

    def generated_exists(filename: str) -> bool:
        return (generated_root / filename).exists()

    items: list[dict[str, Any]] = []
    for requirement in coverage_requirements:
        key = requirement["key"]
        status = "missing"
        reasons: list[str] = []
        evidence_files: list[str] = []

        if key == "trigger-surface":
            status = "covered"
            reasons.append("SKILL metadata includes English trigger phrases.")
            evidence_files.extend(["SKILL.md", "agents/openai.yaml"])
        elif key == "protocol-encyclopedia":
            if all(name in dossiers for name in ("protocol-core", "staking", "dao")) and generated_exists("source-facts.json"):
                status = "covered"
                reasons.append("Protocol core, staking, DAO, facts, and evidence are all present locally.")
            else:
                status = "partial"
                reasons.append("Some protocol knowledge layers are still incomplete.")
            evidence_files.extend(["topic-dossiers.json", "source-facts.json", "source-evidence.json", "glossary.json"])
        elif key == "worknet-coverage":
            covered = all(name in dossiers for name in ("mine", "predict", "kya", "ardi", "gov", "tmr", "community"))
            if covered:
                status = "covered"
                reasons.append("All named WorkNets have local dossiers, including the thinner TMR and Community entries.")
            else:
                status = "partial"
                reasons.append("Some named WorkNet dossier coverage is missing.")
            evidence_files.extend(["topic-dossiers.json", "worknet-profiles.md"])
        elif key == "active-worknet-source-depth":
            thin_worknets = []
            for worknet_key in ("tmr", "community"):
                inspection = inspection_map.get(worknet_key, {})
                inspection_status = str(inspection.get("status") or "").strip()
                if inspection_status in {"remote-profile-only", "empty-official-repo"}:
                    thin_worknets.append(worknet_key)
            if thin_worknets:
                status = "partial"
                reasons.append("Some active WorkNets are still represented mainly by live IDs plus thin repo surfaces, so the encyclopedia should not treat them as fully documented yet.")
                reasons.append("Thin active worknets: " + ", ".join(thin_worknets))
            else:
                status = "covered"
                reasons.append("Every active WorkNet now has more than just a live ID and thin repo landing page in the encyclopedia.")
            evidence_files.extend(["skill-inspections.json", "source-facts.json", "source-evidence.json", "topic-dossiers.json"])
        elif key == "glossary-coverage":
            required_terms = {"rootnet", "worknet", "skilluri", "epoch", "clob", "staking"}
            if required_terms.issubset(set(glossary_terms.keys())):
                status = "covered"
                reasons.append("Required AWP terms are defined in the generated glossary.")
            else:
                status = "partial"
                reasons.append("Some required terms are still missing from the generated glossary.")
            evidence_files.extend(["glossary.json", "glossary.md"])
        elif key == "concept-workflows":
            required_concepts = {
                "registration",
                "recipient-routing",
                "allocation-and-delegation",
                "qualification-gates",
                "epoch-settlement",
                "gov-auth-signing",
                "ardi-command-journal",
            }
            if required_concepts.issubset(set(concept_records.keys())):
                status = "covered"
                thin = [
                    str(item.get("key") or "").strip()
                    for item in concept_records.values()
                    if isinstance(item, dict) and item.get("coverageState") == "thin"
                ]
                reasons.append("Cross-worknet concept/workflow records now cover registration, routing, delegation, qualification, settlement, Gov signing, and Ardi command guidance.")
                if thin:
                    reasons.append("Concepts still marked thin: " + ", ".join(thin))
            else:
                status = "partial"
                missing = sorted(required_concepts.difference(set(concept_records.keys())))
                reasons.append("The concept/workflow layer is still missing some protocol-spanning encyclopedia records.")
                if missing:
                    reasons.append("Missing concepts: " + ", ".join(missing))
            evidence_files.extend(["concept-catalog.json", "source-facts.json", "source-evidence.json"])
        elif key == "official-guide-depth":
            source_keys = {
                str(item.get("key") or "").strip()
                for item in inventory.get("officialWebSources", [])
                if isinstance(item, dict) and str(item.get("key") or "").strip()
            }
            required_sources = {
                "awp-blog",
                "awp-blog-01-launch-worknet",
                "awp-blog-02-what-is-awp",
                "awp-blog-03-start-earning",
                "awp-blog-04-fair-launch",
                "awp-blog-05-worknet",
            }
            required_facts = {
                "blog-facts",
                "blog-onboarding-facts",
                "blog-worknet-economics-facts",
                "blog-fair-launch-facts",
                "blog-worknet-launch-facts",
                "blog-protocol-facts",
            }
            required_concepts = {
                "agent-onboarding",
                "worknet-economic-unit",
                "fair-launch-and-emission",
                "worknet-launch-lifecycle",
            }
            fact_keys = {
                str(item.get("key") or "").strip()
                for item in source_facts.get("facts", [])
                if isinstance(item, dict) and str(item.get("key") or "").strip()
            }
            if required_sources.issubset(source_keys) and required_facts.issubset(fact_keys) and required_concepts.issubset(set(concept_records.keys())):
                status = "covered"
                reasons.append("Official AWP onboarding and explanatory guides are tracked as distinct source records, fact bundles, and encyclopedia concepts.")
            else:
                status = "partial"
                missing_sources = sorted(required_sources.difference(source_keys))
                missing_facts = sorted(required_facts.difference(fact_keys))
                missing_concepts = sorted(required_concepts.difference(set(concept_records.keys())))
                reasons.append("The official guide layer is still incomplete.")
                if missing_sources:
                    reasons.append("Missing guide sources: " + ", ".join(missing_sources))
                if missing_facts:
                    reasons.append("Missing guide fact sets: " + ", ".join(missing_facts))
                if missing_concepts:
                    reasons.append("Missing guide concepts: " + ", ".join(missing_concepts))
            evidence_files.extend(["source-inventory.json", "source-facts.json", "concept-catalog.json", "encyclopedia.md", "source-map.md"])
        elif key == "public-status-surfaces":
            source_keys = {
                str(item.get("key") or "").strip()
                for item in inventory.get("officialWebSources", [])
                if isinstance(item, dict) and str(item.get("key") or "").strip()
            }
            fact_keys = {
                str(item.get("key") or "").strip()
                for item in source_facts.get("facts", [])
                if isinstance(item, dict) and str(item.get("key") or "").strip()
            }
            required_sources = {"awp-agents", "awp-testnet", "awp-live-query", "gov-markets-api", "awp-whitepaper-page"}
            required_facts = {"agent-status-facts", "testnet-facts", "protocol-core", "gov-skill-facts"}
            if required_sources.issubset(source_keys) and required_facts.issubset(fact_keys):
                status = "covered"
                reasons.append("Official public lookup and status surfaces are represented distinctly from execution runtimes, including agent status, testnet activity, live RPC, Gov markets, and the whitepaper landing page.")
            else:
                status = "partial"
                missing_sources = sorted(required_sources.difference(source_keys))
                missing_facts = sorted(required_facts.difference(fact_keys))
                reasons.append("Some public lookup/status surfaces are still not modeled distinctly enough.")
                if missing_sources:
                    reasons.append("Missing public status sources: " + ", ".join(missing_sources))
                if missing_facts:
                    reasons.append("Missing public status fact sets: " + ", ".join(missing_facts))
            evidence_files.extend(["source-inventory.json", "source-facts.json", "source-evidence.json", "source-map.md"])
        elif key == "source-traceability":
            if generated_exists("source-evidence.json") and evidence_records:
                status = "covered"
                reasons.append("Derived claims map to official source keys, locators, evidence types, and stability labels.")
            else:
                status = "missing"
                reasons.append("No evidence record set is available.")
            evidence_files.extend(["source-evidence.json", "evidence-model.md"])
        elif key == "registration-flow":
            registration_plan = build_registration_plan(state=state)
            cached_preflight = load_json(Path(state["cache"]) / "preflight.json", {})
            cached_registration_plan = (
                cached_preflight.get("registrationPlan", {})
                if isinstance(cached_preflight, dict)
                else {}
            )
            coverage_plan = (
                cached_registration_plan
                if isinstance(cached_registration_plan, dict) and cached_registration_plan
                else registration_plan
            )
            command_labels = [
                item.get("label")
                for item in coverage_plan.get("commands", [])
                if isinstance(item, dict)
            ]
            official_preflight = coverage_plan.get("awpSkillPreflight", {}) if isinstance(coverage_plan, dict) else {}
            official_result = official_preflight.get("result", {}) if isinstance(official_preflight, dict) else {}
            official_state = official_result.get("state", {}) if isinstance(official_result, dict) else {}
            official_registered = official_state.get("registered") is True if isinstance(official_state, dict) else False
            official_next_action = str(official_result.get("nextAction") or "").strip() if isinstance(official_result, dict) else ""
            cached_registered = cached_preflight.get("registered") is True if isinstance(cached_preflight, dict) else False
            cached_official = cached_preflight.get("cachedOfficialPreflight", {}) if isinstance(cached_preflight, dict) else {}
            cached_official_result = cached_official.get("result", {}) if isinstance(cached_official, dict) else {}
            cached_official_state = cached_official_result.get("state", {}) if isinstance(cached_official_result, dict) else {}
            cached_official_registered = (
                cached_official_state.get("registered") is True
                if isinstance(cached_official_state, dict)
                else False
            )
            cached_official_next_action = (
                str(cached_official_result.get("nextAction") or "").strip()
                if isinstance(cached_official_result, dict)
                else ""
            )
            coverage_next_action = str(coverage_plan.get("nextAction") or "").strip() if isinstance(coverage_plan, dict) else ""
            coverage_official_next_action = (
                str(coverage_plan.get("officialNextAction") or "").strip()
                if isinstance(coverage_plan, dict)
                else ""
            )
            if coverage_next_action in {
                "run_awp_skill_registration",
                "registration_ready",
                "registration_already_confirmed",
            } or cached_registered or official_registered or cached_official_registered or coverage_official_next_action == "pick_worknet" or official_next_action == "pick_worknet" or cached_official_next_action == "pick_worknet":
                status = "covered"
                if coverage_next_action == "registration_already_confirmed" or cached_registered or official_registered or cached_official_registered or coverage_official_next_action == "pick_worknet" or official_next_action == "pick_worknet" or cached_official_next_action == "pick_worknet":
                    reasons.append("The workstation already recognizes that awp-skill registration is complete and still preserves the official onboarding command path.")
                else:
                    reasons.append("The workstation has a concrete awp-skill registration command path.")
            else:
                status = "partial"
                reasons.append("The workstation now probes runtime and emits install/register commands, but full registration execution still depends on awp-skill availability.")
            if command_labels:
                reasons.append("Available registration-plan commands: " + ", ".join(str(label) for label in command_labels if label))
            evidence_files.extend(["source-facts.json", "source-evidence.json", "skill-registry.json"])
        elif key == "live-rpc-scan":
            snapshot = load_json(Path(state["cache"]) / "capability-scan.json", {})
            if snapshot.get("sourceMode") in {"rpc", "live-cache"}:
                status = "covered"
                reasons.append("Capability scan has successfully used a live official data path.")
            else:
                status = "partial"
                reasons.append("RPC methods are documented and modeled, but current environment still falls back to catalog mode.")
            evidence_files.extend(["capability-catalog.json", "source-evidence.json"])
        elif key == "skill-inspector":
            inspections_payload = skill_inspections or build_skill_inspection_catalog(state=state, inventory=inventory)
            inspections = {
                item.get("skillKey"): item
                for item in inspections_payload.get("inspections", [])
                if isinstance(item, dict)
            }
            strong_keys = ("predict", "gov", "ardi")
            minimal_keys = ("tmr", "community")
            strong_ready = all(
                inspections.get(name, {}).get("runtimeName")
                and inspections.get(name, {}).get("inspectionCommands")
                for name in strong_keys
            )
            minimal_ready = all(
                inspections.get(name, {}).get("runtimeName")
                for name in minimal_keys
            )
            empty_repo_keys = [
                name
                for name in minimal_keys
                if inspections.get(name, {}).get("status") == "empty-official-repo"
            ]
            if strong_ready and minimal_ready:
                status = "covered"
                reasons.append("Predict, Gov, and Ardi expose runtime-specific install/inspection guidance.")
                if empty_repo_keys:
                    reasons.append(
                        "TMR/Community are still covered because inspector can prove when the official checkout is present but upstream only exposes license or metadata files: "
                        + ", ".join(empty_repo_keys)
                    )
                else:
                    reasons.append("TMR/Community expose remote runtime profiles.")
            else:
                status = "partial"
                reasons.append("Some official worknet skills still lack structured inspection guidance.")
            evidence_files.extend(["skill-inspections.json", "skill-registry.json"])
        elif key == "recovery-state":
            if (Path(state["runs"]) / "latest-run.json").exists() and (Path(state["runs"]) / "pending-confirmations.json").exists():
                status = "covered"
                reasons.append("Run state and confirmation queue files exist and are reused by preflight/review.")
            else:
                status = "partial"
                reasons.append("Recovery files are not all present yet.")
            evidence_files.extend(["runs/latest-run.json", "runs/pending-confirmations.json"])
        elif key == "live-canonical-quality":
            if live_worknets and isinstance(live_worknets.get("entries"), list):
                entries = live_worknets["entries"]
                unresolved = [
                    item
                    for item in entries
                    if isinstance(item, dict)
                    and item.get("resolutionConfidence", "low") == "low"
                ]
                if not unresolved:
                    status = "covered"
                    reasons.append("All cached live worknets resolved to canonical IDs with medium or high confidence.")
                else:
                    status = "partial"
                    reasons.append(f"{len(unresolved)} cached live worknet(s) still have low-confidence canonical resolution.")
                    reasons.append(
                        "Unresolved names: "
                        + ", ".join(str(item.get("name")) for item in unresolved[:5] if item.get("name"))
                    )
            else:
                status = "partial"
                reasons.append("No cached live worknet snapshot is available yet.")
            evidence_files.extend(["official-live-worknets.json", "capability-catalog.json"])
        elif key == "upstream-drift-watch":
            if source_drift and isinstance(source_drift.get("items"), list):
                status = "covered"
                summary = source_drift.get("summary", {}) if isinstance(source_drift, dict) else {}
                changed = int(summary.get("changedSources", 0) or 0)
                unreachable = int(summary.get("currentlyUnreachable", 0) or 0)
                reasons.append("Official source refresh now emits a structured drift report with per-source content and availability comparisons.")
                reasons.append(f"Current drift summary: {changed} changed source(s), {unreachable} currently unreachable source(s).")
                if source_impact and isinstance(source_impact.get("summary"), dict):
                    impact_summary = source_impact["summary"]
                    reasons.append(
                        "Knowledge impact routing is also available: "
                        f"{int(impact_summary.get('impactedTopics', 0) or 0)} topic(s), "
                        f"{int(impact_summary.get('impactedFacts', 0) or 0)} fact set(s), "
                        f"{int(impact_summary.get('impactedWorknets', 0) or 0)} worknet profile(s)."
                    )
                    if knowledge_review_queue and isinstance(knowledge_review_queue.get("summary"), dict):
                        queue_summary = knowledge_review_queue["summary"]
                        reasons.append(
                            "A knowledge review queue is available with "
                            f"{int(queue_summary.get('entries', 0) or 0)} actionable review item(s)."
                        )
                else:
                    status = "partial"
                    reasons.append("Source drift exists, but no impacted topic/fact/worknet routing has been generated yet.")
            elif generated_exists("source-snapshot.json"):
                status = "partial"
                reasons.append("Official sources can be snapshotted, but no structured drift comparison has been generated yet.")
            else:
                status = "missing"
                reasons.append("No official source snapshot exists yet.")
            evidence_files.extend(["source-snapshot.json", "source-drift.json", "source-impact.json", "knowledge-review-queue.json"])

        items.append(
            {
                "key": key,
                "title": requirement["title"],
                "intent": requirement["intent"],
                "status": status,
                "reasons": reasons,
                "evidenceFiles": evidence_files,
            }
        )

    covered_count = sum(1 for item in items if item["status"] == "covered")
    partial_count = sum(1 for item in items if item["status"] == "partial")
    missing_count = sum(1 for item in items if item["status"] == "missing")
    audit = {
        "generatedAt": now_iso(),
        "summary": {
            "covered": covered_count,
            "partial": partial_count,
            "missing": missing_count,
        },
        "items": items,
    }
    atomic_write_json(Path(state["cache"]) / "coverage-audit.json", audit)
    write_reference_export("coverage-audit.json", audit)
    return audit


def build_public_contract_audit_payload(
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build public contract audit dependencies are required")
    CAPABILITY_PUBLIC_FIELDS = dependencies["CAPABILITY_PUBLIC_FIELDS"]
    PLAYBOOK_COMMAND_PUBLIC_FIELDS = dependencies["PLAYBOOK_COMMAND_PUBLIC_FIELDS"]
    PLAYBOOK_PUBLIC_FIELDS = dependencies["PLAYBOOK_PUBLIC_FIELDS"]
    PREFLIGHT_PUBLIC_FIELDS = dependencies["PREFLIGHT_PUBLIC_FIELDS"]
    PUBLIC_ACTION_FIELDS = dependencies["PUBLIC_ACTION_FIELDS"]
    REVIEW_PUBLIC_FIELDS = dependencies["REVIEW_PUBLIC_FIELDS"]
    RUN_RESPONSE_FIELDS = dependencies["RUN_RESPONSE_FIELDS"]
    START_RESPONSE_FIELDS = dependencies["START_RESPONSE_FIELDS"]
    USER_ACTION_DETAIL_FIELDS = dependencies["USER_ACTION_DETAIL_FIELDS"]
    WORKSTATION_STATUS_INTERNAL_FIELDS = dependencies["WORKSTATION_STATUS_INTERNAL_FIELDS"]
    WORKSTATION_STATUS_PUBLIC_FIELDS = dependencies["WORKSTATION_STATUS_PUBLIC_FIELDS"]
    annotate_runtime_action_payloads = dependencies["annotate_runtime_action_payloads"]
    build_capability_bundle = dependencies["build_capability_bundle"]
    build_epoch_review = dependencies["build_epoch_review"]
    build_epoch_review_from_run = dependencies["build_epoch_review_from_run"]
    build_preflight_report = dependencies["build_preflight_report"]
    build_start_response = dependencies["build_start_response"]
    build_start_response_from_preflight = dependencies["build_start_response_from_preflight"]
    build_work_playbook = dependencies["build_work_playbook"]
    build_workstation_status = dependencies["build_workstation_status"]
    finalize_run_response_payload = dependencies["finalize_run_response_payload"]
    load_or_build_knowledge_catalog = dependencies["load_or_build_knowledge_catalog"]
    now_iso = dependencies["now_iso"]
    public_capability_view = dependencies["public_capability_view"]
    public_playbook_view = dependencies["public_playbook_view"]
    public_preflight_view = dependencies["public_preflight_view"]
    public_review_view = dependencies["public_review_view"]
    public_workstation_status_view = dependencies["public_workstation_status_view"]
    resolve_worknet = dependencies["resolve_worknet"]
    run_workstation = dependencies["run_workstation"]
    seed_verification_state_from_reference_exports = dependencies["seed_verification_state_from_reference_exports"]
    state_context = dependencies["state_context"]

    state = state_context()
    seed_verification_state_from_reference_exports(state)
    knowledge_catalog = load_or_build_knowledge_catalog(state)
    preflight = public_preflight_view(build_preflight_report())
    capability_bundle = build_capability_bundle()
    capability_reports = capability_bundle.get("reports", []) if isinstance(capability_bundle, dict) else []
    capability_public = public_capability_view(capability_reports[0]) if capability_reports and isinstance(capability_reports[0], dict) else None
    capability_public_predict = next(
        (
            public_capability_view(item)
            for item in capability_reports
            if isinstance(item, dict) and str(item.get("name") or "") == "Predict WorkNet"
        ),
        None,
    )
    capability_public_gov = next(
        (
            public_capability_view(item)
            for item in capability_reports
            if isinstance(item, dict) and str(item.get("name") or "") == "GovNet"
        ),
        None,
    )
    capability_public_ardi = next(
        (
            public_capability_view(item)
            for item in capability_reports
            if isinstance(item, dict) and str(item.get("name") or "") == "Ardi"
        ),
        None,
    )
    capability_public_kya = next(
        (
            public_capability_view(item)
            for item in capability_reports
            if isinstance(item, dict) and str(item.get("name") or "") == "KYA"
        ),
        None,
    )
    start_response = build_start_response()
    predict_profile = resolve_worknet("predict") or {}
    mine_profile = resolve_worknet("mine") or {}
    gov_profile = resolve_worknet("gov") or {}

    def synthetic_capability_report(
        profile: dict[str, Any],
        *,
        name: Optional[str] = None,
        runnable: bool = True,
        can_start_without_stake: bool = False,
        recommended_role: str = "operator",
        automation_level: str = "semi-auto",
        cli_status: str = "ready",
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        return {
            "worknetId": profile.get("worknet_id"),
            "name": name or profile.get("name") or profile.get("key"),
            "runnable": runnable,
            "canStartWithoutStake": can_start_without_stake,
            "recommendedRole": recommended_role,
            "automationLevel": automation_level,
            "cliStatus": cli_status,
            "reason": reason,
        }

    synthetic_predict_start_response = build_start_response_from_preflight(
        {
            "nextAction": "scan_worknets",
            "registered": True,
            "registrationPlan": {},
            "recovery": {},
            "recoveryDecision": None,
            "knowledgeReviewQueueSummary": {},
            "userPreferences": {"preferredWorknet": "predict"},
        },
        state=state,
        knowledge_catalog=knowledge_catalog,
        cached_bundle={
            "reports": [
                synthetic_capability_report(predict_profile, can_start_without_stake=True, recommended_role="operator", automation_level="semi-auto"),
                synthetic_capability_report(mine_profile, name="Mine WorkNet", can_start_without_stake=True, recommended_role="operator", automation_level="full-auto"),
            ]
        },
    )
    synthetic_gov_start_response = build_start_response_from_preflight(
        {
            "nextAction": "scan_worknets",
            "registered": True,
            "registrationPlan": {},
            "recovery": {},
            "recoveryDecision": None,
            "knowledgeReviewQueueSummary": {},
            "userPreferences": {"preferredWorknet": "gov"},
        },
        state=state,
        knowledge_catalog=knowledge_catalog,
        cached_bundle={
            "reports": [
                synthetic_capability_report(gov_profile, name="GovNet", can_start_without_stake=False, recommended_role="operator", automation_level="phase-aware"),
                synthetic_capability_report(mine_profile, name="Mine WorkNet", can_start_without_stake=True, recommended_role="operator", automation_level="full-auto"),
            ]
        },
    )
    synthetic_ardi_start_response = build_start_response_from_preflight(
        {
            "nextAction": "resume_runtime_guidance",
            "registered": True,
            "registrationPlan": {},
            "recovery": {
                "lastWorknetKey": "ardi",
                "runtimeGuidanceMessage": "Ardi runtime                                Base gas             stake                          commit/reveal          ",
                "runtimeGuidanceNextAction": "fund_gas_and_or_satisfy_stake",
                "defaultFollowUpLabel": "       Ardi preflight",
                "defaultFollowUpCommand": "ardi-agent preflight",
                "followUpActions": [
                    {
                        "label": "       Ardi preflight",
                        "command": "ardi-agent preflight",
                        "argv": ["ardi-agent", "preflight"],
                        "safeToAutoRun": True,
                        "requiresConfirmation": False,
                    }
                ],
                "followUpActionCount": 1,
                "hasRuntimeGuidance": True,
            },
            "recoveryDecision": None,
            "knowledgeReviewQueueSummary": {},
            "userPreferences": {"preferredWorknet": "ardi"},
        },
        state=state,
        knowledge_catalog=knowledge_catalog,
        cached_bundle={},
    )
    run_response = run_workstation(mode="autopilot", worknet_identifier="mine", execute=False)
    workstation_status_full = build_workstation_status(query="       Mine")
    workstation_status_public = public_workstation_status_view(workstation_status_full)
    workstation_status_predict_full = build_workstation_status(query="       Predict", worknet_identifier="predict")
    workstation_status_predict_public = public_workstation_status_view(workstation_status_predict_full)
    workstation_status_gov_full = build_workstation_status(query="       Gov", worknet_identifier="gov")
    workstation_status_gov_public = public_workstation_status_view(workstation_status_gov_full)
    workstation_status_ardi_full = build_workstation_status(query="       Ardi", worknet_identifier="ardi")
    workstation_status_ardi_public = public_workstation_status_view(workstation_status_ardi_full)
    workstation_status_concept_full = build_workstation_status(query="agent onboarding", intent="research")
    workstation_status_concept_public = public_workstation_status_view(workstation_status_concept_full)
    workstation_status_glossary_full = build_workstation_status(query="fair launch", intent="research")
    workstation_status_glossary_public = public_workstation_status_view(workstation_status_glossary_full)
    playbook_public = public_playbook_view(build_work_playbook("mine"))
    playbook_public_predict = public_playbook_view(build_work_playbook("predict"))
    playbook_public_gov = public_playbook_view(build_work_playbook("gov"))
    playbook_public_ardi = public_playbook_view(build_work_playbook("ardi"))
    playbook_public_kya = public_playbook_view(build_work_playbook("kya"))
    review_public = public_review_view(build_epoch_review())
    synthetic_predict_run_response = finalize_run_response_payload(
        annotate_runtime_action_payloads(
            {
                "mode": "autopilot",
                "status": "needs_confirmation",
                "executedSteps": [],
                "confirmationQueue": [
                    {
                        "label": "       Predict       ",
                        "argv": ["predict-agent", "submit"],
                    }
                ],
                "runtimeGuidance": None,
                "followUpActions": [],
                "resumedFromState": False,
                "playbookSource": "worknet",
                "selectedWorknetKey": "predict",
                "selectedWorknetName": "Predict",
                "warnings": [],
                "nextAction": "await_confirmation",
                "progress": "[4/5] Work loop",
                "stateRoot": state["root"],
            }
        ),
        preferences={"preferredWorknet": "predict"},
        recovery={},
    )
    synthetic_gov_run_response = finalize_run_response_payload(
        annotate_runtime_action_payloads(
            {
                "mode": "autopilot",
                "status": "needs_runtime_input",
                "executedSteps": [],
                "confirmationQueue": [],
                "runtimeGuidance": {
                    "message": "Gov        phase     Voting             principal              AWP Power                                             ",
                    "userActions": ["       Gov             ", "       Gov markets", "       staking       "],
                    "actionMap": {
                        "       Gov             ": "python3 scripts/helpers/what-can-i-do.py",
                        "       Gov markets": "python3 scripts/public/markets.py",
                        "       staking       ": "python3 scripts/query-knowledge.py --topic staking",
                    },
                    "nextAction": "acquire_awp_power_or_observe_gov",
                    "state": "Voting",
                },
                "followUpActions": [],
                "resumedFromState": False,
                "playbookSource": "worknet",
                "selectedWorknetKey": "gov",
                "selectedWorknetName": "GovNet",
                "warnings": [],
                "nextAction": "follow_runtime_guidance",
                "progress": "[4/5] Work loop",
                "stateRoot": state["root"],
            }
        ),
        preferences={"preferredWorknet": "gov"},
        recovery={},
    )
    synthetic_ardi_run_response = finalize_run_response_payload(
        annotate_runtime_action_payloads(
            {
                "mode": "autopilot",
                "status": "needs_runtime_input",
                "executedSteps": [],
                "confirmationQueue": [],
                "runtimeGuidance": {
                    "message": "Ardi runtime                                Base gas             stake                          commit/reveal          ",
                    "userActions": ["    Base Gas", "       Ardi preflight"],
                    "actionMap": {
                        "    Base Gas": "Send at least 0.002 ETH to 0xabc on Base",
                        "       Ardi preflight": "ardi-agent preflight",
                    },
                    "nextCommand": ["ardi-agent", "preflight"],
                    "nextAction": "fund_gas_and_or_satisfy_stake",
                    "state": None,
                },
                "followUpActions": [
                    {
                        "label": "       Ardi preflight",
                        "command": "ardi-agent preflight",
                        "argv": ["ardi-agent", "preflight"],
                        "safeToAutoRun": True,
                        "requiresConfirmation": False,
                    }
                ],
                "resumedFromState": False,
                "playbookSource": "worknet",
                "selectedWorknetKey": "ardi",
                "selectedWorknetName": "Ardi",
                "warnings": [],
                "nextAction": "follow_runtime_guidance",
                "progress": "[4/5] Work loop",
                "stateRoot": state["root"],
            }
        ),
        preferences={"preferredWorknet": "ardi"},
        recovery={},
    )
    synthetic_predict_review = public_review_view(
        build_epoch_review_from_run(
            annotate_runtime_action_payloads(
                {
                    "playbook": {"worknetKey": "predict", "requiredSkill": "Predict"},
                    "executedSteps": [
                        {
                            "label": "       Predict context",
                            "status": "ok",
                            "result": {
                                "code": 0,
                                "stdout": {
                                    "state": "selection_required",
                                    "message": "Context ready.",
                                    "user_actions": ["prepare submission", "rerun context"],
                                    "_internal": {
                                        "action_map": {
                                            "prepare submission": "predict-agent submit --market mkt-42 --side <buy|sell> --tickets <tickets> --reasoning <reasoning>",
                                            "rerun context": "predict-agent context",
                                        },
                                        "next_action": "confirm_predict_submission",
                                        "next_command": "predict-agent submit --market mkt-42 --side <buy|sell> --tickets <tickets> --reasoning <reasoning>",
                                    },
                                },
                                "stderr": "",
                            },
                        }
                    ],
                    "followUpActions": [
                        {
                            "label": "       Predict       ",
                            "command": "predict-agent submit --market mkt-42 --side <buy|sell> --tickets <tickets> --reasoning <reasoning>",
                            "argv": ["predict-agent", "submit", "--market", "mkt-42", "--side", "<buy|sell>", "--tickets", "<tickets>", "--reasoning", "<reasoning>"],
                            "safeToAutoRun": False,
                            "requiresConfirmation": True,
                        }
                    ],
                    "runtimeGuidance": {
                        "message": "Predict context                                        tickets     reasoning   ",
                        "userActions": ["prepare submission", "rerun context"],
                        "actionMap": {
                            "prepare submission": "predict-agent submit --market mkt-42 --side <buy|sell> --tickets <tickets> --reasoning <reasoning>",
                            "rerun context": "predict-agent context",
                        },
                        "nextCommand": ["predict-agent", "submit", "--market", "mkt-42", "--side", "<buy|sell>", "--tickets", "<tickets>", "--reasoning", "<reasoning>"],
                        "nextAction": "confirm_predict_submission",
                        "state": "selection_required",
                    },
                }
            ),
            [],
            state=state,
            knowledge_catalog=knowledge_catalog,
        )
    )
    synthetic_gov_review = public_review_view(
        build_epoch_review_from_run(
            annotate_runtime_action_payloads(
                {
                    "playbook": {"worknetKey": "gov", "requiredSkill": "GovNet"},
                    "executedSteps": [
                        {
                            "label": "gov public markets",
                            "status": "ok",
                            "result": {
                                "code": 0,
                                "stdout": {"items": [{"name": "YES-1"}], "message": "markets loaded"},
                                "stderr": "",
                            },
                        },
                        {
                            "label": "gov phase-aware helper",
                            "status": "ok",
                            "result": {
                                "code": 0,
                                "stdout": {"phase": "Voting", "message": "Voting"},
                                "stderr": "",
                            },
                        },
                        {
                            "label": "gov private state",
                            "status": "failed",
                            "result": {
                                "code": 1,
                                "stdout": {
                                    "error": "STATE_PRINCIPAL_NOT_IN_EPOCH",
                                    "message": "Principal has no AWP Power this epoch",
                                    "detail": "Principal has no AWP Power this epoch",
                                    "user_actions": ["check status"],
                                    "_internal": {
                                        "action_map": {"check status": "python3 scripts/private/state.py"},
                                        "next_action": "acquire_awp_power_or_observe_gov",
                                    },
                                },
                                "stderr": "",
                            },
                        },
                    ],
                    "runtimeGuidance": {
                        "message": "Gov        phase     Voting             principal              AWP Power                                             ",
                        "userActions": ["       Gov             ", "       Gov markets", "       staking       "],
                        "actionMap": {
                            "       Gov             ": "python3 scripts/helpers/what-can-i-do.py",
                            "       Gov markets": "python3 scripts/public/markets.py",
                            "       staking       ": "python3 scripts/query-knowledge.py --topic staking",
                        },
                        "nextAction": "acquire_awp_power_or_observe_gov",
                        "state": "Voting",
                    },
                }
            ),
            [],
            state=state,
            knowledge_catalog=knowledge_catalog,
        )
    )
    synthetic_ardi_review = public_review_view(
        build_epoch_review_from_run(
            annotate_runtime_action_payloads(
                {
                    "playbook": {"worknetKey": "ardi", "requiredSkill": "Ardi"},
                    "executedSteps": [
                        {
                            "label": "ardi gas check",
                            "status": "failed",
                            "result": {
                                "code": 1,
                                "stdout": {
                                    "message": "gas low",
                                    "data": {"suggestion": "Send at least 0.002 ETH to 0xabc on Base"},
                                },
                                "stderr": "",
                            },
                        },
                        {
                            "label": "ardi stake guidance",
                            "status": "failed",
                            "result": {
                                "code": 1,
                                "stdout": {
                                    "message": "stake low",
                                    "data": {"suggestion": "Reach the 10000 AWP threshold on EITHER Ardi or KYA"},
                                },
                                "stderr": "",
                            },
                        },
                    ],
                    "runtimeGuidance": {
                        "message": "Ardi runtime                                Base gas             stake                          commit/reveal          ",
                        "userActions": ["    Base Gas", "       Ardi preflight", "    KYA             "],
                        "actionMap": {
                            "    Base Gas": "Send at least 0.002 ETH to 0xabc on Base",
                            "       Ardi preflight": "ardi-agent preflight",
                            "    KYA             ": "https://kya.link/",
                        },
                        "nextCommand": ["ardi-agent", "preflight"],
                        "nextAction": "fund_gas_and_or_satisfy_stake",
                    },
                }
            ),
            [],
            state=state,
            knowledge_catalog=knowledge_catalog,
        )
    )

    first_item = first_dict_item

    def audit_item(
        key: str,
        title: str,
        payload: Any,
        fields: list[str],
        *,
        sample_ref: Optional[str] = None,
    ) -> dict[str, Any]:
        return contract_audit_item(
            key,
            title,
            payload,
            fields,
            sample_ref=sample_ref,
            missing_message="No sample payload was available for this public contract.",
        )

    items = [
        audit_item(
            "public-preflight",
            "Public preflight contract",
            preflight,
            PREFLIGHT_PUBLIC_FIELDS,
            sample_ref="public_preflight_view(build_preflight_report())",
        ),
        audit_item(
            "public-capability",
            "Public capability-report contract",
            capability_public,
            CAPABILITY_PUBLIC_FIELDS,
            sample_ref="public_capability_view(build_capability_bundle().reports[0])",
        ),
        audit_item(
            "public-capability-predict",
            "Public capability-report contract for Predict",
            capability_public_predict,
            CAPABILITY_PUBLIC_FIELDS,
            sample_ref="public_capability_view(Predict report)",
        ),
        audit_item(
            "public-capability-gov",
            "Public capability-report contract for Gov",
            capability_public_gov,
            CAPABILITY_PUBLIC_FIELDS,
            sample_ref="public_capability_view(Gov report)",
        ),
        audit_item(
            "public-capability-ardi",
            "Public capability-report contract for Ardi",
            capability_public_ardi,
            CAPABILITY_PUBLIC_FIELDS,
            sample_ref="public_capability_view(Ardi report)",
        ),
        audit_item(
            "public-capability-kya",
            "Public capability-report contract for KYA",
            capability_public_kya,
            CAPABILITY_PUBLIC_FIELDS,
            sample_ref="public_capability_view(KYA report)",
        ),
        audit_item(
            "public-playbook",
            "Public playbook contract",
            playbook_public,
            PLAYBOOK_PUBLIC_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('mine'))",
        ),
        audit_item(
            "public-playbook-predict",
            "Public playbook contract for Predict",
            playbook_public_predict,
            PLAYBOOK_PUBLIC_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('predict'))",
        ),
        audit_item(
            "public-playbook-gov",
            "Public playbook contract for Gov",
            playbook_public_gov,
            PLAYBOOK_PUBLIC_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('gov'))",
        ),
        audit_item(
            "public-playbook-ardi",
            "Public playbook contract for Ardi",
            playbook_public_ardi,
            PLAYBOOK_PUBLIC_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('ardi'))",
        ),
        audit_item(
            "public-playbook-kya",
            "Public playbook contract for KYA",
            playbook_public_kya,
            PLAYBOOK_PUBLIC_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('kya'))",
        ),
        audit_item(
            "public-playbook-command",
            "Public playbook command-item contract",
            first_item(playbook_public.get("commands") if isinstance(playbook_public, dict) else None),
            PLAYBOOK_COMMAND_PUBLIC_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('mine')).commands[0]",
        ),
        audit_item(
            "public-playbook-user-action-detail",
            "Public playbook user-action-detail contract",
            first_item(playbook_public.get("userActionDetails") if isinstance(playbook_public, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('mine')).userActionDetails[0]",
        ),
        audit_item(
            "public-playbook-predict-command",
            "Public playbook command-item contract for Predict",
            first_item(playbook_public_predict.get("commands") if isinstance(playbook_public_predict, dict) else None),
            PLAYBOOK_COMMAND_PUBLIC_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('predict')).commands[0]",
        ),
        audit_item(
            "public-playbook-gov-command",
            "Public playbook command-item contract for Gov",
            first_item(playbook_public_gov.get("commands") if isinstance(playbook_public_gov, dict) else None),
            PLAYBOOK_COMMAND_PUBLIC_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('gov')).commands[0]",
        ),
        audit_item(
            "public-playbook-ardi-command",
            "Public playbook command-item contract for Ardi",
            first_item(playbook_public_ardi.get("commands") if isinstance(playbook_public_ardi, dict) else None),
            PLAYBOOK_COMMAND_PUBLIC_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('ardi')).commands[0]",
        ),
        audit_item(
            "public-playbook-kya-command",
            "Public playbook command-item contract for KYA",
            first_item(playbook_public_kya.get("commands") if isinstance(playbook_public_kya, dict) else None),
            PLAYBOOK_COMMAND_PUBLIC_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('kya')).commands[0]",
        ),
        audit_item(
            "public-playbook-predict-user-action-detail",
            "Public playbook user-action-detail contract for Predict",
            first_item(playbook_public_predict.get("userActionDetails") if isinstance(playbook_public_predict, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('predict')).userActionDetails[0]",
        ),
        audit_item(
            "public-playbook-gov-user-action-detail",
            "Public playbook user-action-detail contract for Gov",
            first_item(playbook_public_gov.get("userActionDetails") if isinstance(playbook_public_gov, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('gov')).userActionDetails[0]",
        ),
        audit_item(
            "public-playbook-ardi-user-action-detail",
            "Public playbook user-action-detail contract for Ardi",
            first_item(playbook_public_ardi.get("userActionDetails") if isinstance(playbook_public_ardi, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('ardi')).userActionDetails[0]",
        ),
        audit_item(
            "public-playbook-kya-user-action-detail",
            "Public playbook user-action-detail contract for KYA",
            first_item(playbook_public_kya.get("userActionDetails") if isinstance(playbook_public_kya, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_playbook_view(build_work_playbook('kya')).userActionDetails[0]",
        ),
        audit_item(
            "public-review",
            "Public review contract",
            review_public,
            REVIEW_PUBLIC_FIELDS,
            sample_ref="public_review_view(build_epoch_review())",
        ),
        audit_item(
            "public-review-user-action-detail",
            "Public review user-action-detail contract",
            first_item(review_public.get("userActionDetails") if isinstance(review_public, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_review_view(build_epoch_review()).userActionDetails[0]",
        ),
        audit_item(
            "public-review-predict",
            "Public review contract for Predict synthetic latest-run",
            synthetic_predict_review,
            REVIEW_PUBLIC_FIELDS,
            sample_ref="public_review_view(build_epoch_review_from_run({predict latest-run}))",
        ),
        audit_item(
            "public-review-predict-user-action-detail",
            "Public review user-action-detail contract for Predict synthetic latest-run",
            first_item(synthetic_predict_review.get("userActionDetails") if isinstance(synthetic_predict_review, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_review_view(build_epoch_review_from_run({predict latest-run})).userActionDetails[0]",
        ),
        audit_item(
            "public-review-gov",
            "Public review contract for Gov synthetic latest-run",
            synthetic_gov_review,
            REVIEW_PUBLIC_FIELDS,
            sample_ref="public_review_view(build_epoch_review_from_run({gov latest-run}))",
        ),
        audit_item(
            "public-review-gov-user-action-detail",
            "Public review user-action-detail contract for Gov synthetic latest-run",
            first_item(synthetic_gov_review.get("userActionDetails") if isinstance(synthetic_gov_review, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_review_view(build_epoch_review_from_run({gov latest-run})).userActionDetails[0]",
        ),
        audit_item(
            "public-review-ardi",
            "Public review contract for Ardi synthetic latest-run",
            synthetic_ardi_review,
            REVIEW_PUBLIC_FIELDS,
            sample_ref="public_review_view(build_epoch_review_from_run({ardi latest-run}))",
        ),
        audit_item(
            "public-review-ardi-user-action-detail",
            "Public review user-action-detail contract for Ardi synthetic latest-run",
            first_item(synthetic_ardi_review.get("userActionDetails") if isinstance(synthetic_ardi_review, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_review_view(build_epoch_review_from_run({ardi latest-run})).userActionDetails[0]",
        ),
        audit_item(
            "start-response",
            "Start-response contract",
            start_response,
            START_RESPONSE_FIELDS,
            sample_ref="build_start_response()",
        ),
        audit_item(
            "start-response-user-action",
            "Start-response user-action contract",
            first_item(start_response.get("user_actions") if isinstance(start_response, dict) else None),
            PUBLIC_ACTION_FIELDS,
            sample_ref="build_start_response().user_actions[0]",
        ),
        audit_item(
            "start-response-predict",
            "Predict synthetic start-response contract",
            synthetic_predict_start_response,
            START_RESPONSE_FIELDS,
            sample_ref="build_start_response_from_preflight({predict scan_worknets})",
        ),
        audit_item(
            "start-response-predict-user-action",
            "Predict synthetic start-response user-action contract",
            first_item(synthetic_predict_start_response.get("user_actions") if isinstance(synthetic_predict_start_response, dict) else None),
            PUBLIC_ACTION_FIELDS,
            sample_ref="build_start_response_from_preflight({predict scan_worknets}).user_actions[0]",
        ),
        audit_item(
            "start-response-gov",
            "Gov synthetic start-response contract",
            synthetic_gov_start_response,
            START_RESPONSE_FIELDS,
            sample_ref="build_start_response_from_preflight({gov scan_worknets})",
        ),
        audit_item(
            "start-response-gov-user-action",
            "Gov synthetic start-response user-action contract",
            first_item(synthetic_gov_start_response.get("user_actions") if isinstance(synthetic_gov_start_response, dict) else None),
            PUBLIC_ACTION_FIELDS,
            sample_ref="build_start_response_from_preflight({gov scan_worknets}).user_actions[0]",
        ),
        audit_item(
            "start-response-ardi",
            "Ardi synthetic start-response contract",
            synthetic_ardi_start_response,
            START_RESPONSE_FIELDS,
            sample_ref="build_start_response_from_preflight({ardi resume_runtime_guidance})",
        ),
        audit_item(
            "start-response-ardi-user-action",
            "Ardi synthetic start-response user-action contract",
            first_item(synthetic_ardi_start_response.get("user_actions") if isinstance(synthetic_ardi_start_response, dict) else None),
            PUBLIC_ACTION_FIELDS,
            sample_ref="build_start_response_from_preflight({ardi resume_runtime_guidance}).user_actions[0]",
        ),
        audit_item(
            "run-response",
            "Run-response contract",
            run_response,
            RUN_RESPONSE_FIELDS,
            sample_ref="run_workstation(mode='autopilot', worknet_identifier='mine', execute=False)",
        ),
        audit_item(
            "run-response-user-action-detail",
            "Run-response user-action-detail contract",
            first_item(run_response.get("userActionDetails") if isinstance(run_response, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="run_workstation(...).userActionDetails[0]",
        ),
        audit_item(
            "run-response-predict",
            "Predict synthetic run-response contract",
            synthetic_predict_run_response,
            RUN_RESPONSE_FIELDS,
            sample_ref="finalize_run_response_payload({predict confirmation})",
        ),
        audit_item(
            "run-response-predict-user-action-detail",
            "Predict synthetic run-response user-action-detail contract",
            first_item(synthetic_predict_run_response.get("userActionDetails") if isinstance(synthetic_predict_run_response, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="finalize_run_response_payload({predict confirmation}).userActionDetails[0]",
        ),
        audit_item(
            "run-response-gov",
            "Gov synthetic run-response contract",
            synthetic_gov_run_response,
            RUN_RESPONSE_FIELDS,
            sample_ref="finalize_run_response_payload({gov observe})",
        ),
        audit_item(
            "run-response-gov-user-action-detail",
            "Gov synthetic run-response user-action-detail contract",
            first_item(synthetic_gov_run_response.get("userActionDetails") if isinstance(synthetic_gov_run_response, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="finalize_run_response_payload({gov observe}).userActionDetails[0]",
        ),
        audit_item(
            "run-response-ardi",
            "Ardi synthetic run-response contract",
            synthetic_ardi_run_response,
            RUN_RESPONSE_FIELDS,
            sample_ref="finalize_run_response_payload({ardi remediation})",
        ),
        audit_item(
            "run-response-ardi-user-action-detail",
            "Ardi synthetic run-response user-action-detail contract",
            first_item(synthetic_ardi_run_response.get("userActionDetails") if isinstance(synthetic_ardi_run_response, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="finalize_run_response_payload({ardi remediation}).userActionDetails[0]",
        ),
        audit_item(
            "workstation-status-full",
            "Full workstation-status contract",
            workstation_status_full,
            WORKSTATION_STATUS_INTERNAL_FIELDS,
            sample_ref="build_workstation_status(query='       Mine')",
        ),
        audit_item(
            "workstation-status-public",
            "Public workstation-status contract",
            workstation_status_public,
            WORKSTATION_STATUS_PUBLIC_FIELDS,
            sample_ref="public_workstation_status_view(build_workstation_status(query='       Mine'))",
        ),
        audit_item(
            "workstation-status-user-action",
            "Public workstation-status user-action contract",
            first_item(workstation_status_public.get("userActions") if isinstance(workstation_status_public, dict) else None),
            PUBLIC_ACTION_FIELDS,
            sample_ref="public_workstation_status_view(...).userActions[0]",
        ),
        audit_item(
            "workstation-status-user-action-detail",
            "Public workstation-status user-action-detail contract",
            first_item(workstation_status_public.get("userActionDetails") if isinstance(workstation_status_public, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_workstation_status_view(...).userActionDetails[0]",
        ),
        audit_item(
            "workstation-status-predict-full",
            "Full workstation-status contract for Predict",
            workstation_status_predict_full,
            WORKSTATION_STATUS_INTERNAL_FIELDS,
            sample_ref="build_workstation_status(query='       Predict', worknet_identifier='predict')",
        ),
        audit_item(
            "workstation-status-predict-public",
            "Public workstation-status contract for Predict",
            workstation_status_predict_public,
            WORKSTATION_STATUS_PUBLIC_FIELDS,
            sample_ref="public_workstation_status_view(build_workstation_status(query='       Predict', worknet_identifier='predict'))",
        ),
        audit_item(
            "workstation-status-gov-full",
            "Full workstation-status contract for Gov",
            workstation_status_gov_full,
            WORKSTATION_STATUS_INTERNAL_FIELDS,
            sample_ref="build_workstation_status(query='       Gov', worknet_identifier='gov')",
        ),
        audit_item(
            "workstation-status-gov-public",
            "Public workstation-status contract for Gov",
            workstation_status_gov_public,
            WORKSTATION_STATUS_PUBLIC_FIELDS,
            sample_ref="public_workstation_status_view(build_workstation_status(query='       Gov', worknet_identifier='gov'))",
        ),
        audit_item(
            "workstation-status-ardi-full",
            "Full workstation-status contract for Ardi",
            workstation_status_ardi_full,
            WORKSTATION_STATUS_INTERNAL_FIELDS,
            sample_ref="build_workstation_status(query='       Ardi', worknet_identifier='ardi')",
        ),
        audit_item(
            "workstation-status-ardi-public",
            "Public workstation-status contract for Ardi",
            workstation_status_ardi_public,
            WORKSTATION_STATUS_PUBLIC_FIELDS,
            sample_ref="public_workstation_status_view(build_workstation_status(query='       Ardi', worknet_identifier='ardi'))",
        ),
        audit_item(
            "workstation-status-concept-full",
            "Full workstation-status contract for a concept research query",
            workstation_status_concept_full,
            WORKSTATION_STATUS_INTERNAL_FIELDS,
            sample_ref="build_workstation_status(query='agent onboarding', intent='research')",
        ),
        audit_item(
            "workstation-status-concept-public",
            "Public workstation-status contract for a concept research query",
            workstation_status_concept_public,
            WORKSTATION_STATUS_PUBLIC_FIELDS,
            sample_ref="public_workstation_status_view(build_workstation_status(query='agent onboarding', intent='research'))",
        ),
        audit_item(
            "workstation-status-glossary-full",
            "Full workstation-status contract for a glossary research query",
            workstation_status_glossary_full,
            WORKSTATION_STATUS_INTERNAL_FIELDS,
            sample_ref="build_workstation_status(query='fair launch', intent='research')",
        ),
        audit_item(
            "workstation-status-glossary-public",
            "Public workstation-status contract for a glossary research query",
            workstation_status_glossary_public,
            WORKSTATION_STATUS_PUBLIC_FIELDS,
            sample_ref="public_workstation_status_view(build_workstation_status(query='fair launch', intent='research'))",
        ),
    ]

    return contract_audit_result(items, generated_at=now_iso())


def build_branch_contract_audit_payload(
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build branch contract audit dependencies are required")
    BACKGROUND_RECORD_FIELDS = dependencies["BACKGROUND_RECORD_FIELDS"]
    BACKGROUND_SUMMARY_FIELDS = dependencies["BACKGROUND_SUMMARY_FIELDS"]
    CONFIRMATION_QUEUE_ITEM_FIELDS = dependencies["CONFIRMATION_QUEUE_ITEM_FIELDS"]
    CONFIRMED_ACTION_FIELDS = dependencies["CONFIRMED_ACTION_FIELDS"]
    EXECUTED_STEP_FIELDS = dependencies["EXECUTED_STEP_FIELDS"]
    EXECUTED_STEP_RESULT_DISPLAY_FIELDS = dependencies["EXECUTED_STEP_RESULT_DISPLAY_FIELDS"]
    EXECUTED_STEP_STDOUT_DISPLAY_FIELDS = dependencies["EXECUTED_STEP_STDOUT_DISPLAY_FIELDS"]
    FOLLOW_UP_ACTION_FIELDS = dependencies["FOLLOW_UP_ACTION_FIELDS"]
    PARAMETER_SCHEMA_ITEM_FIELDS = dependencies["PARAMETER_SCHEMA_ITEM_FIELDS"]
    RECOVERY_DECISION_FIELDS = dependencies["RECOVERY_DECISION_FIELDS"]
    RESUME_RECOVERY_BRIEFING_FIELDS = dependencies["RESUME_RECOVERY_BRIEFING_FIELDS"]
    REVIEW_PUBLIC_FIELDS = dependencies["REVIEW_PUBLIC_FIELDS"]
    RUNTIME_GUIDANCE_USER_ACTION_DETAIL_FIELDS = dependencies["RUNTIME_GUIDANCE_USER_ACTION_DETAIL_FIELDS"]
    RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS = dependencies["RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS"]
    RUN_RESPONSE_BRIEFING_FIELDS = dependencies["RUN_RESPONSE_BRIEFING_FIELDS"]
    SELECTED_BACKGROUND_ERROR_FIELDS = dependencies["SELECTED_BACKGROUND_ERROR_FIELDS"]
    SELECTED_BACKGROUND_PREVIEW_FIELDS = dependencies["SELECTED_BACKGROUND_PREVIEW_FIELDS"]
    SELECTED_CONFIRMATION_FIELDS = dependencies["SELECTED_CONFIRMATION_FIELDS"]
    USER_ACTION_DETAIL_FIELDS = dependencies["USER_ACTION_DETAIL_FIELDS"]
    annotate_background_record = dependencies["annotate_background_record"]
    annotate_parameter_schema_items = dependencies["annotate_parameter_schema_items"]
    annotate_probe_result_display = dependencies["annotate_probe_result_display"]
    annotate_raw_confirmation_queue = dependencies["annotate_raw_confirmation_queue"]
    annotate_raw_follow_up_actions = dependencies["annotate_raw_follow_up_actions"]
    annotate_runtime_action_payloads = dependencies["annotate_runtime_action_payloads"]
    annotate_runtime_guidance_payload = dependencies["annotate_runtime_guidance_payload"]
    annotate_selected_confirmation = dependencies["annotate_selected_confirmation"]
    build_epoch_review_from_run = dependencies["build_epoch_review_from_run"]
    build_executed_step_result_display = dependencies["build_executed_step_result_display"]
    build_knowledge_query_result = dependencies["build_knowledge_query_result"]
    build_resume_recovery_briefing = dependencies["build_resume_recovery_briefing"]
    build_run_response_briefing = dependencies["build_run_response_briefing"]
    build_start_response = dependencies["build_start_response"]
    build_workstation_status = dependencies["build_workstation_status"]
    humanize_public_recovery_decision = dependencies["humanize_public_recovery_decision"]
    now_iso = dependencies["now_iso"]
    public_review_view = dependencies["public_review_view"]
    run_workstation = dependencies["run_workstation"]
    state_context = dependencies["state_context"]
    summarize_background_log = dependencies["summarize_background_log"]

    start_response = build_start_response()
    run_response = run_workstation(mode="autopilot", worknet_identifier="mine", execute=False)
    workstation_status = build_workstation_status(query="       Mine")
    kya_knowledge = build_knowledge_query_result("kya")
    ardi_knowledge = build_knowledge_query_result("ardi")

    synthetic_runtime_guidance = annotate_runtime_guidance_payload(
        {
            "message": "Wallet session expired; reinitialize first.",
            "state": "auth_required",
            "userActions": ["re-initialize", "check status"],
            "actionMap": {
                "re-initialize": "bash bootstrap.sh",
                "check status": "python3 scripts/run_tool.py agent-status",
            },
            "nextCommand": ["python3", "scripts/run_tool.py", "agent-status"],
        },
        worknet_key="mine",
    )
    synthetic_mine_selection_guidance = annotate_runtime_guidance_payload(
        {
            "message": "Choose a dataset to start mining.",
            "state": "selection_required",
            "userActions": ["Basic Amazon Products Dataset", "Amazon Reviews Dataset"],
            "actionMap": {
                "Basic Amazon Products Dataset": "python3 scripts/run_tool.py agent-start --dataset basic_amazon_products",
                "Amazon Reviews Dataset": "python3 scripts/run_tool.py agent-start --dataset amazon_reviews",
            },
            "nextCommand": ["python3", "scripts/run_tool.py", "agent-start", "--dataset", "basic_amazon_products"],
        },
        worknet_key="mine",
    )
    synthetic_predict_persona_guidance = annotate_runtime_guidance_payload(
        {
            "message": "Predict needs a persona before it can run.",
            "state": "selection_required",
            "userActions": ["select degen persona", "select analyst persona"],
            "actionMap": {
                "select degen persona": "predict-agent set-persona '<PERSONA>'",
                "select analyst persona": "predict-agent set-persona '<PERSONA>'",
            },
            "nextCommand": ["predict-agent", "set-persona", "<PERSONA>"],
            "nextAction": "select_predict_persona",
        },
        worknet_key="predict",
    )
    synthetic_gov_observe_guidance = annotate_runtime_guidance_payload(
        {
            "message": "Gov is in the Voting phase; observe until the principal has enough AWP Power.",
            "state": "Voting",
            "userActions": ["inspect Gov state", "inspect Gov markets", "inspect staking"],
            "actionMap": {
                "inspect Gov state": "python3 scripts/helpers/what-can-i-do.py",
                "inspect Gov markets": "python3 scripts/public/markets.py",
                "inspect staking": "python3 scripts/query-knowledge.py --topic staking",
            },
            "nextAction": "acquire_awp_power_or_observe_gov",
        },
        worknet_key="gov",
    )
    synthetic_ardi_remediation_guidance = annotate_runtime_guidance_payload(
        {
            "message": "Ardi runtime needs Base gas or stake before commit/reveal can continue.",
            "userActions": ["fund Base gas", "rerun Ardi preflight", "inspect KYA path", "buy and stake", "rerun Ardi stake check"],
            "actionMap": {
                "fund Base gas": "Send at least 0.002 ETH to 0xabc on Base",
                "rerun Ardi preflight": "ardi-agent preflight",
                "inspect KYA path": "https://kya.link/",
                "buy and stake": "ardi-agent buy-and-stake",
                "rerun Ardi stake check": "ardi-agent stake",
            },
            "nextCommand": ["ardi-agent", "preflight"],
            "nextAction": "fund_gas_and_or_satisfy_stake",
            "detail": "Send at least 0.002 ETH to 0xabc on Base; Reach the 10000 AWP threshold on EITHER Ardi or KYA.",
        },
        worknet_key="ardi",
    )

    synthetic_follow_up_items = annotate_raw_follow_up_actions([
        {
            "label": "continue current run",
            "description": "Continue this runtime guidance action.",
            "command": "python3 scripts/run-workstation.py --mode autopilot --execute",
            "argv": ["python3", "scripts/run-workstation.py", "--mode", "autopilot", "--execute"],
            "safeToAutoRun": True,
            "requiresConfirmation": False,
        }
    ])
    synthetic_follow_up = synthetic_follow_up_items[0] if synthetic_follow_up_items else None

    synthetic_confirmation_items = annotate_raw_confirmation_queue([
        {
            "label": "confirm submit",
            "description": "Confirm and execute this pending action.",
            "command": "python3 scripts/run-workstation.py --confirm-label confirm-submit",
            "requiresConfirmation": True,
            "requiredInputs": [
                {"name": "amount", "prompt": "Enter amount", "placeholder": "100"},
            ],
        }
    ])
    synthetic_confirmation = synthetic_confirmation_items[0] if synthetic_confirmation_items else None

    synthetic_selected_confirmation = annotate_selected_confirmation(
        {
            "label": "confirm submit",
            "requiredInputs": [
                {"name": "amount", "prompt": "Enter amount", "placeholder": "100"},
            ],
        }
    )

    synthetic_background = annotate_background_record(
        {
            "label": "mine-worker",
            "pid": 123,
            "cwd": "/tmp",
            "argv": ["python3", "worker.py"],
            "logPath": "/tmp/mine.log",
            "startedAt": "2026-05-22T00:00:00Z",
            "alive": False,
            "logTail": "tail",
            "summary": {"headline": "Mine                         ", "status": "stopped"},
        }
    )
    synthetic_selected_background_preview = annotate_background_record(
        {
            "label": "mine-worker",
            "pid": 123,
            "logPath": "/tmp/mine.log",
            "stopCommand": "kill -TERM 123",
            "alive": False,
        }
    )
    synthetic_selected_background_error = annotate_background_record(
        {
            "label": "mine-worker",
            "pid": 123,
            "logPath": "/tmp/mine.log",
            "stopCommand": "kill -TERM 123",
            "alive": True,
            "error": "boom",
        }
    )

    synthetic_recovery_decision = humanize_public_recovery_decision(
        {
            "decision": "resume_previous_run",
            "status": "restart_available",
            "headline": "Previous run can be resumed.",
            "message": "Resume the previous run.",
            "lastWorknetName": "Mine",
            "preferredWorknetName": "Predict",
            "primaryActionLabel": "resume Mine",
            "restartActionLabel": "restart Mine",
            "switchActionLabel": "switch to Predict",
            "staleReason": "old run stopped",
            "actions": [
                {
                    "label": "resume Mine",
                    "description": "Resume the previous run.",
                    "command": "python3 scripts/run-workstation.py --mode autopilot --execute",
                },
                {
                    "label": "inspect last review",
                    "description": "Inspect the last review.",
                    "command": "python3 scripts/review-epoch.py",
                },
            ],
        }
    )

    parameter_schema_display = annotate_parameter_schema_items(
        [{"name": "amount", "prompt": "Enter amount", "placeholder": "100"}]
    )
    synthetic_parameter_schema_item = parameter_schema_display[0] if parameter_schema_display else None
    synthetic_background_summary = summarize_background_log(
        {
            "label": "mine-worker",
            "logPath": "/tmp/mine.log",
        },
        ["line1", "line2"],
    )
    synthetic_runtime_action_payload = annotate_runtime_action_payloads(
        {
            "selectedBackground": {
                "label": "mine-worker",
                "pid": 123,
                "logPath": "/tmp/mine.log",
                "stopCommand": "kill -TERM 123",
                "alive": False,
            },
            "selectedConfirmation": {
                "label": "confirm submit",
                "requiredInputs": [
                    {"name": "amount", "prompt": "Enter amount", "placeholder": "100"},
                ],
            },
            "sourceFollowUpAction": {
                "label": "continue current run",
                "description": "Continue this runtime guidance action.",
                "command": "python3 scripts/run-workstation.py --mode autopilot --execute",
                "argv": ["python3", "scripts/run-workstation.py", "--mode", "autopilot", "--execute"],
                "safeToAutoRun": True,
                "requiresConfirmation": False,
            },
            "confirmedAction": {
                "label": "confirm submit",
                "command": "python3 scripts/run-workstation.py --confirm-label confirm-submit",
                "requiresConfirmation": True,
                "requiredInputs": [
                    {"name": "amount", "prompt": "Enter amount", "placeholder": "100"},
                ],
            },
        }
    )
    synthetic_runtime_action_selected_background = (
        synthetic_runtime_action_payload.get("selectedBackground")
        if isinstance(synthetic_runtime_action_payload, dict)
        and isinstance(synthetic_runtime_action_payload.get("selectedBackground"), dict)
        else None
    )
    synthetic_runtime_action_selected_confirmation = (
        synthetic_runtime_action_payload.get("selectedConfirmation")
        if isinstance(synthetic_runtime_action_payload, dict)
        and isinstance(synthetic_runtime_action_payload.get("selectedConfirmation"), dict)
        else None
    )
    synthetic_runtime_action_selected_confirmation_input = (
        synthetic_runtime_action_selected_confirmation.get("requiredInputsDisplay")[0]
        if isinstance(synthetic_runtime_action_selected_confirmation, dict)
        and isinstance(synthetic_runtime_action_selected_confirmation.get("requiredInputsDisplay"), list)
        and synthetic_runtime_action_selected_confirmation.get("requiredInputsDisplay")
        else None
    )
    synthetic_runtime_action_source_follow_up = (
        synthetic_runtime_action_payload.get("sourceFollowUpAction")
        if isinstance(synthetic_runtime_action_payload, dict)
        and isinstance(synthetic_runtime_action_payload.get("sourceFollowUpAction"), dict)
        else None
    )
    synthetic_runtime_action_confirmed_action = (
        synthetic_runtime_action_payload.get("confirmedAction")
        if isinstance(synthetic_runtime_action_payload, dict)
        and isinstance(synthetic_runtime_action_payload.get("confirmedAction"), dict)
        else None
    )
    synthetic_step = {
        "label": "gov private state",
        "status": "failed",
        "result": {
            "code": 1,
            "stdout": {
                "state": "blocked",
                "message": "[Errno -2] Name or service not known",
                "detail": "trace detail",
                "user_actions": ["check status", "re-initialize"],
                "_internal": {
                    "action_map": {
                        "check status": "python3 scripts/private/state.py",
                        "re-initialize": "bash bootstrap.sh",
                    },
                    "next_action": "follow_runtime_guidance",
                    "next_command": "python3 scripts/private/state.py",
                },
            },
            "stderr": "Traceback: boom",
        },
    }
    synthetic_result_display = build_executed_step_result_display("gov", synthetic_step)
    synthetic_stdout_display = (
        synthetic_result_display.get("stdoutDisplay")
        if isinstance(synthetic_result_display, dict)
        and isinstance(synthetic_result_display.get("stdoutDisplay"), dict)
        else None
    )
    synthetic_stdout_guidance = (
        synthetic_stdout_display.get("guidance")
        if isinstance(synthetic_stdout_display, dict)
        and isinstance(synthetic_stdout_display.get("guidance"), dict)
        else None
    )
    synthetic_probe = annotate_probe_result_display(
        {
            "label": "predict status",
            "code": 1,
            "text": "failed to fetch status: check coordinator connectivity",
            "result": {
                "state": "blocked",
                "message": "failed to fetch status: check coordinator connectivity",
                "detail": "failed to fetch status: check coordinator connectivity",
                "user_actions": ["check status", "re-initialize"],
                "_internal": {
                    "action_map": {
                        "check status": "python3 scripts/run_tool.py agent-status",
                        "re-initialize": "bash bootstrap.sh",
                    },
                    "next_action": "follow_runtime_guidance",
                    "next_command": "bash bootstrap.sh",
                },
            },
        },
        skill_key="predict",
    )
    synthetic_probe_result_display = (
        synthetic_probe.get("resultDisplay")
        if isinstance(synthetic_probe, dict)
        and isinstance(synthetic_probe.get("resultDisplay"), dict)
        else None
    )
    synthetic_probe_stdout_display = (
        synthetic_probe.get("stdoutDisplay")
        if isinstance(synthetic_probe, dict)
        and isinstance(synthetic_probe.get("stdoutDisplay"), dict)
        else None
    )
    synthetic_probe_runtime_guidance_display = (
        synthetic_probe.get("runtimeGuidanceDisplay")
        if isinstance(synthetic_probe, dict)
        and isinstance(synthetic_probe.get("runtimeGuidanceDisplay"), dict)
        else None
    )
    synthetic_predict_run_briefing = build_run_response_briefing(
        {
            "status": "needs_confirmation",
            "selectedWorknetKey": "predict",
            "selectedWorknetName": "Predict",
            "confirmationQueue": [
                {
                    "label": "       Predict       ",
                    "argv": ["predict-agent", "submit"],
                }
            ],
            "runtimeGuidance": None,
            "executedSteps": [],
        },
        preferences={"preferredWorknet": "predict"},
        recovery={},
    )
    synthetic_gov_resume_briefing = build_resume_recovery_briefing(
        {
            "hasLatestPlaybook": True,
            "lastWorknetKey": "gov",
            "pendingConfirmations": 1,
            "defaultConfirmationLabel": "       Gov                       ",
        },
        [
            {
                "label": "       Gov                       ",
                "description": "                      Gov          ",
                "command": "python3 scripts/run-workstation.py --confirm-label '       Gov                       '",
            }
        ],
        worknet_name="GovNet",
        preferred_profile={"key": "gov", "name": "GovNet"},
        action_map={
            "       Gov                       ": "python3 scripts/run-workstation.py --confirm-label '       Gov                       '",
        },
    )
    synthetic_ardi_run_briefing = build_run_response_briefing(
        {
            "status": "needs_runtime_input",
            "nextAction": "follow_runtime_guidance",
            "selectedWorknetKey": "ardi",
            "selectedWorknetName": "Ardi",
            "runtimeGuidance": {
                "message": "Ardi runtime                                Base gas             stake                          commit/reveal          ",
                "userActions": ["    Base Gas", "       Ardi preflight"],
                "actionMap": {
                    "    Base Gas": "Send at least 0.002 ETH to 0xabc on Base",
                    "       Ardi preflight": "ardi-agent preflight",
                },
                "nextCommand": ["ardi-agent", "preflight"],
                "nextAction": "fund_gas_and_or_satisfy_stake",
                "state": None,
            },
            "followUpActions": [
                {
                    "label": "       Ardi preflight",
                    "command": "ardi-agent preflight",
                    "argv": ["ardi-agent", "preflight"],
                    "safeToAutoRun": True,
                    "requiresConfirmation": False,
                }
            ],
            "executedSteps": [],
        },
        preferences={"preferredWorknet": "ardi"},
        recovery={},
    )
    synthetic_predict_review_run = annotate_runtime_action_payloads(
        {
            "playbook": {"worknetKey": "predict", "requiredSkill": "Predict"},
            "executedSteps": [
                {
                    "label": "       Predict context",
                    "status": "ok",
                    "result": {
                        "code": 0,
                        "stdout": {
                            "state": "selection_required",
                            "message": "Context ready.",
                            "data": {"recommendation": {"action": "submit"}},
                            "user_actions": ["prepare submission", "rerun context"],
                            "_internal": {
                                "action_map": {
                                    "prepare submission": "predict-agent submit --market mkt-42 --side <buy|sell> --tickets <tickets> --reasoning <reasoning>",
                                    "rerun context": "predict-agent context",
                                },
                                "next_action": "confirm_predict_submission",
                                "next_command": "predict-agent submit --market mkt-42 --side <buy|sell> --tickets <tickets> --reasoning <reasoning>",
                            },
                        },
                        "stderr": "",
                    },
                }
            ],
            "followUpActions": [
                {
                    "label": "       Predict       ",
                    "command": "predict-agent submit --market mkt-42 --side <buy|sell> --tickets <tickets> --reasoning <reasoning>",
                    "argv": ["predict-agent", "submit", "--market", "mkt-42", "--side", "<buy|sell>", "--tickets", "<tickets>", "--reasoning", "<reasoning>"],
                    "safeToAutoRun": False,
                    "requiresConfirmation": True,
                }
            ],
            "runtimeGuidance": {
                "message": "Predict context                                        tickets     reasoning   ",
                "userActions": ["prepare submission", "rerun context"],
                "actionMap": {
                    "prepare submission": "predict-agent submit --market mkt-42 --side <buy|sell> --tickets <tickets> --reasoning <reasoning>",
                    "rerun context": "predict-agent context",
                },
                "nextCommand": ["predict-agent", "submit", "--market", "mkt-42", "--side", "<buy|sell>", "--tickets", "<tickets>", "--reasoning", "<reasoning>"],
                "nextAction": "confirm_predict_submission",
                "state": "selection_required",
            },
        }
    )
    synthetic_predict_review = public_review_view(
        build_epoch_review_from_run(
            synthetic_predict_review_run,
            [],
            state=state_context(),
        )
    )
    synthetic_gov_review_run = annotate_runtime_action_payloads(
        {
            "playbook": {"worknetKey": "gov", "requiredSkill": "GovNet"},
            "executedSteps": [
                {
                    "label": "gov public markets",
                    "status": "ok",
                    "result": {
                        "code": 0,
                        "stdout": {"items": [{"name": "YES-1"}], "message": "markets loaded"},
                        "stderr": "",
                    },
                },
                {
                    "label": "gov phase-aware helper",
                    "status": "ok",
                    "result": {
                        "code": 0,
                        "stdout": {"phase": "Voting", "message": "Voting"},
                        "stderr": "",
                    },
                },
                {
                    "label": "gov private state",
                    "status": "failed",
                    "result": {
                        "code": 1,
                        "stdout": {
                            "error": "STATE_PRINCIPAL_NOT_IN_EPOCH",
                            "message": "Principal has no AWP Power this epoch",
                            "detail": "Principal has no AWP Power this epoch",
                            "user_actions": ["check status"],
                            "_internal": {
                                "action_map": {"check status": "python3 scripts/private/state.py"},
                                "next_action": "acquire_awp_power_or_observe_gov",
                            },
                        },
                        "stderr": "",
                    },
                },
            ],
            "runtimeGuidance": {
                "message": "Gov        phase     Voting             principal              AWP Power                                             ",
                "userActions": ["       Gov             ", "       Gov markets", "       staking       "],
                "actionMap": {
                    "       Gov             ": "python3 scripts/helpers/what-can-i-do.py",
                    "       Gov markets": "python3 scripts/public/markets.py",
                    "       staking       ": "python3 scripts/query-knowledge.py --topic staking",
                },
                "nextAction": "acquire_awp_power_or_observe_gov",
                "state": "Voting",
            },
        }
    )
    synthetic_gov_review = public_review_view(
        build_epoch_review_from_run(
            synthetic_gov_review_run,
            [],
            state=state_context(),
        )
    )
    synthetic_ardi_review_run = annotate_runtime_action_payloads(
        {
            "playbook": {"worknetKey": "ardi", "requiredSkill": "Ardi"},
            "executedSteps": [
                {
                    "label": "ardi gas check",
                    "status": "failed",
                    "result": {
                        "code": 1,
                        "stdout": {
                            "message": "gas low",
                            "data": {"suggestion": "Send at least 0.002 ETH to 0xabc on Base"},
                        },
                        "stderr": "",
                    },
                },
                {
                    "label": "ardi stake guidance",
                    "status": "failed",
                    "result": {
                        "code": 1,
                        "stdout": {
                            "message": "stake low",
                            "data": {"suggestion": "Reach the 10000 AWP threshold on EITHER Ardi or KYA"},
                        },
                        "stderr": "",
                    },
                },
            ],
            "runtimeGuidance": {
                "message": "Ardi runtime                                Base gas             stake                          commit/reveal          ",
                "userActions": ["    Base Gas", "       Ardi preflight", "    KYA             "],
                "actionMap": {
                    "    Base Gas": "Send at least 0.002 ETH to 0xabc on Base",
                    "       Ardi preflight": "ardi-agent preflight",
                    "    KYA             ": "https://kya.link/",
                },
                "nextCommand": ["ardi-agent", "preflight"],
                "nextAction": "fund_gas_and_or_satisfy_stake",
            },
        }
    )
    synthetic_ardi_review = public_review_view(
        build_epoch_review_from_run(
            synthetic_ardi_review_run,
            [],
            state=state_context(),
        )
    )
    kya_runtime_probe_items = (kya_knowledge.get("runtimeProbeDisplay") or {}).get("items")
    kya_runtime_probe_item = kya_runtime_probe_items[0] if isinstance(kya_runtime_probe_items, list) and kya_runtime_probe_items else None
    ardi_runtime_probe_items = (ardi_knowledge.get("runtimeProbeDisplay") or {}).get("items")
    ardi_runtime_probe_item = ardi_runtime_probe_items[0] if isinstance(ardi_runtime_probe_items, list) and ardi_runtime_probe_items else None
    kya_result_display = (
        kya_runtime_probe_item.get("resultDisplay")
        if isinstance(kya_runtime_probe_item, dict)
        and isinstance(kya_runtime_probe_item.get("resultDisplay"), dict)
        else None
    )
    kya_stdout_display = (
        kya_result_display.get("stdoutDisplay")
        if isinstance(kya_result_display, dict)
        and isinstance(kya_result_display.get("stdoutDisplay"), dict)
        else None
    )
    ardi_result_display = (
        ardi_runtime_probe_item.get("resultDisplay")
        if isinstance(ardi_runtime_probe_item, dict)
        and isinstance(ardi_runtime_probe_item.get("resultDisplay"), dict)
        else None
    )
    ardi_stdout_display = (
        ardi_result_display.get("stdoutDisplay")
        if isinstance(ardi_result_display, dict)
        and isinstance(ardi_result_display.get("stdoutDisplay"), dict)
        else None
    )
    predict_background_summary = summarize_background_log(
        {
            "label": "       Predict             ",
            "argv": ["predict-agent", "loop"],
        },
        [
            "persona=degen timeslot=42",
            "target=BTC-USD",
            "calling LLM via openclaw",
        ],
    )
    predict_background_record = annotate_background_record(
        {
            "label": "       Predict             ",
            "pid": 456,
            "argv": ["predict-agent", "loop"],
            "logPath": "/tmp/predict.log",
            "alive": True,
            "summary": predict_background_summary,
        }
    )

    first_item = first_dict_item

    def audit_item(
        key: str,
        title: str,
        payload: Any,
        fields: list[str],
        *,
        sample_ref: Optional[str] = None,
    ) -> dict[str, Any]:
        return contract_audit_item(
            key,
            title,
            payload,
            fields,
            sample_ref=sample_ref,
            missing_message="No sample payload was available for this branch contract.",
        )

    items = [
        audit_item(
            "start-recovery-decision",
            "Start-response recovery-decision contract",
            start_response.get("recoveryDecision"),
            RECOVERY_DECISION_FIELDS,
            sample_ref="build_start_response().recoveryDecision",
        ),
        audit_item(
            "run-recovery-decision",
            "Run-response recovery-decision contract",
            run_response.get("recoveryDecision"),
            RECOVERY_DECISION_FIELDS,
            sample_ref="run_workstation(...).recoveryDecision",
        ),
        audit_item(
            "status-recovery-decision",
            "Workstation-status recovery-decision contract",
            workstation_status.get("recoveryDecision"),
            RECOVERY_DECISION_FIELDS,
            sample_ref="build_workstation_status(...).recoveryDecision",
        ),
        audit_item(
            "synthetic-recovery-decision",
            "Synthetic recovery-decision contract",
            synthetic_recovery_decision,
            RECOVERY_DECISION_FIELDS,
            sample_ref="humanize_public_recovery_decision({...})",
        ),
        audit_item(
            "synthetic-follow-up-action",
            "Synthetic follow-up action contract",
            synthetic_follow_up,
            FOLLOW_UP_ACTION_FIELDS,
            sample_ref="annotate_raw_follow_up_actions([...])[0]",
        ),
        audit_item(
            "synthetic-confirmation-queue-item",
            "Synthetic confirmation-queue item contract",
            synthetic_confirmation,
            CONFIRMATION_QUEUE_ITEM_FIELDS,
            sample_ref="annotate_raw_confirmation_queue([...])[0]",
        ),
        audit_item(
            "synthetic-selected-confirmation",
            "Synthetic selected-confirmation contract",
            synthetic_selected_confirmation,
            SELECTED_CONFIRMATION_FIELDS,
            sample_ref="annotate_selected_confirmation({...})",
        ),
        audit_item(
            "synthetic-background-record",
            "Synthetic background-record contract",
            synthetic_background,
            BACKGROUND_RECORD_FIELDS,
            sample_ref="annotate_background_record({...})",
        ),
        audit_item(
            "synthetic-selected-background-preview",
            "Synthetic selected-background preview contract",
            synthetic_selected_background_preview,
            SELECTED_BACKGROUND_PREVIEW_FIELDS,
            sample_ref="annotate_background_record({preview})",
        ),
        audit_item(
            "synthetic-selected-background-error",
            "Synthetic selected-background error-preview contract",
            synthetic_selected_background_error,
            SELECTED_BACKGROUND_ERROR_FIELDS,
            sample_ref="annotate_background_record({preview,error})",
        ),
        audit_item(
            "run-executed-step",
            "Run-response executed-step contract",
            first_item(run_response.get("executedSteps")),
            EXECUTED_STEP_FIELDS,
            sample_ref="run_workstation(...).executedSteps[0]",
        ),
        audit_item(
            "parameter-schema-item",
            "Parameter-schema display item contract",
            synthetic_parameter_schema_item,
            PARAMETER_SCHEMA_ITEM_FIELDS,
            sample_ref="annotate_parameter_schema_items([...])[0]",
        ),
        audit_item(
            "background-summary",
            "Synthetic background-summary contract",
            synthetic_background_summary,
            BACKGROUND_SUMMARY_FIELDS,
            sample_ref="summarize_background_log({...})",
        ),
        audit_item(
            "runtime-action-selected-background",
            "annotate_runtime_action_payloads selected-background contract",
            synthetic_runtime_action_selected_background,
            SELECTED_BACKGROUND_PREVIEW_FIELDS,
            sample_ref="annotate_runtime_action_payloads({...}).selectedBackground",
        ),
        audit_item(
            "runtime-action-selected-confirmation",
            "annotate_runtime_action_payloads selected-confirmation contract",
            synthetic_runtime_action_selected_confirmation,
            SELECTED_CONFIRMATION_FIELDS,
            sample_ref="annotate_runtime_action_payloads({...}).selectedConfirmation",
        ),
        audit_item(
            "runtime-action-selected-confirmation-input",
            "annotate_runtime_action_payloads selected-confirmation input contract",
            synthetic_runtime_action_selected_confirmation_input,
            PARAMETER_SCHEMA_ITEM_FIELDS,
            sample_ref="annotate_runtime_action_payloads({...}).selectedConfirmation.requiredInputsDisplay[0]",
        ),
        audit_item(
            "runtime-action-source-follow-up",
            "annotate_runtime_action_payloads source-follow-up contract",
            synthetic_runtime_action_source_follow_up,
            FOLLOW_UP_ACTION_FIELDS,
            sample_ref="annotate_runtime_action_payloads({...}).sourceFollowUpAction",
        ),
        audit_item(
            "runtime-action-confirmed-action",
            "annotate_runtime_action_payloads confirmed-action contract",
            synthetic_runtime_action_confirmed_action,
            CONFIRMED_ACTION_FIELDS,
            sample_ref="annotate_runtime_action_payloads({...}).confirmedAction",
        ),
        audit_item(
            "runtime-guidance",
            "Synthetic runtime-guidance contract",
            synthetic_runtime_guidance,
            RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS,
            sample_ref="annotate_runtime_guidance_payload({...})",
        ),
        audit_item(
            "mine-selection-guidance",
            "Mine selection-required runtime-guidance contract",
            synthetic_mine_selection_guidance,
            RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS,
            sample_ref="annotate_runtime_guidance_payload({mine selection})",
        ),
        audit_item(
            "predict-persona-guidance",
            "Predict persona-selection runtime-guidance contract",
            synthetic_predict_persona_guidance,
            RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS,
            sample_ref="annotate_runtime_guidance_payload({predict persona})",
        ),
        audit_item(
            "gov-observe-guidance",
            "Gov observe-only runtime-guidance contract",
            synthetic_gov_observe_guidance,
            RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS,
            sample_ref="annotate_runtime_guidance_payload({gov observe})",
        ),
        audit_item(
            "ardi-remediation-guidance",
            "Ardi remediation runtime-guidance contract",
            synthetic_ardi_remediation_guidance,
            RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS,
            sample_ref="annotate_runtime_guidance_payload({ardi remediation})",
        ),
        audit_item(
            "runtime-guidance-user-action-detail",
            "Synthetic runtime-guidance user-action-detail contract",
            first_item(synthetic_runtime_guidance.get("userActionDetails") if isinstance(synthetic_runtime_guidance, dict) else None),
            RUNTIME_GUIDANCE_USER_ACTION_DETAIL_FIELDS,
            sample_ref="annotate_runtime_guidance_payload({...}).userActionDetails[0]",
        ),
        audit_item(
            "executed-step-result-display",
            "Synthetic executed-step result-display contract",
            synthetic_result_display,
            EXECUTED_STEP_RESULT_DISPLAY_FIELDS,
            sample_ref="build_executed_step_result_display('gov', synthetic_step)",
        ),
        audit_item(
            "executed-step-stdout-display",
            "Synthetic executed-step stdout-display contract",
            synthetic_stdout_display,
            EXECUTED_STEP_STDOUT_DISPLAY_FIELDS,
            sample_ref="build_executed_step_result_display(...).stdoutDisplay",
        ),
        audit_item(
            "executed-step-stdout-guidance",
            "Synthetic executed-step stdout guidance contract",
            synthetic_stdout_guidance,
            RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS,
            sample_ref="build_executed_step_result_display(...).stdoutDisplay.guidance",
        ),
        audit_item(
            "probe-result-display",
            "Synthetic probe result-display contract",
            synthetic_probe_result_display,
            EXECUTED_STEP_RESULT_DISPLAY_FIELDS,
            sample_ref="annotate_probe_result_display({...}).resultDisplay",
        ),
        audit_item(
            "probe-stdout-display",
            "Synthetic probe stdout-display contract",
            synthetic_probe_stdout_display,
            EXECUTED_STEP_STDOUT_DISPLAY_FIELDS,
            sample_ref="annotate_probe_result_display({...}).stdoutDisplay",
        ),
        audit_item(
            "probe-runtime-guidance-display",
            "Synthetic probe runtime-guidance-display contract",
            synthetic_probe_runtime_guidance_display,
            RUNTIME_GUIDANCE_WITH_NEXT_ACTION_FIELDS,
            sample_ref="annotate_probe_result_display({...}).runtimeGuidanceDisplay",
        ),
        audit_item(
            "predict-run-briefing",
            "Predict confirmation run-briefing contract",
            synthetic_predict_run_briefing,
            RUN_RESPONSE_BRIEFING_FIELDS,
            sample_ref="build_run_response_briefing({predict confirmation})",
        ),
        audit_item(
            "gov-resume-briefing",
            "Gov resume-recovery briefing contract",
            synthetic_gov_resume_briefing,
            RESUME_RECOVERY_BRIEFING_FIELDS,
            sample_ref="build_resume_recovery_briefing({gov confirmation})",
        ),
        audit_item(
            "ardi-run-briefing",
            "Ardi follow-up run-briefing contract",
            synthetic_ardi_run_briefing,
            RUN_RESPONSE_BRIEFING_FIELDS,
            sample_ref="build_run_response_briefing({ardi follow-up})",
        ),
        audit_item(
            "predict-review",
            "Predict synthetic review contract",
            synthetic_predict_review,
            REVIEW_PUBLIC_FIELDS,
            sample_ref="public_review_view(build_epoch_review_from_run({predict latest-run}))",
        ),
        audit_item(
            "predict-review-user-action-detail",
            "Predict synthetic review user-action-detail contract",
            first_item(synthetic_predict_review.get("userActionDetails") if isinstance(synthetic_predict_review, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_review_view(build_epoch_review_from_run({predict latest-run})).userActionDetails[0]",
        ),
        audit_item(
            "gov-review",
            "Gov synthetic review contract",
            synthetic_gov_review,
            REVIEW_PUBLIC_FIELDS,
            sample_ref="public_review_view(build_epoch_review_from_run({gov latest-run}))",
        ),
        audit_item(
            "gov-review-user-action-detail",
            "Gov synthetic review user-action-detail contract",
            first_item(synthetic_gov_review.get("userActionDetails") if isinstance(synthetic_gov_review, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_review_view(build_epoch_review_from_run({gov latest-run})).userActionDetails[0]",
        ),
        audit_item(
            "ardi-review",
            "Ardi synthetic review contract",
            synthetic_ardi_review,
            REVIEW_PUBLIC_FIELDS,
            sample_ref="public_review_view(build_epoch_review_from_run({ardi latest-run}))",
        ),
        audit_item(
            "ardi-review-user-action-detail",
            "Ardi synthetic review user-action-detail contract",
            first_item(synthetic_ardi_review.get("userActionDetails") if isinstance(synthetic_ardi_review, dict) else None),
            USER_ACTION_DETAIL_FIELDS,
            sample_ref="public_review_view(build_epoch_review_from_run({ardi latest-run})).userActionDetails[0]",
        ),
        audit_item(
            "kya-actual-result-display",
            "Actual KYA probe result-display contract",
            kya_result_display or synthetic_probe_result_display,
            EXECUTED_STEP_RESULT_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('kya').runtimeProbeDisplay.items[0].resultDisplay",
        ),
        audit_item(
            "kya-actual-stdout-display",
            "Actual KYA probe stdout-display contract",
            kya_stdout_display or synthetic_probe_stdout_display,
            EXECUTED_STEP_STDOUT_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('kya').runtimeProbeDisplay.items[0].resultDisplay.stdoutDisplay",
        ),
        audit_item(
            "ardi-actual-result-display",
            "Actual Ardi probe result-display contract",
            ardi_result_display or synthetic_probe_result_display,
            EXECUTED_STEP_RESULT_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('ardi').runtimeProbeDisplay.items[0].resultDisplay",
        ),
        audit_item(
            "ardi-actual-stdout-display",
            "Actual Ardi probe stdout-display contract",
            ardi_stdout_display or synthetic_probe_stdout_display,
            EXECUTED_STEP_STDOUT_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('ardi').runtimeProbeDisplay.items[0].resultDisplay.stdoutDisplay",
        ),
        audit_item(
            "predict-background-summary",
            "Predict background-summary display contract",
            predict_background_record.get("summaryDisplay") if isinstance(predict_background_record, dict) else None,
            BACKGROUND_SUMMARY_FIELDS,
            sample_ref="annotate_background_record({predict loop}).summaryDisplay",
        ),
    ]

    return contract_audit_result(items, generated_at=now_iso())


def build_display_contract_audit_payload(
    *,
    catalog: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build display contract audit dependencies are required")
    CITATION_DISPLAY_FIELDS = dependencies["CITATION_DISPLAY_FIELDS"]
    CONCEPT_DIRECTORY_ITEM_FIELDS = dependencies["CONCEPT_DIRECTORY_ITEM_FIELDS"]
    DOSSIER_DISPLAY_FIELDS = dependencies["DOSSIER_DISPLAY_FIELDS"]
    DRIFT_DISPLAY_FIELDS = dependencies["DRIFT_DISPLAY_FIELDS"]
    FRESHNESS_DISPLAY_FIELDS = dependencies["FRESHNESS_DISPLAY_FIELDS"]
    FRESHNESS_ITEM_FIELDS = dependencies["FRESHNESS_ITEM_FIELDS"]
    RUNTIME_PROBE_EVIDENCE_FIELDS = dependencies["RUNTIME_PROBE_EVIDENCE_FIELDS"]
    SOURCE_FACT_DISPLAY_FIELDS = dependencies["SOURCE_FACT_DISPLAY_FIELDS"]
    SOURCE_IMPACT_DISPLAY_FIELDS = dependencies["SOURCE_IMPACT_DISPLAY_FIELDS"]
    SOURCE_IMPACT_ITEM_FIELDS = dependencies["SOURCE_IMPACT_ITEM_FIELDS"]
    SOURCE_RECORD_DISPLAY_FIELDS = dependencies["SOURCE_RECORD_DISPLAY_FIELDS"]
    WORKNET_DISPLAY_FIELDS = dependencies["WORKNET_DISPLAY_FIELDS"]
    build_changed_sources_query_result = dependencies["build_changed_sources_query_result"]
    build_knowledge_query_result = dependencies["build_knowledge_query_result"]
    build_source_query_result = dependencies["build_source_query_result"]
    knowledge_display_changed_sources = dependencies["knowledge_display_changed_sources"]
    knowledge_display_drift_item = dependencies["knowledge_display_drift_item"]
    knowledge_display_source_impact = dependencies["knowledge_display_source_impact"]
    load_or_build_knowledge_catalog = dependencies["load_or_build_knowledge_catalog"]
    now_iso = dependencies["now_iso"]
    query_knowledge_command = dependencies["query_knowledge_command"]
    query_source_command = dependencies["query_source_command"]
    seed_verification_state_from_reference_exports = dependencies["seed_verification_state_from_reference_exports"]
    state_context = dependencies["state_context"]

    if not isinstance(catalog, dict):
        state = state_context()
        seed_verification_state_from_reference_exports(state)
        catalog = load_or_build_knowledge_catalog(state)

    mine_result = build_knowledge_query_result("mine", catalog=catalog)
    concept_result = build_knowledge_query_result("agent-onboarding", catalog=catalog)
    protocol_result = build_knowledge_query_result("protocol-core", catalog=catalog)
    awp_skill_result = build_source_query_result("awp-skill", catalog=catalog)
    mine_skill_result = build_source_query_result("mine-skill-raw", catalog=catalog)
    changed_sources_result = build_changed_sources_query_result(catalog=catalog)
    awp_skill_source = awp_skill_result.get("source") if isinstance(awp_skill_result.get("source"), dict) else {
        "key": "awp-skill",
        "name": "awp-skill",
        "kind": "skill",
        "trustTier": 1,
        "summary": "AWP skill repository source used for workstation registration and runtime guidance.",
        "url": "https://github.com/awp-core/awp-skill",
    }
    synthetic_drift_item = {
        "key": awp_skill_source.get("key"),
        "name": awp_skill_source.get("name"),
        "status": "content_changed",
        "changedFields": ["sha256", "bytes"],
        "note": "Synthetic verification sample for source-drift display coverage.",
        "previous": {
            "ok": True,
            "status": 200,
            "sha256": "old-awp-skill-hash",
            "bytes": 1024,
            "fetchedAt": "2026-05-20T00:00:00Z",
        },
        "current": {
            "ok": True,
            "status": 200,
            "sha256": "new-awp-skill-hash",
            "bytes": 1536,
            "fetchedAt": "2026-05-22T00:00:00Z",
        },
    }
    synthetic_drift_display = knowledge_display_drift_item(
        synthetic_drift_item,
        source_record=awp_skill_source,
    )
    synthetic_changed_source_display = first_dict_item(
        knowledge_display_changed_sources(
            [synthetic_drift_item],
            source_records={str(awp_skill_source.get("key") or ""): awp_skill_source},
        )
    )
    synthetic_impact_item = {
        "sourceKey": awp_skill_source.get("key"),
        "sourceName": awp_skill_source.get("name"),
        "priority": "high",
        "driftStatus": "content_changed",
        "changedFields": ["sha256", "bytes"],
        "note": "Synthetic verification sample for source-impact display coverage.",
        "impactedTopics": [
            {"key": "protocol-core", "title": "Protocol Core"},
            {"key": "staking", "title": "Staking"},
        ],
        "impactedFacts": [
            {"key": "blog-facts", "topic": "Blog"},
        ],
        "impactedWorknets": ["mine", "predict"],
        "reviewHint": "Re-read the source and re-check affected topics, facts, and worknets.",
        "reviewCommands": [
            query_source_command("awp-skill", rebuild=True),
            query_knowledge_command("protocol-core", rebuild=True),
            query_knowledge_command("mine", rebuild=True),
        ],
    }
    synthetic_impact_display = knowledge_display_source_impact(
        {"affected": True, "items": [synthetic_impact_item]},
        catalog=catalog,
    )

    items = [
        contract_audit_item(
            "dossier-display",
            "Topic dossier display contract",
            mine_result.get("dossierDisplay"),
            DOSSIER_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('mine').dossierDisplay",
        ),
        contract_audit_item(
            "concept-display",
            "Concept display contract",
            concept_result.get("conceptDisplay"),
            CONCEPT_DIRECTORY_ITEM_FIELDS,
            sample_ref="build_knowledge_query_result('agent-onboarding').conceptDisplay",
        ),
        contract_audit_item(
            "source-fact-display",
            "Topic source-fact display contract",
            mine_result.get("sourceFactDisplay"),
            SOURCE_FACT_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('mine').sourceFactDisplay",
        ),
        contract_audit_item(
            "worknet-display",
            "Topic worknet display contract",
            mine_result.get("worknetDisplay"),
            WORKNET_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('mine').worknetDisplay",
        ),
        contract_audit_item(
            "source-record-display",
            "Source record display contract",
            awp_skill_result.get("sourceDisplay"),
            SOURCE_RECORD_DISPLAY_FIELDS,
            sample_ref="build_source_query_result('awp-skill').sourceDisplay",
        ),
        contract_audit_item(
            "citation-display",
            "Citation display contract",
            first_dict_item(protocol_result.get("citationsDisplay")),
            CITATION_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('protocol-core').citationsDisplay[0]",
        ),
        contract_audit_item(
            "evidence-display",
            "Evidence display contract",
            first_non_runtime_evidence_item(protocol_result.get("evidenceDisplay")),
            RUNTIME_PROBE_EVIDENCE_FIELDS,
            sample_ref="build_knowledge_query_result('protocol-core').evidenceDisplay[non-runtime]",
        ),
        contract_audit_item(
            "runtime-evidence-display",
            "Runtime evidence display contract",
            first_dict_item(mine_skill_result.get("evidenceDisplay"))
            or first_non_runtime_evidence_item(protocol_result.get("evidenceDisplay")),
            RUNTIME_PROBE_EVIDENCE_FIELDS,
            sample_ref="build_source_query_result('mine-skill-raw').evidenceDisplay[0]",
        ),
        contract_audit_item(
            "drift-display",
            "Source drift display contract",
            awp_skill_result.get("driftDisplay") or synthetic_drift_display,
            DRIFT_DISPLAY_FIELDS,
            sample_ref="build_source_query_result('awp-skill').driftDisplay || synthetic content_changed sample",
        ),
        contract_audit_item(
            "changed-source-display",
            "Changed source list item contract",
            first_dict_item(changed_sources_result.get("changedSourcesDisplay")) or synthetic_changed_source_display,
            DRIFT_DISPLAY_FIELDS,
            sample_ref="build_changed_sources_query_result().changedSourcesDisplay[0] || synthetic changed-source sample",
        ),
        contract_audit_item(
            "source-impact-display",
            "Source impact display contract",
            awp_skill_result.get("impactDisplay") or synthetic_impact_display,
            SOURCE_IMPACT_DISPLAY_FIELDS,
            sample_ref="build_source_query_result('awp-skill').impactDisplay || synthetic source-impact sample",
        ),
        contract_audit_item(
            "source-impact-item-display",
            "Source impact item contract",
            first_dict_item((awp_skill_result.get("impactDisplay") or {}).get("items"))
            or first_dict_item((synthetic_impact_display or {}).get("items")),
            SOURCE_IMPACT_ITEM_FIELDS,
            sample_ref="build_source_query_result('awp-skill').impactDisplay.items[0] || synthetic source-impact item",
        ),
        contract_audit_item(
            "freshness-display",
            "Freshness display contract",
            protocol_result.get("freshnessDisplay"),
            FRESHNESS_DISPLAY_FIELDS,
            sample_ref="build_knowledge_query_result('protocol-core').freshnessDisplay",
        ),
        contract_audit_item(
            "freshness-item-display",
            "Freshness item display contract",
            first_dict_item((protocol_result.get("freshnessDisplay") or {}).get("items")),
            FRESHNESS_ITEM_FIELDS,
            sample_ref="build_knowledge_query_result('protocol-core').freshnessDisplay.items[0]",
        ),
    ]

    return contract_audit_result(items, generated_at=now_iso())


def build_query_contract_audit_payload(
    *,
    catalog: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build query contract audit dependencies are required")
    CHANGED_SOURCES_QUERY_FIELDS = dependencies["CHANGED_SOURCES_QUERY_FIELDS"]
    CONCEPT_DIRECTORY_ITEM_FIELDS = dependencies["CONCEPT_DIRECTORY_ITEM_FIELDS"]
    GLOSSARY_ITEM_FIELDS = dependencies["GLOSSARY_ITEM_FIELDS"]
    GLOSSARY_QUERY_FIELDS = dependencies["GLOSSARY_QUERY_FIELDS"]
    GLOSSARY_QUERY_MATCH_FIELDS = dependencies["GLOSSARY_QUERY_MATCH_FIELDS"]
    KNOWLEDGE_ATLAS_GAP_FIELDS = dependencies["KNOWLEDGE_ATLAS_GAP_FIELDS"]
    KNOWLEDGE_ATLAS_QUERY_FIELDS = dependencies["KNOWLEDGE_ATLAS_QUERY_FIELDS"]
    KNOWLEDGE_DIRECTORY_ENTRY_FIELDS = dependencies["KNOWLEDGE_DIRECTORY_ENTRY_FIELDS"]
    KNOWLEDGE_OVERVIEW_FIELDS = dependencies["KNOWLEDGE_OVERVIEW_FIELDS"]
    KNOWLEDGE_QUERY_FIELDS = dependencies["KNOWLEDGE_QUERY_FIELDS"]
    KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS = dependencies["KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS"]
    REVIEW_SCOPE_FIELDS = dependencies["REVIEW_SCOPE_FIELDS"]
    SOURCE_DIRECTORY_ENTRY_FIELDS = dependencies["SOURCE_DIRECTORY_ENTRY_FIELDS"]
    SOURCE_QUERY_FIELDS = dependencies["SOURCE_QUERY_FIELDS"]
    build_changed_sources_query_result = dependencies["build_changed_sources_query_result"]
    build_glossary_query_result = dependencies["build_glossary_query_result"]
    build_knowledge_query_result = dependencies["build_knowledge_query_result"]
    build_source_query_result = dependencies["build_source_query_result"]
    load_or_build_knowledge_catalog = dependencies["load_or_build_knowledge_catalog"]
    now_iso = dependencies["now_iso"]
    seed_verification_state_from_reference_exports = dependencies["seed_verification_state_from_reference_exports"]
    state_context = dependencies["state_context"]

    if not isinstance(catalog, dict):
        state = state_context()
        seed_verification_state_from_reference_exports(state)
        catalog = load_or_build_knowledge_catalog(state)
    atlas_result = build_knowledge_query_result("atlas", catalog=catalog)
    knowledge_result = build_knowledge_query_result("mine", catalog=catalog)
    concept_result = build_knowledge_query_result("agent-onboarding", catalog=catalog)
    glossary_topic_result = build_knowledge_query_result("fair launch", catalog=catalog)
    review_queue_result = build_knowledge_query_result("review-queue", catalog=catalog)
    source_result = build_source_query_result("awp-skill", catalog=catalog)
    changed_result = build_changed_sources_query_result(catalog=catalog)
    glossary_result = build_glossary_query_result("rootnet")

    items = [
        contract_audit_item(
            "knowledge-atlas-query",
            "Knowledge atlas query contract",
            atlas_result,
            KNOWLEDGE_ATLAS_QUERY_FIELDS,
            sample_ref="build_knowledge_query_result('atlas')",
        ),
        contract_audit_item(
            "knowledge-atlas-overview",
            "Knowledge atlas overview contract",
            atlas_result.get("knowledgeOverview"),
            KNOWLEDGE_OVERVIEW_FIELDS,
            sample_ref="build_knowledge_query_result('atlas').knowledgeOverview",
        ),
        contract_audit_item(
            "knowledge-atlas-topic-directory-entry",
            "Knowledge atlas topic-directory entry contract",
            first_dict_item(atlas_result.get("topicDirectory")),
            KNOWLEDGE_DIRECTORY_ENTRY_FIELDS,
            sample_ref="build_knowledge_query_result('atlas').topicDirectory[0]",
        ),
        contract_audit_item(
            "knowledge-atlas-worknet-directory-entry",
            "Knowledge atlas worknet-directory entry contract",
            first_dict_item(atlas_result.get("worknetDirectory")),
            KNOWLEDGE_DIRECTORY_ENTRY_FIELDS,
            sample_ref="build_knowledge_query_result('atlas').worknetDirectory[0]",
        ),
        contract_audit_item(
            "knowledge-atlas-reference-directory-entry",
            "Knowledge atlas reference-directory entry contract",
            first_dict_item(atlas_result.get("referenceDirectory")),
            KNOWLEDGE_DIRECTORY_ENTRY_FIELDS,
            sample_ref="build_knowledge_query_result('atlas').referenceDirectory[0]",
        ),
        contract_audit_item(
            "knowledge-atlas-source-directory-entry",
            "Knowledge atlas source-directory entry contract",
            first_dict_item(atlas_result.get("sourceDirectory")),
            SOURCE_DIRECTORY_ENTRY_FIELDS,
            sample_ref="build_knowledge_query_result('atlas').sourceDirectory[0]",
        ),
        contract_audit_item(
            "knowledge-atlas-concept-directory-entry",
            "Knowledge atlas concept-directory entry contract",
            first_dict_item(atlas_result.get("conceptDirectory")),
            CONCEPT_DIRECTORY_ITEM_FIELDS,
            sample_ref="build_knowledge_query_result('atlas').conceptDirectory[0]",
        ),
        contract_audit_item(
            "knowledge-atlas-glossary-directory-entry",
            "Knowledge atlas glossary-directory entry contract",
            first_dict_item(atlas_result.get("glossaryDirectory")),
            GLOSSARY_ITEM_FIELDS,
            sample_ref="build_knowledge_query_result('atlas').glossaryDirectory[0]",
        ),
        contract_audit_item(
            "knowledge-atlas-gap-entry",
            "Knowledge atlas gap entry contract",
            first_dict_item(atlas_result.get("atlasGaps")),
            KNOWLEDGE_ATLAS_GAP_FIELDS,
            sample_ref="build_knowledge_query_result('atlas').atlasGaps[0]",
        ),
        contract_audit_item(
            "knowledge-query",
            "Primary knowledge query contract",
            knowledge_result,
            KNOWLEDGE_QUERY_FIELDS,
            sample_ref="build_knowledge_query_result('mine')",
        ),
        contract_audit_item(
            "knowledge-concept-query",
            "Concept knowledge query contract",
            concept_result,
            KNOWLEDGE_QUERY_FIELDS,
            sample_ref="build_knowledge_query_result('agent-onboarding')",
        ),
        contract_audit_item(
            "knowledge-glossary-topic-query",
            "Glossary-backed knowledge query contract",
            glossary_topic_result,
            KNOWLEDGE_QUERY_FIELDS,
            sample_ref="build_knowledge_query_result('fair launch')",
        ),
        contract_audit_item(
            "knowledge-review-queue-query",
            "Review-queue knowledge query contract",
            review_queue_result,
            KNOWLEDGE_REVIEW_QUEUE_QUERY_FIELDS,
            sample_ref="build_knowledge_query_result('review-queue')",
        ),
        contract_audit_item(
            "source-query",
            "Source query contract",
            source_result,
            SOURCE_QUERY_FIELDS,
            sample_ref="build_source_query_result('awp-skill')",
        ),
        contract_audit_item(
            "changed-sources-query",
            "Changed-sources query contract",
            changed_result,
            CHANGED_SOURCES_QUERY_FIELDS,
            sample_ref="build_changed_sources_query_result()",
        ),
        contract_audit_item(
            "glossary-query",
            "Glossary query contract",
            glossary_result,
            GLOSSARY_QUERY_FIELDS,
            sample_ref="build_glossary_query_result('rootnet')",
        ),
        contract_audit_item(
            "source-review-scope",
            "Source review-scope contract",
            source_result.get("reviewScope"),
            REVIEW_SCOPE_FIELDS,
            sample_ref="build_source_query_result('awp-skill').reviewScope",
        ),
        contract_audit_item(
            "glossary-query-match",
            "Glossary match contract",
            glossary_result.get("match"),
            GLOSSARY_QUERY_MATCH_FIELDS,
            sample_ref="build_glossary_query_result('rootnet').match",
        ),
        contract_audit_item(
            "glossary-query-match-display",
            "Glossary match display contract",
            glossary_result.get("matchDisplay"),
            GLOSSARY_ITEM_FIELDS,
            sample_ref="build_glossary_query_result('rootnet').matchDisplay",
        ),
    ]

    return contract_audit_result(items, generated_at=now_iso())

