# License Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify the configured license with the remote service before any report data or image attachment is read or uploaded.

**Architecture:** The remote client requests `GET /license/status` with the existing Bearer authorization header. A response may proceed only when it is HTTP 200 and contains `{"ok": true, "status": "active"}`; server `401` and `403`, malformed responses, and non-active status stop the command before report payload construction.

**Tech Stack:** Python standard library (`urllib.request`, `unittest.mock`).

---

### Task 1: Add failing tests for the license preflight contract

**Files:**
- Modify: `tests/test_remote_generate.py:1-22`
- Test: `tests/test_remote_generate.py`

- [x] **Step 1: Add contract tests**

```python
@mock.patch.object(remote_generate, "urlopen")
def test_request_license_status_sends_bearer_token_to_status_endpoint(...):
    status = remote_generate.request_license_status(
        "http://154.201.65.69:8787", "valid-license", 10
    )
    self.assertEqual(status["status"], "active")

def test_require_active_license_rejects_non_active_status(...):
    with self.assertRaisesRegex(SystemExit, "授权已过期"):
        remote_generate.require_active_license({"ok": False, "message": "授权已过期"})
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_remote_generate -v`
Expected: FAIL because the preflight functions do not exist.

### Task 2: Implement the preflight request and response guard

**Files:**
- Modify: `scripts/remote_generate.py:83-104`
- Modify: `scripts/remote_generate.py:117-127`
- Test: `tests/test_remote_generate.py`

- [x] **Step 1: Add the minimum client functions**

```python
def request_license_status(api_base_url: str, license_key: str, timeout: int) -> dict[str, Any]:
    # GET /license/status with Authorization: Bearer <key>

def require_active_license(status: dict[str, Any]) -> None:
    if status.get("ok") is True and status.get("status") == "active":
        return
    raise SystemExit(status.get("message") or "授权码无效、已过期或不可用。请提供有效授权码。")
```

Call both functions after the existing empty-key check and before `read_json(data_path)`.

- [x] **Step 2: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_remote_generate -v`
Expected: PASS.

### Task 3: Document preflight behavior

**Files:**
- Modify: `SKILL.md:71-81`

- [x] **Step 1: State the authorization gate**

Document that a missing license key stops immediately, and that inactive, expired, invalid, or exhausted licenses stop before report generation.

- [x] **Step 2: Run final verification**

Run: `python3 -m unittest discover -v && python3 -m compileall -q scripts tests`
Expected: all tests pass and the client compiles.
