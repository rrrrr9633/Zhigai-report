# Default Remote API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the report client use the configured cloud server by default while preserving all explicit configuration overrides.

**Architecture:** `scripts/remote_generate.py` will expose one default API base URL and resolve the effective value in this order: command line/environment, saved config, then the default. The service listens on port 8787 according to the bundled server reference, so the default base URL is `http://154.201.65.69:8787` and the request code continues to append `/generate`.

**Tech Stack:** Python standard library, `unittest`, Bash wrapper.

---

### Task 1: Add regression coverage for default configuration

**Files:**
- Create: `tests/test_remote_generate.py`
- Test: `tests/test_remote_generate.py`

- [x] **Step 1: Write the failing test**

```python
def test_resolve_api_base_url_uses_cloud_default_without_overrides():
    assert remote_generate.resolve_api_base_url(None, {}) == "http://154.201.65.69:8787"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_remote_generate -v`
Expected: FAIL because `resolve_api_base_url` does not exist.

### Task 2: Resolve the API base URL with a default fallback

**Files:**
- Modify: `scripts/remote_generate.py:22-23`
- Modify: `scripts/remote_generate.py:112-115`
- Test: `tests/test_remote_generate.py`

- [x] **Step 1: Write minimal implementation**

```python
DEFAULT_API_BASE_URL = "http://154.201.65.69:8787"

def resolve_api_base_url(explicit_value: str | None, config: dict[str, Any]) -> str:
    return explicit_value or config.get("apiBaseUrl") or DEFAULT_API_BASE_URL
```

Replace the existing `api_base_url` assignment with:

```python
api_base_url = resolve_api_base_url(args.api_base_url, config)
```

- [x] **Step 2: Run test to verify it passes**

Run: `python3 -m unittest tests.test_remote_generate -v`
Expected: PASS.

### Task 3: Document the no-address client invocation

**Files:**
- Modify: `SKILL.md:58-80`

- [x] **Step 1: Update the remote invocation example**

State that the cloud server address is built into the client and show the command with `--license-key`, `--data`, and `--output`, omitting `--api-base-url`.

- [x] **Step 2: Run the focused regression test**

Run: `python3 -m unittest tests.test_remote_generate -v`
Expected: PASS.

### Task 4: Validate client behavior without transmitting report data

**Files:**
- Modify: none
- Test: `scripts/remote_generate.py`

- [x] **Step 1: Invoke the client with only required file arguments**

Run: `python3 scripts/remote_generate.py --data examples/test_data.json --output /tmp/zhigai-default-url-check.docx`
Expected: it must not report a missing remote service address; it should stop only at the missing license key.

- [x] **Step 2: Check changed-file whitespace**

Run: `git diff --no-index --check /dev/null scripts/remote_generate.py`
Expected: no whitespace diagnostics. `SKILL.md` has existing Markdown line-break whitespace outside this change and is not reformatted.
