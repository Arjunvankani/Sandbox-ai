# AI Sandbox Agent — V2

A production-oriented autonomous coding agent that executes user tasks inside an isolated Docker sandbox.

Version 2 introduces a structured sandbox workspace, autonomous multi-step execution, task-level logging, verification, error handling, and persistent artifact collection.

---

# 1. Overview

The AI Sandbox Agent is designed to allow an LLM to perform coding and file-based tasks inside an isolated execution environment.

The agent receives a natural-language task such as:

```text
Create hello.py that prints "Hello from Sandbox", execute it, and verify that the file exists.
```

The agent then:

1. Creates a dedicated Docker sandbox.
2. Creates the `/sandbox` workspace.
3. Sends the task to the LLM.
4. Receives one shell command.
5. Executes the command inside Docker.
6. Captures stdout, stderr, and exit code.
7. Sends the execution result back to the LLM.
8. Allows the LLM to determine the next action.
9. Continues until the task is verified.
10. Collects generated artifacts.
11. Copies artifacts to persistent host storage.
12. Creates an artifact manifest.
13. Generates task logs and execution traces.
14. Destroys the temporary Docker container.

The important design principle is:

```text
LLM does not execute commands directly on the host.
```

Instead:

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
Generated Command
  |
  v
SandboxManager
  |
  v
Docker Container
  |
  v
/sandbox
```

---

# 2. Version

```text
Version: V2
Workspace: /sandbox
Execution: Docker
Agent Mode: Autonomous
Command Interface: Shell commands
Artifact Storage: Persistent host directory
Logging: Text + JSONL
```

V2 is an important architectural step between the basic V1 implementation and the tool-based architecture introduced later.

---

# 3. Goals of V2

V2 was designed around the following goals.

## 3.1 Isolated execution

User-generated or LLM-generated commands must execute inside a Docker container rather than directly on the EC2 host.

## 3.2 Dedicated workspace

Every task receives a dedicated workspace:

```text
/sandbox
```

The agent should operate inside this directory.

## 3.3 Autonomous execution

The LLM determines the sequence of operations required to complete a task.

For example:

```text
Create file
   |
   v
Execute file
   |
   v
Inspect result
   |
   v
Verify file
   |
   v
DONE
```

## 3.4 Verification

The agent should not declare success merely because a command succeeds.

The actual task must be verified.

For example:

```text
python3 hello.py
```

returning:

```text
Hello from Sandbox
```

is useful, but the agent may still need to verify:

```text
test -f hello.py
```

## 3.5 Error handling

If a command fails, the result is returned to the LLM.

The LLM can then:

```text
OBSERVE
   |
   v
ANALYZE ERROR
   |
   v
FIX
   |
   v
RETRY
```

## 3.6 Persistent artifacts

Files generated during the task should survive destruction of the Docker container.

For example:

```text
Container:
/sandbox/hello.py

        |
        | artifact collection
        v

Host:
/home/ec2-user/sandbox-ai/artifacts/<task-id>/hello.py
```

This allows users to access generated files after the sandbox has been destroyed.

---

# 4. V2 Architecture

The V2 architecture consists of several logical components.

```text
                         +----------------+
                         |     USER       |
                         +-------+--------+
                                 |
                                 v
                         +----------------+
                         |    agent.py    |
                         +-------+--------+
                                 |
                                 v
                         +----------------+
                         |   OpenAI LLM   |
                         +-------+--------+
                                 |
                         Generated command
                                 |
                                 v
                     +------------------------+
                     |    SandboxManager      |
                     +-----------+------------+
                                 |
                                 v
                     +------------------------+
                     |    Docker Container    |
                     |                        |
                     |      /sandbox          |
                     |       /files            |
                     |       /outputs          |
                     |       /artifacts        |
                     +-----------+------------+
                                 |
                                 v
                         Command execution
                                 |
                                 v
                         stdout / stderr
                                 |
                                 v
                         agent.py observation
                                 |
                                 v
                            OpenAI LLM
```

After successful completion:

```text
Docker Sandbox
      |
      | artifact collection
      v
Host artifacts/
      |
      +-- task-xxxx/
           |
           +-- generated files
           |
           +-- manifest.json
```

---

# 5. V2 Project Structure

A typical V2 project contains:

```text
sandbox-ai/
│
├── agent.py
├── sandbox_manager.py
├── logger.py
├── .env
├── requirements.txt
│
├── artifacts/
│
├── logs/
│
└── README.md
```

Additional testing files may exist depending on the V2 implementation.

---

# 6. File Responsibilities

## 6.1 `agent.py`

This is the main application entry point.

Responsibilities include:

* loading environment variables
* initializing the OpenAI client
* defining the system prompt
* creating task IDs
* creating the logger
* creating the sandbox
* maintaining the LLM conversation
* calling the LLM
* executing generated commands
* collecting stdout/stderr
* sending observations back to the LLM
* handling retries
* determining task completion
* collecting artifacts
* generating the final task summary
* destroying the sandbox

Run the agent using:

```bash
python agent.py
```

---

# 7. `sandbox_manager.py`

`SandboxManager` controls the Docker execution environment.

Its responsibilities include:

```text
Create container
     |
     v
Prepare /sandbox
     |
     v
Execute commands
     |
     v
Collect artifacts
     |
     v
Destroy container
```

The sandbox manager isolates task execution from the host machine.

---

# 8. Docker Sandbox

Each task receives a separate Docker container.

Example:

```text
agent-sandbox-4fad4657
```

The container has:

```text
/sandbox
```

as its working directory.

The sandbox workspace contains directories such as:

```text
/sandbox/
├── files/
├── outputs/
└── artifacts/
```

Task-specific files are created inside `/sandbox`.

---

# 9. Workspace Rule

The V2 system prompt instructs the LLM that:

```text
Your current working directory is:

/sandbox
```

Task files should be created inside:

```text
/sandbox
```

Examples:

```text
hello.py
project/
project/main.py
outputs/result.json
```

The agent explicitly discourages use of unrelated host directories such as:

```text
/root
/workspace
/tmp
/home
/etc
```

unless explicitly required by the user.

This establishes a clear workspace boundary.

---

# 10. Autonomous Agent Loop

The core V2 execution model is:

```text
PLAN
  |
  v
EXECUTE
  |
  v
OBSERVE
  |
  v
FIX
  |
  v
VERIFY
  |
  v
DONE
```

The LLM is called repeatedly.

Each call must return either:

```text
ONE shell command
```

or:

```text
DONE
```

---

# 11. Example Execution

User:

```text
Create hello.py that prints "Hello from Sandbox", execute it,
and verify that the file exists.
```

The LLM might generate:

```bash
printf '%s\n' 'print("Hello from Sandbox")' > hello.py && python3 hello.py && test -f hello.py && ls -l hello.py
```

The command is executed inside:

```text
/sandbox
```

The sandbox returns:

```text
Hello from Sandbox
-rw-r--r--. 1 root root 28 Sep 25 08:15 hello.py
```

The observation is then sent back to the LLM.

The LLM may respond:

```text
DONE
```

The task is then marked successful.

---

# 12. Multi-Step Execution

The LLM is not required to complete everything in a single command.

For example:

```text
Step 1
Create hello.py

Step 2
Run hello.py

Step 3
Verify hello.py exists

Step 4
DONE
```

The agent maintains the conversation history between steps.

Conceptually:

```text
LLM
 |
 | command
 v
Sandbox
 |
 | result
 v
Agent
 |
 | observation
 v
LLM
 |
 | next command
 v
Sandbox
```

This loop continues until:

```text
DONE
```

or the maximum number of steps is reached.

---

# 13. Maximum Steps

The default maximum number of steps is:

```text
10
```

This is controlled by:

```bash
MAX_STEPS
```

Environment variable.

Example:

```env
MAX_STEPS=10
```

The purpose of the limit is to prevent an agent from running indefinitely.

If the maximum number of steps is reached without completion, the task is marked:

```text
INCOMPLETE
```

---

# 14. Environment Configuration

V2 uses a `.env` file.

Example:

```env
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-5.6
MAX_STEPS=10
```

The application loads these values using:

```python
load_dotenv()
```

---

# 15. OpenAI Client

V2 uses the OpenAI Python SDK.

The client is initialized using:

```python
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
```

The model is configured through:

```env
OPENAI_MODEL=gpt-5.6
```

If no model is specified, the application uses:

```text
gpt-5.6
```

as the default.

---

# 16. LLM Communication

The LLM receives a system prompt defining the agent's operating rules.

The initial conversation contains:

```text
System message
+
User task
```

After every command execution, the agent adds:

```text
Assistant:
generated command

User:
execution observation
```

This creates an iterative execution history.

---

# 17. Observation Format

After executing a command, the agent sends an observation containing:

```text
STEP
WORKING DIRECTORY
COMMAND
EXIT CODE
SUCCESS
STDOUT
STDERR
```

Example:

```text
STEP: 2

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

This allows the LLM to reason from actual execution results.

---

# 18. Error Handling

Command execution produces:

```text
return code
stdout
stderr
success
```

For example:

```text
return_code = 1
success = False
stderr = "File not found"
```

The agent records the error.

The observation is then sent to the LLM.

The LLM can generate a corrective command.

Example:

```text
Command 1:
python3 app.py

Error:
python3: can't open file 'app.py'

Command 2:
ls -la

Command 3:
python3 main.py

Command 4:
DONE
```

The exact behavior depends on the task and LLM response.

---

# 19. Retry Tracking

V2 maintains:

```text
error_count
retry_count
```

Whenever an execution step fails:

```text
error_count += 1
retry_count += 1
```

These values are included in the task summary.

Example:

```text
Errors        : 1
Retries       : 1
```

---

# 20. Task IDs

Every task receives a unique ID.

Example:

```text
task-734fdf8e98d2
```

The ID is used to associate:

* logs
* artifacts
* manifest
* task execution
* metrics

with a single execution.

---

# 21. Logging

V2 provides two types of task logs.

## Human-readable log

```text
logs/task-734fdf8e98d2.log
```

## Machine-readable JSONL trace

```text
logs/task-734fdf8e98d2.jsonl
```

---

# 22. Log Events

The agent records events such as:

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

This provides a complete execution trail.

---

# 23. Token Tracking

V2 tracks LLM token usage.

The agent records:

```text
Input Tokens
Output Tokens
Total Tokens
```

For every LLM call.

At the end these are aggregated.

Example:

```text
Input Tokens  : 2029
Output Tokens : 86
Total Tokens  : 2115
```

This provides visibility into model usage.

---

# 24. Execution Timing

V2 measures execution duration.

Timing is recorded for:

* LLM requests
* sandbox creation
* command execution
* complete task execution

Example:

```text
Duration      : 6.76s
```

This is useful for performance monitoring.

---

# 25. Artifact Collection

One of the major V2 improvements is persistent artifact collection.

The Docker container is temporary.

Therefore:

```text
Container
    |
    | destroyed
    v
Files would normally disappear
```

V2 prevents this by copying task artifacts to the host before destroying the container.

---

# 26. Artifact Directory

Each task receives its own artifact directory:

```text
artifacts/<task-id>/
```

Example:

```text
artifacts/task-734fdf8e98d2/
```

Inside:

```text
hello.py
manifest.json
```

---

# 27. Artifact Persistence

Example:

```text
Docker:

/sandbox/hello.py
```

is copied to:

```text
/home/ec2-user/sandbox-ai/artifacts/task-734fdf8e98d2/hello.py
```

After Docker destruction, the host copy remains.

Therefore:

```text
Docker lifecycle:

CREATE
  |
RUN
  |
COLLECT
  |
DESTROY

Host artifact lifecycle:

CREATE
  |
PERSIST
  |
AVAILABLE AFTER CONTAINER DESTRUCTION
```

---

# 28. Artifact Manifest

Every successful task generates:

```text
manifest.json
```

Example:

```json
{
  "task_id": "task-734fdf8e98d2",
  "container": "agent-sandbox-b41c2f83",
  "workspace": "/sandbox",
  "artifact_directory": "/home/ec2-user/sandbox-ai/artifacts/task-734fdf8e98d2",
  "count": 1,
  "artifacts": [
    {
      "path": "/sandbox/hello.py",
      "relative_path": "hello.py",
      "host_path": "/home/ec2-user/sandbox-ai/artifacts/task-734fdf8e98d2/hello.py",
      "type": "python"
    }
  ]
}
```

---

# 29. Artifact Metadata

Each artifact contains metadata such as:

```text
path
relative_path
host_path
type
```

Example:

```text
path:
    /sandbox/hello.py

relative_path:
    hello.py

host_path:
    /home/ec2-user/sandbox-ai/artifacts/task-734fdf8e98d2/hello.py

type:
    python
```

This allows another application to consume artifact information without scanning the filesystem.

---

# 30. Artifact Types

The artifact collector identifies file types.

For example:

```text
.py       -> python
.json     -> json
.md       -> markdown
.txt      -> text
.csv      -> csv
.js       -> javascript
.html     -> html
.css      -> css
```

The exact supported mapping depends on the implementation.

Unknown extensions can be treated as generic files.

---

# 31. Artifact Collection Flow

The collection process is:

```text
Task Completed
      |
      v
ARTIFACT_COLLECTION_START
      |
      v
find /sandbox -type f
      |
      v
Identify generated files
      |
      v
Copy files to host
      |
      v
Generate manifest.json
      |
      v
ARTIFACT_COLLECTION_FINISHED
```

---

# 32. Artifact Exclusion

Internal sandbox artifact directories should not be recursively collected as user artifacts.

The collector therefore excludes the sandbox's internal artifact directory where applicable.

This prevents:

```text
artifact
  -> artifact
      -> artifact
          -> ...
```

style recursive collection.

---

# 33. Successful V2 Example

A successful task produces:

```text
============================================================
TASK SUMMARY
============================================================
Task ID       : task-734fdf8e98d2
Sandbox       : agent-sandbox-b41c2f83
Workspace     : /sandbox
Steps         : 4
LLM Calls     : 4
Input Tokens  : 2029
Output Tokens : 86
Total Tokens  : 2115
Errors        : 0
Retries       : 0
Artifacts     : 1
Duration      : 6.76s
Status        : SUCCESS

Artifacts:
  - /sandbox/hello.py [python]
============================================================
```

---

# 34. Persistent Host Output

After the task finishes:

```bash
ls -lah artifacts/task-734fdf8e98d2/
```

Example:

```text
total 8.0K
drwxr-xr-x. 2 ec2-user ec2-user  43 Sep 25 08:20 .
drwxr-xr-x. 3 ec2-user ec2-user  31 Sep 25 08:20 ..
-rw-r--r--. 1 ec2-user ec2-user  28 Sep 25 08:20 hello.py
-rw-r--r--. 1 ec2-user ec2-user 411 Sep 25 08:20 manifest.json
```

The generated file remains available even though the Docker container has been removed.

---

# 35. How to Install V2

Navigate to the project:

```bash
cd ~/sandbox-ai
```

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

---

# 36. Environment Setup

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

Never commit the real API key to Git.

---

# 37. Validate Python Files

Before running the application:

```bash
python -m py_compile agent.py
python -m py_compile sandbox_manager.py
python -m py_compile logger.py
```

If all commands return without an error, the files are syntactically valid.

---

# 38. Run V2

Start the agent:

```bash
python agent.py
```

The application displays:

```text
============================================
        AI SANDBOX AGENT V2
============================================
Model: gpt-5.6
Max steps: 10
Workspace: /sandbox
```

Then enter a task.

Example:

```text
Create hello.py that prints "Hello from Sandbox", execute it, and verify that the file exists.
```

---

# 39. Interactive Usage

The expected interaction is:

```text
You: Create hello.py that prints "Hello from Sandbox", execute it, and verify that the file exists.
```

The agent then executes the task autonomously.

A successful execution eventually displays:

```text
AI: Task completed.
```

followed by the task summary.

---

# 40. Checking Artifacts

After completion:

```bash
ls -lah artifacts/
```

Find the task directory:

```bash
ls -lah artifacts/task-<task-id>/
```

Read the generated file:

```bash
cat artifacts/task-<task-id>/hello.py
```

Read the manifest:

```bash
cat artifacts/task-<task-id>/manifest.json
```

---

# 41. Checking Logs

List logs:

```bash
ls -lah logs/
```

Human-readable log:

```bash
cat logs/task-<task-id>.log
```

Machine-readable execution trace:

```bash
cat logs/task-<task-id>.jsonl
```

---

# 42. V2 Testing Strategy

V2 should be tested using increasingly complex tasks.

## Test 1 — File Creation

```text
Create hello.py containing a Hello World program.
```

Expected:

```text
hello.py
```

---

## Test 2 — File Creation + Execution

```text
Create hello.py, execute it, and verify its output.
```

Expected:

```text
Hello...
```

---

## Test 3 — Verification

```text
Create hello.py, execute it, and verify that the file exists.
```

Expected:

```text
file exists
```

---

## Test 4 — Multiple Files

```text
Create a Python project with main.py and utils.py.
Run main.py and verify the result.
```

Expected artifacts:

```text
main.py
utils.py
```

---

## Test 5 — Error Recovery

```text
Create a Python program with an intentional syntax error,
detect the error, fix it, execute it, and verify the output.
```

The agent should:

```text
create
  |
run
  |
error
  |
analyze
  |
fix
  |
run again
  |
verify
```

---

## Test 6 — Nested Project

```text
Create project/app/main.py and execute it.
```

Expected:

```text
project/
└── app/
    └── main.py
```

---

# 43. Security Model

V2 provides isolation primarily through Docker.

The execution model is:

```text
Host
 |
 +---- Agent
 |
 +---- Docker Sandbox
          |
          +---- /sandbox
```

The LLM-generated commands execute inside the container.

The system prompt also restricts normal task operations to `/sandbox`.

---

# 44. Path Safety

The sandbox should prevent task operations from escaping the intended workspace.

The intended model is:

```text
/sandbox/project/file.py
```

Allowed.

Paths such as:

```text
../../etc/passwd
```

should not be allowed by workspace-aware filesystem operations.

This concept becomes even more explicit in the V3 tool registry.

---

# 45. Container Lifecycle

Each task has an independent container.

```text
TASK START
    |
    v
CREATE CONTAINER
    |
    v
PREPARE WORKSPACE
    |
    v
RUN AGENT
    |
    v
COLLECT ARTIFACTS
    |
    v
CREATE MANIFEST
    |
    v
DESTROY CONTAINER
    |
    v
TASK COMPLETE
```

This means one task's sandbox is not intended to become the persistent workspace for another task.

---

# 46. Failure Scenarios

## Sandbox creation failure

If Docker cannot create the sandbox, the task cannot proceed.

Example:

```text
TASK_FATAL_ERROR
```

---

## LLM failure

If the LLM API request fails, the agent logs:

```text
LLM_ERROR
```

and the task does not falsely report success.

---

## Command failure

A failed command generates:

```text
STEP_ERROR
```

and the error is returned to the LLM.

---

## Maximum steps

If the agent cannot finish within:

```text
MAX_STEPS
```

the task becomes:

```text
INCOMPLETE
```

---

## Artifact collection failure

The task execution may succeed while artifact collection encounters an error.

This is recorded using:

```text
ARTIFACT_COLLECTION_ERROR
```

The implementation should clearly distinguish task execution status from artifact persistence status.

---

# 47. V2 Design Principles

V2 follows these core principles:

### Isolation

Run untrusted/generated commands inside Docker.

### Workspace ownership

The agent owns a dedicated `/sandbox` workspace.

### Autonomous execution

The LLM determines the next command based on previous observations.

### Verification

Completion requires actual verification.

### Observability

Every important operation is logged.

### Persistence

Generated artifacts survive container destruction.

### Traceability

Every task has a unique task ID.

### Bounded execution

The agent has a maximum step limit.

---

# 48. V1 vs V2

| Capability                    | V1            | V2         |
| ----------------------------- | ------------- | ---------- |
| Docker sandbox                | Basic         | Structured |
| `/sandbox` workspace          | Limited/basic | Dedicated  |
| Autonomous loop               | Basic         | Multi-step |
| Error observation             | Basic         | Structured |
| Verification                  | Basic         | Explicit   |
| Task IDs                      | Limited       | Yes        |
| Human logs                    | Basic         | Yes        |
| JSONL trace                   | Limited       | Yes        |
| Token tracking                | Limited       | Yes        |
| Execution timing              | Limited       | Yes        |
| Persistent artifacts          | No/limited    | Yes        |
| Artifact manifest             | No            | Yes        |
| Container lifecycle           | Basic         | Managed    |
| Workspace artifact collection | No/limited    | Yes        |

---

# 49. V2.2 Enhancement

The tested V2.2 implementation adds the persistent artifact workflow.

The important difference is:

```text
V2 execution:

Docker
  |
  v
/sandbox
  |
  v
destroy container
```

versus:

```text
V2.2:

Docker
  |
  v
/sandbox
  |
  v
collect artifacts
  |
  v
host artifacts/task-id/
  |
  v
manifest.json
  |
  v
destroy container
```

This was successfully validated with:

```text
hello.py
```

and:

```text
manifest.json
```

remaining on the EC2 host after container destruction.

---

# 50. V2 Limitations

V2 intentionally uses raw shell commands generated by the LLM.

For example:

```text
printf ...
python3 hello.py
test -f hello.py
```

The LLM therefore has to understand shell syntax.

This creates several limitations:

1. Shell syntax errors are possible.
2. Command parsing is dependent on the LLM.
3. Tool intent is represented indirectly through shell commands.
4. Path handling requires careful validation.
5. The LLM may generate unnecessarily complex commands.
6. Command-level security is harder to reason about than explicit tool schemas.

These limitations motivate the V3 architecture.

---

# 51. Why V3 Was Introduced

V3 changes the interaction model from:

```text
LLM
 |
 v
RAW SHELL COMMAND
 |
 v
Sandbox
```

to:

```text
LLM
 |
 v
STRUCTURED TOOL CALL
 |
 v
TOOL REGISTRY
 |
 v
SANDBOX
```

Example V3 request:

```json
{
  "tool": "filesystem.write",
  "arguments": {
    "path": "hello.py",
    "content": "print(\"Hello from V3\")"
  }
}
```

Instead of requiring the LLM to construct shell syntax directly.

---

# 52. V2 → V3 Migration

V2:

```text
LLM
  |
  | "printf ..."
  v
Shell
  |
  v
Docker
```

V3:

```text
LLM
  |
  | filesystem.write
  v
ToolRegistry
  |
  v
SandboxManager
  |
  v
Docker
```

V3 therefore provides a stronger abstraction layer between the model and execution environment.

---

# 53. Recommended V2 Operational Flow

For normal operation:

```bash
cd ~/sandbox-ai
```

Activate environment:

```bash
source .venv/bin/activate
```

Validate:

```bash
python -m py_compile agent.py
python -m py_compile sandbox_manager.py
python -m py_compile logger.py
```

Run:

```bash
python agent.py
```

Enter the task.

After completion:

```bash
ls -lah artifacts/
```

Then inspect:

```bash
cat artifacts/<task-id>/manifest.json
```

and:

```bash
cat logs/<task-id>.log
```

---

# 54. Complete V2 Flow

The complete V2 lifecycle is:

```text
                     USER
                       |
                       v
                  TASK PROMPT
                       |
                       v
                  agent.py
                       |
                       v
                CREATE TASK ID
                       |
                       v
                  AgentLogger
                       |
                       v
                SandboxManager
                       |
                       v
                 Docker Sandbox
                       |
                       v
                    /sandbox
                       |
                       v
                 OpenAI LLM
                       |
                       v
               Generate Command
                       |
                       v
                Execute Command
                       |
              +--------+--------+
              |                 |
           Success             Error
              |                 |
              +--------+--------+
                       |
                       v
                    Observe
                       |
                       v
                Send to LLM
                       |
                       v
              Next Command / DONE
                       |
                 +-----+-----+
                 |           |
              Command       DONE
                 |           |
                 |           v
                 |      Collect Artifacts
                 |           |
                 |           v
                 |      Copy to Host
                 |           |
                 |           v
                 |      manifest.json
                 |           |
                 |           v
                 |      Destroy Docker
                 |           |
                 |           v
                 |        SUCCESS
                 |
                 +----> repeat
```

---

# 55. Example Production Directory After Several Tasks

After multiple executions, the host may contain:

```text
sandbox-ai/
│
├── agent.py
├── sandbox_manager.py
├── logger.py
├── .env
├── requirements.txt
│
├── artifacts/
│   │
│   ├── task-734fdf8e98d2/
│   │   ├── hello.py
│   │   └── manifest.json
│   │
│   ├── task-f0af34ebf46c/
│   │   ├── hello.py
│   │   └── manifest.json
│   │
│   └── ...
│
├── logs/
│   ├── task-734fdf8e98d2.log
│   ├── task-734fdf8e98d2.jsonl
│   ├── task-f0af34ebf46c.log
│   ├── task-f0af34ebf46c.jsonl
│   └── ...
│
└── README.md
```

Each task is independently traceable.

---

# 56. Production Considerations

Before deploying V2 for untrusted users, additional controls should be considered around:

* Docker resource limits
* CPU limits
* memory limits
* execution timeouts
* network access
* container privileges
* filesystem mounts
* process limits
* image hardening
* secrets exposure
* command auditing
* artifact size limits
* artifact type restrictions
* concurrent task limits

V2 establishes the core sandbox architecture but should not be treated as a complete multi-tenant security boundary without additional hardening.

---

# 57. V2 Success Criteria

A V2 task is considered successful when:

```text
1. Sandbox created successfully
2. Agent executes the task
3. Commands complete successfully
4. Required result is verified
5. LLM returns DONE
6. Artifacts are collected
7. Manifest is created
8. Task summary is generated
9. Sandbox is destroyed
10. Persistent artifacts remain available on host
```

---

# 58. Example End-to-End Test

Run:

```bash
python agent.py
```

Enter:

```text
Create hello.py that prints "Hello from Sandbox", execute it, and verify that the file exists.
```

Expected artifact:

```text
artifacts/<task-id>/hello.py
```

Expected content:

```python
print("Hello from Sandbox")
```

Expected manifest:

```text
artifacts/<task-id>/manifest.json
```

Expected status:

```text
SUCCESS
```

Expected Docker behavior:

```text
container created
container executed
artifacts collected
container destroyed
```

Expected host behavior:

```text
generated artifacts remain available
```

---

# 59. Summary

V2 transforms the initial sandbox agent into a more complete autonomous execution system.

Its primary capabilities are:

```text
Docker isolation
       +
Dedicated /sandbox workspace
       +
Autonomous LLM loop
       +
Command execution
       +
Observation
       +
Error recovery
       +
Verification
       +
Task logging
       +
Token tracking
       +
Persistent artifacts
       +
Artifact manifest
```

The most important architectural improvement is persistent artifact handling.

The Docker container is temporary, but task outputs are persistent:

```text
Temporary Execution Environment
            |
            v
        /sandbox
            |
            v
     Artifact Collection
            |
            v
      Host Persistence
            |
            v
artifacts/<task-id>/
```

V2 therefore provides the foundation for the next architectural generation.

V3 builds on this foundation by replacing raw shell-command generation with structured tool calls through a Tool Registry.

---

# 60. Version Roadmap

```text
V1
 |
 | Basic autonomous sandbox execution
 v
V2
 |
 | Structured workspace
 | Logging
 | Verification
 | Error recovery
 | Persistent artifacts
 | Manifest
 v
V3
 |
 | Structured Tool Registry
 | filesystem.write
 | filesystem.read
 | filesystem.list
 | python.run
 | terminal.exec
 | Path security
 v
Future
 |
 | More tools
 | Better permissions
 | Resource controls
 | Artifact APIs
 | Multi-user execution
 | Web/API interface
 | Job management
 | Streaming events
```

V2 is therefore the bridge between the initial shell-based agent and the structured tool-based agent architecture.
