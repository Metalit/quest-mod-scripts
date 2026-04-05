from lib.args import arg, parse
from lib.constants import DEFAULT_APP, find_ndk
from lib.run import run
from lib.util import get_pid, start_unity_app

from pathlib import Path


class ProfileArgs:
    """
    profile
    Runs the NDK SimplePerf profiler on Beat Saber and creates a HTML report.
    Beat Saber must be made debuggable for this to work without ADB root.
    """

    app_id = arg("a", "app-id", DEFAULT_APP, help="the application id")
    data_file = arg("d", "data", Path("./perf.data"), help="the raw data file")
    out_file = arg(
        "o", "out", Path("./report.html"), "FILE", help="the output for the html report"
    )
    no_profile = arg("P", "no-profile", False, help="only creates a html report")
    no_report = arg(
        "R", "no-report", False, help="skips creating a html report on exit"
    )
    symbols_dir = arg(
        "s",
        "symbols",
        Path("./build/debug/"),
        "DIRECTORY",
        help="the location of debug .so files",
    )
    use_root = arg("u", "use-root", False, help="attempts to use adb root")


def run_profiler(args: ProfileArgs, ndk_path: Path):
    if get_pid(args.app_id) is None:
        start_unity_app(args.app_id)
    run(
        "python",
        ndk_path / "SimplePerf/app_profiler.py",
        "-lib",
        args.symbols_dir,
        "-o",
        args.data_file,
        "-p",
        args.app_id,
        "" if args.use_root else "--disable_adb_root",
        "--ndk_path",
        ndk_path.absolute(),
        '-r "-g -e cpu-cycles"',
    )


def run_report(args: ProfileArgs, ndk_path: Path):
    run(
        "python",
        ndk_path / "SimplePerf/report_html.py",
        "-i",
        args.data_file,
        "-o",
        args.out_file,
        "--ndk_path",
        ndk_path.absolute(),
        "--no_browser",
    )


def main(args: ProfileArgs):
    ndk_path = find_ndk()
    if not args.no_profile:
        run_profiler(args, ndk_path)
    if not args.no_report:
        run_report(args, ndk_path)


if __name__ == "__main__":
    with parse(ProfileArgs) as args:
        main(args)
