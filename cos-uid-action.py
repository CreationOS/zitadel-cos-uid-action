#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 CreationOS
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sets up (or removes) the ZITADEL Action "cosUid" that single sign-on to Nextcloud needs: one extra claim, cos_uid, in the ID token and userinfo of a person with a VERIFIED e-mail address.

  ZITADEL_PAT=<token> python3 cos-uid-action.py --check            only looks: is the Action there, is it on the two triggers, what else is on them
  ZITADEL_PAT=<token> python3 cos-uid-action.py --apply            makes or updates the Action and puts it on "Pre Userinfo creation" and "Pre access token creation" (asks first; --yes for no question)
  ZITADEL_PAT=<token> python3 cos-uid-action.py --remove           takes it off both triggers and deletes it (asks first)

Settings (environment): ZITADEL_URL (default https://accounts.creationinc.ai), ZITADEL_PAT (a personal access token of a ZITADEL user who may manage Actions of the organisation, for example an organisation owner:
read from the environment only, never printed, never written anywhere), ZITADEL_HOST_HEADER (only for a test instance reached by another address).
What it does NOT do: it never replaces what is on a trigger already (the existing Actions are kept, ours is added), and it makes the Action "allowed to fail" (a bug in it can never stop anybody from signing in: the claim is then simply missing and
only the Nextcloud sign-in refuses). It changes nothing about any application. It only uses ZITADEL's management API: /management/v1/actions and /management/v1/flows/2 (flow 2 = "Complement Token")."""
import json, os, sys, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("ZITADEL_URL", "https://accounts.creationinc.ai").rstrip("/")
PAT = os.environ.get("ZITADEL_PAT", "")
HOST = os.environ.get("ZITADEL_HOST_HEADER", "")
NAME = "cosUid"
TRIGGERS = {"4": "Pre Userinfo creation", "5": "Pre access token creation"}
FLOW = "2"  # Complement Token

def die(text, code=2):
    print("!! " + text, file=sys.stderr)
    raise SystemExit(code)

if not PAT:
    die("ZITADEL_PAT is not set (a personal access token of a ZITADEL user who may manage Actions). Put it in the environment for this one command; it is never printed or kept.")

def call(method, path, body=None, ok=(200,)):
    headers = {"Authorization": "Bearer " + PAT, "Content-Type": "application/json", **({"Host": HOST} if HOST else {})}
    req = urllib.request.Request(BASE + path, method=method, data=None if body is None else json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode()
            return r.status, (json.loads(text) if text else {})
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        try:
            data = json.loads(text)
        except Exception:
            data = {"raw": text[:200]}
        if e.code in ok:
            return e.code, data
        die("%s %s -> HTTP %s %s" % (method, path, e.code, json.dumps(data)[:300]))
    except urllib.error.URLError as e:
        die("cannot reach %s: %s" % (BASE, e.reason))

def actions():
    _, r = call("POST", "/management/v1/actions/_search", {"queries": []})
    return r.get("result", [])

def mine():
    found = [a for a in actions() if a.get("name") == NAME]
    return found[0] if found else None

def triggers():
    """{ "4": [{id, name}], "5": [...] } as they are now on the Complement Token flow"""
    _, r = call("GET", "/management/v1/flows/" + FLOW)
    out = {t: [] for t in TRIGGERS}
    for ta in r.get("flow", {}).get("triggerActions", []):
        t = str(ta.get("triggerType", {}).get("id"))
        if t in out:
            out[t] = [{"id": a["id"], "name": a.get("name", "?")} for a in ta.get("actions", [])]
    return out

def show():
    a = mine()
    print("ZITADEL: " + BASE)
    print("Action %s: %s" % (NAME, "NOT THERE" if not a else "there (id %s, state %s, timeout %s, allowed to fail: %s)" % (a["id"], a.get("state", "?").replace("ACTION_STATE_", ""), a.get("timeout", "?"), bool(a.get("allowedToFail", False)))))
    t = triggers()
    for k, label in TRIGGERS.items():
        names = [x["name"] for x in t[k]]
        print("  trigger \"%s\": %s" % (label, ", ".join(names) if names else "(nothing)"))
    return a, t

def confirm(what):
    if "--yes" in sys.argv:
        return
    if not sys.stdin.isatty():
        die("there is no keyboard to ask on: run it with --yes if you mean it")
    if input("%s\nType yes to go on: " % what).strip() != "yes":
        die("not confirmed: nothing was changed", 1)

mode = "--apply" if "--apply" in sys.argv else "--remove" if "--remove" in sys.argv else "--check"
a, t = show()

if mode == "--apply":
    script = open(os.path.join(HERE, "cos-uid-action.js")).read()
    confirm("This will %s the Action %s and add it to both triggers, keeping everything already on them." % ("update" if a else "make", NAME))
    want = {"name": NAME, "script": script, "timeout": "10s", "allowedToFail": True}
    if a:
        call("PUT", "/management/v1/actions/" + a["id"], want, ok=(200, 400))  # 400 "No changes" = it is already like this
        aid = a["id"]
    else:
        _, r = call("POST", "/management/v1/actions", want)
        aid = r["id"]
    for k in TRIGGERS:
        ids = [x["id"] for x in t[k]]
        if aid not in ids:
            call("POST", "/management/v1/flows/%s/trigger/%s" % (FLOW, k), {"actionIds": ids + [aid]})
    print("done:")
    show()
elif mode == "--remove":
    if not a:
        print("nothing to remove")
        raise SystemExit(0)
    confirm("This will take %s off both triggers (everything else on them stays) and delete it." % NAME)
    for k in TRIGGERS:
        rest = [x["id"] for x in t[k] if x["id"] != a["id"]]
        if len(rest) != len(t[k]):
            if rest:
                call("POST", "/management/v1/flows/%s/trigger/%s" % (FLOW, k), {"actionIds": rest})
            else:
                call("POST", "/management/v1/flows/%s/trigger/%s" % (FLOW, k), {"actionIds": []}, ok=(200, 400))
    call("DELETE", "/management/v1/actions/" + a["id"])
    print("removed:")
    show()
