import json
import os
import time
import uuid

from dotenv import load_dotenv
from openai import OpenAI

from sandbox_manager import SandboxManager
from logger import AgentLogger
from tool_registry import ToolRegistry


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6")
MAX_STEPS = int(os.getenv("MAX_STEPS", "10"))

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an autonomous coding agent operating inside an isolated
Docker sandbox.

The sandbox workspace is:

/sandbox

You have access to the following tools:

1. filesystem.write
2. filesystem.read
3. filesystem.list
4. python.run
5. terminal.exec

You MUST use tools to perform actions.

Do NOT generate shell commands directly as your response.

Return EXACTLY ONE JSON object per step.

============================================================
TOOL FORMAT
============================================================

filesystem.write:

{
  "tool": "filesystem.write",
  "arguments": {
    "path": "hello.py",
    "content": "print('Hello')"
  }
}

filesystem.read:

{
  "tool": "filesystem.read",
  "arguments": {
    "path": "hello.py"
  }
}

filesystem.list:

{
  "tool": "filesystem.list",
  "arguments": {
    "path": "."
  }
}

python.run:

{
  "tool": "python.run",
  "arguments": {
    "path": "hello.py"
  }
}

terminal.exec:

{
  "tool": "terminal.exec",
  "arguments": {
    "command": "pwd && ls -la"
  }
}

============================================================
COMPLETION
============================================================

When the task is completely finished and verified, return:

{
  "action": "DONE"
}

============================================================
RULES
============================================================

1. Work only inside /sandbox.

2. Use relative paths whenever possible.

3. Never access files outside /sandbox.

4. Use filesystem.write to create or modify files.

5. Use filesystem.read to inspect files.

6. Use filesystem.list to discover files.

7. Use python.run to execute Python files.

8. Use terminal.exec only when necessary.

9. Inspect tool results.

10. If a tool fails, analyze the error.

11. Fix the problem using another tool call.

12. Verify the final result.

13. Do not claim completion without verification.

14. Do not intentionally suppress errors.

15. Continue until the user's task is actually complete.

16. Return only ONE JSON object.

============================================================
AUTONOMOUS LOOP
============================================================

PLAN
? TOOL CALL
? OBSERVE
? FIX
? VERIFY
? DONE
"""


# ============================================================
# LLM CALL
# ============================================================

def call_llm(
    client,
    messages,
    logger,
    step,
    model
):

    logger.event(
        "LLM_CALL_START",
        step=step,
        model=model
    )

    start = time.perf_counter()

    response = client.chat.completions.create(
        model=model,
        messages=messages
    )

    duration = time.perf_counter() - start

    usage = response.usage

    input_tokens = 0
    output_tokens = 0
    total_tokens = 0

    if usage:

        input_tokens = getattr(
            usage,
            "prompt_tokens",
            0
        )

        output_tokens = getattr(
            usage,
            "completion_tokens",
            0
        )

        total_tokens = getattr(
            usage,
            "total_tokens",
            0
        )

    content = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

    logger.event(
        "LLM_CALL_FINISHED",

        step=step,

        model=model,

        input_tokens=input_tokens,

        output_tokens=output_tokens,

        total_tokens=total_tokens,

        duration_seconds=round(
            duration,
            3
        ),

        response=content
    )

    return (
        content,
        input_tokens,
        output_tokens,
        total_tokens
    )


# ============================================================
# PARSE TOOL CALL
# ============================================================

def parse_agent_response(response):

    response = response.strip()

    # Remove accidental markdown fences.
    if response.startswith("```"):

        lines = response.splitlines()

        if lines:

            lines = lines[1:]

        if lines and lines[-1].strip() == "```":

            lines = lines[:-1]

        response = "\n".join(lines).strip()

    try:

        data = json.loads(response)

    except json.JSONDecodeError as e:

        raise ValueError(
            f"Invalid JSON from agent: {e}"
        )

    if not isinstance(data, dict):

        raise ValueError(
            "Agent response must be a JSON object"
        )

    return data


# ============================================================
# RUN ONE TASK
# ============================================================

def run_task(user_prompt):

    task_id = (
        f"task-{uuid.uuid4().hex[:12]}"
    )

    logger = AgentLogger(
        task_id
    )

    sandbox = SandboxManager(
        logger,
        task_id
    )

    task_start = time.perf_counter()

    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0

    error_count = 0
    retry_count = 0

    step_number = 0

    task_success = False

    artifacts = []

    container = None

    tool_registry = None

    logger.event(
        "TASK_STARTED",
        prompt=user_prompt,
        model=MODEL,
        max_steps=MAX_STEPS
    )

    try:

        # ====================================================
        # CREATE SANDBOX
        # ====================================================

        container = sandbox.create()

        logger.event(
            "AGENT_READY",
            container=container,
            workdir="/sandbox"
        )

        # ====================================================
        # TOOL REGISTRY
        # ====================================================

        tool_registry = ToolRegistry(
            sandbox=sandbox,
            logger=logger
        )

        logger.event(
            "TOOL_REGISTRY_READY",
            tools=tool_registry.list_tools()
            if hasattr(tool_registry, "list_tools")
            else "registered"
        )

        # ====================================================
        # INITIAL CONVERSATION
        # ====================================================

        conversation = [

            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },

            {
                "role": "user",
                "content": user_prompt
            }

        ]

        # ====================================================
        # AUTONOMOUS LOOP
        # ====================================================

        while step_number < MAX_STEPS:

            step_number += 1

            logger.event(
                "STEP_STARTED",
                step=step_number,
                max_steps=MAX_STEPS
            )

            # =================================================
            # LLM
            # =================================================

            try:

                (
                    ai_response,
                    input_tokens,
                    output_tokens,
                    request_tokens
                ) = call_llm(
                    client,
                    conversation,
                    logger,
                    step_number,
                    MODEL
                )

            except Exception as e:

                error_count += 1

                logger.event(
                    "LLM_ERROR",
                    step=step_number,
                    error=str(e)
                )

                print(
                    f"\nLLM ERROR: {e}"
                )

                break

            # =================================================
            # TOKEN ACCOUNTING
            # =================================================

            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            total_tokens += request_tokens

            # =================================================
            # PARSE RESPONSE
            # =================================================

            try:

                action = parse_agent_response(
                    ai_response
                )

            except Exception as e:

                error_count += 1
                retry_count += 1

                logger.event(
                    "AGENT_RESPONSE_ERROR",
                    step=step_number,
                    error=str(e),
                    response=ai_response
                )

                conversation.append(
                    {
                        "role": "assistant",
                        "content": ai_response
                    }
                )

                conversation.append(
                    {
                        "role": "user",
                        "content": (
                            "Your response was invalid. "
                            "Return exactly one valid JSON "
                            "tool call or {\"action\":\"DONE\"}."
                        )
                    }
                )

                continue

            # =================================================
            # DONE
            # =================================================

            if action.get("action") == "DONE":

                logger.event(
                    "AGENT_DONE",
                    step=step_number
                )

                print(
                    "\nAI: Task completed."
                )

                task_success = True

                break

            # =================================================
            # TOOL CALL VALIDATION
            # =================================================

            tool_name = action.get(
                "tool"
            )

            arguments = action.get(
                "arguments",
                {}
            )

            if not tool_name:

                error_count += 1
                retry_count += 1

                logger.event(
                    "TOOL_CALL_INVALID",
                    step=step_number,
                    error="Missing tool name",
                    response=action
                )

                conversation.append(
                    {
                        "role": "assistant",
                        "content": ai_response
                    }
                )

                conversation.append(
                    {
                        "role": "user",
                        "content": (
                            "Invalid tool call. "
                            "Provide a tool field and arguments."
                        )
                    }
                )

                continue

            # =================================================
            # DISPLAY TOOL CALL
            # =================================================

            logger.event(
                "TOOL_DISPATCH",
                step=step_number,
                tool=tool_name,
                arguments=arguments
            )

            print(
                f"\n[STEP {step_number}]"
            )

            print(
                "AI TOOL:"
            )

            print(
                tool_name
            )

            print(
                "ARGUMENTS:"
            )

            print(
                json.dumps(
                    arguments,
                    indent=2
                )
            )

            # =================================================
            # EXECUTE TOOL
            # =================================================

            try:

                result = tool_registry.execute(
                    tool_name,
                    arguments
                )

            except Exception as e:

                error_count += 1
                retry_count += 1

                logger.event(
                    "TOOL_EXECUTION_ERROR",
                    step=step_number,
                    tool=tool_name,
                    error=str(e)
                )

                result = {
                    "success": False,
                    "error": str(e)
                }

            # =================================================
            # RESULT
            # =================================================

            logger.event(
                "TOOL_RESULT",
                step=step_number,
                tool=tool_name,
                success=result.get(
                    "success",
                    False
                ),
                result=result
            )

            success = result.get(
                "success",
                False
            )

            if success:

                logger.event(
                    "STEP_SUCCESS",
                    step=step_number,
                    tool=tool_name,
                    success=True
                )

            else:

                error_count += 1
                retry_count += 1

                logger.event(
                    "STEP_ERROR",
                    step=step_number,
                    tool=tool_name,
                    success=False,
                    error=result.get(
                        "error"
                    )
                )

            # =================================================
            # OBSERVATION
            # =================================================

            observation = {
                "step": step_number,
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
                "instruction": (
                    "Inspect this result and decide the "
                    "next action. Continue until the task "
                    "is completely verified."
                )
            }

            # =================================================
            # CONVERSATION
            # =================================================

            conversation.append(
                {
                    "role": "assistant",
                    "content": ai_response
                }
            )

            conversation.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        observation,
                        default=str
                    )
                }
            )

            logger.event(
                "OBSERVATION_SENT_TO_AGENT",
                step=step_number,
                tool=tool_name,
                success=success
            )

        # ====================================================
        # MAX STEPS
        # ====================================================

        if (
            step_number >= MAX_STEPS
            and not task_success
        ):

            logger.event(
                "MAX_STEPS_REACHED",
                step=step_number
            )

            print(
                "\nAI: Maximum steps reached."
            )

        # ====================================================
        # ARTIFACT COLLECTION
        # ====================================================

        if task_success:

            try:

                artifacts = (
                    sandbox.collect_artifacts()
                )

                logger.event(
                    "ARTIFACTS_READY",
                    count=len(artifacts)
                )

            except Exception as e:

                logger.event(
                    "ARTIFACT_COLLECTION_ERROR",
                    error=str(e)
                )

        else:

            logger.event(
                "ARTIFACT_COLLECTION_SKIPPED",
                reason="task_not_successful"
            )

        # ====================================================
        # DURATION
        # ====================================================

        duration = (
            time.perf_counter()
            - task_start
        )

        status = (
            "SUCCESS"
            if task_success
            else "INCOMPLETE"
        )

        # ====================================================
        # SUMMARY
        # ====================================================

        logger.event(
            "TASK_SUMMARY",

            steps=step_number,

            input_tokens=total_input_tokens,

            output_tokens=total_output_tokens,

            total_tokens=total_tokens,

            errors=error_count,

            retries=retry_count,

            artifacts_count=len(
                artifacts
            ),

            duration_seconds=round(
                duration,
                3
            ),

            status=status
        )

        print()
        print("=" * 60)
        print("TASK SUMMARY")
        print("=" * 60)

        print(
            f"Task ID       : {task_id}"
        )

        print(
            f"Sandbox       : {container}"
        )

        print(
            "Workspace     : /sandbox"
        )

        print(
            f"Steps         : {step_number}"
        )

        print(
            f"LLM Calls     : {step_number}"
        )

        print(
            f"Input Tokens  : {total_input_tokens}"
        )

        print(
            f"Output Tokens : {total_output_tokens}"
        )

        print(
            f"Total Tokens  : {total_tokens}"
        )

        print(
            f"Errors        : {error_count}"
        )

        print(
            f"Retries       : {retry_count}"
        )

        print(
            f"Artifacts     : {len(artifacts)}"
        )

        print(
            f"Duration      : {duration:.2f}s"
        )

        print(
            f"Status        : {status}"
        )

        if artifacts:

            print()
            print("Artifacts:")

            for artifact in artifacts:

                if isinstance(
                    artifact,
                    dict
                ):

                    print(
                        f"  - "
                        f"{artifact.get('path', '')} "
                        f"["
                        f"{artifact.get('type', '')}"
                        f"]"
                    )

                else:

                    print(
                        f"  - {artifact}"
                    )

        print("=" * 60)

        print(
            f"Trace: logs/{task_id}.jsonl"
        )

        print(
            f"Log:   logs/{task_id}.log"
        )

    except Exception as e:

        logger.event(
            "TASK_FATAL_ERROR",
            error=str(e)
        )

        print(
            f"\nTASK ERROR: {e}"
        )

    finally:

        # ====================================================
        # DESTROY SANDBOX
        # ====================================================

        if container:

            try:

                sandbox.destroy()

            except Exception as e:

                logger.event(
                    "SANDBOX_DESTROY_ERROR",
                    error=str(e)
                )

        logger.event(
            "PROCESS_FINISHED"
        )


# ============================================================
# INTERACTIVE LOOP
# ============================================================

def main():

    print(
        "============================================"
    )

    print(
        "        AI SANDBOX AGENT V3"
    )

    print(
        "============================================"
    )

    print(
        f"Model: {MODEL}"
    )

    print(
        f"Max steps: {MAX_STEPS}"
    )

    print(
        "Workspace: /sandbox"
    )

    print()

    while True:

        try:

            user_prompt = input(
                "You: "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print(
                "\nExiting."
            )

            break

        if not user_prompt:

            continue

        if user_prompt.lower() in (
            "exit",
            "quit"
        ):

            print(
                "Exiting."
            )

            break

        run_task(
            user_prompt
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()