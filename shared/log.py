from lib.args import arg, parse
from lib.constants import DEFAULT_APP, PROJECT_PATH, get_mod_data, get_mod_id
from lib.run import run
from lib.util import get_pid, log

from dataclasses import dataclass
from pathlib import Path
from re import match, compile as re_comp
from sys import stdout
from tempfile import TemporaryDirectory
from typing import List, TextIO, Tuple


# logcat, paperlog, order
LEVELS = {
    "debug": ("D", "D", 1),
    "info": ("I", "I", 2),
    "warning": ("W", "W", 3),
    "error": ("E", "E", 4),
    "critical": ("F", "C", 5),
    "off": ("S", "O", 6),
}
# reversed access
LOGCAT_LEVELS = dict(((tup[0], level) for level, tup in LEVELS.items()))
PAPER_LEVELS = dict(((tup[1], level) for level, tup in LEVELS.items()))

LOGCAT_RE = re_comp(
    r"\d+-\d+ (\d+:\d+:\d+)\.\d+ (\w)/(\S+)\s*\(\s*\d+\): \[(.*?)\] (.*)"
)
PAPER_RE = re_comp(r"(\w) \d+-\d+-\d+ (\d+:\d+:\d+) \[(.*?)\] \[(.*?)\] (.*)")
PAPER_SINGLE_RE = re_comp(r"(\w) \d+-\d+-\d+ (\d+:\d+:\d+) \[(.*?)\] (.*)")
LINE_RE = re_comp(r"(.*)(:\d*:\d* @ .*)")


class LogArgs:
    """
    log
    Retrieves Beat Saber mod log messages.
    """

    app_id = arg("a", "app-id", DEFAULT_APP, help="the application id")
    all_mods = arg("A", "all", False, help="view logs from all mods")
    clear_log = arg("c", "clear", False, help="clear logcat before starting log")
    interactive = arg("i", "interactive", False, help="choose from a list of log files")
    realtime = arg("l", "live", False, help="save realtime logcat output")
    min_level = arg(
        "L",
        "level",
        "debug",
        help="minimum log level (debug, info, warning, error, or critical)",
    )
    out_file = arg(
        "o", "out", Path("./log.log"), "FILE", help="the output for the log file"
    )
    console = arg("p", "print", False, help="print output to console instead of file")
    raw = arg(
        "r", "raw", False, help="skip all processing and normalization of messages"
    )
    tag = arg("t", "tag", str, help="the custom logger tag of your mod, if not default")
    trims = arg(
        "T",
        "trim",
        [],
        "time|level|tag|line|all",
        help="trims header information from messages",
    )
    fix_paths = arg(
        "x", "expand-paths", False, help="add project dir to paths in logged line info"
    )


@dataclass
class Trims:
    time: bool = False
    level: bool = False
    tag: bool = False
    line: bool = False


def parse_message(message: str, args: LogArgs):
    regex = (
        LOGCAT_RE if args.realtime else (PAPER_RE if args.all_mods else PAPER_SINGLE_RE)
    )
    matched = match(regex, message)
    if not matched:
        return None
    groups: Tuple[str, ...] = matched.groups()
    if args.realtime:
        time, level, tag, line, text = groups
    elif args.all_mods:
        level, time, tag, line, text = groups
    else:
        level, time, line, text = groups
        tag = args.tag or ""
    levels_dict = LOGCAT_LEVELS if args.realtime else PAPER_LEVELS
    return time, levels_dict[level], tag, line, text


def process_log_message(args: LogArgs, trims: Trims, message: str, output: TextIO):
    if args.raw:
        print(message, file=output)
    elif parsed := parse_message(message, args):
        time, level, tag, line, text = parsed
        if args.fix_paths and not trims.line:
            if matched := match(LINE_RE, line):
                path, etc = matched.groups()
                line = str(PROJECT_PATH / path) + etc
        # don't bother checking tag (mod) because it should have already been filtered
        meta: List[str] = []
        if not trims.level:
            meta.append(LEVELS[level][1])  # use paper abbreviation
        if not trims.time:
            meta.append(time)
        if not trims.tag:
            meta.append(f"[{tag}]")
        if not trims.line:
            meta.append(f"[{line}]")
        print(*meta, text, file=output)


def construct_trims(args: LogArgs) -> Trims:
    trims = Trims()
    for trim in args.trims:
        trim = trim.lower()
        if trim == "all":
            return Trims(True, True, True, True)
        if trim in vars(trims):
            setattr(trims, trim, True)
    return trims


def run_with_output(args: LogArgs, output: TextIO):
    logcat_level, _, min_level_idx = LEVELS[args.min_level]
    trims = construct_trims(args)
    if args.realtime:
        pid_filter = ""
        if (pid := get_pid(args.app_id)) is not None:
            pid_filter = f"--pid {pid}"
        if args.clear_log:
            run("adb logcat -c")
        tag = "*" if args.all_mods else (args.tag or "")
        msg_filter = f"{tag}:{logcat_level}"
        for line in run(
            "adb logcat -v time *:S", pid_filter, msg_filter, yield_capture=True
        ):
            process_log_message(args, trims, line.strip(), output)
    else:
        search = "Paperlog.log" if args.all_mods else (args.tag or "")
        logs_path = get_mod_data(args.app_id, "logs2")
        all_logs = run("adb shell ls", logs_path, capture=True).strip().splitlines()
        for log_file in all_logs:
            if search.lower() in log_file.lower():
                args.tag = log_file.strip(".log")
                with TemporaryDirectory("r") as d:
                    f = Path(d) / "log.log"
                    run("adb pull", f"{logs_path}/{log_file}", f.absolute())
                    for line in f.read_text().splitlines():
                        level = PAPER_LEVELS[line[0]]
                        if LEVELS[level][2] < min_level_idx:
                            continue
                        process_log_message(args, trims, line.strip(), output)
                break
        else:
            log("Error: log for", search, "not found")
            exit(1)


def get_file_choice(files: List[str]) -> int:
    try:
        import readline as _  # improves input()
    except ModuleNotFoundError:
        pass
    while True:
        log("Choose a file:", end=" ")
        selected = input()
        try:
            parsed = int(selected)
            if parsed < 0:
                log("Error: Index is below 0")
                continue
            if parsed >= len(files):
                log("Error: Index is above", len(files) - 1)
                continue
            return parsed
        except ValueError:
            for i, name in enumerate(files):
                if selected.lower() in name.lower():
                    return i
            log("Error:", selected, "not found")


def set_interactive_input(args: LogArgs):
    if args.realtime:
        log("Error: --interactive is not compatible with --live")
        exit(1)
    files = run(
        "adb shell ls -p", get_mod_data(args.app_id, "logs2"), capture=True
    ).splitlines()
    if len(files) == 0:
        log("Error: No logs found")
        exit(1)
    for i, name in enumerate(files):
        print(i, "\t  ", name)
    try:
        idx = get_file_choice(files)
    except KeyboardInterrupt:
        exit(1)
    args.tag = files[idx]


def set_min_level(args: LogArgs):
    if args.min_level:
        args.min_level = args.min_level.lower()
        for level in LEVELS:
            if level.startswith(args.min_level):
                args.min_level = level
                return
    log("Error: Invalid minimum level")
    exit(1)


def main(args: LogArgs):
    set_min_level(args)
    if args.tag is None:
        args.tag = get_mod_id()
    if args.interactive:
        set_interactive_input(args)
    if args.console:
        run_with_output(args, stdout)
    else:
        with open(args.out_file, "w") as f:
            run_with_output(args, f)


if __name__ == "__main__":
    with parse(LogArgs) as args:
        main(args)
