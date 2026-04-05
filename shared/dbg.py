from lib.args import arg, parse
from lib.constants import DEFAULT_APP, find_ndk, get_mod_data
from lib.run import run
from lib.util import log

from datetime import datetime
from pathlib import Path
from re import search, compile as re_comp
from tempfile import TemporaryDirectory
from typing import Optional


MODIFIED_RE = re_comp(r"(?<=Modify: )\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?=.\d{9})")
MODIFIED_FMT = "%Y-%m-%d %H:%M:%S"
TRACE_HEADER = "*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***"
TRACE_TIME_RE = re_comp(r"\d{2}:\d{2}:\d{2}")
TRACE_TIME_FMT = "%H:%M:%S"
TRACE_CONTENT = re_comp(r"#\d{2}  pc \d+.*")


class DbgArgs:
    """
    dbg
    Retrieves the most recent Beat Saber crash log and backtrace.
    """

    app_id = arg("a", "app-id", DEFAULT_APP, help="the application id")
    no_analyze = arg(
        "A", "no-analyze", False, help="skip running ndk-stack on the backtrace"
    )
    alt_input = arg(
        "i",
        "input",
        Path,
        "FILE",
        help="analyze an input file instead of pulling the most recent crash",
    )
    out_file = arg(
        "o", "out", Path("./crash.log"), "FILE", help="the output for the backtrace"
    )
    quiet = arg("q", "quiet", False, help="suppress printed status information")
    symbols_dir = arg(
        "s",
        "symbols",
        Path("./build/debug/"),
        "DIRECTORY",
        help="directories containing debug .so files",
    )


def get_modified_time(path: str) -> Optional[datetime]:
    stats = run("adb shell stat", path, capture=True)
    if modifed := search(MODIFIED_RE, stats):
        return datetime.strptime(modifed.group(), MODIFIED_FMT)
    return None


def format_modified_time(time: datetime) -> str:
    mins = int((datetime.now() - time).total_seconds()) // 60
    return f"{mins} minute{"" if mins == 1 else "s"} ago"


def get_best_tombstone(args: DbgArgs):
    files_path = f"/sdcard/Android/data/{args.app_id}/files/"
    files = run("adb shell ls", files_path, capture=True).strip().splitlines()
    tombstones = [name for name in files if "tombstone_" in name]
    if len(tombstones) == 0:
        if not args.quiet:
            log("No tombstones found")
        return None
    recent_time = None
    recent_tombstone = None
    for tombstone in tombstones:
        time = get_modified_time(files_path + tombstone)
        if not time:
            log("Error: failed to find last modified time for", tombstone)
            continue
        if not args.quiet:
            log("Found", tombstone, format_modified_time(time))
        if recent_time is None or time > recent_time:
            recent_time = time
            recent_tombstone = tombstone
    if recent_time is None or recent_tombstone is None:
        return None
    with TemporaryDirectory("r") as d:
        f = Path(d) / "tombstone.log"
        run("adb pull", files_path + recent_tombstone, f.absolute(), silent=True)
        return recent_time, f.read_text()


def check_file_exists(path: str) -> bool:
    return run("adb shell", f'"[ -f {path} ]"', silent=True, fail_ok=True) == 0


def get_log_stacktrace(args: DbgArgs):
    log_path = get_mod_data(args.app_id, "logs2/Paperlog.log")
    if not check_file_exists(log_path):
        log("Error: failed to find log file")
        return None
    # might want to avoid pulling and reading the whole file?
    with TemporaryDirectory("r") as d:
        f = Path(d) / "crash.log"
        run("adb pull", log_path, f.absolute(), silent=True)
        text = f.read_text()
    # find the most recent backtrace header, then find all frames immediately following it
    last_pos = text.rfind(TRACE_HEADER)
    if last_pos == -1:
        if not args.quiet:
            log("No stacktrace found in log")
        return None
    last_pos_start = text.rfind("\n", 0, last_pos) + 1
    trace = TRACE_HEADER + "\n"
    # skip lines (such as the header) until we actually see some backtrace frames
    seen_frames = False
    for line in text[last_pos:].splitlines():
        line = search(TRACE_CONTENT, line)
        if line is None:
            if seen_frames:
                break
            else:
                continue
        seen_frames = True
        # ndk-stack will not work without at least one space before the frames
        trace += "  " + line.group().strip() + "\n"
    time = get_modified_time(log_path)
    exact_time = search(TRACE_TIME_RE, text[last_pos_start:last_pos])
    if time and exact_time:
        exact_time = datetime.strptime(exact_time.group(), TRACE_TIME_FMT)
        time.replace(
            hour=exact_time.hour, minute=exact_time.minute, second=exact_time.second
        )
        if not args.quiet:
            log("Found log stacktrace", format_modified_time(time))
    else:
        log("Error: failed to find last modified time for log stacktrace")
        return None
    return time, trace


def pull_trace(args: DbgArgs) -> str:
    # find the most recent stack trace between beatsaber-hook logs and tombstone files
    tombstone = get_best_tombstone(args)
    log_trace = get_log_stacktrace(args)
    if tombstone is None or log_trace is None:
        if log_trace:
            return log_trace[1]
        elif tombstone:
            return tombstone[1]
        else:
            log("Error: no crash logs found")
            exit(1)
    elif tombstone[0] >= log_trace[0]:
        return tombstone[1]
    else:
        return log_trace[1]


def analyze(args: DbgArgs, trace: str):
    # windows is .cmd, mac/linux has no extension
    ndk_stack = find_ndk() / "ndk-stack.cmd"
    if not ndk_stack.exists():
        ndk_stack = find_ndk() / "ndk-stack"
    if not ndk_stack.exists():
        log("Error:", ndk_stack, "not found")
        exit(1)
    analyzed = run(
        ndk_stack, "-sym", args.symbols_dir, stdin=trace, capture=True
    ).strip()
    if not analyzed:
        if not args.quiet:
            log("Error: failed to analyze trace, outputting non-analyzed")
        analyzed = trace
    args.out_file.write_text(analyzed)


def output(args: DbgArgs, trace: str):
    if args.no_analyze:
        args.out_file.write_text(trace)
    else:
        analyze(args, trace)


def main(args: DbgArgs):
    if args.alt_input:
        if not args.alt_input.exists():
            log("Error:", args.alt_input, "not found")
            exit(1)
        output(args, args.alt_input.read_text().strip())
    else:
        output(args, pull_trace(args))


if __name__ == "__main__":
    with parse(DbgArgs) as args:
        main(args)
