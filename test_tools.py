from sandbox_manager import SandboxManager
from logger import AgentLogger
from tools.registry import ToolRegistry


TASK_ID = "v3-test"


logger = AgentLogger(
    TASK_ID
)

sandbox = SandboxManager(
    logger,
    TASK_ID
)

container = sandbox.create()


try:

    tools = ToolRegistry(
        sandbox,
        logger
    )

    print("\n============================================")
    print("V3 TOOL REGISTRY TEST")
    print("============================================")

    # =====================================================
    # 1. filesystem.write
    # =====================================================

    print("\n[1] filesystem.write")

    result = tools.execute(
        "filesystem.write",
        {
            "path": "hello.py",
            "content": 'print("Hello from V3")'
        }
    )

    print(result)

    # =====================================================
    # 2. filesystem.read
    # =====================================================

    print("\n[2] filesystem.read")

    result = tools.execute(
        "filesystem.read",
        {
            "path": "hello.py"
        }
    )

    print(result)

    # =====================================================
    # 3. python.run
    # =====================================================

    print("\n[3] python.run")

    result = tools.execute(
        "python.run",
        {
            "path": "hello.py"
        }
    )

    print(result)

    # =====================================================
    # 4. filesystem.list
    # =====================================================

    print("\n[4] filesystem.list")

    result = tools.execute(
        "filesystem.list",
        {
            "path": "."
        }
    )

    print(result)

    # =====================================================
    # 5. terminal.exec
    # =====================================================

    print("\n[5] terminal.exec")

    result = tools.execute(
        "terminal.exec",
        {
            "command": "pwd && ls -la"
        }
    )

    print(result)

    # =====================================================
    # 6. PATH SECURITY TEST
    # =====================================================

    print("\n[6] PATH SECURITY TEST")

    result = tools.execute(
        "filesystem.read",
        {
            "path": "../../etc/passwd"
        }
    )

    print(result)

    print("\n============================================")
    print("V3 TOOL TEST FINISHED")
    print("============================================")


finally:

    sandbox.destroy()