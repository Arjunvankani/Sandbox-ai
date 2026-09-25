# Sandbox AI Agent — V1

## Autonomous Coding Agent with Isolated Docker Execution

**Version:** V1
**Status:** Legacy / Foundation Version
**Primary Runtime:** Python 3
**Execution Environment:** Docker
**LLM:** OpenAI-compatible chat model
**Execution Model:** LLM-generated shell commands
**Workspace:** `/sandbox`

---

# 1. Overview

Sandbox AI Agent V1 is an autonomous coding agent that allows a user to provide a natural-language coding or execution task and have an LLM autonomously perform that task inside an isolated Docker container.

The primary objective of V1 is to establish a safe execution boundary between the host machine and AI-generated commands.

Instead of allowing the AI model to execute commands directly on the host machine, the system:

1. Receives a task from the user.
2. Creates a temporary Docker sandbox.
3. Starts the sandbox with `/sandbox` as the working directory.
4. Sends the user's task and system instructions to the LLM.
5. Receives one shell command from the LLM.
6. Executes the command inside the Docker sandbox.
7. Captures stdout, stderr and exit code.
8. Sends the execution result back to the LLM.
9. Allows the LLM to decide the next command.
10. Repeats until the task is completed or the maximum number of steps is reached.
11. Destroys the Docker sandbox after execution.

V1 therefore establishes the fundamental autonomous execution loop:

```text
User
  |
  v
Agent
  |
  v
LLM
  |
  v
Shell Command
  |
  v
Docker Sandbox
  |
  v
Command Result
  |
  v
LLM
  |
  +----> Next Command
  |
  +----> DONE
```

---

# 2. Goals

The primary goals of Version 1 are:

* Execute AI-generated coding tasks.
* Keep execution isolated inside Docker.
* Prevent normal task execution from directly affecting the host.
* Give the LLM access to command output.
* Allow the LLM to iteratively solve problems.
* Detect command failures.
* Allow the agent to recover from failures.
* Limit autonomous execution using a maximum step count.
* Maintain execution logs.
* Track token usage.
* Provide a simple interactive CLI.

---

# 3. Non-Goals of V1

V1 intentionally keeps the architecture simple.

The following capabilities are not part of the original V1 architecture:

* Native OpenAI tool/function calling.
* Structured tool registry.
* Dedicated filesystem tools.
* Dedicated Python execution tools.
* Persistent artifact collection.
* Artifact manifests.
* Long-term task storage.
* Web/browser tools.
* Database tools.
* Multi-agent orchestration.
* Human approval workflows.
* Production job queues.
* Persistent sandbox containers.

These capabilities can be introduced in later versions.

---

# 4. Core Architecture

The V1 architecture consists of four major components:

```text
+----------------------+
|       User           |
+----------+-----------+
           |
           v
+----------------------+
|      agent.py        |
|                      |
| Task orchestration   |
| LLM communication    |
| Autonomous loop      |
| Token accounting     |
+----------+-----------+
           |
           v
+----------------------+
|      OpenAI API      |
|                      |
| Task reasoning       |
| Command generation   |
+----------+-----------+
           |
           v
+----------------------+
|  SandboxManager      |
|                      |
| Docker lifecycle     |
| Command execution    |
+----------+-----------+
           |
           v
+----------------------+
|   Docker Sandbox     |
|                      |
|      /sandbox        |
|                      |
| AI-generated code    |
| AI-generated files   |
| Commands             |
+----------------------+
```

Logging runs alongside the entire process:

```text
agent.py
   |
   +----> logger.py
             |
             +----> Console
             |
             +----> logs/<task-id>.log
             |
             +----> logs/<task-id>.jsonl
```

---

# 5. V1 Project Structure

A typical V1 project structure is:

```text
sandbox-ai/
│
├── agent.py
├── sandbox_manager.py
├── logger.py
├── .env
├── requirements.txt
│
├── logs/
│   ├── task-xxxxxxxxxxxx.log
│   └── task-xxxxxxxxxxxx.jsonl
│
└── .venv/
```

The exact supporting files may differ depending on the deployment, but the primary V1 application consists of:

```text
agent.py
sandbox_manager.py
logger.py
```

---

# 6. File Responsibilities

## 6.1 `agent.py`

`agent.py` is the main application entry point and orchestration layer.

It is responsible for:

* Loading environment variables.
* Creating the OpenAI client.
* Loading model configuration.
* Loading maximum execution steps.
* Defining the system prompt.
* Creating a unique task ID.
* Creating the logger.
* Creating the sandbox manager.
* Creating the Docker sandbox.
* Sending prompts to the LLM.
* Receiving generated commands.
* Executing commands.
* Processing command results.
* Maintaining the conversation.
* Tracking execution steps.
* Tracking token usage.
* Tracking errors.
* Detecting `DONE`.
* Printing the final task summary.
* Destroying the sandbox.

Conceptually:

```text
agent.py
   |
   +-- Configuration
   |
   +-- OpenAI Client
   |
   +-- System Prompt
   |
   +-- Task ID
   |
   +-- Logger
   |
   +-- Sandbox Manager
   |
   +-- Agent Loop
   |
   +-- Metrics
   |
   +-- Final Summary
```

---

# 7. `sandbox_manager.py`

`sandbox_manager.py` manages the Docker execution environment.

Its responsibility is to provide the isolation boundary between the AI agent and the host system.

The manager handles operations such as:

```text
Create Docker container
        |
        v
Set /sandbox working directory
        |
        v
Execute shell command
        |
        v
Capture result
        |
        v
Destroy container
```

The agent should not need to manage Docker commands directly.

Instead, `agent.py` communicates with the abstraction provided by `SandboxManager`.

---

# 8. `logger.py`

`logger.py` provides structured task logging.

The logger records information such as:

* Task start.
* Sandbox creation.
* LLM request.
* LLM response.
* Generated command.
* Command execution.
* Command result.
* Errors.
* Step completion.
* Task completion.
* Task summary.
* Sandbox destruction.

V1 uses a task-specific identifier so that each execution can be traced independently.

Example:

```text
task-483c37f8fcf2
```

The corresponding logs are stored under:

```text
logs/
```

Example:

```text
logs/task-483c37f8fcf2.log
logs/task-483c37f8fcf2.jsonl
```

---

# 9. Task ID

Every task receives a unique task ID.

Example:

```text
task-483c37f8fcf2
```

The task ID is used to associate:

* Logs
* Execution events
* Metrics
* Errors
* Task lifecycle events

with one particular execution.

This makes debugging individual agent executions possible.

---

# 10. Environment Configuration

V1 loads configuration through environment variables.

The `.env` file can contain values such as:

```env
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-5.6
MAX_STEPS=10
```

The application loads these values using:

```python
from dotenv import load_dotenv

load_dotenv()
```

The model is configured through:

```env
OPENAI_MODEL=gpt-5.6
```

If no model is supplied, the application uses its configured default.

The maximum autonomous execution steps are configured using:

```env
MAX_STEPS=10
```

---

# 11. OpenAI Client

V1 uses the OpenAI Python client.

Conceptually:

```python
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
```

The LLM receives the conversation and returns the next action.

The model is not directly connected to Docker.

Instead:

```text
LLM
 |
 | generates command
 v
agent.py
 |
 | sends command
 v
SandboxManager
 |
 v
Docker
```

This separation is important because the agent application remains responsible for execution.

---

# 12. System Prompt

The system prompt defines the behavior of the autonomous coding agent.

The key requirements are:

* Work inside `/sandbox`.
* Create files inside `/sandbox`.
* Execute code inside `/sandbox`.
* Inspect command output.
* Analyze errors.
* Fix failures.
* Verify the task.
* Return one shell command per step.
* Return `DONE` only after verification.

The fundamental instruction is:

```text
PLAN
EXECUTE
OBSERVE
FIX
VERIFY
```

The LLM therefore operates as an iterative coding agent.

---

# 13. V1 Agent Loop

The most important component of V1 is the autonomous loop.

The flow is:

```text
START
  |
  v
Create Sandbox
  |
  v
Send User Task to LLM
  |
  v
LLM Generates Command
  |
  v
Execute Command
  |
  v
Capture Result
  |
  v
Send Result to LLM
  |
  +------ Command required ------+
  |                              |
  |                              v
  |                         Execute Again
  |
  +------ DONE ------------------+
                 |
                 v
             Task Complete
                 |
                 v
          Destroy Sandbox
```

---

# 14. Step-by-Step Execution

## Step 1 — User enters task

Example:

```text
Create hello.py that prints "Hello from Sandbox",
execute it, and verify that the file exists.
```

---

## Step 2 — Task ID is generated

Example:

```text
task-483c37f8fcf2
```

---

## Step 3 — Logger is initialized

The logger creates task-specific log files.

```text
logs/task-483c37f8fcf2.log
logs/task-483c37f8fcf2.jsonl
```

---

## Step 4 — Docker sandbox is created

The application creates an isolated Docker container.

The working directory is:

```text
/sandbox
```

The AI operates inside this workspace.

---

# 15. Why `/sandbox` Exists

The `/sandbox` directory is the designated workspace for AI-generated work.

The agent's system prompt tells the model:

```text
Your current working directory is:

/sandbox
```

The agent should create files such as:

```text
hello.py
project/main.py
outputs/result.json
```

rather than creating files in host-level directories.

The workspace boundary is a fundamental part of the V1 architecture.

---

# 16. LLM Command Generation

After the sandbox is created, the LLM receives the task.

For example, it may generate:

```bash
printf '%s\n' 'print("Hello from Sandbox")' > hello.py
```

V1 does not have a dedicated filesystem tool.

The LLM therefore expresses its desired operation as a shell command.

---

# 17. Command Execution

The generated command is passed to:

```text
SandboxManager
```

The command executes inside the Docker container.

The host machine does not execute the generated command directly.

The execution result contains:

```text
stdout
stderr
return code
success
```

Example:

```text
return_code = 0
success = true

stdout:
Hello from Sandbox
```

---

# 18. Observation

The command result is converted into an observation and added back to the conversation.

The LLM receives information similar to:

```text
STEP: 1

WORKING DIRECTORY:
/sandbox

COMMAND:
python3 hello.py

EXIT CODE:
0

SUCCESS:
True

STDOUT:
Hello from Sandbox

STDERR:

You must now decide the next action.
```

This allows the model to reason about what happened.

---

# 19. Error Handling

If a command fails, the result is returned to the LLM.

Example:

```text
EXIT CODE:
1

SUCCESS:
False

STDERR:
python3: can't open file 'hello.py'
```

The agent increments its error/retry counters.

The LLM then receives the error and can generate another command.

Example:

```text
ls -la
```

followed by a corrective command.

This creates the recovery loop:

```text
Command
   |
   v
Failure
   |
   v
Error Observation
   |
   v
LLM Analysis
   |
   v
Corrective Command
   |
   v
Execution
```

---

# 20. Error and Retry Counters

V1 maintains:

```text
error_count
retry_count
```

When a command fails:

```text
error_count += 1
retry_count += 1
```

These values are included in the final task summary.

Important distinction:

* `error_count` represents observed execution errors.
* `retry_count` represents attempts made after failures.

---

# 21. Maximum Steps

The agent cannot execute indefinitely.

The configured limit is:

```env
MAX_STEPS=10
```

The loop continues while:

```text
step_number < MAX_STEPS
```

If the agent reaches the maximum number of steps without returning `DONE`, the task is marked:

```text
INCOMPLETE
```

This protects the application from uncontrolled autonomous execution.

---

# 22. Completion Detection

The V1 agent expects the model to return:

```text
DONE
```

when the task is completely finished and verified.

The application checks:

```python
if ai_response == "DONE":
```

When this happens:

```text
AGENT_DONE
```

is logged and the task is considered successful.

---

# 23. Important Completion Rule

The model is explicitly instructed not to return `DONE` before verification.

For example, if the user requests:

```text
Create hello.py and execute it.
```

the agent should not simply create the file and stop.

It should:

```text
Create file
    |
    v
Execute file
    |
    v
Observe output
    |
    v
Verify result
    |
    v
DONE
```

This is the foundation of reliable autonomous execution.

---

# 24. Token Accounting

V1 records token usage returned by the LLM API.

The application tracks:

```text
Input Tokens
Output Tokens
Total Tokens
```

For multiple LLM calls, these are accumulated.

Example:

```text
Step 1
Input: 371
Output: 71
Total: 442

Step 2
Input: 532
Output: 4
Total: 536
```

The final task summary aggregates all requests.

---

# 25. Task Metrics

V1 tracks several execution metrics:

```text
Steps
LLM Calls
Input Tokens
Output Tokens
Total Tokens
Errors
Retries
Duration
Status
```

These metrics are useful for:

* Debugging
* Cost analysis
* Performance analysis
* Agent behavior analysis
* Future optimization

---

# 26. Logging Architecture

V1 produces two primary log formats.

## Human-readable log

```text
logs/<task-id>.log
```

This is intended for developers and operators.

Example:

```text
2026-09-25 08:15:00 | INFO | TASK_STARTED
```

## JSONL trace

```text
logs/<task-id>.jsonl
```

Each line represents a structured event.

Conceptually:

```json
{
  "timestamp": "...",
  "task_id": "task-...",
  "event": "TASK_STARTED"
}
```

The JSONL format is useful for:

* Log processing
* Analytics
* Debugging
* Observability systems
* Future dashboards

---

# 27. Typical V1 Events

A successful task can generate events such as:

```text
TASK_STARTED
SANDBOX_CREATE_START
SANDBOX_CREATED
SANDBOX_WORKSPACE_READY
AGENT_READY

STEP_STARTED
LLM_CALL_START
LLM_CALL_FINISHED
COMMAND_GENERATED
TOOL_CALL_START
TOOL_CALL_FINISHED
STEP_SUCCESS
OBSERVATION_SENT_TO_AGENT

AGENT_DONE

TASK_SUMMARY
SANDBOX_DESTROY_START
SANDBOX_DESTROYED
PROCESS_FINISHED
```

The exact event names depend on the implementation version.

---

# 28. Example V1 Task

User:

```text
Create hello.py that prints "Hello from Sandbox",
execute it, and verify that the file exists.
```

Possible LLM command:

```bash
printf '%s\n' 'print("Hello from Sandbox")' > hello.py && \
python3 hello.py && \
test -f hello.py && \
ls -l hello.py
```

Execution:

```text
Hello from Sandbox
-rw-r--r-- 1 root root 28 hello.py
```

The LLM observes the result and returns:

```text
DONE
```

The agent then completes the task.

---

# 29. V1 End-to-End Flow

The complete lifecycle is:

```text
                    USER
                      |
                      v
                Task Prompt
                      |
                      v
                run_task()
                      |
                      v
                Generate Task ID
                      |
                      v
                Create Logger
                      |
                      v
              Create Docker Sandbox
                      |
                      v
              Initialize Conversation
                      |
                      v
                  LLM Call
                      |
                      v
             Generate Shell Command
                      |
                      v
             SandboxManager.execute()
                      |
                      v
              Docker Container
                      |
                      v
             stdout/stderr/exit code
                      |
                      v
              Build Observation
                      |
                      v
               Send to LLM
                      |
             +--------+--------+
             |                 |
             v                 v
        More Work             DONE
             |                 |
             |                 v
             |             Task Success
             |                 |
             +<----------------+
                               |
                               v
                       Task Summary
                               |
                               v
                       Destroy Sandbox
                               |
                               v
                              END
```

---

# 30. Security Boundary

The fundamental V1 security concept is Docker isolation.

The intended architecture is:

```text
Host Machine
     |
     | Docker
     v
+---------------------+
| Isolated Container  |
|                     |
| /sandbox            |
|                     |
| AI-generated work   |
+---------------------+
```

The AI-generated command should execute inside the container rather than directly on the host.

The system prompt also restricts the intended workspace to:

```text
/sandbox
```

---

# 31. V1 Security Limitations

V1 should be considered a foundation rather than a hardened production execution environment.

Because V1 uses raw shell commands generated by the model, additional security controls may be required before exposing it to untrusted users or high-risk workloads.

Potential future controls include:

* Command allowlists/denylists.
* Resource limits.
* CPU limits.
* Memory limits.
* Process limits.
* Network restrictions.
* Filesystem restrictions.
* Container capability restrictions.
* Read-only base filesystem.
* Non-root execution.
* Execution timeouts.
* Output size limits.
* Native tool interfaces.

These improvements are addressed progressively in later versions.

---

# 32. V1 Installation

Create a Python environment:

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

Verify Docker:

```bash
docker --version
```

Verify Python:

```bash
python --version
```

---

# 33. Environment Setup

Create:

```text
.env
```

Example:

```env
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_MODEL=gpt-5.6
MAX_STEPS=10
```

Never commit API keys to source control.

Add `.env` to `.gitignore`.

---

# 34. Running V1

Activate the environment:

```bash
source .venv/bin/activate
```

Run:

```bash
python agent.py
```

The application displays:

```text
============================================
        AI SANDBOX AGENT V1
============================================
Model: gpt-5.6
Max steps: 10
Workspace: /sandbox
```

Then:

```text
You:
```

Enter the task.

Example:

```text
Create hello.py that prints "Hello from Sandbox", execute it, and verify that the file exists.
```

---

# 35. Example Interactive Session

```text
You: Create hello.py that prints "Hello from Sandbox", execute it, and verify that the file exists.
```

The agent creates a Docker sandbox.

The model generates a command.

The command is executed inside `/sandbox`.

The result is returned to the model.

The model continues until verification is complete.

Finally:

```text
AI: Task completed.
```

---

# 36. Failure Scenario

Suppose the model generates:

```bash
python3 missing.py
```

The container returns:

```text
python3: can't open file 'missing.py'
```

The agent records the failure:

```text
STEP_ERROR
```

The error is added to the conversation.

The LLM can then decide to inspect the workspace:

```bash
ls -la
```

and subsequently create or execute the correct file.

---

# 37. V1 Task Status

A task can end in different states.

## SUCCESS

The agent returned:

```text
DONE
```

and the task completed.

## INCOMPLETE

The agent reached:

```text
MAX_STEPS
```

without completing the task.

## LLM ERROR

The OpenAI request failed.

## SANDBOX ERROR

The Docker sandbox could not be created or managed.

---

# 38. Why V1 Was Built First

V1 establishes the basic autonomous agent execution architecture without introducing a complicated tool abstraction.

The initial architecture is intentionally simple:

```text
LLM
 |
 | shell command
 v
Sandbox
 |
 | result
 v
LLM
```

This makes it useful as a baseline implementation for evaluating:

* Autonomous execution.
* Prompt design.
* Docker isolation.
* Error recovery.
* LLM token usage.
* Agent step behavior.
* Execution latency.

---

# 39. V1 Limitations

The most important architectural limitation is that the LLM communicates with the environment through raw shell commands.

For example:

```bash
cat hello.py
```

rather than a structured operation such as:

```json
{
  "tool": "filesystem.read",
  "arguments": {
    "path": "hello.py"
  }
}
```

This means the model must reason about shell syntax.

It also makes it more difficult to:

* Validate operations.
* Apply per-tool permissions.
* Validate arguments.
* Audit high-level operations.
* Add structured tools.
* Control dangerous commands.

These limitations motivated the V3 tool architecture.

---

# 40. Evolution Toward V2

V2 builds on V1 by strengthening the sandbox workspace model.

The key concept becomes:

```text
/sandbox
├── files/
├── outputs/
└── artifacts/
```

This provides clearer separation between workspace areas.

V2 also introduces stronger workspace initialization and lifecycle management.

---

# 41. Evolution Toward V2.2

V2.2 fixes the sandbox workspace creation sequence.

The important lifecycle becomes:

```text
Create Container
       |
       v
Ensure /sandbox exists
       |
       v
Initialize workspace
       |
       v
Execute Agent
```

This avoids attempting to execute a command with `/sandbox` as the working directory before `/sandbox` exists.

---

# 42. Evolution Toward V2.3

V2.3 introduces persistent artifact collection.

Instead of losing files when the Docker container is destroyed, task outputs are copied to the host.

Example:

```text
artifacts/
└── task-734fdf8e98d2/
    ├── hello.py
    └── manifest.json
```

The container remains temporary.

The artifacts become persistent.

Architecture:

```text
Temporary Docker Sandbox
        |
        | collect
        v
Host Artifact Directory
        |
        v
artifacts/<task-id>/
```

---

# 43. Evolution Toward V3

V3 replaces raw shell-command generation as the primary agent interface with a structured tool registry.

Instead of:

```text
LLM
 |
 v
Shell Command
```

V3 introduces:

```text
LLM
 |
 v
Tool Selection
 |
 v
Tool Registry
 |
 +-- filesystem.write
 +-- filesystem.read
 +-- filesystem.list
 +-- python.run
 +-- terminal.exec
 |
 v
Sandbox
```

This provides a cleaner foundation for future tool calling.

---

# 44. V1 vs V2 vs V3

| Capability           |    V1 |       V2 |     V2.3 |         V3 |
| -------------------- | ----: | -------: | -------: | ---------: |
| Docker sandbox       |   Yes |      Yes |      Yes |        Yes |
| `/sandbox` workspace |   Yes |      Yes |      Yes |        Yes |
| Autonomous loop      |   Yes |      Yes |      Yes |        Yes |
| Raw shell commands   |   Yes |      Yes |      Yes |    Reduced |
| Persistent artifacts |    No |       No |      Yes |        Yes |
| Artifact manifest    |    No |       No |      Yes |        Yes |
| Structured tools     |    No |       No |       No |        Yes |
| Filesystem tools     |    No |       No |       No |        Yes |
| Python tool          |    No |       No |       No |        Yes |
| Terminal tool        |    No |       No |       No |        Yes |
| Path validation      | Basic | Improved | Improved | Tool-level |
| Tool registry        |    No |       No |       No |        Yes |

---

# 45. Recommended V1 Use Cases

V1 is suitable for controlled experiments involving:

### Coding Tasks

```text
Create a Python script.
Run the script.
Fix an error.
Verify the result.
```

### File Generation

```text
Create a JSON configuration file.
```

### Debugging

```text
Run the program and fix the error.
```

### Data Processing

```text
Create a Python script that processes a CSV file.
```

### Environment Experiments

```text
Check which Python version is available.
```

### Autonomous Verification

```text
Create a file and verify that it exists.
```

---

# 46. Example Coding Workflow

A typical coding task looks like:

```text
User Task
   |
   v
LLM analyzes requirement
   |
   v
Generate shell command
   |
   v
Create source file
   |
   v
Run source file
   |
   v
Observe error/output
   |
   v
Fix if necessary
   |
   v
Run again
   |
   v
Verify
   |
   v
DONE
```

---

# 47. Operational Considerations

For development environments, monitor:

```text
Docker containers
CPU usage
Memory usage
Disk usage
LLM token usage
Execution duration
Number of steps
Number of failures
```

Particularly important are:

* Docker disk usage.
* Container cleanup.
* Log growth.
* API token usage.

Temporary containers should not accumulate indefinitely.

---

# 48. Troubleshooting

## Docker is unavailable

Check:

```bash
docker --version
```

Then:

```bash
docker ps
```

---

## OpenAI API key problem

Check:

```bash
echo $OPENAI_API_KEY
```

Do not print the key in shared logs or documentation.

---

## Sandbox creation failure

Inspect Docker:

```bash
docker ps -a
```

Check Docker daemon availability and container configuration.

---

## Agent reaches maximum steps

Review:

```text
logs/<task-id>.log
logs/<task-id>.jsonl
```

Look for:

```text
STEP_STARTED
COMMAND_GENERATED
STEP_ERROR
OBSERVATION_SENT_TO_AGENT
MAX_STEPS_REACHED
```

---

## Agent repeatedly generates incorrect commands

Inspect the LLM responses in:

```text
logs/<task-id>.jsonl
```

Review the system prompt and observation formatting.

---

# 49. Debugging Strategy

When debugging V1, use the task ID.

Example:

```text
task-483c37f8fcf2
```

Then inspect:

```bash
cat logs/task-483c37f8fcf2.log
```

For structured events:

```bash
cat logs/task-483c37f8fcf2.jsonl
```

The JSONL trace is especially useful for reconstructing the exact agent lifecycle.

---

# 50. Production Readiness

V1 should be treated as an experimental/foundation architecture rather than a fully hardened production execution system.

Before production deployment, consider implementing:

```text
[ ] Resource limits
[ ] Command restrictions
[ ] Network policy
[ ] Container capability restrictions
[ ] Non-root execution
[ ] Execution timeout
[ ] Output limits
[ ] Rate limiting
[ ] Authentication
[ ] Authorization
[ ] Persistent artifact storage
[ ] Structured tool interface
[ ] Security auditing
[ ] Monitoring
[ ] Alerting
[ ] Cleanup policies
```

---

# 51. Development Philosophy

The architecture evolves incrementally.

The intended progression is:

```text
V1
Simple autonomous shell execution
        |
        v
V2
Stronger sandbox/workspace lifecycle
        |
        v
V2.3
Persistent artifact collection
        |
        v
V3
Structured tool registry
        |
        v
Future
Native tool calling + production controls
```

Each version should preserve the working behavior of the previous version while introducing one major architectural improvement.

---

# 52. V1 Design Principle

The central principle of V1 is:

> The LLM decides what should happen; the sandbox controls where it happens.

The LLM is responsible for reasoning and command generation.

The sandbox is responsible for execution isolation.

The agent orchestrator is responsible for connecting the two.

---

# 53. Complete V1 Lifecycle

```text
Application Start
       |
       v
Load Environment
       |
       v
Initialize OpenAI Client
       |
       v
Wait for User Task
       |
       v
Generate Task ID
       |
       v
Initialize Logger
       |
       v
Create Docker Sandbox
       |
       v
Initialize Conversation
       |
       v
+---------------------------+
|       AGENT LOOP          |
|                           |
|  LLM Request              |
|       |                   |
|       v                   |
|  Command Generated        |
|       |                   |
|       v                   |
|  Execute in Docker        |
|       |                   |
|       v                   |
|  Capture Result           |
|       |                   |
|       v                   |
|  Send Observation         |
|       |                   |
|       +----> Continue     |
|       |                   |
|       +----> DONE         |
+---------------------------+
       |
       v
Calculate Metrics
       |
       v
Write Task Summary
       |
       v
Destroy Docker Sandbox
       |
       v
Process Finished
```

---

# 54. Summary

Sandbox AI Agent V1 is the foundational implementation of the project.

It establishes the core autonomous execution loop:

```text
User
→ Agent
→ LLM
→ Shell Command
→ Docker Sandbox
→ Observation
→ LLM
→ Repeat
→ DONE
```

Its most important contributions are:

1. Autonomous task execution.
2. Docker-based isolation.
3. `/sandbox` workspace.
4. Iterative LLM reasoning.
5. Command execution and observation.
6. Error recovery.
7. Maximum-step protection.
8. Token accounting.
9. Structured task logging.
10. Clear separation between reasoning and execution.

V1 intentionally uses raw shell commands because the primary objective was to validate the autonomous sandbox execution architecture.

Later versions build on this foundation:

```text
V1
  |
  | Sandbox execution
  v
V2
  |
  | Workspace lifecycle
  v
V2.3
  |
  | Persistent artifacts
  v
V3
  |
  | Structured tool registry
  v
Future
  |
  | Native tool calling
  | Security hardening
  | Additional tools
  | Production orchestration
```

---

# 55. Version Information

```text
Project: Sandbox AI Agent
Documentation: V1
Architecture: Autonomous LLM + Docker Sandbox
Execution: Raw Shell Commands
Workspace: /sandbox
Artifact Persistence: Not part of original V1
Tool Registry: Not part of V1
Status: Foundation / Legacy Version
```

This document should remain associated with the V1 implementation as historical architecture documentation. Later versions should have separate documentation so that the evolution of the system remains clear.
