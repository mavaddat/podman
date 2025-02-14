import configparser
import json
import os
import shutil
import subprocess
import sys
import tempfile


class Podman:
    """
    Instances hold the configuration and setup for running podman commands
    """

    def __init__(self):
        """Initialize a Podman instance with global options"""
        binary = os.getenv("PODMAN", "bin/podman")
        self.cmd = [binary, "--storage-driver=vfs"]

        cgroupfs = os.getenv("CGROUP_MANAGER", "systemd")
        self.cmd.append(f"--cgroup-manager={cgroupfs}")

        self.anchor_directory = tempfile.mkdtemp(prefix="podman_restapi_")
        self.cmd.append("--root=" + os.path.join(self.anchor_directory, "crio"))
        self.cmd.append("--runroot=" + os.path.join(self.anchor_directory, "crio-run"))

        os.environ["CONTAINERS_REGISTRIES_CONF"] = os.path.join(
            self.anchor_directory, "registry.conf"
        )
        p = configparser.ConfigParser()
        p.read_dict(
            {
                "registries.search": {"registries": "['quay.io']"},
                "registries.insecure": {"registries": "[]"},
                "registries.block": {"registries": "[]"},
            }
        )
        with open(os.environ["CONTAINERS_REGISTRIES_CONF"], "w") as w:
            p.write(w)

    def open(self, command, *args, **kwargs):
        """Podman initialized instance to run a given command

        :param self: Podman instance
        :param command: podman sub-command to run
        :param args: arguments and options for command
        :param kwargs: See subprocess.Popen() for shell keyword
        :return: subprocess.Popen() instance configured to run podman instance
        """
        cmd = self.cmd.copy()
        cmd.append(command)
        cmd.extend(args)

        shell = kwargs.get("shell", False)

        return subprocess.Popen(
            cmd,
            shell=shell,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def run(self, command, *args, **kwargs):
        """Run given podman command

        :param self: Podman instance
        :param command: podman sub-command to run
        :param args: arguments and options for command
        :param kwargs: See subprocess.Popen() for shell and check keywords
        :return: subprocess.Popen() instance configured to run podman instance
        """
        cmd = self.cmd.copy()
        cmd.append(command)
        cmd.extend(args)

        check = kwargs.get("check", False)
        shell = kwargs.get("shell", False)

        try:
            return subprocess.run(
                cmd,
                shell=shell,
                check=check,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            if e.stdout:
                sys.stdout.write("\nRun Stdout:\n" + e.stdout.decode("utf-8"))
            if e.stderr:
                sys.stderr.write("\nRun Stderr:\n" + e.stderr.decode("utf-8"))
            raise

    def tear_down(self):
        shutil.rmtree(self.anchor_directory, ignore_errors=True)
