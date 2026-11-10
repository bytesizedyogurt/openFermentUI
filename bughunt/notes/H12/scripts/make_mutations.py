"""Write bughunt/notes/H12/mutations.json: H12's mutations, one small realistic break each, with the tests that
should catch it (the module's own test file and the tests that import the module, narrowed where a file is long)."""
import json
from pathlib import Path

T = lambda *fs: [f"tests/{f}" for f in fs]  # noqa: E731
M = []


def m(id_, target, file, old, new, tests, why, **kw):
    M.append({"id": id_, "target": target, "file": file, "old": old, "new": new, "tests": tests, "why": why, **kw})


BASIS = T("test_basis.py", "test_estimates.py", "test_measurements.py", "test_finite_inputs.py", "test_params.py")
# 1. basis.basis_provenance and the provenance readers
m("M01", "basis.basis_provenance", "openferment_core/basis.py",
  '    if found != "assumed" and any(is_measurement(i.source) for i in basis.inputs):\n        return "measured"\n',
  "", BASIS, "a run on a reading never reads measured")
m("M02", "basis.basis_provenance", "openferment_core/basis.py",
  "    if any(i.source.kind in ASSUMED_KINDS for i in basis.inputs):\n        return \"assumed\"",
  "    if any(i.source.kind == \"assumption\" for i in basis.inputs):\n        return \"assumed\"",
  BASIS, "a model's estimate no longer makes a value assumed (only a person's assumption does)")
m("M03", "basis.basis_provenance", "openferment_core/basis.py",
  '    if found != "assumed" and any(is_measurement(i.source) for i in basis.inputs):',
  '    if found == "computed" and any(is_measurement(i.source) for i in basis.inputs):',
  BASIS, "a reading beside a weaker record leaves the weaker class (ADR-006 says measured)")
m("M04", "basis._provenance_of", "openferment_core/basis.py",
  "    if item is None:\n        return _UNKNOWN", "    if item is None:\n        return \"computed\"",
  BASIS, "a record or artifact the caller cannot find reads as computed")
m("M05", "basis.is_measurement", "openferment_core/basis.py",
  '    return (source.kind == "deposition" and bool(READING_REF.fullmatch(source.id or ""))\n'
  '            and bool(_MEASURED.match(source.note or "")))',
  '    return (source.kind == "deposition" and bool(READING_REF.fullmatch(source.id or "")))',
  BASIS + T("test_fermos.py", "test_exports.py", "test_comparisons.py"),
  "a deposition source naming a dep/entry id reads as a measurement whatever its note says")
m("M06", "basis.origin_of", "openferment_core/basis.py",
  '    return Origin(kind=kind, ref=source.id, by=source.by, at=stamped.group(1) if stamped else None,',
  '    return Origin(kind=kind, ref=source.id, by=source.by, at=None,',
  BASIS + T("test_runs.py"), "an origin read back from a basis source loses the day stamped in its note")
m("M07", "basis.override_of", "openferment_core/basis.py",
  "    if q.unit != unit:\n        raise InputRefused(", "    if False:\n        raise InputRefused(",
  BASIS, "a value in another unit than its parameter's is taken as if it were in the parameter's")
m("M08", "basis.override_of", "openferment_core/basis.py",
  "    if not (origin.at or \"\").strip():\n        raise InputRefused(",
  "    if False:\n        raise InputRefused(", BASIS, "a value that does not say when it was set is taken")
# estimate_in / refuse_estimates
EST = T("test_estimates.py", "test_biorepo.py", "test_project_state.py", "test_extract.py", "test_writes.py")
m("M09", "basis.estimate_in", "openferment_core/basis.py",
  '        if value.get("provenance") == "assumed":\n            return f"{path}.provenance" if path else "provenance"\n',
  "", EST, "a value calling itself assumed enters a record store")
m("M10", "basis.estimate_in", "openferment_core/basis.py",
  "    if isinstance(value, (list, tuple)):\n        for n, v in enumerate(value):",
  "    if False:\n        for n, v in enumerate(value):",
  EST, "an estimate inside a list (a candidate list, a deposition's entries) is not found")
m("M11", "extract._put refusal", "openferment_core/extract.py",
  '    refuse_estimates(result, "the candidates store")\n', "", EST, "the candidates store keeps an estimate")
m("M12", "project_state.put refusal", "openferment_core/project_state.py",
  "            refuse_estimates(value, f\"a project's {kind}\")", "            pass",
  EST, "a project's depositions and measured evidence keep an estimate")
m("M13", "biorepo.write refusal", "openferment_core/biorepo.py",
  '        refuse_estimates(decision, "BioRepo")', "        pass", EST, "BioRepo keeps a decision carrying an estimate")
# 2. the unit conversion
UNITS = T("test_units.py", "test_units_minus.py", "test_measurements.py", "test_biorepo.py")
m("M14", "units.convert", "openferment_core/units.py",
  '    return (base - ut.get("offset", 0)) / ut["factor"]', '    return base / ut["factor"]',
  UNITS, "an affine unit's offset is dropped on the way out (°C, °F)")
m("M15", "units.convert", "openferment_core/units.py",
  '    if uf["family"] != ut["family"]:\n        raise UnitError(',
  '    if False:\n        raise UnitError(', UNITS, "a conversion across families goes through")
m("M16", "units.quantity_equals", "openferment_core/units.py",
  "    return abs(av - bv) / abs(bv) <= tolerance_pct / 100", "    return abs(av - bv) / abs(bv) <= tolerance_pct",
  UNITS + T("test_anchor.py", "test_witness.py"), "the tolerance is read as a fraction a hundred times wider")
# 3. the project scoping in api.py
PROJ = T("test_projects.py", "test_openapi.py", "test_events.py", "test_route_models.py")
m("M17", "api.act_in_the_named_project", "openferment_core/api.py",
  "    if not known:\n        return JSONResponse(status_code=404,", "    if False:\n        return JSONResponse(status_code=404,",
  PROJ, "a request naming a project the database does not hold goes on in it")
m("M18", "api.act_in_the_named_project", "openferment_core/api.py",
  "    named = request.headers.get(projects.HEADER) or request.query_params.get(projects.QUERY)",
  "    named = request.query_params.get(projects.QUERY) or request.headers.get(projects.HEADER)",
  PROJ, "?project= wins over the header when both name a project")
m("M19", "api.act_in_the_named_project", "openferment_core/api.py",
  "    if not projects.valid_id(named):\n        return JSONResponse(status_code=422,",
  "    if False:\n        return JSONResponse(status_code=422,", PROJ, "a malformed project id goes to the database")
# 4. engine/runs.keep_run
RUNS = T("test_runs.py", "test_engines.py", "test_engine_diagnostics.py", "test_proforma_runs.py", "test_events.py")
RUNS_K = ["-k", "keep or run or receipt or held or twice or row"]
m("M20", "runs.keep_run", "openferment_core/engine/runs.py",
  "    if held is not None and (held.status == \"refused\" or held.sff is not None or held.sffRefused is not None):\n"
  "        return report(run_id)\n", "", RUNS, "the same run kept twice is written and said again")
m("M21", "runs.keep_run", "openferment_core/engine/runs.py",
  "    first, when, asked = (held.by, held.at, held.scenarioId) if held is not None else (who, _now(), scenario_id)",
  "    first, when, asked = (who, _now(), scenario_id)", RUNS,
  "a held row with neither file nor words is rewritten under the second asker's name, time and scenario")
m("M22", "runs.keep_run", "openferment_core/engine/runs.py",
  "    kept = EngineRun(**base, status=\"done\", provenance=art.provenance,",
  "    kept = EngineRun(**base, status=\"done\", provenance=\"computed\",", RUNS,
  "a run row says computed whatever its artifact's provenance")
m("M23", "runs.keep_run", "openferment_core/engine/runs.py",
  "    if art is not None and (art.id, art.tool, art.toolVersion) != (run_id, tool, version):",
  "    if False:", RUNS, "an artifact of another basis is kept as this run's")
m("M24", "runs.keep_run", "openferment_core/engine/runs.py",
  "    reported = (held.diagnostics if held is not None and held.diagnostics else",
  "    reported = (None if False else", RUNS, "a held row's own diagnostics give way to the second computation's")
# 5. the key override in llm.py and its middleware
KEY = T("test_key_override.py", "test_llm.py", "test_request_guard.py")
m("M25", "llm._default_client", "openferment_core/llm.py",
  '    key = _REQUEST_KEY.get() or os.environ.get("ANTHROPIC_API_KEY")',
  '    key = os.environ.get("ANTHROPIC_API_KEY") or _REQUEST_KEY.get()', KEY,
  "core/.env's key wins over the key a request names")
m("M26", "api.use_the_key_a_request_names", "openferment_core/api.py",
  "    if project is not None:\n        await db.arun(audit.add(project,", "    if False:\n        await db.arun(audit.add(project,",
  KEY, "no audit row says an override was used")
m("M27", "api.use_the_key_a_request_names", "openferment_core/api.py",
  '                                detail={"override": True}))',
  '                                detail={"override": True, "key": named[-4:]}))', KEY,
  "the audit row keeps the key's last four characters")
m("M28", "llm.request_key", "openferment_core/llm.py",
  '    token = _REQUEST_KEY.set((key or "").strip() or None)', '    token = _REQUEST_KEY.set(key)', KEY,
  "a whitespace key is held as a key (the middleware refuses it first)")
# 6. guard.py's check
GUARD = T("test_request_guard.py", "test_key_override.py", "test_projects.py")
m("M29", "guard.same_site", "openferment_core/guard.py",
  "    return origin_port == h[1] if h[1] is not None else origin_port in DEFAULT_PORTS.values()",
  "    return True", GUARD, "another port on the same host is the same site")
m("M30", "guard.refusal", "openferment_core/guard.py",
  "        forwarded and answers_to(hostname(forwarded)) and same_site(origin, forwarded)",
  "        forwarded and same_site(origin, forwarded)", GUARD, "X-Forwarded-Host may name any host")
m("M31", "guard.key_refusal", "openferment_core/guard.py",
  '    if FUNNEL in headers:\n        return "a request through Tailscale Funnel comes from the public internet and may not name a key"',
  '    if False:\n        return "a request through Tailscale Funnel comes from the public internet and may not name a key"',
  GUARD, "a key may be named through Funnel")
m("M32", "guard.answers_to", "openferment_core/guard.py",
  '    return "." not in host or host.endswith(OWN_SUFFIXES)', '    return "." not in host or host.endswith((*OWN_SUFFIXES, ".net"))',
  GUARD, "any .net name is the owner's")
# 7. measurements' lookup
MEAS = T("test_measurements.py", "test_basis.py", "test_finite_inputs.py")
m("M33", "measurements._held_to_rules", "openferment_core/measurements.py",
  "    if entry.get(\"confirmed\") is not True:\n        raise MeasurementRefused(",
  "    if entry.get(\"confirmed\") is False:\n        raise MeasurementRefused(", MEAS,
  "a reading with no confirmed field at all is taken")
m("M34", "measurements._held_to_rules", "openferment_core/measurements.py",
  "    if (origin.at or \"\").strip() and _time(origin.at) != when:", "    if False:", MEAS,
  "a value naming another time than its reading's is taken")
m("M35", "measurements._held_to_rules", "openferment_core/measurements.py",
  "    if not _number(q.value) or float(q.value) != float(own) or q.unit != own_unit:",
  "    if not _number(q.value) or q.unit != own_unit:", MEAS, "a value sent beside a reading need not be the reading's")
m("M36", "measurements._held_to_rules", "openferment_core/measurements.py",
  "        if not math.isfinite(set_to):\n            raise MeasurementRefused(",
  "        if False:\n            raise MeasurementRefused(", MEAS, "a conversion to an infinite number is taken")
m("M37", "measurements.corrected_by", "openferment_core/measurements.py",
  "    return str(later[-1].get(\"id\")) if later else None", "    return str(later[0].get(\"id\")) if later else None",
  MEAS, "the first correction is named in place of the latest")
# 8. validate.py's number detection
VAL = T("test_validate.py", "test_number_rule_fold.py", "test_number_rule_chemistry.py", "test_number_rule_kinetics.py",
        "test_number_rule_steps.py", "test_postdoc_agent.py", "test_phase5_review.py")
m("M38", "validate.find_number", "openferment_core/validate.py",
  "    if m := _MAGNITUDE.search(masked):\n        return m.group(0)\n", "", VAL, "magnitude words pass the number rule")
m("M39", "validate.find_number", "openferment_core/validate.py",
  "    if m := _WORD_NUMBER.search(masked):\n        return m.group(0)\n", "", VAL, "word numbers pass the number rule")
m("M40", "validate.validate_plan", "openferment_core/validate.py",
  "        def reject(why: str) -> None:\n            out.rejected += 1\n",
  "        def reject(why: str) -> None:\n            out.rejected += 0\n", VAL, "a dropped claim is not counted")
m("M41", "tools.numbers_in", "openferment_core/tools/__init__.py",
  "    elif isinstance(value, list):\n        for n, v in enumerate(value):\n            found += numbers_in(v, f\"{path}[{n}]\", quantities)",
  "    elif isinstance(value, list):\n        pass", T("test_tools.py", "test_module_tools.py", "test_finite_inputs.py", "test_mcp.py"),
  "a number inside a list in a tool input passes")
# 9. spend.py's caps
SPEND = T("test_spend.py", "test_llm.py", "test_ready.py", "test_phase3_review.py")
m("M42", "spend._reserve", "openferment_core/spend.py",
  "        if spent + reserved + projected_usd > cap:", "        if spent + projected_usd > cap:", SPEND,
  "what is reserved and unsettled is left out of the cap")
m("M43", "spend._setting", "openferment_core/spend.py",
  "    if value < 0:\n        raise BudgetSettingInvalid(", "    if False:\n        raise BudgetSettingInvalid(", SPEND,
  "a negative budget is taken")
m("M44", "spend._day_state", "openferment_core/spend.py",
  '        elif r.state == "reserved" and r.expires_at is not None and r.expires_at > now:',
  '        elif r.state == "reserved" and r.expires_at is not None and r.expires_at < now:', SPEND,
  "a live reservation holds nothing and an expired one holds")
m("M45", "spend._reserve", "openferment_core/spend.py",
  "        await db.lock(s, \"spend\", day.isoformat())\n        now = datetime.now(timezone.utc)\n        # An abandoned",
  "        now = datetime.now(timezone.utc)\n        # An abandoned", SPEND, "check and hold are no longer one step")
# 10. the registry's load refusals
REG = T("test_engines.py", "test_boundaries.py")
REG_K = ["-k", "registry or registered or entry or load or engine_name or set_aside or heavy or declar or names_itself or discover"]
m("M46", "registry._why_not", "openferment_core/engine/registry.py",
  "    if own != name:\n        return f\"the object at {entry} names itself", "    if False:\n        return f\"the object at {entry} names itself",
  REG, "an object whose own name differs from its entry point's is used")
m("M47", "registry._load", "openferment_core/engine/registry.py",
  "            wrong = _imported_in_service(obj, set(sys.modules) - before)", "            wrong = []",
  REG, "an engine whose import brings its heavy modules into the service is used")
m("M48", "registry._discover", "openferment_core/engine/registry.py",
  "            if len(core) != 1:", "            if len(core) > 1:", REG,
  "two outside packages registering one name: the first is used")
m("M49", "registry._why_not", "openferment_core/engine/registry.py",
  "    if worker is None and heavy:\n        return (", "    if False:\n        return (", REG,
  "an engine declaring heavy modules and no worker is used")
# 11. conform's checks
CONF = T("test_engines.py", "test_engine_diagnostics.py", "test_measurements.py", "test_train.py", "test_pureos_build_tool.py")
CONF_K = ["-k", "not sigterm_ends_the_command"]
m("M50", "conform._replayed (check 4)", "openferment_core/engine/conform.py",
  "        four = (bool(r.withinTolerance or r.identical),", "        four = (True,", CONF + CONF_K,
  "check 4 holds whatever the replay says")
m("M51", "conform._run_twice (check 3)", "openferment_core/engine/conform.py",
  "        ok = a.id == b.id and rows == 1 and a.status == \"done\" and a.engine == engine.name and keyed and diagnosed",
  "        ok = a.id == b.id and a.status == \"done\" and a.engine == engine.name and keyed and diagnosed",
  CONF + CONF_K, "check 3 holds when a run asked twice is two rows")
m("M52", "conform._bare_number (check 1)", "openferment_core/engine/conform.py",
  "    ok = codes == [422, 422] and bool(tool.error) and not calls and not kept",
  "    ok = codes == [422, 422] and bool(tool.error) and not kept", CONF + CONF_K,
  "check 1 holds when the engine was reached")
m("M53", "conform._replayed (check 5)", "openferment_core/engine/conform.py",
  "        return four, (bool(run.sff.valid and run.sff.score is not None),",
  "        return four, (run.sff.score is not None,", CONF + CONF_K, "check 5 holds on an SFF file that is not valid")
m("M54", "conform._asked_by (check 8)", "openferment_core/engine/conform.py",
  "    ok = who == by and run.by == by", "    ok = run.by == by", CONF + CONF_K,
  "check 8 holds whoever the row's created_by is")
# 12. the SFF import-url address check
URL = T("test_sff_url.py", "test_collectors.py", "test_intake_sources.py", "test_intake.py")
m("M55", "collectors.refused_class", "openferment_core/literature/collectors.py",
  '    ("is_private", "a private address"),\n', "", URL, "a private address is fetched")
m("M56", "collectors.public_addresses", "openferment_core/literature/collectors.py",
  "    for address in found:\n        why = refused_class(address)", "    for address in found[:1]:\n        why = refused_class(address)",
  URL, "a name resolving to a public and a private address passes on the first")
m("M57", "collectors.refused_class", "openferment_core/literature/collectors.py",
  "    seen = _v4(address)\n", "    seen = address\n", URL, "an IPv4-mapped IPv6 loopback is fetched")
m("M58", "collectors._literal", "openferment_core/literature/collectors.py",
  "    try:\n        return ipaddress.IPv4Address(socket.inet_aton(host))\n    except (OSError, ValueError):\n        return None",
  "    return None", URL, "a short numeric host (127.1, 2130706433) is resolved as a name")
# 13. project_state.deposition_refusal
DEP = T("test_project_state.py", "test_measurements.py", "test_runbooks.py", "test_route_models.py")
m("M59", "project_state.deposition_refusal", "openferment_core/project_state.py",
  "        if old.get(\"confirmed\") is True and new.get(\"confirmed\") is not True:",
  "        if False:", DEP, "a confirmed reading may be unconfirmed")
m("M60", "project_state.deposition_refusal", "openferment_core/project_state.py",
  "    if before.get(\"reconciliation\") is not None and before.get(\"reconciliation\") != after.get(\"reconciliation\"):",
  "    if False:", DEP, "a reconciliation may be rewritten")
m("M61", "project_state.deposition_refusal", "openferment_core/project_state.py",
  "        if (before.get(\"sampleTimes\") or {}) != (after.get(\"sampleTimes\") or {}):",
  "        if False:", DEP, "a closed deposition's sample times may move")
m("M62", "project_state._appended", "openferment_core/project_state.py",
  "    if sent[: len(held)] != held:\n        return f\"{item_id} keeps its {what}s in the order",
  "    if False:\n        return f\"{item_id} keeps its {what}s in the order", DEP, "readings may be reordered")
m("M63", "project_state.deposition_refusal", "openferment_core/project_state.py",
  "        if before.get(\"operatorId\") != after.get(\"operatorId\"):", "        if False:", DEP,
  "a closed deposition's operator may change")
# 14. the migrations' head check
MIG = T("test_db.py", "test_ready.py", "test_import_alpha1.py")
m("M64", "ready.check_data", "openferment_core/ready.py",
  "    if at != head:\n        return Check(\"data\", \"fail\"", "    if False:\n        return Check(\"data\", \"fail\"", MIG,
  "a database behind the newest schema reads ok")
m("M65", "ready.check_literature", "openferment_core/ready.py",
  "    if at != head or width is None:", "    if width is None:", MIG,
  "the kit's schema behind its newest revision reads ok")
m("M66", "import_alpha1._write", "openferment_core/import_alpha1.py",
  "        if at != head:\n            raise ImportRefused(", "        if False:\n            raise ImportRefused(", MIG,
  "an import into a database behind the newest schema goes on")
m("M67", "migrations.upgrade", "openferment_core/migrations.py",
  '    command.upgrade(_kit_config(target), "head")', '    command.upgrade(_kit_config(target), "-1") if False else command.upgrade(_kit_config(target), "0005")',
  MIG, "the kit's schema is migrated one revision short of its head")
# 15. weakest_provenance and biorepo.provenance_of
m("M68", "models.weakest_provenance", "openferment_core/models.py",
  '    return PROVENANCE_ORDER[worst] if worst < len(PROVENANCE_ORDER) else "assumed"',
  '    return PROVENANCE_ORDER[worst] if worst < len(PROVENANCE_ORDER) else "unverified"', BASIS + T("test_postdoc_agent.py"),
  "an unknown class reads as unverified")
m("M69", "biorepo.provenance_of", "openferment_core/biorepo.py",
  '        return "gold" if _is_gold(d) else "verified"', '        return "verified" if _is_gold(d) else "gold"',
  T("test_biorepo.py", "test_writes.py", "test_import_alpha1.py", "test_evidence_pool.py"), "gold and verified swapped")
m("M70", "biorepo.provenance_of", "openferment_core/biorepo.py",
  '    if d.status == "verified":\n        return "gold" if _is_gold(d) else "verified"\n    return "unverified"',
  '    if d.status in ("verified", "corrected"):\n        return "gold" if _is_gold(d) else "verified"\n    return "unverified"',
  T("test_biorepo.py", "test_writes.py", "test_import_alpha1.py", "test_evidence_pool.py"),
  "a corrected decision a reviewer left unverified reads verified")
# 16. the event stream's project filter
m("M71", "events.publish project", "openferment_core/events.py", None, None, T("test_events.py"), "placeholder", skip=True)

Path("/home/user/openFermentUI/bughunt/notes/H12/mutations.json").write_text(json.dumps([x for x in M if not x.get("skip")], indent=1))
print(len([x for x in M if not x.get("skip")]))
