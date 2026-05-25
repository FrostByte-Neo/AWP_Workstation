"""Capability scanning and live WorkNet enrichment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional


def fallback_capability_reports_payload(
    inventory: dict[str, Any], state: Optional[dict[str, Any]] = None,
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    if dependencies is None:
        raise ValueError("fallback capability reports dependencies are required")
    KNOWN_WORKNETS = dependencies["KNOWN_WORKNETS"]
    build_skill_inspection_catalog = dependencies["build_skill_inspection_catalog"]
    canonical_worknet_scan_reason = dependencies["canonical_worknet_scan_reason"]
    ensure_user_preferences = dependencies["ensure_user_preferences"]
    humanize_capability_reason_part = dependencies["humanize_capability_reason_part"]
    infer_runnable = dependencies["infer_runnable"]
    inspection_status_blocks_runtime = dependencies["inspection_status_blocks_runtime"]
    inspection_status_enables_runtime = dependencies["inspection_status_enables_runtime"]
    join_product_sentences = dependencies["join_product_sentences"]
    knowledge_worknet_metadata = dependencies["knowledge_worknet_metadata"]
    looks_official_skill_uri = dependencies["looks_official_skill_uri"]
    official_remote_manifest = dependencies["official_remote_manifest"]
    predict_loop_ready = dependencies["predict_loop_ready"]
    runtime_probe_blockers = dependencies["runtime_probe_blockers"]
    runtime_spec_reason_parts = dependencies["runtime_spec_reason_parts"]
    skill_registry_from_inventory = dependencies["skill_registry_from_inventory"]
    state_context = dependencies["state_context"]
    strip_sentence_end = dependencies["strip_sentence_end"]

    state = state or state_context()
    preferences = ensure_user_preferences(state)
    local_by_key = {
        item["key"]: item for item in inventory.get("localSources", []) if isinstance(item, dict)
    }
    skill_registry = {
        item["key"]: item for item in skill_registry_from_inventory(inventory, state=state)
    }
    skill_inspections = {
        item["skillKey"]: item
        for item in build_skill_inspection_catalog(state=state, inventory=inventory).get("inspections", [])
        if isinstance(item, dict)
    }
    reports: list[dict[str, Any]] = []
    for profile in KNOWN_WORKNETS:
        local_source = local_by_key.get(profile.get("local_source_key"))
        local_skill_path: Optional[str] = None
        skill_root: Optional[Path] = None
        if local_source and local_source.get("available"):
            skill_root = Path(str(local_source["path"]))
            local_skill_path = str(skill_root / "SKILL.md")
        inspection = skill_inspections.get(profile["key"], {})
        skills_uri = profile.get("skills_uri")
        official_skill = looks_official_skill_uri(profile.get("install_uri") or skills_uri)
        inspection_status = str(inspection.get("status", "missing"))
        manifest = official_remote_manifest(profile["key"])
        execution_blockers = runtime_probe_blockers(profile["key"], inspection)
        predict_loop_is_ready = profile["key"] == "predict" and predict_loop_ready(state, inspection)
        runnable = infer_runnable(profile, local_source)
        worknet_metadata = knowledge_worknet_metadata(
            worknet_key=profile["key"],
            worknet_id=profile.get("worknet_id"),
            source_keys=profile.get("source_keys", []),
            install_uri=profile.get("install_uri") or profile.get("skills_uri"),
            capability_report=None,
        )
        runtime_ready_for_execution = inspection_status_enables_runtime(inspection_status) and (
            inspection.get("scriptCount", 0) > 0
            or bool(manifest.get("binaryRuntime"))
        )
        if runtime_ready_for_execution:
            runnable = runnable or profile["key"] in {"gov", "ardi", "predict", "tmr", "community", "mine", "kya"}
        if inspection_status_blocks_runtime(inspection_status):
            runnable = False
        if execution_blockers and not predict_loop_is_ready:
            runnable = False
        predict_observe_hours = int(preferences.get("observeBeforePredictHours", 24) or 0)
        if profile["key"] == "predict" and predict_loop_is_ready:
            runnable = True
        can_start_without_stake = True if profile["key"] == "predict" and predict_loop_is_ready else profile["min_stake"] in (None, 0)
        reason_parts = [canonical_worknet_scan_reason(profile, runnable=runnable, can_start_without_stake=can_start_without_stake) or profile.get("goal", "")]
        install_status = skill_registry.get(profile["key"], {}).get("status")
        if local_source and local_source.get("available"):
            reason_parts.append(f"local source present at {local_source['path']}")
        elif install_status == "managed-installed":
            reason_parts.append("official runtime checkout is installed locally")
        elif profile.get("install_uri"):
            reason_parts.append("official install URI known, but runtime not installed locally")
        else:
            reason_parts.append("no verified local runtime found")
        if inspection_status == "runtime-error":
            probe_labels = [
                str(item.get("label"))
                for item in inspection.get("probeResults", [])
                if isinstance(item, dict) and item.get("ok") is False
            ]
            if probe_labels:
                reason_parts.append("runtime probe failed for " + ", ".join(probe_labels))
            else:
                reason_parts.append("runtime probe failed")
        elif inspection_status == "installed-needs-bootstrap":
            reason_parts.append("runtime exists but still needs bootstrap before safe execution")
        elif inspection_status == "remote-profile-only":
            reason_parts.append("workstation only has remote runtime guidance, not a local install")
        elif inspection_status == "network-blocked":
            reason_parts.append("local runtime is present, but its live probes are blocked by the current network environment")
        elif inspection_status == "empty-official-repo":
            reason_parts.append("official runtime checkout currently only exposes license or metadata files, so there is nothing safe to auto-run yet")
        reason_parts.extend(
            runtime_spec_reason_parts(
                runtime_spec_state=worknet_metadata.get("runtimeSpecState"),
                runtime_spec_state_display=worknet_metadata.get("runtimeSpecStateDisplay"),
                canonical_worknet_id=worknet_metadata.get("canonicalWorknetId"),
                min_stake_hint_display=worknet_metadata.get("minStakeHintDisplay"),
            )
        )
        if profile["key"] == "predict" and predict_loop_is_ready and predict_observe_hours > 0:
            reason_parts.append(f"user preference still suggests observing Predict outcomes for the first {predict_observe_hours} hours even though the official loop can start now")
            reason_parts.append("Predict can start with virtual chips now; staking remains an enhancement path rather than a hard prerequisite for the loop")
        if profile["key"] == "predict" and predict_loop_is_ready:
            if execution_blockers:
                reason_parts.append("If you want the stake-backed path later, use the official staking or KYA route and then re-run Predict stake checks")
        else:
            reason_parts.extend(execution_blockers)
        normalized_reason_parts = [
            humanize_capability_reason_part(part)
            for part in reason_parts
            if isinstance(part, str) and str(part).strip()
        ]
        primary_reason = str(normalized_reason_parts[0] or "").strip() if normalized_reason_parts else ""
        technical_reason = join_product_sentences(normalized_reason_parts[1:])
        public_reason = primary_reason
        if technical_reason:
            public_reason = (
                f"{strip_sentence_end(primary_reason)}. {technical_reason}"
                if primary_reason
                else technical_reason
            )
        reports.append(
            {
                "worknetId": profile["worknet_id"],
                "name": profile["name"],
                "symbol": profile["symbol"],
                "status": profile["status"],
                "skillsUri": skills_uri,
                "officialSkill": official_skill,
                "minStake": profile["min_stake"],
                "runnable": runnable,
                "automationLevel": profile["automation_level"],
                "riskLevel": profile["risk_level"],
                "recommendedRole": profile["recommended_role"],
                "reason": public_reason,
                "localSkillPath": local_skill_path,
                "installStatus": skill_registry.get(profile["key"], {}).get("status"),
                "apiStatus": "unknown",
                "cliStatus": inspection_status,
                "canStartWithoutStake": can_start_without_stake,
                "safeLongRun": runnable and profile["key"] == "mine",
                "skillInspection": inspection,
            }
        )
    return reports


def resolve_live_worknet_id_payload(
    entry: dict[str, Any],
    profile: Optional[dict[str, Any]],
    auxiliary_candidates: Optional[list[dict[str, Any]]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> tuple[Any, str, list[dict[str, Any]]]:
    if dependencies is None:
        raise ValueError("resolve live worknet id dependencies are required")
    first_present = dependencies["first_present"]
    normalize_search_entries = dependencies["normalize_search_entries"]
    normalize_worknet_id = dependencies["normalize_worknet_id"]
    normalize_worknet_token = dependencies["normalize_worknet_token"]
    rpc_call = dependencies["rpc_call"]

    observed = normalize_worknet_id(first_present(entry, ["worknetId", "id", "worknet_id", "subnetId"]))
    if profile:
        canonical = normalize_worknet_id(profile.get("worknet_id"))
        predecessor_ids = {
            normalize_worknet_id(value)
            for value in profile.get("predecessor_worknet_ids", [])
            if normalize_worknet_id(value) not in (None, "")
        }
        if canonical not in (None, "") and observed in predecessor_ids:
            return canonical, "profile-successor", [
                {
                    "query": "entry",
                    "ok": True,
                    "match": "predecessor_worknet_id",
                    "candidateId": observed,
                    "promotedId": canonical,
                }
            ]
    if observed not in (None, ""):
        return observed, "entry", []
    if profile and str(profile.get("worknet_id", "")).isdigit():
        return str(profile["worknet_id"]), "profile", []

    auxiliary_candidates = auxiliary_candidates or []
    search_queries = []
    name = str(first_present(entry, ["name"], "")).strip()
    symbol = str(first_present(entry, ["symbol", "tokenSymbol"], "")).strip()
    if name:
        search_queries.append(name)
    if symbol:
        search_queries.append(symbol)
    if profile:
        for candidate in [
            profile.get("name", ""),
            profile.get("key", ""),
            *profile.get("aliases", []),
            profile.get("symbol", ""),
        ]:
            text = str(candidate or "").strip()
            if text and text not in search_queries:
                search_queries.append(text)

    normalized_name = normalize_worknet_token(name)
    normalized_symbol = normalize_worknet_token(symbol)
    for candidate in auxiliary_candidates:
        cid = normalize_worknet_id(first_present(candidate, ["worknetId", "id", "worknet_id", "subnetId"]))
        if cid in (None, ""):
            continue
        cname = normalize_worknet_token(str(first_present(candidate, ["name"], "")))
        csymbol = normalize_worknet_token(str(first_present(candidate, ["symbol", "tokenSymbol"], "")))
        if normalized_name and cname == normalized_name:
            return cid, "ranked-name", [{"query": "listRanked", "ok": True, "match": "name", "candidateId": cid}]
        if normalized_symbol and csymbol == normalized_symbol:
            return cid, "ranked-symbol", [{"query": "listRanked", "ok": True, "match": "symbol", "candidateId": cid}]

    search_attempts: list[dict[str, Any]] = []
    for query in search_queries:
        response = rpc_call("worknets.search", params={"query": query, "limit": 20})
        if not response.get("ok"):
            search_attempts.append({"query": query, "ok": False, "error": response.get("error")})
            continue
        candidates = normalize_search_entries(response.get("body"))
        ranked: list[tuple[int, dict[str, Any]]] = []
        for candidate in candidates:
            cid = normalize_worknet_id(first_present(candidate, ["worknetId", "id", "worknet_id", "subnetId"]))
            if cid in (None, ""):
                continue
            score = 0
            cname = normalize_worknet_token(str(first_present(candidate, ["name"], "")))
            csymbol = normalize_worknet_token(str(first_present(candidate, ["symbol", "tokenSymbol"], "")))
            if normalized_name and cname == normalized_name:
                score += 100
            if normalized_symbol and csymbol == normalized_symbol:
                score += 80
            if profile and str(profile.get("worknet_id", "")) == str(cid):
                score += 200
            if score > 0:
                ranked.append((score, candidate))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        search_attempts.append(
            {
                "query": query,
                "ok": True,
                "candidateCount": len(candidates),
                "rankedCount": len(ranked),
                "topCandidateId": normalize_worknet_id(first_present(ranked[0][1], ["worknetId", "id", "worknet_id", "subnetId"])) if ranked else None,
            }
        )
        if ranked:
            chosen = ranked[0][1]
            cid = normalize_worknet_id(first_present(chosen, ["worknetId", "id", "worknet_id", "subnetId"]))
            if cid not in (None, ""):
                return cid, f"search:{query}", search_attempts
    return None, "unresolved", search_attempts


def enrich_reports_with_rpc_payload(
    reports: list[dict[str, Any]], inventory: dict[str, Any], agent_address: Optional[str],
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if dependencies is None:
        raise ValueError("enrich reports with rpc dependencies are required")
    first_present = dependencies["first_present"]
    looks_official_skill_uri = dependencies["looks_official_skill_uri"]
    match_profile_from_rpc = dependencies["match_profile_from_rpc"]
    normalize_worknet_entries = dependencies["normalize_worknet_entries"]
    rpc_call = dependencies["rpc_call"]
    rpc_result_body = dependencies["rpc_result_body"]
    rpc_try_many = dependencies["rpc_try_many"]
    trim_output = dependencies["trim_output"]

    rpc_meta: dict[str, Any] = {"used": False, "errors": []}
    response = rpc_call("worknets.list", params={})
    if not response.get("ok"):
        rpc_meta["errors"].append(trim_output(response.get("error")))
        return reports, rpc_meta
    entries = normalize_worknet_entries(response.get("body"))
    if not entries:
        rpc_meta["errors"].append("worknets.list returned no usable entries")
        return reports, rpc_meta
    by_name = {item["name"]: item for item in reports}
    by_id = {str(item["worknetId"]): item for item in reports}
    for entry in entries:
        profile = match_profile_from_rpc(entry)
        existing = None
        observed_entry_id = first_present(entry, ["worknetId", "id", "worknet_id", "subnetId", "subnet_id"])
        entry_id = (
            profile.get("worknet_id")
            if profile and (observed_entry_id is None or str(observed_entry_id).startswith("unknown:"))
            else observed_entry_id
        )
        entry_name = first_present(entry, ["name"], "Unknown WorkNet")
        if entry_id is not None and str(entry_id) in by_id:
            existing = by_id[str(entry_id)]
        elif entry_name in by_name:
            existing = by_name[entry_name]
        if existing is None:
            existing = {
                "worknetId": entry_id or f"unknown:{entry_name.lower().replace(' ', '-')}",
                "name": profile["name"] if profile else entry_name,
                "symbol": first_present(entry, ["symbol", "tokenSymbol"], "UNKNOWN"),
                "status": first_present(entry, ["status", "state"], "unknown"),
                "skillsUri": first_present(entry, ["skillsUri", "skillsURI", "skillUri", "skillURI", "skills_uri"]),
                "officialSkill": False,
                "minStake": first_present(entry, ["minStake", "min_stake"]),
                "runnable": False,
                "automationLevel": "unknown",
                "riskLevel": "unknown",
                "recommendedRole": "observer",
                "reason": "discovered through live RPC, not yet profiled by the workstation",
                "localSkillPath": None,
                "installStatus": None,
                "apiStatus": "ready",
                "cliStatus": "unknown",
                "canStartWithoutStake": None,
                "safeLongRun": False,
            }
            reports.append(existing)
            by_id[str(existing["worknetId"])] = existing
        existing["worknetId"] = entry_id or existing["worknetId"]
        existing["name"] = profile["name"] if profile else entry_name
        existing["symbol"] = first_present(entry, ["symbol", "tokenSymbol"], existing["symbol"])
        existing["status"] = first_present(entry, ["status", "state"], existing["status"])
        existing["skillsUri"] = first_present(
            entry,
            ["skillsUri", "skillsURI", "skillUri", "skillURI", "skills_uri"],
            existing["skillsUri"],
        )
        existing["minStake"] = first_present(entry, ["minStake", "min_stake"], existing["minStake"])
        existing["officialSkill"] = looks_official_skill_uri(existing.get("skillsUri")) or existing.get("officialSkill", False)
        existing["apiStatus"] = "ready"
        if existing.get("canStartWithoutStake") is None:
            existing["canStartWithoutStake"] = existing.get("minStake") in (None, 0)
        if profile:
            existing["automationLevel"] = profile["automation_level"]
            existing["riskLevel"] = profile["risk_level"]
            existing["recommendedRole"] = profile["recommended_role"]
            existing["safeLongRun"] = bool(existing.get("runnable")) and profile["key"] == "mine"
        diagnostics: dict[str, Any] = {}
        deep_rpc_scan = os.environ.get("AWP_WORKSTATION_DEEP_RPC_SCAN") == "1"
        if deep_rpc_scan and entry_id is not None and not str(entry_id).startswith("unknown:"):
            skills_call = rpc_try_many(
                "worknets.getSkills",
                [{"worknetId": entry_id}, {"id": entry_id}],
            )
            if skills_call.get("ok"):
                diagnostics["skills"] = trim_output(rpc_result_body(skills_call["body"]))
            token_call = rpc_try_many(
                "tokens.getWorknetTokenPrice",
                [{"worknetId": entry_id}, {"id": entry_id}, {"symbol": existing["symbol"]}],
            )
            if token_call.get("ok"):
                diagnostics["tokenPrice"] = trim_output(rpc_result_body(token_call["body"]))
            if agent_address:
                agent_call = rpc_try_many(
                    "staking.getAgentInfo",
                    [
                        {"worknetId": entry_id, "agentAddress": agent_address},
                        {"id": entry_id, "agent": agent_address},
                    ],
                )
                if agent_call.get("ok"):
                    diagnostics["agentInfo"] = trim_output(rpc_result_body(agent_call["body"]))
                earnings_call = rpc_try_many(
                    "worknets.getEarnings",
                    [
                        {"worknetId": entry_id, "agentAddress": agent_address},
                        {"id": entry_id, "agent": agent_address},
                    ],
                )
                if earnings_call.get("ok"):
                    diagnostics["earnings"] = trim_output(rpc_result_body(earnings_call["body"]))
        if diagnostics:
            existing["rpcDiagnostics"] = diagnostics
    rpc_meta["used"] = True
    rpc_meta["entryCount"] = len(entries)
    return reports, rpc_meta


def enrich_reports_with_cached_live_worknets_payload(
    reports: list[dict[str, Any]], snapshot: dict[str, Any],
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if dependencies is None:
        raise ValueError("enrich reports with cached live worknets dependencies are required")
    looks_official_skill_uri = dependencies["looks_official_skill_uri"]
    match_profile_from_rpc = dependencies["match_profile_from_rpc"]
    normalize_worknet_id = dependencies["normalize_worknet_id"]
    safe_slug = dependencies["safe_slug"]

    meta: dict[str, Any] = {
        "used": True,
        "source": "official-live-worknets-cache",
        "generatedAt": snapshot.get("generatedAt"),
        "entryCount": len(snapshot.get("entries", [])),
        "errors": snapshot.get("errors", []),
    }
    by_name = {item["name"]: item for item in reports}
    by_id = {str(item["worknetId"]): item for item in reports}

    for entry in snapshot.get("entries", []):
        if not isinstance(entry, dict):
            continue
        profile = match_profile_from_rpc(entry)
        observed_wid = normalize_worknet_id(entry.get("worknetId") or entry.get("subnet_id"))
        wid = None if str(observed_wid or "").startswith("unknown:") else observed_wid
        wid = wid or (profile["worknet_id"] if profile else None)
        name = entry.get("name", "Unknown WorkNet")
        observed_name = entry.get("observedName", name)
        existing = None
        if wid is not None and str(wid) in by_id:
            existing = by_id[str(wid)]
        elif name in by_name:
            existing = by_name[name]
        else:
            existing = {
                "worknetId": wid or f"unknown:{safe_slug(str(name))}",
                "name": profile["name"] if profile else name,
                "symbol": entry.get("symbol", "UNKNOWN"),
                "status": entry.get("status", "unknown"),
                "skillsUri": entry.get("skillsUri"),
                "officialSkill": entry.get("officialSkill", False),
                "minStake": entry.get("minStake"),
                "runnable": False,
                "automationLevel": "unknown",
                "riskLevel": "unknown",
                "recommendedRole": "observer",
                "reason": "discovered from cached live official worknet scan",
            }
            reports.append(existing)
        existing["worknetId"] = wid or existing["worknetId"]
        existing["observedName"] = observed_name
        if entry.get("observedWorknetId") not in (None, ""):
            existing["observedWorknetId"] = entry.get("observedWorknetId")
        existing["resolvedVia"] = entry.get("resolvedVia", existing.get("resolvedVia"))
        existing["resolutionConfidence"] = entry.get(
            "resolutionConfidence",
            existing.get("resolutionConfidence", "low"),
        )
        if not profile:
            existing["name"] = name
        existing["symbol"] = entry.get("symbol", existing.get("symbol"))
        existing["status"] = entry.get("status", existing.get("status"))
        observed_skills_uri = entry.get("skillsUri")
        if observed_skills_uri not in (None, ""):
            existing["observedSkillsUri"] = observed_skills_uri
        canonical_skills_uri = profile.get("skills_uri") or profile.get("install_uri") if profile else None
        if canonical_skills_uri:
            existing["skillsUri"] = canonical_skills_uri
        elif profile and profile.get("key") == "predict" and isinstance(observed_skills_uri, str) and "mine-skill" in observed_skills_uri:
            existing["skillsUri"] = None
            existing["liveWarnings"] = list({*(existing.get("liveWarnings", [])), "observed skillsUri looked mismatched for Predict and was not promoted"})
            existing["officialSkill"] = False
        elif observed_skills_uri not in (None, ""):
            existing["skillsUri"] = observed_skills_uri
        if existing.get("skillsUri") is not None:
            existing["officialSkill"] = looks_official_skill_uri(existing.get("skillsUri")) or bool(entry.get("officialSkill"))

        observed_min_stake = entry.get("minStake")
        existing["observedMinStake"] = observed_min_stake
        canonical_min_stake = profile.get("min_stake") if profile else existing.get("minStake")
        if canonical_min_stake is not None and observed_min_stake not in (None, ""):
            try:
                existing["minStake"] = max(int(canonical_min_stake), int(observed_min_stake))
            except (TypeError, ValueError):
                existing["minStake"] = canonical_min_stake
        elif observed_min_stake not in (None, ""):
            existing["minStake"] = observed_min_stake
        else:
            existing["minStake"] = canonical_min_stake
        existing["apiStatus"] = "cached-live"
        if existing.get("canStartWithoutStake") is None:
            existing["canStartWithoutStake"] = existing.get("minStake") in (None, 0, "0")
        if profile:
            existing["automationLevel"] = profile["automation_level"]
            existing["riskLevel"] = profile["risk_level"]
            existing["recommendedRole"] = profile["recommended_role"]
            existing["safeLongRun"] = bool(existing.get("runnable")) and profile["key"] == "mine"
        diagnostics = {}
        if entry.get("tokenPrice") is not None:
            diagnostics["tokenPrice"] = entry.get("tokenPrice")
        if entry.get("agentInfo") is not None:
            diagnostics["agentInfo"] = entry.get("agentInfo")
        if entry.get("earnings") is not None:
            diagnostics["earnings"] = entry.get("earnings")
        if diagnostics:
            existing["rpcDiagnostics"] = diagnostics
    return reports, meta


def build_capability_bundle_payload(
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("build capability bundle dependencies are required")
    annotate_capability_bundle_payload = dependencies["annotate_capability_bundle_payload"]
    atomic_write_json = dependencies["atomic_write_json"]
    attach_knowledge_to_capability_reports = dependencies["attach_knowledge_to_capability_reports"]
    awp_wallet_snapshot = dependencies["awp_wallet_snapshot"]
    build_skill_inspection_catalog = dependencies["build_skill_inspection_catalog"]
    build_source_inventory = dependencies["build_source_inventory"]
    derive_capability_execution_state = dependencies["derive_capability_execution_state"]
    enrich_reports_with_cached_live_worknets = dependencies["enrich_reports_with_cached_live_worknets"]
    enrich_reports_with_rpc = dependencies["enrich_reports_with_rpc"]
    ensure_user_preferences = dependencies["ensure_user_preferences"]
    fallback_capability_reports = dependencies["fallback_capability_reports"]
    load_cached_live_worknets = dependencies["load_cached_live_worknets"]
    load_cached_skill_inspection_catalog = dependencies["load_cached_skill_inspection_catalog"]
    load_or_build_knowledge_catalog = dependencies["load_or_build_knowledge_catalog"]
    now_iso = dependencies["now_iso"]
    skill_registry_from_inventory = dependencies["skill_registry_from_inventory"]
    state_context = dependencies["state_context"]
    write_reference_export = dependencies["write_reference_export"]

    state = state_context()
    inventory = build_source_inventory()
    preferences = ensure_user_preferences(state)
    wallet = awp_wallet_snapshot()
    knowledge_catalog = load_or_build_knowledge_catalog(state)
    skill_inspections = load_cached_skill_inspection_catalog(state) or build_skill_inspection_catalog(
        state=state,
        inventory=inventory,
    )
    reports = fallback_capability_reports(inventory, state=state)
    cached_live = load_cached_live_worknets(state)
    if cached_live:
        reports, rpc_meta = enrich_reports_with_cached_live_worknets(reports, cached_live)
        source_mode = "live-cache"
    else:
        reports, rpc_meta = enrich_reports_with_rpc(reports, inventory, wallet.get("address"))
        source_mode = "rpc" if rpc_meta.get("used") else "catalog"
    reports = attach_knowledge_to_capability_reports(reports, catalog=knowledge_catalog)
    reports = [
        (
            {
                **item,
                **derive_capability_execution_state(item),
                "resumeStatus": None,
                "resumeStatusDisplay": None,
            }
            if isinstance(item, dict)
            else item
        )
        for item in reports
    ]
    skill_registry = skill_registry_from_inventory(inventory, state=state)
    bundle = annotate_capability_bundle_payload({
        "generatedAt": now_iso(),
        "sourceMode": source_mode,
        "rpc": rpc_meta,
        "inventory": inventory,
        "skillRegistry": skill_registry,
        "skillInspections": skill_inspections["inspections"],
        "userPreferences": preferences,
        "reports": reports,
    })
    atomic_write_json(Path(state["cache"]) / "source-inventory.json", inventory)
    atomic_write_json(Path(state["skills"]) / "install-status.json", skill_registry)
    atomic_write_json(Path(state["cache"]) / "capability-scan.json", bundle)
    write_reference_export("source-inventory.json", inventory)
    write_reference_export("skill-registry.json", skill_registry)
    write_reference_export("skill-inspections.json", skill_inspections)
    write_reference_export("capability-catalog.json", bundle)
    return bundle


def load_cached_capability_bundle_payload(
    state: dict[str, Any],
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if dependencies is None:
        raise ValueError("load cached capability bundle dependencies are required")
    annotate_capability_bundle_payload = dependencies["annotate_capability_bundle_payload"]
    load_json = dependencies["load_json"]

    payload = load_json(Path(state["cache"]) / "capability-scan.json", None)
    if not isinstance(payload, dict):
        return None
    reports = payload.get("reports")
    if not isinstance(reports, list):
        return None
    return annotate_capability_bundle_payload(payload)


def sync_live_worknets_payload(
    state: Optional[dict[str, Any]] = None,
    *,
    agent_address: Optional[str] = None,
    limit: int = 100,
    max_pages: int = 5,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("sync live worknets dependencies are required")
    atomic_write_json = dependencies["atomic_write_json"]
    awp_wallet_snapshot = dependencies["awp_wallet_snapshot"]
    first_present = dependencies["first_present"]
    looks_official_skill_uri = dependencies["looks_official_skill_uri"]
    match_profile_from_rpc = dependencies["match_profile_from_rpc"]
    normalize_worknet_entries = dependencies["normalize_worknet_entries"]
    normalize_worknet_id = dependencies["normalize_worknet_id"]
    now_iso = dependencies["now_iso"]
    official_live_worknets_cache_path = dependencies["official_live_worknets_cache_path"]
    resolution_confidence = dependencies["resolution_confidence"]
    resolve_live_worknet_id = dependencies["resolve_live_worknet_id"]
    rpc_call = dependencies["rpc_call"]
    rpc_result_body = dependencies["rpc_result_body"]
    rpc_try_many = dependencies["rpc_try_many"]
    state_context = dependencies["state_context"]
    trim_output = dependencies["trim_output"]
    write_reference_export = dependencies["write_reference_export"]

    state = state or state_context()
    wallet = awp_wallet_snapshot()
    agent_address = agent_address or wallet.get("address")
    entries: list[dict[str, Any]] = []
    ranked_entries: list[dict[str, Any]] = []
    errors: list[str] = []

    for page in range(1, max_pages + 1):
        response = rpc_call("worknets.list", params={"page": page, "limit": limit})
        if not response.get("ok"):
            errors.append(str(response.get("error")))
            break
        page_entries = normalize_worknet_entries(response.get("body"))
        if not page_entries:
            break
        entries.extend(page_entries)
        if len(page_entries) < limit:
            break

    for page in range(1, max_pages + 1):
        response = rpc_call("worknets.listRanked", params={"page": page, "limit": limit})
        if not response.get("ok"):
            errors.append(f"listRanked: {response.get('error')}")
            break
        page_entries = normalize_worknet_entries(response.get("body"))
        if not page_entries:
            break
        ranked_entries.extend(page_entries)
        if len(page_entries) < limit:
            break

    normalized: list[dict[str, Any]] = []
    for entry in entries:
        profile = match_profile_from_rpc(entry)
        wid, resolved_via, search_attempts = resolve_live_worknet_id(entry, profile, auxiliary_candidates=ranked_entries)
        observed_id = normalize_worknet_id(first_present(entry, ["worknetId", "id", "worknet_id", "subnetId"]))
        observed_name = first_present(entry, ["name"], "Unknown WorkNet")
        observed_status = first_present(entry, ["status", "state"], "unknown")
        item = {
            "worknetId": wid,
            "name": observed_name,
            "symbol": first_present(entry, ["symbol", "tokenSymbol"], "UNKNOWN"),
            "status": observed_status,
            "skillsUri": first_present(entry, ["skillsUri", "skillsURI", "skillUri", "skillURI"]),
            "minStake": first_present(entry, ["minStake", "min_stake"]),
            "officialSkill": False,
            "tokenPrice": None,
            "agentInfo": None,
            "earnings": None,
            "errors": [],
            "resolvedVia": resolved_via,
            "resolutionConfidence": resolution_confidence(resolved_via),
            "searchAttempts": search_attempts,
            "observedName": observed_name,
            "observedStatus": observed_status,
        }
        if observed_id not in (None, "") and str(observed_id) != str(wid):
            item["observedWorknetId"] = observed_id
        if profile is not None and not item["skillsUri"]:
            item["skillsUri"] = profile.get("skills_uri") or profile.get("install_uri")
        if wid is not None:
            worknet_call = rpc_try_many("worknets.get", [{"worknetId": wid}, {"id": wid}])
            if worknet_call.get("ok"):
                raw = rpc_result_body(worknet_call["body"])
                if isinstance(raw, dict):
                    item["name"] = first_present(raw, ["name"], item["name"])
                    item["symbol"] = first_present(raw, ["symbol", "tokenSymbol"], item["symbol"])
                    item["status"] = first_present(raw, ["status", "state"], item["status"])
                    item["minStake"] = first_present(raw, ["minStake", "min_stake"], item["minStake"])
                    owner = first_present(raw, ["owner"])
                    if owner not in (None, ""):
                        item["owner"] = owner
                    created_at = first_present(raw, ["createdAt", "created_at"])
                    if created_at not in (None, ""):
                        item["createdAt"] = created_at
                    lp_pool = first_present(raw, ["lpPool", "lp_pool"])
                    if lp_pool not in (None, ""):
                        item["lpPool"] = lp_pool
            else:
                item["errors"].append(f"worknets.get: {worknet_call.get('error')}")
            skills_call = rpc_try_many("worknets.getSkills", [{"worknetId": wid}, {"id": wid}])
            if skills_call.get("ok"):
                raw = rpc_result_body(skills_call["body"])
                if isinstance(raw, dict):
                    item["skillsUri"] = first_present(raw, ["skillsURI", "skills_uri", "skillsUri", "skillUri"], item["skillsUri"])
                elif isinstance(raw, str) and raw:
                    item["skillsUri"] = raw
            else:
                item["errors"].append(f"getSkills: {skills_call.get('error')}")

            item["officialSkill"] = looks_official_skill_uri(item.get("skillsUri"))

            token_call = rpc_try_many("tokens.getWorknetTokenPrice", [{"worknetId": wid}, {"id": wid}])
            if token_call.get("ok"):
                item["tokenPrice"] = trim_output(rpc_result_body(token_call["body"]))
            else:
                item["errors"].append(f"tokenPrice: {token_call.get('error')}")

            if agent_address:
                agent_call = rpc_try_many(
                    "worknets.getAgentInfo",
                    [{"worknetId": wid, "agent": agent_address}, {"id": wid, "agent": agent_address}],
                )
                if agent_call.get("ok"):
                    item["agentInfo"] = trim_output(rpc_result_body(agent_call["body"]))
                else:
                    item["errors"].append(f"agentInfo: {agent_call.get('error')}")

                earnings_call = rpc_try_many(
                    "worknets.getEarnings",
                    [{"worknetId": wid, "limit": 3}, {"id": wid, "limit": 3}],
                )
                if earnings_call.get("ok"):
                    item["earnings"] = trim_output(rpc_result_body(earnings_call["body"]))
                else:
                    item["errors"].append(f"earnings: {earnings_call.get('error')}")

        item["officialSkill"] = looks_official_skill_uri(item.get("skillsUri"))
        normalized.append(item)

    payload = {
        "generatedAt": now_iso(),
        "agentAddress": agent_address,
        "ok": bool(normalized),
        "errors": errors,
        "entries": normalized,
        "rankedIndexCount": len(ranked_entries),
    }
    atomic_write_json(official_live_worknets_cache_path(state), payload)
    write_reference_export("official-live-worknets.json", payload)
    return payload


def load_cached_live_worknets_payload(
    state: dict[str, Any],
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if dependencies is None:
        raise ValueError("load cached live worknets dependencies are required")
    load_json = dependencies["load_json"]
    official_live_worknets_cache_path = dependencies["official_live_worknets_cache_path"]

    payload = load_json(official_live_worknets_cache_path(state), None)
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        return payload
    return None


def capability_reports_by_worknet_key_payload(
    *,
    state: Optional[dict[str, Any]] = None,
    bundle: Optional[dict[str, Any]] = None,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, dict[str, Any]]:
    if dependencies is None:
        raise ValueError("capability reports by worknet key dependencies are required")
    load_cached_capability_bundle = dependencies["load_cached_capability_bundle"]
    resolve_worknet = dependencies["resolve_worknet"]
    state_context = dependencies["state_context"]

    state = state or state_context()
    bundle = bundle if isinstance(bundle, dict) else load_cached_capability_bundle(state)
    if not isinstance(bundle, dict):
        return {}
    reports: dict[str, dict[str, Any]] = {}
    for item in bundle.get("reports", []):
        if not isinstance(item, dict):
            continue
        profile = (
            resolve_worknet(str(item.get("worknetId") or ""))
            or resolve_worknet(str(item.get("name") or ""))
            or resolve_worknet(str(item.get("symbol") or ""))
        )
        if isinstance(profile, dict) and str(profile.get("key") or "").strip():
            reports[str(profile["key"]).strip()] = item
    return reports
