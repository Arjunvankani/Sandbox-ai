import os
import uuid
import time

from dotenv import load_dotenv
from openai import OpenAI

from sandbox_manager import SandboxManager
from logger import AgentLogger


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6"
)

MAX_STEPS = int(
    os.getenv(
        "MAX_STEPS",
        "10"
    )
)


# ============================================================
# OPENAI CLIENT
# ============================================================

client = OpenAI(
    api_key=os.getenv(
        "OPENAI_API_KEY"
    )
)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an autonomous coding agent operating inside an isolated
Docker sandbox.

============================================================
WORKSPACE RULE
============================================================

Your current working directory is:

/sandbox

ALL task files MUST be created inside:

/sandbox

Use relative paths whenever possible.

Examples:

hello.py
project/
project/main.py
outputs/result.json

DO NOT use:

/root
/workspace
/tmp
/home
/etc

unless the user explicitly asks for those locations.

============================================================
YOUR JOB
============================================================

Complete the user's task autonomously.

Use this loop:

PLAN
EXECUTE
OBSERVE
FIX
VERIFY

You receive the output of every previous command.

For every step return EXACTLY ONE shell command.

Do not return markdown.

Do not explain the command.

Return only the shell command.

============================================================
IMPORTANT RULES
============================================================

1. Work only inside /sandbox.

2. Create files inside /sandbox.

3. Modify files inside /sandbox.

4. Execute code inside /sandbox.

5. Inspect stdout and stderr.

6. If a command fails, analyze the error.

7. Fix the problem.

8. Continue until the task is completely finished.

9. Verify the result before completing the task.

10. Never hide errors.

11. Never intentionally suppress errors.

12. Never use:

    ; true
    || true
    2>/dev/null

13. Do not mark a task as completed unless it has actually
    been verified.

14. If a command returns a non-zero exit code, treat it as
    an error and decide how to fix it.

============================================================
COMPLETION
============================================================

When the task is completely finished and verified, return:

DONE
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

    duration = (
        time.perf_counter()
        - start
    )

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
# RUN ONE TASK
# ============================================================

def run_task(user_prompt):

    # --------------------------------------------------------
    # UNIQUE TASK ID
    # --------------------------------------------------------

    task_id = (
        f"task-{uuid.uuid4().hex[:12]}"
    )

    # --------------------------------------------------------
    # TASK LOGGER
    # --------------------------------------------------------

    logger = AgentLogger(
        task_id
    )

    # --------------------------------------------------------
    # SANDBOX
    # --------------------------------------------------------

    sandbox = SandboxManager(
    logger,
    task_id
    )

    task_start = time.perf_counter()

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0

    error_count = 0
    retry_count = 0

    step_number = 0

    task_success = False

    artifacts = []

    container = None

    # ========================================================
    # TASK START
    # ========================================================

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

            total_input_tokens += (
                input_tokens
            )

            total_output_tokens += (
                output_tokens
            )

            total_tokens += (
                request_tokens
            )

            # =================================================
            # AGENT FINISHED
            # =================================================

            if ai_response == "DONE":

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
            # COMMAND
            # =================================================

            command = ai_response

            logger.event(

                "COMMAND_GENERATED",

                step=step_number,

                command=command
            )

            print(
                f"\n[STEP {step_number}]"
            )

            print(
                "AI COMMAND:"
            )

            print(
                command
            )

            # =================================================
            # EXECUTE COMMAND
            # =================================================

            result = sandbox.execute(
                command
            )

            stdout = result[
                "stdout"
            ]

            stderr = result[
                "stderr"
            ]

            return_code = result[
                "returncode"
            ]

            success = result[
                "success"
            ]

            # =================================================
            # DISPLAY OUTPUT
            # =================================================

            if stdout:

                print(
                    "\nOUTPUT:"
                )

                print(
                    stdout
                )

            if stderr:

                print(
                    "\nERROR:"
                )

                print(
                    stderr
                )

            # =================================================
            # SUCCESS
            # =================================================

            if success:

                logger.event(

                    "STEP_SUCCESS",

                    step=step_number,

                    return_code=return_code
                )

            # =================================================
            # ERROR
            # =================================================

            else:

                error_count += 1

                retry_count += 1

                logger.event(

                    "STEP_ERROR",

                    step=step_number,

                    return_code=return_code,

                    error_count=error_count,

                    retry_count=retry_count,

                    stderr=stderr
                )

            # =================================================
            # OBSERVATION
            # =================================================

            observation = f"""
STEP: {step_number}

WORKING DIRECTORY:
/sandbox

COMMAND:
{command}

EXIT CODE:
{return_code}

SUCCESS:
{success}

STDOUT:
{stdout}

STDERR:
{stderr}

You must now decide the next action.

If the task is completely finished and verified, return:

DONE

Otherwise return exactly ONE shell command.
"""

            # =================================================
            # ADD ASSISTANT COMMAND
            # =================================================

            conversation.append(

                {
                    "role": "assistant",

                    "content": command
                }

            )

            # =================================================
            # ADD TOOL OBSERVATION
            # =================================================

            conversation.append(

                {
                    "role": "user",

                    "content": observation
                }

            )

            logger.event(

                "OBSERVATION_SENT_TO_AGENT",

                step=step_number,

                return_code=return_code,

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

                    count=len(
                        artifacts
                    )
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
        # TASK DURATION
        # ====================================================

        duration = (
            time.perf_counter()
            - task_start
        )

        # ====================================================
        # STATUS
        # ====================================================

        status = (
            "SUCCESS"
            if task_success
            else "INCOMPLETE"
        )

        # ====================================================
        # TASK SUMMARY LOG
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

        # ====================================================
        # TERMINAL SUMMARY
        # ====================================================

        print()

        print(
            "=" * 60
        )

        print(
            "TASK SUMMARY"
        )

        print(
            "=" * 60
        )

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

        # ====================================================
        # ARTIFACT LIST
        # ====================================================

        if artifacts:

            print()

            print(
                "Artifacts:"
            )

            for artifact in artifacts:

                print(

                    f"  - "
                    f"{artifact['path']} "
                    f"[{artifact['type']}]"

                )

        print(
            "=" * 60
        )

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
        # ALWAYS DESTROY SANDBOX
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
# MAIN
# ============================================================

def main():

    print(
        "============================================"
    )

    print(
        "        AI SANDBOX AGENT V2.2"
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

    # ========================================================
    # MULTI-TASK LOOP
    # ========================================================

    while True:

        try:

            user_prompt = input(
                "You: "
            ).strip()

        except KeyboardInterrupt:

            print(
                "\nExiting."
            )

            break

        except EOFError:

            print(
                "\nExiting."
            )

            break

        # ----------------------------------------------------
        # EMPTY PROMPT
        # ----------------------------------------------------

        if not user_prompt:

            continue

        # ----------------------------------------------------
        # EXIT
        # ----------------------------------------------------

        if user_prompt.lower() in [

            "exit",

            "quit"

        ]:

            print(
                "Exiting."
            )

            break

        # ----------------------------------------------------
        # RUN TASK
        # ----------------------------------------------------

        run_task(
            user_prompt
        )

        print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()