# AI Sandbox Agent V3

Production-oriented autonomous coding agent that executes AI-generated actions through a controlled Docker sandbox using a structured **Tool Registry**.

V3 is the evolution of the project from raw shell-command execution into a tool-based agent architecture.

---

# 1. Version Overview

| Version | Architecture                   | Main Capability                                                            |
| ------- | ------------------------------ | -------------------------------------------------------------------------- |
| V1      | Direct command execution       | LLM generates shell commands                                               |
| V2      | Persistent artifact collection | Sandbox files are copied to host storage                                   |
| V3      | Tool Registry                  | LLM selects structured tools instead of directly generating shell commands |

The major architectural change in V3 is:

```text
V1

User
 ↓
LLM
 ↓
Shell Command
 ↓
Docker Sandbox
 ↓
Result
```

```text
V2

User
 ↓
LLM
 ↓
Shell Command
 ↓
Docker Sandbox
 ↓
Artifact Collection
 ↓
Host Artifacts
```

```text
V3

User
 ↓
LLM
 ↓
Tool Selection
 ↓
Tool Registry
 ↓
Tool Implementation
 ↓
Docker Sandbox
 ↓
Structured Tool Result
 ↓
LLM
 ↓
Next Tool
 ↓
Task Completion
 ↓
Persistent Artifacts
```

V3 therefore introduces a clean separation between:

1. Agent reasoning
2. Tool selection
3. Tool execution
4. Sandbox isolation
5. Artifact persistence
6. Logging
7. Security validation

---

# 2. Project Objective

The purpose of the AI Sandbox Agent is to provide an autonomous coding environment where an LLM can perform tasks such as:

* Create files
* Read files
* Modify files
* Execute Python programs
* Inspect directories
* Run terminal commands
* Debug errors
* Verify results
* Produce persistent artifacts

The agent should never directly modify the host machine.

All generated code and task files are created inside:

```text
/sandbox
```

inside an isolated Docker container.

---

# 3. Core Design Principles

V3 follows these principles.

## 3.1 Sandbox Isolation

Every task receives its own Docker container.

Example:

```text
agent-sandbox-8e3cd9ce
```

The agent operates inside:

```text
/sandbox
```

The host machine remains outside the sandbox.

---

## 3.2 Structured Tools

Instead of asking the LLM to generate arbitrary shell commands, V3 asks it to select a registered tool.

Example:

```json
{
  "tool": "filesystem.write",
  "arguments": {
    "path": "hello.py",
    "content": "print(\"Hello from V3\")"
  }
}
```

The LLM does not need to know how `filesystem.write` is implemented.

The Tool Registry handles that.

---

## 3.3 Persistent Artifacts

Files created during successful tasks are copied from the temporary Docker container to the host.

Example:

```text
artifacts/
└── task-f0af34ebf46c/
    ├── hello.py
    └── manifest.json
```

The Docker container can be destroyed after the task while the artifacts remain available.

---

## 3.4 Path Security

Tools must not allow access outside `/sandbox`.

For example:

```text
hello.py
project/main.py
outputs/result.json
```

are valid.

But:

```text
../../etc/passwd
/root/file
/home/ec2-user/file
/etc/passwd
```

must be rejected.

The V3 test confirms this behavior:

```text
Path escapes sandbox workspace
```

---

# 4. V3 Project Structure

Recommended project structure:

```text
sandbox-ai/
│
├── agent.py
├── sandbox_manager.py
├── tool_registry.py
├── logger.py
├── test_tools.py
│
├── artifacts/
│   ├── task-xxxxxxxxxxxx/
│   │   ├── hello.py
│   │   └── manifest.json
│   │
│   └── ...
│
├── logs/
│   ├── task-xxxxxxxxxxxx.log
│   ├── task-xxxxxxxxxxxx.jsonl
│   └── ...
│
├── .env
├── .venv/
└── README.md
```

---

# 5. File Responsibilities

## 5.1 `agent.py`

This is the main application.

Responsibilities:

* Accept user input
* Create task ID
* Initialize logging
* Create Docker sandbox
* Initialize Tool Registry
* Send task to LLM
* Parse tool requests
* Dispatch tools
* Send tool results back to LLM
* Continue autonomous loop
* Detect task completion
* Collect artifacts
* Generate task summary
* Destroy sandbox

This is the main orchestration layer.

Run:

```bash
python agent.py
```

---

# 6. `sandbox_manager.py`

The Sandbox Manager controls the Docker execution environment.

Responsibilities include:

* Creating containers
* Creating `/sandbox`
* Creating workspace directories
* Executing commands inside the container
* Capturing stdout
* Capturing stderr
* Capturing return codes
* Collecting artifacts
* Copying files to host
* Creating artifact manifests
* Destroying containers

Conceptually:

```text
SandboxManager
      │
      ├── create()
      │
      ├── execute()
      │
      ├── collect_artifacts()
      │
      └── destroy()
```

The agent does not directly manage Docker commands.

---

# 7. `tool_registry.py`

This is the main V3 architectural component.

The Tool Registry provides a controlled interface between the LLM and the sandbox.

Current tools:

```text
filesystem.write
filesystem.read
filesystem.list
python.run
terminal.exec
```

The agent asks the registry to execute a tool.

Example:

```python
registry.dispatch(
    "filesystem.write",
    {
        "path": "hello.py",
        "content": "print(\"Hello from V3\")"
    }
)
```

The registry determines:

1. Whether the tool exists
2. Whether arguments are valid
3. Whether paths are safe
4. Which implementation should run
5. What structured result should be returned

---

# 8. Available V3 Tools

## 8.1 `filesystem.write`

Purpose:

Create or overwrite a file inside `/sandbox`.

Example request:

```json
{
  "tool": "filesystem.write",
  "arguments": {
    "path": "hello.py",
    "content": "print(\"Hello from V3\")"
  }
}
```

Result:

```json
{
  "success": true,
  "path": "/sandbox/hello.py"
}
```

Use cases:

* Creating Python files
* Creating configuration files
* Creating JSON
* Creating Markdown
* Creating project files
* Generating source code

---

# 9. `filesystem.read`

Purpose:

Read a file inside the sandbox.

Example:

```json
{
  "tool": "filesystem.read",
  "arguments": {
    "path": "hello.py"
  }
}
```

Result:

```json
{
  "success": true,
  "path": "/sandbox/hello.py",
  "content": "print(\"Hello from V3\")\n"
}
```

Use cases:

* Inspect generated code
* Verify files
* Read configuration
* Debug source files
* Inspect previous agent output

---

# 10. `filesystem.list`

Purpose:

List files within the sandbox.

Example:

```json
{
  "tool": "filesystem.list",
  "arguments": {
    "path": "."
  }
}
```

Result:

```json
{
  "success": true,
  "files": [
    "./hello.py"
  ]
}
```

Use cases:

* Discover generated files
* Inspect project structure
* Verify output files
* Locate source files

---

# 11. `python.run`

Purpose:

Execute a Python file inside the sandbox.

Example:

```json
{
  "tool": "python.run",
  "arguments": {
    "path": "hello.py"
  }
}
```

Result:

```json
{
  "success": true,
  "stdout": "Hello from V3\n",
  "stderr": "",
  "return_code": 0
}
```

Use cases:

* Execute Python programs
* Test generated code
* Validate scripts
* Run data-processing scripts
* Debug Python applications

---

# 12. `terminal.exec`

Purpose:

Execute a terminal command inside `/sandbox`.

Example:

```json
{
  "tool": "terminal.exec",
  "arguments": {
    "command": "pwd && ls -la"
  }
}
```

Result:

```json
{
  "success": true,
  "stdout": "...",
  "stderr": "",
  "return_code": 0
}
```

This tool provides lower-level terminal functionality.

It should be treated as a controlled capability rather than the primary interface for every task.

Future versions can restrict or replace this capability with more specialized tools.

---

# 13. Tool Registry Architecture

The architecture is:

```text
                    ┌─────────────────────┐
                    │       LLM           │
                    │                     │
                    │ Selects tool        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Tool Registry     │
                    │                     │
                    │ Validate tool       │
                    │ Validate arguments  │
                    │ Dispatch tool       │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
       filesystem.*       python.run       terminal.exec
             │                 │                 │
             └─────────────────┼─────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │  Sandbox Manager    │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │   Docker Sandbox    │
                    │      /sandbox       │
                    └─────────────────────┘
```

---

# 14. V3 Agent Loop

V3 uses an autonomous tool-calling loop.

The high-level process is:

```text
USER TASK
   │
   ▼
Create Task ID
   │
   ▼
Create Docker Sandbox
   │
   ▼
Initialize Tool Registry
   │
   ▼
Send task + available tools to LLM
   │
   ▼
LLM selects tool
   │
   ▼
Validate tool
   │
   ▼
Execute tool
   │
   ▼
Return structured result
   │
   ▼
LLM observes result
   │
   ├── Task incomplete ──► select next tool
   │
   └── Task complete
              │
              ▼
       Collect artifacts
              │
              ▼
       Create manifest
              │
              ▼
       Generate summary
              │
              ▼
       Destroy container
```

---

# 15. Example Task

User:

```text
Create hello.py that prints "Hello from V3".
Run it, read the file, verify the output, and confirm the task is complete.
```

The agent can perform:

### Step 1

```json
{
  "tool": "filesystem.write",
  "arguments": {
    "path": "hello.py",
    "content": "print(\"Hello from V3\")\n"
  }
}
```

### Step 2

```json
{
  "tool": "python.run",
  "arguments": {
    "path": "hello.py"
  }
}
```

### Step 3

```json
{
  "tool": "filesystem.read",
  "arguments": {
    "path": "hello.py"
  }
}
```

### Step 4

```json
{
  "action": "DONE"
}
```

The important difference from V2 is that the LLM is selecting capabilities rather than constructing the underlying implementation command.

---

# 16. Tool Result Feedback

Every tool returns a structured result.

Example:

```json
{
  "success": true,
  "stdout": "Hello from V3\n",
  "stderr": "",
  "return_code": 0
}
```

The result is added to the conversation.

The LLM then determines the next action.

If the result contains an error:

```json
{
  "success": false,
  "stderr": "ModuleNotFoundError: ..."
}
```

the agent can reason about the error and select another tool.

This creates the:

```text
PLAN
 ↓
TOOL
 ↓
OBSERVE
 ↓
FIX
 ↓
VERIFY
```

loop.

---

# 17. Task Completion

The agent should not mark a task complete merely because a tool succeeded.

For example:

```text
filesystem.write
```

returning:

```text
success=true
```

only proves that the file was written.

It does not prove that the program works.

The agent should perform verification where required.

Example:

```text
filesystem.write
        ↓
python.run
        ↓
filesystem.read
        ↓
DONE
```

This provides stronger task verification.

---

# 18. Artifact Persistence

V3 retains the V2 persistent artifact mechanism.

Each task receives a host directory:

```text
artifacts/<task-id>/
```

Example:

```text
artifacts/task-f0af34ebf46c/
```

After successful completion:

```text
/sandbox/hello.py
```

is copied to:

```text
artifacts/task-f0af34ebf46c/hello.py
```

The Docker container can then be destroyed without losing the generated file.

---

# 19. Artifact Manifest

Every successful task creates:

```text
manifest.json
```

Example:

```json
{
  "task_id": "task-f0af34ebf46c",
  "container": "agent-sandbox-8e3cd9ce",
  "workspace": "/sandbox",
  "artifact_directory": "/home/ec2-user/sandbox-ai/artifacts/task-f0af34ebf46c",
  "count": 1,
  "artifacts": [
    {
      "path": "/sandbox/hello.py",
      "relative_path": "hello.py",
      "host_path": "/home/ec2-user/sandbox-ai/artifacts/task-f0af34ebf46c/hello.py",
      "type": "python"
    }
  ]
}
```

The manifest provides a machine-readable record of generated artifacts.

---

# 20. Artifact Directory Structure

Example:

```text
artifacts/
│
├── task-f734fdf8e98d2/
│   ├── hello.py
│   └── manifest.json
│
├── task-f0af34ebf46c/
│   ├── hello.py
│   └── manifest.json
│
└── v3-test/
```

Each task has an independent artifact directory.

This prevents files from different tasks from being mixed together.

---

# 21. Logging Architecture

V3 maintains two log formats.

## Human-readable log

```text
logs/task-xxxx.log
```

Useful for:

* Debugging
* Operations
* Manual inspection
* Development

## JSONL event log

```text
logs/task-xxxx.jsonl
```

Useful for:

* Log ingestion
* Analytics
* Monitoring
* Auditing
* Future UI integration

---

# 22. Important V3 Events

Typical events include:

```text
TASK_STARTED
SANDBOX_CREATE_START
SANDBOX_CREATED
SANDBOX_WORKSPACE_READY
ARTIFACT_DIRECTORY_READY
AGENT_READY
TOOL_REGISTRY_READY
STEP_STARTED
LLM_CALL_START
LLM_CALL_FINISHED
TOOL_DISPATCH
TOOL_CALL_START
TOOL_CALL_FINISHED
TOOL_RESULT
STEP_SUCCESS
STEP_ERROR
OBSERVATION_SENT_TO_AGENT
AGENT_DONE
ARTIFACT_COLLECTION_START
ARTIFACT_COPIED
ARTIFACT_MANIFEST_CREATED
ARTIFACT_COLLECTION_FINISHED
ARTIFACTS_READY
TASK_SUMMARY
SANDBOX_DESTROY_START
SANDBOX_DESTROYED
```

This event model makes V3 easier to integrate into future monitoring systems.

---

# 23. `logger.py`

`logger.py` contains:

```python
class AgentLogger:
```

It is responsible for:

* Console logging
* File logging
* JSONL event logging
* Timestamp generation
* Task ID association

Example:

```python
logger.event(
    "TOOL_RESULT",
    tool="python.run",
    success=True
)
```

The logger should remain independent of the agent's business logic.

---

# 24. `test_tools.py`

`test_tools.py` is the V3 Tool Registry integration test.

It verifies:

1. Sandbox creation
2. Artifact directory creation
3. `filesystem.write`
4. `filesystem.read`
5. `python.run`
6. `filesystem.list`
7. `terminal.exec`
8. Path security
9. Sandbox destruction

Run:

```bash
python test_tools.py
```

Expected final output:

```text
============================================
V3 TOOL TEST FINISHED
============================================
```

---

# 25. V3 Test Result

The current V3 implementation successfully demonstrated:

```text
filesystem.write       PASS
filesystem.read        PASS
python.run             PASS
filesystem.list        PASS
terminal.exec          PASS
path security          PASS
sandbox destruction    PASS
```

The security test:

```text
../../etc/passwd
```

was rejected with:

```text
Path escapes sandbox workspace
```

This confirms that the basic sandbox path boundary is functioning.

---

# 26. Environment Setup

Create the virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

If the project does not yet contain `requirements.txt`, install the required packages used by the current implementation.

---

# 27. Environment Variables

Create:

```text
.env
```

Example:

```env
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-5.6
MAX_STEPS=10
```

Do not commit `.env` to Git.

Recommended `.gitignore`:

```text
.env
.venv/
__pycache__/
*.pyc
logs/
artifacts/
```

If artifacts are intended to be versioned for a particular deployment, remove `artifacts/` from `.gitignore`.

---

# 28. Running V3

From the project directory:

```bash
cd ~/sandbox-ai
```

Activate the environment:

```bash
source .venv/bin/activate
```

Compile the main files:

```bash
python -m py_compile agent.py
python -m py_compile sandbox_manager.py
python -m py_compile tool_registry.py
python -m py_compile logger.py
```

Run the tool test:

```bash
python test_tools.py
```

Then run the agent:

```bash
python agent.py
```

---

# 29. Example V3 Session

Start:

```text
AI SANDBOX AGENT V3
Model: gpt-5.6
Max steps: 10
Workspace: /sandbox
```

Enter:

```text
Create hello.py that prints "Hello from V3".
Run it, read the file, verify the output, and confirm the task is complete.
```

The agent performs structured tool calls:

```text
filesystem.write
        ↓
python.run
        ↓
filesystem.read
        ↓
DONE
```

Then artifacts are collected.

---

# 30. Expected Artifact Output

After successful execution:

```bash
ls -lah artifacts/<task-id>/
```

Expected:

```text
hello.py
manifest.json
```

Check:

```bash
cat artifacts/<task-id>/hello.py
```

Expected:

```python
print("Hello from V3")
```

Check manifest:

```bash
cat artifacts/<task-id>/manifest.json
```

---

# 31. Docker Lifecycle

Every task follows:

```text
CREATE
  ↓
RUN
  ↓
TOOLS
  ↓
VERIFY
  ↓
COLLECT ARTIFACTS
  ↓
DESTROY
```

Example:

```text
SANDBOX_CREATE_START
        ↓
SANDBOX_CREATED
        ↓
TOOL EXECUTION
        ↓
ARTIFACT_COLLECTION
        ↓
SANDBOX_DESTROY_START
        ↓
SANDBOX_DESTROYED
```

The container is temporary.

Artifacts are persistent.

---

# 32. Why the Sandbox Is Temporary

The Docker container is intentionally treated as ephemeral.

This provides:

* Isolation between tasks
* Clean execution environment
* Reduced state leakage
* Easier cleanup
* Reproducibility

Persistent state belongs on the host artifact layer, not inside the temporary container.

---

# 33. Security Model

V3 currently has several security boundaries.

## Container Isolation

Agent operations happen inside Docker.

## Workspace Restriction

Operations are restricted to:

```text
/sandbox
```

## Path Validation

Relative paths are resolved and checked before execution.

Invalid:

```text
../../etc/passwd
```

Valid:

```text
project/main.py
outputs/result.json
```

## Artifact Isolation

Artifacts are stored under the task-specific directory:

```text
artifacts/<task-id>/
```

This prevents cross-task artifact collisions.

---

# 34. Current V3 Architecture Limitations

V3 is a significant architectural improvement, but it is not yet a complete production security boundary.

Important areas for future hardening include:

* Tool argument schema validation
* More restrictive terminal execution
* Command allowlists
* Resource limits
* CPU limits
* Memory limits
* Execution timeouts
* Network restrictions
* File size limits
* Output size limits
* Container user restrictions
* Read-only host filesystem
* Secret isolation
* Tool permission policies
* Tool-level audit records

These should be addressed before exposing the agent to untrusted users or arbitrary workloads.

---

# 35. Recommended Production Tool Policy

A production deployment should distinguish tools by risk.

Example:

```text
LOW RISK

filesystem.read
filesystem.list


MEDIUM RISK

filesystem.write
python.run


HIGH RISK

terminal.exec
```

The application can eventually implement permission policies such as:

```text
Agent
 │
 ├── filesystem.read     ALLOW
 ├── filesystem.list     ALLOW
 ├── filesystem.write    ALLOW
 ├── python.run         ALLOW
 └── terminal.exec      RESTRICTED
```

---

# 36. V3 vs V2

## V2

LLM output:

```text
printf 'print("Hello")\n' > hello.py
```

The sandbox executes the shell command.

## V3

LLM output:

```json
{
  "tool": "filesystem.write",
  "arguments": {
    "path": "hello.py",
    "content": "print(\"Hello\")"
  }
}
```

The Tool Registry handles implementation.

This is the key architectural improvement.

---

# 37. Benefits of Tool-Based Architecture

The Tool Registry makes it possible to add capabilities without modifying the agent's core reasoning loop.

For example:

```text
filesystem.write
filesystem.read
filesystem.list
python.run
terminal.exec
```

can later become:

```text
git.clone
git.commit
git.diff

filesystem.write
filesystem.read

python.run

package.install

browser.open
browser.search

database.query

http.request

docker.build
```

The agent architecture remains largely unchanged.

Only new tools need to be implemented and registered.

---

# 38. Future V3.x Tool Expansion

Potential tools:

```text
filesystem.delete
filesystem.move
filesystem.copy

python.run
python.install_package

git.status
git.diff
git.commit
git.clone

http.get

database.query

json.read
json.write

csv.read
csv.write

package.install
```

Each tool should have:

```text
Name
Description
Arguments
Validation
Execution
Result schema
Permission level
Audit logging
```

---

# 39. Future V4 Direction

The next major evolution can introduce stronger agent infrastructure.

Potential architecture:

```text
                    USER
                      │
                      ▼
               AGENT ORCHESTRATOR
                      │
             ┌────────┴────────┐
             ▼                 ▼
          PLANNER          TOOL POLICY
             │                 │
             └────────┬────────┘
                      ▼
                 TOOL REGISTRY
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
      Filesystem    Python     Terminal
          │           │           │
          └───────────┼───────────┘
                      ▼
                  SANDBOX
                      │
                      ▼
                 ARTIFACTS
                      │
                      ▼
                  STORAGE
```

---

# 40. Production Deployment Concept

A production deployment can eventually expose the agent through an API:

```text
Frontend
   │
   ▼
Agent API
   │
   ▼
Task Queue
   │
   ▼
Agent Worker
   │
   ▼
Docker Sandbox
   │
   ├── Tools
   ├── Files
   └── Execution
   │
   ▼
Artifact Storage
```

Possible interfaces:

```text
Web UI
REST API
CLI
Chat interface
IDE integration
```

---

# 41. Example Real-World Applications

## Coding Assistant

User:

```text
Create a FastAPI application with a health endpoint.
Run it and verify the endpoint.
```

The agent can:

```text
filesystem.write
python.run
terminal.exec
filesystem.read
```

---

## Data Analysis Agent

User:

```text
Create a Python script that analyzes sales.csv
and produces summary statistics.
```

Potential workflow:

```text
filesystem.list
filesystem.read
filesystem.write
python.run
filesystem.list
```

---

## Code Debugging Agent

User:

```text
Find and fix the error in main.py.
```

Workflow:

```text
filesystem.read
python.run
filesystem.write
python.run
filesystem.read
DONE
```

---

## Project Generator

User:

```text
Create a complete Python project with:
main.py
config.py
requirements.txt
README.md
```

Workflow:

```text
filesystem.write
filesystem.write
filesystem.write
filesystem.write
filesystem.list
```

Artifacts are then persisted.

---

# 42. Operational Workflow

For each task, operators should be able to trace:

```text
Task ID
   ↓
LLM Calls
   ↓
Tool Calls
   ↓
Tool Results
   ↓
Errors
   ↓
Verification
   ↓
Artifacts
```

Example:

```text
task-f0af34ebf46c

LLM calls:       4
Tool calls:      3
Errors:          0
Artifacts:       1
Status:          SUCCESS
```

---

# 43. Debugging Workflow

If the agent fails:

### Step 1

Check syntax:

```bash
python -m py_compile agent.py
python -m py_compile tool_registry.py
python -m py_compile sandbox_manager.py
```

### Step 2

Run Tool Registry tests:

```bash
python test_tools.py
```

### Step 3

Run the agent:

```bash
python agent.py
```

### Step 4

Inspect the task log:

```bash
cat logs/<task-id>.log
```

### Step 5

Inspect structured events:

```bash
cat logs/<task-id>.jsonl
```

### Step 6

Inspect artifacts:

```bash
ls -lah artifacts/<task-id>/
```

---

# 44. Recommended Development Sequence

Do not change multiple architectural layers simultaneously.

Recommended order:

```text
1. Sandbox Manager
       ↓
2. Artifact Collection
       ↓
3. Tool Registry
       ↓
4. Agent Tool Calling
       ↓
5. Tool Validation
       ↓
6. Security Hardening
       ↓
7. Additional Tools
       ↓
8. API
       ↓
9. Web UI
       ↓
10. Production Deployment
```

This makes failures easier to isolate.

---

# 45. Version History

## V1 — Command Agent

Initial architecture.

```text
LLM → Shell Command → Docker
```

Primary objective:

Autonomous command execution.

---

## V2 — Persistent Artifacts

Added:

```text
artifacts/
task-specific artifact directories
manifest.json
persistent host files
```

Architecture:

```text
LLM
 ↓
Shell
 ↓
Docker
 ↓
Artifact Collection
 ↓
Host Storage
```

Primary objective:

Do not lose generated files when Docker containers are destroyed.

---

## V3 — Tool Registry

Added:

```text
tool_registry.py
```

Tools:

```text
filesystem.write
filesystem.read
filesystem.list
python.run
terminal.exec
```

Architecture:

```text
LLM
 ↓
Tool Selection
 ↓
Tool Registry
 ↓
Sandbox
 ↓
Structured Result
```

Primary objective:

Replace raw LLM-generated shell commands with controlled tool execution.

---

# 46. Current V3 Acceptance Criteria

V3 is considered functionally working when all of the following succeed:

```text
[PASS] Sandbox creation
[PASS] /sandbox workspace
[PASS] Tool Registry initialization
[PASS] filesystem.write
[PASS] filesystem.read
[PASS] filesystem.list
[PASS] python.run
[PASS] terminal.exec
[PASS] Path traversal protection
[PASS] Agent tool selection
[PASS] Tool result feedback
[PASS] Agent completion
[PASS] Artifact collection
[PASS] manifest.json
[PASS] Task logging
[PASS] Sandbox destruction
```

The demonstrated V3 run satisfies these core functional requirements.

---

# 47. Quick Start

```bash
cd ~/sandbox-ai

source .venv/bin/activate

python -m py_compile agent.py
python -m py_compile sandbox_manager.py
python -m py_compile tool_registry.py
python -m py_compile logger.py

python test_tools.py

python agent.py
```

Then provide a task such as:

```text
Create hello.py that prints "Hello from V3".
Run it, read the file, verify the output, and confirm the task is complete.
```

---

# 48. Final Architecture

The V3 system can be summarized as:

```text
                         USER
                           │
                           ▼
                     ┌───────────┐
                     │  agent.py │
                     └─────┬─────┘
                           │
                           ▼
                    ┌──────────────┐
                    │     LLM      │
                    └──────┬───────┘
                           │
                    Tool Selection
                           │
                           ▼
                  ┌─────────────────┐
                  │ Tool Registry   │
                  └────────┬────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
 filesystem.*         python.run       terminal.exec
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ SandboxManager  │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Docker Sandbox  │
                  │    /sandbox     │
                  └────────┬────────┘
                           │
                           ▼
                    Tool Execution
                           │
                           ▼
                   Structured Result
                           │
                           ▼
                         LLM
                           │
                    ┌──────┴──────┐
                    │             │
                  NEXT          DONE
                  TOOL            │
                    │             ▼
                    │      Artifact Collection
                    │             │
                    │             ▼
                    │       Host Artifacts
                    │             │
                    └─────────────┤
                                  ▼
                           manifest.json
                                  │
                                  ▼
                           Sandbox Destroy
```

---

# 49. V3 Summary

V3 establishes the foundation for a production-grade autonomous coding agent.

The major components are:

```text
agent.py
    ↓
Reasoning + orchestration

tool_registry.py
    ↓
Controlled tool interface

sandbox_manager.py
    ↓
Docker isolation + execution

logger.py
    ↓
Observability + audit trail

artifacts/
    ↓
Persistent task outputs

logs/
    ↓
Task execution history
```

The most important architectural transition is:

```text
V1:
LLM → Commands

V2:
LLM → Commands → Persistent Artifacts

V3:
LLM → Tools → Sandbox → Structured Results
                 ↓
          Persistent Artifacts
```

This provides the base required for future expansion into a more secure, extensible, API-driven autonomous agent platform.
