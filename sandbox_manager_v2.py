import subprocess
import uuid
import time
import json
import os
import shutil


class SandboxManager:

    WORKDIR = "/sandbox"

    def __init__(self, logger, task_id):

        self.logger = logger
        self.task_id = task_id

        self.container_name = (
            f"agent-sandbox-{uuid.uuid4().hex[:8]}"
        )

        # Host-side persistent artifact directory
        self.host_artifact_dir = os.path.abspath(
            os.path.join(
                "artifacts",
                self.task_id
            )
        )

    # ========================================================
    # CREATE SANDBOX
    # ========================================================

    def create(self):

        self.logger.event(
            "SANDBOX_CREATE_START",
            container=self.container_name,
            workdir=self.WORKDIR
        )

        start = time.perf_counter()

        command = [
            "docker",
            "run",
            "-d",

            "--name",
            self.container_name,

            "--network",
            "none",

            "python:3.11-slim",

            "sleep",
            "infinity"
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        duration = (
            time.perf_counter() - start
        )

        if result.returncode != 0:

            self.logger.event(
                "SANDBOX_CREATE_ERROR",
                container=self.container_name,
                stderr=result.stderr,
                return_code=result.returncode
            )

            raise RuntimeError(
                result.stderr
            )

        docker_id = result.stdout.strip()

        # ----------------------------------------------------
        # CREATE WORKSPACE INSIDE CONTAINER
        # ----------------------------------------------------

        workspace_command = [
            "docker",
            "exec",
            self.container_name,
            "mkdir",
            "-p",
            "/sandbox/files",
            "/sandbox/outputs",
            "/sandbox/artifacts"
        ]

        workspace_result = subprocess.run(
            workspace_command,
            capture_output=True,
            text=True
        )

        if workspace_result.returncode != 0:

            self.logger.event(
                "SANDBOX_WORKSPACE_ERROR",
                container=self.container_name,
                stderr=workspace_result.stderr,
                return_code=workspace_result.returncode
            )

            raise RuntimeError(
                "Could not create sandbox workspace"
            )

        # ----------------------------------------------------
        # VERIFY
        # ----------------------------------------------------

        verify_command = [
            "docker",
            "exec",
            self.container_name,
            "test",
            "-d",
            "/sandbox"
        ]

        verify_result = subprocess.run(
            verify_command,
            capture_output=True,
            text=True
        )

        if verify_result.returncode != 0:

            raise RuntimeError(
                "Sandbox workspace verification failed"
            )

        # ----------------------------------------------------
        # CREATE HOST ARTIFACT DIRECTORY
        # ----------------------------------------------------

        os.makedirs(
            self.host_artifact_dir,
            exist_ok=True
        )

        # ----------------------------------------------------
        # LOG
        # ----------------------------------------------------

        self.logger.event(
            "SANDBOX_CREATED",
            container=self.container_name,
            docker_id=docker_id,
            workdir=self.WORKDIR,
            duration_seconds=round(
                duration,
                3
            )
        )

        self.logger.event(
            "SANDBOX_WORKSPACE_READY",
            container=self.container_name,
            workdir=self.WORKDIR
        )

        self.logger.event(
            "ARTIFACT_DIRECTORY_READY",
            host_directory=self.host_artifact_dir
        )

        return self.container_name

    # ========================================================
    # EXECUTE COMMAND
    # ========================================================

    def execute(self, command):

        self.logger.event(
            "TOOL_CALL_START",
            container=self.container_name,
            command=command
        )

        start = time.perf_counter()

        docker_command = [
            "docker",
            "exec",

            "-w",
            self.WORKDIR,

            self.container_name,

            "bash",
            "-c",

            command
        ]

        result = subprocess.run(
            docker_command,
            capture_output=True,
            text=True
        )

        duration = (
            time.perf_counter() - start
        )

        success = (
            result.returncode == 0
        )

        self.logger.event(
            "TOOL_CALL_FINISHED",

            container=self.container_name,

            command=command,

            return_code=result.returncode,

            success=success,

            stdout=result.stdout,

            stderr=result.stderr,

            duration_seconds=round(
                duration,
                3
            )
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": success,
            "duration_seconds": round(
                duration,
                3
            )
        }

    # ========================================================
    # LIST FILES
    # ========================================================

    def list_files(self):

        result = self.execute(
            "find /sandbox "
            "-type f "
            "-not -path '/sandbox/artifacts/*' "
            "-printf '%p\\n'"
        )

        if not result["success"]:
            return []

        files = []

        for line in result["stdout"].splitlines():

            line = line.strip()

            if line:
                files.append(line)

        return files

    # ========================================================
    # ARTIFACT TYPE
    # ========================================================

    @staticmethod
    def detect_type(path):

        extension = (
            os.path.splitext(path)[1]
            .lower()
        )

        types = {

            ".py": "python",
            ".json": "json",
            ".csv": "csv",
            ".txt": "text",
            ".md": "markdown",
            ".html": "html",
            ".js": "javascript",
            ".ts": "typescript",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".xml": "xml",
            ".sql": "sql",
            ".sh": "shell",
            ".css": "css",

        }

        return types.get(
            extension,
            "file"
        )

    # ========================================================
    # COPY ONE FILE FROM CONTAINER
    # ========================================================

    def copy_from_container(
        self,
        container_path,
        host_path
    ):

        os.makedirs(
            os.path.dirname(host_path),
            exist_ok=True
        )

        result = subprocess.run(

            [
                "docker",
                "cp",

                f"{self.container_name}:{container_path}",

                host_path
            ],

            capture_output=True,

            text=True
        )

        if result.returncode != 0:

            self.logger.event(

                "ARTIFACT_COPY_ERROR",

                container=self.container_name,

                source=container_path,

                destination=host_path,

                stderr=result.stderr,

                return_code=result.returncode
            )

            return False

        return True

    # ========================================================
    # COLLECT ARTIFACTS
    # ========================================================

    def collect_artifacts(self):

        self.logger.event(
            "ARTIFACT_COLLECTION_START",
            container=self.container_name
        )

        files = self.list_files()

        artifacts = []

        for container_path in files:

            # Convert:
            #
            # /sandbox/hello.py
            #
            # to:
            #
            # hello.py

            relative_path = os.path.relpath(
                container_path,
                self.WORKDIR
            )

            host_path = os.path.join(
                self.host_artifact_dir,
                relative_path
            )

            # Prevent path traversal
            host_path = os.path.abspath(
                host_path
            )

            artifact_root = os.path.abspath(
                self.host_artifact_dir
            )

            if not host_path.startswith(
                artifact_root + os.sep
            ):

                self.logger.event(
                    "ARTIFACT_SKIPPED",
                    path=container_path,
                    reason="path_traversal_protection"
                )

                continue

            # ------------------------------------------------
            # COPY
            # ------------------------------------------------

            copied = self.copy_from_container(
                container_path,
                host_path
            )

            if not copied:
                continue

            artifact = {

                "path": container_path,

                "relative_path": relative_path,

                "host_path": host_path,

                "type": self.detect_type(
                    container_path
                )

            }

            artifacts.append(
                artifact
            )

            self.logger.event(

                "ARTIFACT_COPIED",

                source=container_path,

                destination=host_path,

                type=artifact["type"]
            )

        # ----------------------------------------------------
        # MANIFEST
        # ----------------------------------------------------

        manifest = {

            "task_id": self.task_id,

            "container": self.container_name,

            "workspace": self.WORKDIR,

            "artifact_directory":
                self.host_artifact_dir,

            "count": len(artifacts),

            "artifacts": artifacts

        }

        manifest_path = os.path.join(
            self.host_artifact_dir,
            "manifest.json"
        )

        with open(
            manifest_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                manifest,
                f,
                indent=2
            )

        self.logger.event(

            "ARTIFACT_MANIFEST_CREATED",

            path=manifest_path,

            count=len(artifacts)
        )

        self.logger.event(

            "ARTIFACT_COLLECTION_FINISHED",

            count=len(artifacts),

            host_directory=self.host_artifact_dir
        )

        return artifacts

    # ========================================================
    # DESTROY
    # ========================================================

    def destroy(self):

        self.logger.event(

            "SANDBOX_DESTROY_START",

            container=self.container_name
        )

        result = subprocess.run(

            [
                "docker",
                "rm",
                "-f",
                self.container_name
            ],

            capture_output=True,

            text=True
        )

        self.logger.event(

            "SANDBOX_DESTROYED",

            container=self.container_name,

            return_code=result.returncode
        )