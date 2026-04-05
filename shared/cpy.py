from lib.args import arg, parse
from lib.constants import (
    DEFAULT_APP,
    MOD_JSON_PATH,
    MOD_TEMPLATE_PATH,
    PROJECT_PATH,
    QPM_SHARED_PATH,
    get_mod_data,
)
from lib.run import run
from lib.util import log

from json import loads
from pathlib import Path
from typing import List


class CopyArgs:
    """
    copy

    Copies files to their locations on the Quest. Does not build.
    """

    app_id = arg("a", "app-id", DEFAULT_APP, help="the application id")
    # assets = arg(
    #     "A",
    #     "assets-folder",
    #     Path("./assets/"),
    #     "DIRECTORY",
    #     help="the folder to search for bsml files",
    # )
    # bsml = arg("b", "bsml", False, help="copies all bsml files in the assets folder")
    # only_bsml = arg("B", "only-bsml", False, help="copies only bsml files")
    # clean = arg("c", "clean", False, help="removes all previously copied files")
    skip_missing = arg(
        "s", "skip", False, help="skip copying files not found in qmodIncludeDirs"
    )
    regen = arg("r", "regen", False, help="always regenerate mod.json")
    no_regen = arg("R", "no-regen", False, help="never regenerate mod.json")


def modified_after(file: Path, relative_to: Path) -> bool:
    return file.stat().st_mtime >= relative_to.stat().st_mtime


def try_push(filename: str, destination: str, searches: List[Path], skip_missing: bool):
    file = None
    for path in searches:
        if (path / filename).exists():
            file = path / filename
            break
    if not file:
        if skip_missing:
            log("Warning: cannot find file", filename)
            return
        else:
            log("Error: cannot find file", filename)
            exit(1)
    run("adb push", file.absolute(), destination, fail_ok=skip_missing)


def update_mod_json(args: CopyArgs):
    if not args.regen:
        if not MOD_JSON_PATH.exists():
            if args.no_regen:
                log(
                    "Error: mod.json not found while no-regen was specified, cannot copy"
                )
                exit(1)
            if not MOD_TEMPLATE_PATH.exists():
                log("Error: mod.json and mod.template.json not found, cannot copy")
                exit(1)
        elif (
            args.no_regen
            or not MOD_TEMPLATE_PATH.exists()
            or not QPM_SHARED_PATH.exists()
            or (
                modified_after(MOD_JSON_PATH, MOD_TEMPLATE_PATH)
                and modified_after(MOD_JSON_PATH, QPM_SHARED_PATH)
            )
        ):
            return
    if not MOD_TEMPLATE_PATH.exists() or not QPM_SHARED_PATH.exists():
        log(
            "Error: cannot generate mod.json without mod.template.json and qpm.shared.json"
        )
        exit(1)
    run("qpm qmod manifest", wd=PROJECT_PATH)


def find_qmod_searches(args: CopyArgs) -> List[Path]:
    qpm_json = loads(QPM_SHARED_PATH.read_text())
    search_paths = qpm_json["config"]["workspace"]["qmodIncludeDirs"]

    if len(search_paths) == 0:
        if args.skip_missing:
            log("Warning: empty qmodIncludeDirs")
            return []
        else:
            log("Error: empty qmodIncludeDirs, cannot copy")
            exit(1)

    return [Path(p) for p in search_paths]


def copy_qmod(args: CopyArgs):
    search_paths = find_qmod_searches(args)

    mod_json = loads(MOD_JSON_PATH.read_text())
    mod_data = get_mod_data(args.app_id, "Modloader")

    def copy_libs(source_arr: str, loader_dir: str):
        for filename in mod_json.get(source_arr, []):
            destination = f'"{mod_data}/{loader_dir}/{filename}"'
            try_push(filename, destination, search_paths, args.skip_missing)

    copy_libs("modFiles", "early_mods")
    copy_libs("lateModFiles", "mods")
    copy_libs("libraryFiles", "libs")

    for copy in mod_json.get("fileCopies", []):
        filename, destination = copy["name"], copy["destination"]
        try_push(filename, destination, search_paths, args.skip_missing)


def main(args: CopyArgs):
    update_mod_json(args)
    copy_qmod(args)


if __name__ == "__main__":
    with parse(CopyArgs) as args:
        main(args)
