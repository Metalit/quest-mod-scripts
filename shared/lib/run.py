from pathlib import Path
from signal import SIG_DFL, SIGINT, signal
from subprocess import PIPE, STDOUT, Popen
from sys import stderr
from threading import Thread
from typing import Any, Generator, Literal, Optional, Tuple, Union, overload


class Runner:
    def __init__(
        self,
        *args: Any,
        wd: Optional[Path],
        stdin: Optional[str],
        capture: bool,
        silent: bool,
        raise_interrupt: bool,
    ) -> None:
        self.command = " ".join((str(arg) for arg in args))
        self.wd = wd
        self.stdin = stdin
        self.capture = capture
        self.silent = silent
        self.code = 0
        self.raise_interrupt = False
        self.interrupt = False

    def write_stdin(self, process: Popen[str]):
        if process.stdin:
            if self.stdin is not None:
                process.stdin.write(self.stdin)
            process.stdin.close()

    def sigint_handler(self, *_: Any):
        self.interrupt = True

    def __iter__(self):
        sub_stdout = PIPE if self.capture or self.silent else None
        sub_stderr = STDOUT if self.silent else None
        # catching the interrupt doesn't seem to work right
        signal(SIGINT, self.sigint_handler)
        process = Popen(
            self.command,
            shell=True,
            text=True,
            cwd=self.wd,
            stdin=PIPE,
            stdout=sub_stdout,
            stderr=sub_stderr,
        )
        try:
            Thread(target=self.write_stdin, args=[process], daemon=True).start()
            if process.stdout:
                for line in process.stdout:
                    yield line
            process.wait()
        finally:
            process.terminate()
            signal(SIGINT, SIG_DFL)
        if self.interrupt and self.raise_interrupt:
            raise KeyboardInterrupt
        elif self.interrupt:
            self.code = 0
        else:
            self.code = process.poll() or 0


@overload
def run(
    *args: Any,
    wd: Optional[Path] = None,
    stdin: Optional[str] = None,
    silent: bool = False,
    yield_capture: Literal[True],
    raise_interrupt: bool = True,
) -> Generator[str, None, None]: ...


@overload
def run(
    *args: Any,
    wd: Optional[Path] = None,
    stdin: Optional[str] = None,
    silent: bool = False,
    capture: Literal[True],
    fail_ok: Literal[True],
    raise_interrupt: bool = True,
) -> Tuple[int, str]: ...


@overload
def run(
    *args: Any,
    wd: Optional[Path] = None,
    stdin: Optional[str] = None,
    silent: bool = False,
    capture: Literal[False],
    fail_ok: Literal[True],
    raise_interrupt: bool = True,
) -> int: ...


@overload
def run(
    *args: Any,
    wd: Optional[Path] = None,
    stdin: Optional[str] = None,
    silent: bool = False,
    fail_ok: Literal[True],
    raise_interrupt: bool = True,
) -> int: ...


@overload
def run(
    *args: Any,
    wd: Optional[Path] = None,
    stdin: Optional[str] = None,
    silent: bool = False,
    capture: bool = False,
    fail_ok: Literal[False],
    raise_interrupt: bool = True,
) -> str: ...


@overload
def run(
    *args: Any,
    wd: Optional[Path] = None,
    stdin: Optional[str] = None,
    silent: bool = False,
    capture: bool = False,
    raise_interrupt: bool = True,
) -> str: ...


def run(
    *args: Any,
    wd: Optional[Path] = None,
    stdin: Optional[str] = None,
    silent: bool = False,
    yield_capture: bool = False,
    capture: bool = False,
    fail_ok: bool = False,
    raise_interrupt: bool = True,
) -> Union[Generator[str, None, None], int, str, Tuple[int, str]]:
    process = Runner(
        *args,
        wd=wd,
        stdin=stdin,
        capture=capture or yield_capture,
        silent=silent,
        raise_interrupt=raise_interrupt,
    )
    if yield_capture:
        return process.__iter__()
    else:
        output = ""
        for line in process:
            output += line
        output = output.strip()
        if not fail_ok:
            if process.code != 0:
                print("Error running:", process.command, file=stderr)
                if output:
                    print(output, file=stderr)
                exit(process.code)
            return output
        if not capture:
            return process.code
        return process.code, output


__all__ = ["run"]
