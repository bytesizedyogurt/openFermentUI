"""Malformed and boundary requests at the engine doors: POST /api/engines/{name}/run, GET
/api/engines/{name}/parameters and the engine tools at POST /api/tools/{name}. Each case prints its
status, the head of its answer, and how many runs rows the project gained.
usage: doors.py ORIGIN PROJECT"""
import json, sys
import httpx

O, P = sys.argv[1], sys.argv[2]
c = httpx.Client(trust_env=False, timeout=120, headers={"X-OpenFerment-Project": P})
A = {"kind": "person-assumption", "by": "H1", "at": "2026-11-10"}


def q(v, unit="placeholder-unit", **extra):
    return {"value": v, "unit": unit, "origin": {**A, **extra.pop("origin", {})}, **extra}


def runs():
    return len(c.get(f"{O}/api/runs").json())


def case(label, method, path, body=None, raw=None, params=None):
    before = runs()
    if raw is not None:
        r = c.request(method, O + path, content=raw, headers={"content-type": "application/json"}, params=params)
    else:
        r = c.request(method, O + path, json=body, params=params)
    gained = runs() - before
    text = r.text.replace("\n", " ")
    print(f"{label:<58} {r.status_code}  +{gained} rows  {text[:230]}")
    return r


R = "/api/engines/mirror/run"
base = {"thing": "reflect", "by": "H1"}
case("bare number for a quantity", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": 1.5}]})
case("stray field", "POST", R, {**base, "n": 3})
case("NaN literal", "POST", R, raw='{"thing":"reflect","by":"H1","inputs":[{"name":"placeholder-a","quantity":{"value":NaN,"unit":"placeholder-unit","origin":{"kind":"person-assumption","by":"H1","at":"2026-11-10"}}}]}')
case("Infinity literal", "POST", R, raw='{"thing":"reflect","by":"H1","inputs":[{"name":"placeholder-a","quantity":{"value":Infinity,"unit":"placeholder-unit","origin":{"kind":"person-assumption","by":"H1","at":"2026-11-10"}}}]}')
case("1e999", "POST", R, raw='{"thing":"reflect","by":"H1","inputs":[{"name":"placeholder-a","quantity":{"value":1e999,"unit":"placeholder-unit","origin":{"kind":"person-assumption","by":"H1","at":"2026-11-10"}}}]}')
case("integer of 400 digits", "POST", R, raw='{"thing":"reflect","by":"H1","inputs":[{"name":"placeholder-a","quantity":{"value":' + "9" * 400 + ',"unit":"placeholder-unit","origin":{"kind":"person-assumption","by":"H1","at":"2026-11-10"}}}]}')
case("value true", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": q(True)}]})
case("low true", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": q(1.0, low=True)}]})
case("low and high on a contract run", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": q(1.0, low=0.5, high=2.0)}]})
case("basis on a contract run", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": q(1.0, basis="dry")}]})
case("unknown key", "POST", R, {**base, "inputs": [{"name": "placeholder-c", "quantity": q(1.0)}]})
case("key set twice", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": q(1.0)}, {"name": "placeholder-a", "quantity": q(2.0)}]})
case("wrong unit", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": q(1.0, unit="other")}]})
case("words for a number", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": q("one")}]})
case("numeric string for a number", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": q("1.5")}]})
case("origin library-default", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": {"value": 1.0, "unit": "placeholder-unit", "origin": {"kind": "library-default", "ref": "x"}}}]})
case("origin convention", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": {"value": 1.0, "unit": "placeholder-unit", "origin": {"kind": "convention", "note": "x"}}}]})
case("no origin", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": {"value": 1.0, "unit": "placeholder-unit"}}]})
case("assumption with no at", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": {"value": 1.0, "unit": "placeholder-unit", "origin": {"kind": "person-assumption", "by": "H1"}}}]})
case("assumption at spaces", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": q(1.0, origin={"at": "   "})}]})
case("assumption at not a day", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": q(1.0, origin={"at": "whenever"})}]})
case("assumption by spaces", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": q(1.0, origin={"by": "  "})}]})
case("stray origin field", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": q(1.0, origin={"n": 2})}]})
case("measurement the project lacks", "POST", R, {**base, "inputs": [{"name": "placeholder-a", "quantity": {"value": 1.0, "unit": "placeholder-unit", "origin": {"kind": "measurement", "ref": "dep-x/entry-y"}}}]})
case("thing empty", "POST", R, {"thing": "", "by": "H1"})
case("thing with spaces around", "POST", R, {"thing": "  reflect  ", "by": "H1"})
case("thing unknown", "POST", R, {"thing": "nothing", "by": "H1"})
case("configuration for a thing that takes none", "POST", R, {**base, "configuration": "x"})
case("configuration spaces", "POST", R, {**base, "configuration": "   "})
case("configuration 81 chars", "POST", R, {**base, "configuration": "c" * 81})
case("name 201 chars", "POST", R, {**base, "inputs": [{"name": "n" * 201, "quantity": q(1.0)}]})
case("by spaces", "POST", R, {"thing": "reflect", "by": "   ", "inputs": [{"name": "placeholder-b", "quantity": q(7.0, unit="another-placeholder-unit")}]})
case("inputs null", "POST", R, {"thing": "reflect", "by": "H1", "inputs": None})
case("body a list", "POST", R, [base])
case("engine unknown", "POST", "/api/engines/nosuch/run", base)
case("engine set aside", "POST", "/api/engines/h1e-misnamed/run", base)
case("engine name with spaces", "POST", "/api/engines/%20mirror%20/run", base)
case("engine name upper case", "POST", "/api/engines/MIRROR/run", base)
case("probe ok: a past its max", "POST", "/api/engines/probe/run", {"thing": "ok", "by": "H1", "inputs": [{"name": "a", "quantity": q(11.0, unit="u")}]})
case("probe ok: a at its max", "POST", "/api/engines/probe/run", {"thing": "ok", "by": "H1", "inputs": [{"name": "a", "quantity": q(10.0, unit="u")}]})
case("probe ok: a below min -0.0", "POST", "/api/engines/probe/run", {"thing": "ok", "by": "H1", "inputs": [{"name": "a", "quantity": q(-0.0, unit="u")}]})
case("probe cfg: no configuration (default one)", "POST", "/api/engines/probe/run", {"thing": "cfg", "by": "H1"})
case("probe cfg: configuration ' two ' as listed", "POST", "/api/engines/probe/run", {"thing": "cfg", "by": "H1", "configuration": " two "})
P_ = "/api/engines/mirror/parameters"
case("parameters: no thing", "GET", P_)
case("parameters: thing unknown", "GET", P_, params={"thing": "nothing"})
case("parameters: configuration for none", "GET", P_, params={"thing": "reflect", "configuration": "x"})
case("parameters: probe cfg ' two '", "GET", "/api/engines/probe/parameters", params={"thing": "cfg", "configuration": " two "})
T = "/api/tools/engine_run"
case("tool engine_run: no caller", "POST", T, {"engine": "mirror", "plant": "reflect"})
case("tool engine_run: by", "POST", T, {"engine": "mirror", "plant": "reflect", "note": "h1"}, params={"by": "H1 tool"})
case("tool engine_run: configuration a number", "POST", T, {"engine": "mirror", "plant": "reflect", "configuration": 7}, params={"by": "H1"})
case("tool engine_run: stray field inputs", "POST", T, {"engine": "mirror", "plant": "reflect", "inputs": [{"name": "placeholder-a", "quantity": 1}]}, params={"by": "H1"})
case("tool engine_run: scenario on mirror", "POST", T, {"engine": "mirror", "plant": "reflect", "scenario": "s1"}, params={"by": "H1"})
case("tool engine_run: engine set aside", "POST", T, {"engine": "h1e-misnamed", "plant": "reflect"}, params={"by": "H1"})
case("tool engine_run: probe slow (worker answers in 4 s)", "POST", T, {"engine": "probe", "plant": "garbage"}, params={"by": "H1"})
case("tool engine_parameters: probe garbage-free", "POST", "/api/tools/engine_parameters", {"engine": "probe", "plant": "ok"})
case("tool engine_plants: probe-badthings", "POST", "/api/tools/engine_plants", {"engine": "probe-badthings"})
case("tool engine_report: a mirror run named biosteam", "POST", "/api/tools/engine_report", {"engine": "biosteam", "run": "23aad3d656855f71"})
