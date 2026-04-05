from lib.args import arg, parse
from lib.run import run
from lib.util import log

from pathlib import Path
from shutil import rmtree, move
from zipfile import ZipFile


CMAKE_DEFINE_PREFIX = "_bs_build_def_"


class BuildArgs:
    """
    build

    Compiles the mod into a .so library. Does not create a QMOD.
    """

    build_dir = arg(
        "b",
        "build",
        Path("./build/"),
        "DIRECTORY",
        help="the directory for the build files",
    )
    build_flags = arg(
        "B", "build-flags", [], "FLAGS", help="flags to pass to the compiler"
    )
    clean = arg("c", "clean", False, help="removes previous build files")
    config_flags = arg("C", "config-flags", [], "FLAGS", help="flags to pass to cmake")
    debug = arg("d", "debug", False, help="builds a debug binary")
    defines = arg("D", "define", [], "DEFINITIONS", help="extra c++ definitions to add")
    java_dir = arg(
        "j", "java", Path, "DIRECTORY", help="a java project to additionally compile"
    )
    java_out = arg(
        "o",
        "java-out",
        Path("./assets/classes.dex"),
        "FILE",
        help="the destination for java classes.dex",
    )
    parallel = arg(
        "p", "parallel", 4, "COUNT", help="the amount of threads to use while building"
    )
    source_dir = arg(
        "s",
        "source",
        Path("."),
        "DIRECTORY",
        help="the directory containing CMakeLists.txt",
    )


def clean(args: BuildArgs):
    rmtree(args.build_dir)
    if args.java_dir:
        rmtree(args.java_dir / "app/build")


def build_java(args: BuildArgs):
    assert args.java_dir
    move_file = next(args.java_dir.rglob("build.gradle*disabled*"), None)
    move_temp = move_file.parent / "build.gradle" if move_file else Path()
    if move_file:
        move(move_file, move_temp)
    try:
        run("gradlew", "build", wd=args.java_dir)
    finally:
        if move_file:
            move(move_temp, move_file)
    with ZipFile(
        args.java_dir / "app/build/outputs/apk/release/app-release-unsigned.apk",
        "r",
    ) as apk:
        apk.extract("classes.dex", args.java_out)
    args.java_out.touch()


def create_define(define: str) -> str:
    if not "=" in define:
        define += '=""'
    return f"-D{CMAKE_DEFINE_PREFIX}{define}"


def configure(args: BuildArgs):
    mode = "Debug" if args.debug else "RelWithDebInfo"
    run(
        "cmake",
        "-G Ninja",
        f"-DCMAKE_BUILD_TYPE={mode}",
        "-B",
        args.build_dir.resolve(),
        f"-U{CMAKE_DEFINE_PREFIX}*",
        *[create_define(d) for d in args.defines],
        " ".join(args.config_flags),
        wd=args.source_dir,
    )


def build(args: BuildArgs):
    run(
        "cmake",
        "--build",
        args.build_dir.resolve(),
        "-j",
        args.parallel,
        "--" if len(args.build_flags) > 0 else "",
        " ".join(args.build_flags),
        wd=args.source_dir,
    )


def main(args: BuildArgs):
    for path in (args.source_dir, args.java_dir):
        if path and not path.exists():
            log("Error:", path, "does not exist")
            exit(1)
    if args.clean:
        clean(args)
    if args.java_dir:
        build_java(args)
    configure(args)
    build(args)


if __name__ == "__main__":
    with parse(BuildArgs) as args:
        main(args)
