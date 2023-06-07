from __future__ import annotations

import functools
import logging
import os
import asyncio
import random
from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE, STDOUT

import ModuleUpdate

ModuleUpdate.update_ran = True

import json
import Utils
from MultiServer import mark_raw

from worlds.kh2.WorldLocations import *

from worlds import network_data_package

if __name__ == "__main__":
    Utils.init_logging("HadesClient", exception_logger="Client")

hades_logger = logging.getLogger("Hades")

from NetUtils import ClientStatus
from CommonClient import gui_enabled, logger, get_base_parser, ClientCommandProcessor, \
    CommonContext, server_loop

ModuleUpdate.update()

HADES_PIPE_PREFIX = "APHades:\t"
PROXY_FILENAME = "proxy.txt"


def world_state_to_lua_table(world_state: dict) -> str:
    result = "{\n"
    for key in world_state:
        result += f"{key} = {world_state[key]},\n"
    result += "}"

    return result


class HadesClientProcessor(ClientCommandProcessor):
    ctx: HadesContext
    @mark_raw
    def _cmd_set_path(self, path: str = '') -> bool:
        """Manually set the Hades install directory (if the automatic detection fails)."""
        if path:
            os.environ["HADESPATH"] = path
            return is_mod_installed_correctly()
        else:
            hades_logger.warning("When using set_path, you must type the path to your Hades install directory.")
        return False

    def _cmd_download_data(self) -> bool:
        """Download the most recent release of the necessary files for playing Hades with
        Archipelago. Will overwrite existing files."""
        if "HADESPATH" not in os.environ:
            check_game_install_path()

        return True

        # if os.path.exists(os.environ["SC2PATH"]+"ArchipelagoSC2Version.txt"):
        #     with open(os.environ["SC2PATH"]+"ArchipelagoSC2Version.txt", "r") as f:
        #         current_ver = f.read()
        # else:
        #     current_ver = None
        #
        # tempzip, version = download_latest_release_zip('TheCondor07', 'Starcraft2ArchipelagoData',
        #                                                current_version=current_ver, force_download=True)
        #
        # if tempzip != '':
        #     try:
        #         zipfile.ZipFile(tempzip).extractall(path=os.environ["SC2PATH"])
        #         sc2_logger.info(f"Download complete. Version {version} installed.")
        #         with open(os.environ["SC2PATH"]+"ArchipelagoSC2Version.txt", "w") as f:
        #             f.write(version)
        #     finally:
        #         os.remove(tempzip)
        # else:
        #     sc2_logger.warning("Download aborted/failed. Read the log for more information.")
        #     return False
        # return True


class HadesContext(CommonContext):
    game = "Hades"
    items_handling = 0b101  # Indicates you get items sent from other worlds.
    command_processor = HadesClientProcessor
    game_state = {
        "unlockedBonusBoons": 0
    }

    def __init__(self, server_address, password):
        super(HadesContext, self).__init__(server_address, password)

    async def run_hades(self):
        with open("proxy.txt", "w") as proxy:
            proxy.write("")
        self.game = await create_subprocess_exec(
            "F:\\SteamLibrary\\steamapps\\common\\Hades\\x64\\Hades.exe",
            stdout=PIPE,
            stderr=STDOUT
        )

        try:
            while self.game.returncode is None:
                output = await self.game.stdout.readline()
                try:
                    output = output.decode(encoding="utf-8")
                except ValueError as e:
                    message = f"Error: Failed to process line: {e}"
                    print(message)
                    continue
                if not output:
                    break
                output = output.rstrip("\r\n")

                if not output.startswith(HADES_PIPE_PREFIX):
                    continue

                output = output[len(HADES_PIPE_PREFIX):]
                match output:
                    case "room_transition":
                        self.transfer_game_state()
                    case "reconnect":
                        self.transfer_game_state()
                    case "ack":
                        print("ack")
                        with open(PROXY_FILENAME, "w") as proxy:
                            proxy.write("")

                    case _:
                        print(f"???: {output}")

        except KeyboardInterrupt:
            force = True # Todo: what to do here?

        print("Hades closed. Oh no!")

    def transfer_game_state(self):
        with open(PROXY_FILENAME, "w") as proxy:
            proxy.writelines(f'return {world_state_to_lua_table(self.game_state)}')


    def run_gui(self):
        """Import kivy UI system and start running it as self.ui_task."""
        from kvui import GameManager

        class HadesManager(GameManager):
            logging_pairs = [
                ("Client", "Archipelago")
            ]
            base_title = "Archipelago Hades Client"
            ctx: HadesContext

            def __init__(self, ctx):
                super().__init__(ctx)

        self.ui = HadesManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")


def finishedGame(ctx: HadesContext, message):
    return False


if __name__ == '__main__':
    async def main(args):
        ctx = HadesContext(args.connect, args.password)
        asyncio.create_task(ctx.run_hades(), name="hades runner")
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        #progression_watcher = asyncio.create_task(
        #        hades_watcher(ctx), name="HadesProgressionWatcher")

        await ctx.exit_event.wait()
        ctx.server_address = None

        #await progression_watcher

        await ctx.shutdown()


    import colorama

    parser = get_base_parser(description="Hades Client, for text interfacing.")

    args, rest = parser.parse_known_args()
    colorama.init()
    asyncio.run(main(args))

    colorama.deinit()


def is_mod_installed_correctly() -> bool:
    return True


def check_game_install_path() -> bool:
    return True
