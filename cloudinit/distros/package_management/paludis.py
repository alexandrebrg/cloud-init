import logging
from typing import Iterable, Optional, Sequence, Mapping

from cloudinit import helpers, subp, util
from cloudinit.distros.package_management.package_manager import (
    PackageManager,
    UninstalledPackages,
)
from cloudinit.settings import PER_ALWAYS, PER_INSTANCE

LOG = logging.getLogger(__name__)

CAVE_UPGRADE_COMMAND = ["resolve", "-c", "world", "-x"]

CAVE_REPOS_SYNC_COMMAND = ["sync"]

# Cave allows to define customs sub-commands
CAVE_COMMANDS_DIR = "/etc/cloud-init/cave"


class Paludis(PackageManager):
    name = "paludis"

    def __init__(
        self,
        runner: helpers.Runners,
        *,
        cave_command: list[str] | None = None,
        cave_sync_subcommand: list[str] | None = None,
        cave_system_upgrade_subcommand: list[str] | None = None,
    ):
        super().__init__(runner)

        if cave_command is None:
            self.cave_command = ["cave"]
        else:
            self.cave_command = cave_command

        if cave_sync_subcommand is None:
            self.cave_sync_subcommand = CAVE_REPOS_SYNC_COMMAND
        else:
            self.cave_sync_subcommand = cave_sync_subcommand

        if cave_system_upgrade_subcommand is None:
            self.cave_system_upgrade_subcommand = CAVE_UPGRADE_COMMAND
        else:
            self.cave_system_upgrade_subcommand = (
                cave_system_upgrade_subcommand
            )

        self.cave_commands_dir = CAVE_COMMANDS_DIR

    @classmethod
    def from_config(cls, runner: helpers.Runners, cfg: Mapping) -> "Paludis":
        return Paludis(
            runner,
            cave_sync_subcommand=cfg.get("cave_sync_subcommand"),
            cave_system_upgrade_subcommand=cfg.get(
                "cave_system_upgrade_subcommand"
            ),
        )

    def update_package_sources(self, *, force=False):
        self.runner.run(
            "update-sources",
            self.run_package_command,
            self.cave_sync_subcommand,
            freq=PER_ALWAYS if force else PER_INSTANCE,
        )

    def available(self):
        return bool(subp.which(self.cave_command[0]))

    def install_packages(self, pkglist: Iterable) -> UninstalledPackages:
        pkglist = util.expand_package_list("%s:%s", pkglist)
        self.run_package_command(["resolve"], ["-x", " ".join(pkglist)])
        return []

    def run_package_command(self, command, args=None):
        full_command = self.cave_command

        if command == "upgrade":
            command = self.cave_system_upgrade_subcommand
        elif command == "sync":
            command = self.cave_sync_subcommand

        full_command.extend(command)

        if args and isinstance(args, str):
            full_command.append(args)
        elif args and isinstance(args, list):
            full_command.extend(args)

        # Allow the output of this to flow outwards (ie not be captured)
        subp.subp(
            args=full_command,
            capture=False,
            update_env={
                "HOME": "/tmp",
                "CAVE_COMMANDS_PATH": CAVE_COMMANDS_DIR,
            },
        )
