import os
import json


class ToolRegistry:

    def __init__(self, sandbox, logger):
        self.sandbox = sandbox
        self.logger = logger

        self.tools = {
            "filesystem.write": self.filesystem_write,
            "filesystem.read": self.filesystem_read,
            "filesystem.list": self.filesystem_list,
            "terminal.exec": self.terminal_exec,
            "python.run": self.python_run,
        }

    # =========================================================
    # TOOL DISPATCH
    # =========================================================

    def execute(self, tool_name, arguments):

        self.logger.event(
            "TOOL_DISPATCH",
            tool=tool_name,
            arguments=json.dumps(arguments)
        )

        if tool_name not in self.tools:

            self.logger.event(
                "TOOL_REJECTED",
                tool=tool_name,
                reason="unknown_tool"
            )

            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }

        try:

            result = self.tools[tool_name](
                arguments
            )

            self.logger.event(
                "TOOL_RESULT",
                tool=tool_name,
                success=result.get("success", False)
            )

            return result

        except Exception as e:

            self.logger.event(
                "TOOL_ERROR",
                tool=tool_name,
                error=str(e)
            )

            return {
                "success": False,
                "error": str(e)
            }

    # =========================================================
    # PATH VALIDATION
    # =========================================================

    def validate_path(self, path):

        if not path:
            raise ValueError("Path is required")

        # Never allow absolute paths from the model
        if os.path.isabs(path):

            raise ValueError(
                "Absolute paths are not allowed"
            )

        # Normalize path
        normalized = os.path.normpath(path)

        # Prevent ../ escape
        if normalized == ".." or normalized.startswith(
            ".." + os.sep
        ):

            raise ValueError(
                "Path escapes sandbox workspace"
            )

        return normalized

    # =========================================================
    # FILESYSTEM WRITE
    # =========================================================

    def filesystem_write(self, args):

        path = self.validate_path(
            args.get("path")
        )

        content = args.get(
            "content",
            ""
        )

        command = (
            "mkdir -p \"$(dirname '%s')\" && "
            "cat > '%s' <<'SANDBOX_EOF'\n"
            "%s\n"
            "SANDBOX_EOF"
        ) % (
            path,
            path,
            content
        )

        result = self.sandbox.execute(
            command
        )

        return {
            "success": result["success"],
            "path": f"/sandbox/{path}",
            "stdout": result["stdout"],
            "stderr": result["stderr"]
        }

    # =========================================================
    # FILESYSTEM READ
    # =========================================================

    def filesystem_read(self, args):

        path = self.validate_path(
            args.get("path")
        )

        result = self.sandbox.execute(
            f"cat '{path}'"
        )

        return {
            "success": result["success"],
            "path": f"/sandbox/{path}",
            "content": result["stdout"],
            "error": result["stderr"]
        }

    # =========================================================
    # FILESYSTEM LIST
    # =========================================================

    def filesystem_list(self, args):

        path = self.validate_path(
            args.get("path", ".")
        )

        result = self.sandbox.execute(
            f"find '{path}' -maxdepth 3 -type f -print"
        )

        return {
            "success": result["success"],
            "files": result["stdout"].splitlines(),
            "error": result["stderr"]
        }

    # =========================================================
    # TERMINAL EXEC
    # =========================================================

    def terminal_exec(self, args):

        command = args.get("command")

        if not command:

            return {
                "success": False,
                "error": "command is required"
            }

        result = self.sandbox.execute(
            command
        )

        return {
            "success": result["success"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "return_code": result["returncode"]
        }

    # =========================================================
    # PYTHON RUN
    # =========================================================

    def python_run(self, args):

        path = self.validate_path(
            args.get("path")
        )

        result = self.sandbox.execute(
            f"python3 '{path}'"
        )

        return {
            "success": result["success"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "return_code": result["returncode"]
        }
