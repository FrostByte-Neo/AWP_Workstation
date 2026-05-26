"""Work playbook builder."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def build_work_playbook_payload(
    worknet_identifier: str,
    *,
    dependencies: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if dependencies is None:
        raise ValueError("playbook dependencies are required")
    annotate_execution_actions = dependencies["annotate_execution_actions"]
    annotate_playbook_commands = dependencies["annotate_playbook_commands"]
    append_unique_text = dependencies["append_unique_text"]
    atomic_write_json = dependencies["atomic_write_json"]
    build_manifest_commands = dependencies["build_manifest_commands"]
    build_playbook_user_action_details = dependencies["build_playbook_user_action_details"]
    build_skill_inspect_command = dependencies["build_skill_inspect_command"]
    build_skill_sync_command = dependencies["build_skill_sync_command"]
    build_source_inventory = dependencies["build_source_inventory"]
    canonical_worknet_caution_text = dependencies["canonical_worknet_caution_text"]
    canonical_worknet_loop_text = dependencies["canonical_worknet_loop_text"]
    capability_knowledge_caveat = dependencies["capability_knowledge_caveat"]
    compact_knowledge_context = dependencies["compact_knowledge_context"]
    dedupe_action_entries = dependencies["dedupe_action_entries"]
    dedupe_playbook_commands = dependencies["dedupe_playbook_commands"]
    derive_playbook_execution_state = dependencies["derive_playbook_execution_state"]
    ensure_user_preferences = dependencies["ensure_user_preferences"]
    humanize_playbook_confirmation_item = dependencies["humanize_playbook_confirmation_item"]
    humanize_playbook_failure_mode = dependencies["humanize_playbook_failure_mode"]
    humanize_playbook_goal = dependencies["humanize_playbook_goal"]
    humanize_playbook_loop = dependencies["humanize_playbook_loop"]
    humanize_playbook_role = dependencies["humanize_playbook_role"]
    humanize_playbook_success_metric = dependencies["humanize_playbook_success_metric"]
    inspect_skill_runtime = dependencies["inspect_skill_runtime"]
    knowledge_action_description = dependencies["knowledge_action_description"]
    knowledge_context_for_worknet = dependencies["knowledge_context_for_worknet"]
    knowledge_refresh_action_description = dependencies["knowledge_refresh_action_description"]
    knowledge_related_reference_highlights = dependencies["knowledge_related_reference_highlights"]
    knowledge_related_source_highlights = dependencies["knowledge_related_source_highlights"]
    knowledge_source_action_description = dependencies["knowledge_source_action_description"]
    knowledge_source_labels_text = dependencies["knowledge_source_labels_text"]
    knowledge_worknet_metadata = dependencies["knowledge_worknet_metadata"]
    load_or_build_knowledge_catalog = dependencies["load_or_build_knowledge_catalog"]
    now_iso = dependencies["now_iso"]
    official_remote_manifest = dependencies["official_remote_manifest"]
    resolve_skill_root = dependencies["resolve_skill_root"]
    resolve_worknet = dependencies["resolve_worknet"]
    rewrite_command_for_skill_root = dependencies["rewrite_command_for_skill_root"]
    skill_registry_from_inventory = dependencies["skill_registry_from_inventory"]
    state_context = dependencies["state_context"]

    profile = resolve_worknet(worknet_identifier)
    if profile is None:
        raise ValueError(f"unknown worknet: {worknet_identifier}")
    state = state_context()
    preferences = ensure_user_preferences(state)
    knowledge_catalog = load_or_build_knowledge_catalog(state)
    knowledge_context = compact_knowledge_context(
        knowledge_context_for_worknet(knowledge_catalog, str(profile.get("key") or ""))
    )
    knowledge_reference_highlights = knowledge_related_reference_highlights(
        knowledge_catalog,
        knowledge_context,
    ) if isinstance(knowledge_context, dict) else []
    knowledge_source_highlights = knowledge_related_source_highlights(
        knowledge_catalog,
        knowledge_context,
    ) if isinstance(knowledge_context, dict) else []
    knowledge_caveat = capability_knowledge_caveat(knowledge_context, knowledge_source_highlights)
    inventory = build_source_inventory()
    local_sources = {item["key"]: item for item in inventory.get("localSources", [])}
    local_source = local_sources.get(profile.get("local_source_key"))
    resolved_root, _resolved_origin = resolve_skill_root(profile["key"], inventory=inventory, state=state)
    skill_registry = {
        item["key"]: item for item in skill_registry_from_inventory(inventory, state=state)
    }
    skill_record = skill_registry.get(profile["key"], {})
    inspection = inspect_skill_runtime(profile["key"], state=state, inventory=inventory)
    inspection_status = str(inspection.get("status", "missing"))
    manifest = official_remote_manifest(profile["key"])
    worknet_metadata = knowledge_worknet_metadata(
        worknet_key=profile["key"],
        worknet_id=profile.get("worknet_id"),
        source_keys=profile.get("source_keys", []),
        install_uri=profile.get("install_uri") or profile.get("skills_uri"),
        capability_report=None,
    )
    commands: list[dict[str, Any]] = []
    install_command = (
        build_skill_sync_command(skill_record)
        if isinstance(skill_record, dict) and skill_record.get("status") == "official-remote"
        else None
    )
    if install_command is not None:
        commands.append(install_command)
    manifest_bootstrap_commands = build_manifest_commands(
        profile["key"],
        state=state,
        skill_root=resolved_root,
        section="bootstrapCommands",
    )
    manifest_inspection_commands = build_manifest_commands(
        profile["key"],
        state=state,
        skill_root=resolved_root,
        section="inspectionCommands",
    )
    if skill_record.get("installUri") or profile.get("install_uri"):
        commands.append(build_skill_inspect_command(profile["key"]))
    if inspection_status != "ready":
        commands.extend(manifest_bootstrap_commands)
    commands.extend(manifest_inspection_commands)
    local_root = resolved_root if isinstance(resolved_root, Path) else None
    if local_root is not None:
        commands.extend(
            rewrite_command_for_skill_root(command, skill_root=local_root)
            for command in list(profile.get("commands", []))
        )
    remediation_commands = inspection.get("remediationCommands", []) if isinstance(inspection, dict) else []
    if inspection_status != "ready" and isinstance(remediation_commands, list):
        commands.extend(remediation_commands)
    commands = dedupe_playbook_commands(commands)
    commands = annotate_playbook_commands(commands, inspection_status=inspection_status)
    success_metrics_raw = [str(item) for item in profile.get("success_metrics", []) if str(item).strip()]
    failure_modes_raw = [str(item) for item in profile.get("failure_modes", []) if str(item).strip()]
    human_confirmations_raw = [str(item) for item in profile.get("human_confirmations", []) if str(item).strip()]
    success_metrics = [humanize_playbook_success_metric(item) for item in success_metrics_raw]
    failure_modes = [humanize_playbook_failure_mode(item) for item in failure_modes_raw]
    human_confirmations = [humanize_playbook_confirmation_item(item) for item in human_confirmations_raw]
    runtime_spec_state = str(worknet_metadata.get("runtimeSpecState") or "").strip()
    runtime_spec_state_display = str(worknet_metadata.get("runtimeSpecStateDisplay") or "").strip()
    canonical_worknet_id = str(worknet_metadata.get("canonicalWorknetId") or "").strip()
    min_stake_hint_display = str(worknet_metadata.get("minStakeHintDisplay") or "").strip()
    if runtime_spec_state == "runtime-doc-available":
        append_unique_text(
            failure_modes,
            "Runtime spec is available, but checkout and inspection still need review."
            + (f" Canonical ID: {canonical_worknet_id}." if canonical_worknet_id else "")
        )
        append_unique_text(
            human_confirmations,
            f"Confirm {profile['name']} runtime inspection before execution."
            + (f" Live minStake hint: {min_stake_hint_display}." if min_stake_hint_display else "")
        )
    elif runtime_spec_state == "thin-repo-only":
        append_unique_text(
            failure_modes,
            "Live ID is known, but the official runtime repository is still thin.",
        )
        append_unique_text(
            human_confirmations,
            f"Confirm {profile['name']} skill contents before relying on README or SKILL.md guidance.",
        )
    elif runtime_spec_state == "thin-repo-plus-hub":
        append_unique_text(
            failure_modes,
            "Live ID is known, but runtime details still depend on community hub context.",
        )
        append_unique_text(
            human_confirmations,
            f"Confirm {profile['name']} community hub context before runtime execution.",
        )
    if isinstance(knowledge_context, dict):
        label = str(knowledge_context.get("label") or profile.get("name") or profile.get("key") or "       WorkNet").strip()
        source_labels = knowledge_source_labels_text(
            knowledge_source_highlights,
            affected_only=True,
            limit=3,
        )
        if knowledge_caveat:
            append_unique_text(
                failure_modes,
                (
                    f"{label} has changed source context ({source_labels}); review the playbook before execution."
                    if source_labels
                    else f"{label} has changed knowledge context; review the playbook before execution."
                ),
            )
            append_unique_text(
                human_confirmations,
                (
                    f"Confirm the {label} playbook after reviewing changed sources: {source_labels}."
                    if source_labels
                    else f"Confirm the {label} playbook after reviewing changed knowledge context."
                ),
            )
    playbook = {
        "generatedAt": now_iso(),
        "worknetKey": profile["key"],
        "worknetId": profile["worknet_id"],
        "goal": humanize_playbook_goal(profile["key"], str(profile["goal"])),
        "goalRaw": profile["goal"],
        "role": humanize_playbook_role(str(profile["recommended_role"])),
        "roleRaw": profile["recommended_role"],
        "loop": humanize_playbook_loop(profile["key"], str(profile["loop"])),
        "loopRaw": profile["loop"],
        "goalNarrative": knowledge_context.get("summary") if isinstance(knowledge_context, dict) else None,
        "loopNarrative": canonical_worknet_loop_text(profile["key"]),
        "riskNarrative": canonical_worknet_caution_text(profile["key"]),
        "knowledgeCaveat": knowledge_caveat,
        "knowledgeContext": knowledge_context,
        "knowledgeReferenceHighlights": knowledge_reference_highlights,
        "knowledgeSourceHighlights": knowledge_source_highlights,
        "knowledgeActions": [
            {
                "label": f"Review {knowledge_context.get('label') or profile['name']} context",
                "description": knowledge_action_description(knowledge_context),
                "command": knowledge_context.get("queryCommand"),
            },
            {
                "label": f"Refresh {knowledge_context.get('label') or profile['name']} context",
                "description": knowledge_refresh_action_description(knowledge_context),
                "command": knowledge_context.get("primaryCommand"),
            },
        ] if isinstance(knowledge_context, dict) else [],
        "requiredSkill": profile["name"],
        "requiredRuntime": manifest.get("runtimeName"),
        "requiredSkillInstallUri": profile.get("install_uri"),
        "requiredSkillLocalPath": local_source.get("path") if isinstance(local_source, dict) else None,
        "requiredSkillStatus": skill_record.get("status"),
        "skillInspection": inspection,
        "executionModel": "probe_then_single_primary_work",
        "commands": commands,
        "successMetrics": success_metrics,
        "successMetricsRaw": success_metrics_raw,
        "failureModes": failure_modes,
        "failureModesRaw": failure_modes_raw,
        "humanConfirmations": human_confirmations,
        "humanConfirmationsRaw": human_confirmations_raw,
        "preferencesSnapshot": preferences,
        "recoveryPath": str(Path(state["playbooks"]) / f"{profile['key']}.json"),
        "stateRoot": state["root"],
        "progress": "[3/5] Playbook build",
    }
    if knowledge_source_highlights:
        playbook["knowledgeActions"].extend(
            {
                "label": f"Review source {item.get('label') or item.get('key')}",
                "description": knowledge_source_action_description(item),
                "command": item.get("queryCommand"),
            }
            for item in knowledge_source_highlights[:3]
            if isinstance(item, dict) and (item.get("queryCommand"))
        )
        for item in knowledge_source_highlights[:2]:
            if not isinstance(item, dict):
                continue
            primary_command = str(item.get("primaryCommand") or "").strip()
            query_command = str(item.get("queryCommand") or "").strip()
            if primary_command and primary_command != query_command:
                playbook["knowledgeActions"].append(
                    {
                        "label": f"Refresh source {item.get('label') or item.get('key')}",
                        "description": f"Refresh {item.get('label') or item.get('key')} before updating the playbook.",
                        "command": primary_command,
                    }
                )
    playbook["knowledgeActions"] = dedupe_action_entries(playbook["knowledgeActions"])
    playbook_state = derive_playbook_execution_state(
        profile,
        inspection_status=inspection_status,
        knowledge_caveat=knowledge_caveat,
    )
    playbook.update(
        {
            "resumeStatus": None,
            "resumeStatusDisplay": None,
            "executionState": playbook_state.get("executionState"),
            "executionStateDisplay": playbook_state.get("executionStateDisplay"),
            "executionHeadline": playbook_state.get("executionHeadline"),
        }
    )
    user_action_details = build_playbook_user_action_details(playbook)
    user_action_details = annotate_execution_actions(user_action_details)
    playbook["primaryUserAction"] = user_action_details[0]["label"] if user_action_details else None
    playbook["primaryUserActionDisplay"] = user_action_details[0]["displayLabel"] if user_action_details else None
    playbook["primaryUserActionCommand"] = user_action_details[0]["command"] if user_action_details else None
    playbook["userActionDetails"] = user_action_details
    slug = profile["key"]
    atomic_write_json(Path(state["playbooks"]) / f"{slug}.json", playbook)
    atomic_write_json(Path(state["playbooks"]) / "last-selected.json", playbook)
    return playbook
