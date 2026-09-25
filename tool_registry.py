import json
import shlex
import time


class ToolRegistry:

    def __init__(self, sandbox, logger):

        self.sandbox = sandbox
        self.logger = logger

        self.tools = {
            "filesystem.write": self.filesystem_write,
            "filesystem.read": self.filesystem_read,
            "filesystem.list": self.filesystem_list,
            "python.run": self.python_run,
            "terminal.exec": self.terminal_exec,
        }

    # ========================================================
    # TOOL LIST
    # ========================================================

    def list_tools(self):

        return list(self.tools.keys())

    # ========================================================
    # DISPATCH
    # ========================================================

    def execute(self, tool_name, arguments):

        self.logger.event(
            "TOOL_DISPATCH",
            tool=tool_name,
            arguments=json.dumps(
                arguments,
                default=str
            )
        )

        if tool_name not in self.tools:

            error = (
                f"Unknown tool: {tool_name}"
            )

            self.logger.event(
                "TOOL_ERROR",
                tool=tool_name,
                error=error
            )

            return {
                "success": False,
                "error": error
            }

        try:

            result = self.tools[
                tool_name
            ](
                arguments
            )

            self.logger.event(
                "TOOL_RESULT",
                tool=tool_name,
                success=result.get(
                    "success",
                    False
                )
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

    # ========================================================
    # PATH VALIDATION
    # ========================================================

    def _safe_path(self, path):

        if not path:
            raise ValueError(
                "Path is required"
            )

        # Never allow absolute paths.
        if path.startswith("/"):
            raise ValueError(
                "Absolute paths are not allowed"
            )

        # Normalize and reject traversal.
        normalized = path.replace(
            "\\",
            "/"
        )

        parts = normalized.split("/")

        if ".." in parts:

            raise ValueError(
                "Path escapes sandbox workspace"
            )

        return normalized

    # ========================================================
    # FILESYSTEM WRITE
    # ========================================================

    def filesystem_write(self, arguments):

        path = self._safe_path(
            arguments.get("path")
        )

        content = arguments.get(
            "content",
            ""
        )

        quoted_path = shlex.quote(
            path
        )

        # Use Python inside the sandbox to safely
        # create directories and write content.
        script = (
            "import os\n"
            f"path={path!r}\n"
            f"content={content!r}\n"
            "directory=os.path.dirname(path)\n"
            "if directory:\n"
            "    os.makedirs(directory, exist_ok=True)\n"
            "with open(path, 'w', encoding='utf-8') as f:\n"
            "    f.write(content)\n"
        )

        command = (
            "python3 - <<'PY'\n"
            f"{script}"
            "PY"
        )

        result = self.sandbox.execute(
            command
        )

        return {
            "success": result["success"],
            "path": f"/sandbox/{path}",
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "error": (
                result["stderr"]
                if not result["success"]
                else ""
            )
        }

    # ========================================================
    # FILESYSTEM READ
    # ========================================================

    def filesystem_read(self, arguments):

        path = self._safe_path(
            arguments.get("path")
        )

        command = (
            f"cat {shlex.quote(path)}"
        )

        result = self.sandbox.execute(
            command
        )

        return {
            "success": result["success"],
            "path": f"/sandbox/{path}",
            "content": result["stdout"]
            if result["success"]
            else "",
            "error": result["stderr"]
            if not result["success"]
            else ""
        }

    # ========================================================
    # FILESYSTEM LIST
    # ========================================================

    def filesystem_list(self, arguments):

        path = self._safe_path(
            arguments.get(
                "path",
                "."
            )
        )

        command = (
            "find "
            f"{shlex.quote(path)} "
            "-maxdepth 3 "
            "-type f "
            "-print"
        )

        result = self.sandbox.execute(
            command
        )

        files = []

        if result["success"]:

            files = [
                line.strip()
                for line in result["stdout"].splitlines()
                if line.strip()
            ]

        return {
            "success": result["success"],
            "files": files,
            "error": result["stderr"]
            if not result["success"]
            else ""
        }

    # ========================================================
    # PYTHON RUN
    # ========================================================

    def python_run(self, arguments):

        path = self._safe_path(
            arguments.get("path")
        )

        command = (
            f"python3 {shlex.quote(path)}"
        )

        result = self.sandbox.execute(
            command
        )

        return {
            "success": result["success"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "return_code": result["returncode"],
            "error": result["stderr"]
            if not result["success"]
            else ""
        }

    # ========================================================
    # TERMINAL EXEC
    # ========================================================

    def terminal_exec(self, arguments):

        command = arguments.get(
            "command"
        )

        if not command:

            return {
                "success": False,
                "error": "command is required"
            }

        # Basic protection against obvious
        # workspace escape attempts.
        dangerous = [
            "cd /",
            "cd /root",
            "cd /etc",
            "cd /home",
            "cd /tmp",
            "rm -rf /",
        ]

        for pattern in dangerous:

            if pattern in command:

                return {
                    "success": False,
                    "error": (
                        "Command rejected by "
                        "sandbox security policy"
                    )
                }

        result = self.sandbox.execute(
            command
        )

        return {
            "success": result["success"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "return_code": result["returncode"],
            "error": result["stderr"]
            if not result["success"]
            else ""
        }
