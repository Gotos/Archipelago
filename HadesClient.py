from __future__ import annotations

import functools
import logging
import os
import asyncio
import random
from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE, STDOUT, Process
from typing import Optional

import ModuleUpdate
from worlds.hades.Items import item_id_to_name
from worlds.hades.Locations import lookup_id_to_name

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
        if type(world_state[key]) == str:
            result += f"{key} = \"{world_state[key]}\",\n"
        else:
            result += f"{key} = {world_state[key]},\n"
    result += "}"

    return result


class HadesClientProcessor(ClientCommandProcessor):
    ctx: HadesContext

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
    game_process: Optional[Process] = None
    items_handling = 0b101  # Indicates you get items sent from other worlds.
    command_processor = HadesClientProcessor
    game_state = {
        "unlockedBonusBoons": 0,
        "nextAPItem": "",
    }
    hades_running = False
    current_location_is_check_location = False
    player = -1
    next_location = -1

    def __init__(self, server_address, password, hades_dir):
        super(HadesContext, self).__init__(server_address, password)
        self.hades_dir = hades_dir

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super(HadesContext, self).server_auth(password_requested)
        await self.get_username()
        await self.send_connect()
        asyncio.create_task(self.run_hades(), name="hades runner")

    async def run_hades(self):
        if self.hades_running:
            return

        with open(PROXY_FILENAME, "w") as proxy:
            proxy.write("")
        self.game_process = await create_subprocess_exec(
            os.path.join(self.hades_dir, "Hades.exe"),
            stdout=PIPE,
            stderr=STDOUT
        )

        try:
            while self.game_process.returncode is None:
                output = await self.game_process.stdout.readline()
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
                        print(f"{json.dumps(self.game_state)}")
                    case "ack":
                        print("ack")
                        with open(PROXY_FILENAME, "w") as proxy:
                            proxy.write("")

                    case s if s.startswith("StartRoom "):
                        reward = output[len("StartRoom "):]
                        if reward == "APItem":
                            self.current_location_is_check_location = True
                        else:
                            self.current_location_is_check_location = False

                    case "HandleLootPickup":
                        if self.current_location_is_check_location:
                            await self.send_msgs([{"cmd": 'LocationChecks', "locations": self.next_location}])
                            self.game_state["nextAPItem"] = ""
                            await self.get_next_item()
                            # todo: tell the server we got the item
                    case _:
                        print(f"???: {output}")

        except KeyboardInterrupt:
            force = True # Todo: what to do here?

        logger.warning("Hades was closed and you have been disconnected from the Archipelago server.")
        self.game_process = None
        await self.disconnect()

    async def get_next_item(self):
        self.next_location = self.missing_locations.pop()
        await self.send_msgs([{"cmd": 'LocationScouts', "locations": [self.next_location]}])

    def on_package(self, cmd: str, args: dict):
        print(f"onPackage: {cmd}: {json.dumps(args)}")
        print(json.dumps(list(self.locations_scouted)))

        if cmd in {"Connected"}:
            if "slot" in args:
                self.player = args["slot"]
            asyncio.create_task(self.get_next_item())

        if cmd in {"LocationInfo"}:
            for location_item in args["locations"]:
                [item, location, player, _] = location_item
                if location == self.next_location and player == self.player:
                    self.game_state["nextAPItem"] = item_id_to_name[item]
                    print(f"{location}: {item_id_to_name[item]}")
            self.transfer_game_state()

        if cmd in {"RoomUpdate"}:
            if "checked_locations" in args:
                new_locations = set(args["checked_locations"])
                # TODO: make this take locations from other players on the same slot so proper coop happens
                #  items_to_give = [self.kh2slotdata["LocalItems"][str(location_id)] for location_id in new_locations if
                #                 location_id in self.kh2LocalItems.keys()]
                self.checked_locations |= new_locations

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

    options = Utils.get_options()
    hades_dir = Utils.user_path(options["hades_options"]["hades_directory"])

    async def main(args):
        ctx = HadesContext(args.connect, args.password, hades_dir)
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
