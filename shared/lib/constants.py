from lib.util import log

from json import loads
from os import getenv
from pathlib import Path

PROJECT_PATH = Path.cwd()
MOD_JSON_PATH = PROJECT_PATH / "mod.json"
MOD_TEMPLATE_PATH = PROJECT_PATH / "mod.template.json"
QPM_JSON_PATH = PROJECT_PATH / "qpm.json"
QPM_SHARED_PATH = PROJECT_PATH / "qpm.shared.json"

DEFAULT_APP = "com.beatgames.beatsaber"


def find_ndk() -> Path:
    try:
        if (txt_ndk := PROJECT_PATH / "ndkpath.txt").exists():
            return Path(txt_ndk.read_text().strip())
        elif env_ndk := getenv("ANDROID_NDK_HOME"):
            return Path(env_ndk)
        elif env_ndk := getenv("ANDROID_NDK_LATEST_HOME"):
            return Path(env_ndk)
    except:
        pass
    log("Error: Android NDK not found")
    log("Set ndkpath.txt or ANDROID_NDK_HOME")
    exit(1)


def find_llvm_prebuilts() -> Path:
    base_path = find_ndk() / "toolchains" / "llvm" / "prebuilt"
    for child in base_path.iterdir():
        return child / "bin"
    log("Error: Android NDK toolchains/llvm/prebuilt directory was empty")
    exit(1)


def get_mod_data(app_id: str = DEFAULT_APP, folder: str = "") -> str:
    return f"/sdcard/ModData/{app_id}/{folder}"


def get_mod_id() -> str:
    if not QPM_JSON_PATH.exists():
        log("Error: qpm.json not found")
        exit(1)
    qpm_json = loads(QPM_JSON_PATH.read_text())
    name = qpm_json.get("info", {}).get("name")
    if name is None:
        log("Error: name not found")
        exit(1)
    # how qpm does it by defualt: mod name without spaces
    # (yes I know this is the MOD_ID, don't blame me...)
    return str(name).replace(" ", "")


def get_so_name() -> str:
    if not QPM_JSON_PATH.exists():
        log("Error: qpm.json not found")
        exit(1)
    qpm_json = loads(QPM_JSON_PATH.read_text())
    info = qpm_json.get("info", {})
    override = info.get("additionalData", {}).get("overrideSoName")
    if override is not None:
        return override
    mod_id: str | None = info.get("id")
    mod_version: str | None = info.get("version")
    if mod_id is None or mod_version is None:
        log("Error: mod id or version not found in qpm.json")
        exit(1)
    return f"lib{mod_id}_{mod_version.replace('.', '_')}.so"


__all__ = [
    "PROJECT_PATH",
    "MOD_JSON_PATH",
    "MOD_TEMPLATE_PATH",
    "QPM_JSON_PATH",
    "QPM_SHARED_PATH",
    "DEFAULT_APP",
    "find_ndk",
    "find_llvm_prebuilts",
    "get_mod_data",
    "get_mod_id",
    "get_so_name",
]
