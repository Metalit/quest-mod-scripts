# Quest Mod Scripts

Building and debugging scripts for quest mods, intended to be used with my template (coming soon).

<details>

<summary>How to add to an existing QPM package</summary>

Run: `qpm dependency add mod-scripts`

Add the following to `workspace` in your `qpm.json`:

```json
"scripts": {
  "build": [
    "python ./extern/includes/mod-scripts/shared/build.py $0:?"
  ],
  "copy": [
    "python ./extern/includes/mod-scripts/shared/cpy.py $0:?"
  ],
  "dbg": [
    "python ./extern/includes/mod-scripts/shared/dbg.py $0:?"
  ],
  "log": [
    "python ./extern/includes/mod-scripts/shared/log.py $0:?"
  ],
  "profile": [
    "python ./extern/includes/mod-scripts/shared/profile.py $0:?"
  ],
  "restart": [
    "python ./extern/includes/mod-scripts/shared/restart.py $0:?"
  ]
},
```

</details>

## Build

Compiles the code into a `.so` library. This script does not create a QMOD, since `qpm qmod zip` exists and will automatically run `qpm s build`.

- `-b` / `--build`: The directory where the build files will be written. Warning: will be recursively deleted with `--clean`. Default: `build`.

- `-B` / `--build-flags`: Extra flags that will be passed to the compiler, through extra arguments in `cmake --build`. Can be a string or list of strings.

- `-c` / `--clean`: Removes the build directory before building to ensure a clean build.

- `-d` / `--debug`: Creates a debug binary, in terms of build type (`Debug` instead of `RelWithDebInfo`).

- `-D` / `--define`: Adds extra C++ compile definitions to the build. Can be with a value, such as `-D FOO=1`, or just `-D FOO`. Note: requires extra code in `CMakeLists.txt` to work.

- `-j` / `--java`: An optional path to a java directory that will also be built first. See the [hollywood](https://github.com/Fernthedev/HollywoodQuest) mod for an example setup of this.

- `-o` / `--java-out`: The destination for the `classes.dex` built from the java project. Does nothing if `--java` is not specified. Default: `assets/classes.dex`.

- `-p` / `--parallel`: The amount of threads to use while building. Note: only affects the C++ build, not `--java`. Default: 4.

- `-s` / `--source`: The root directory of the project that should contain the `CMakeLists.txt` file. Default: `.` (the current directory with `qpm.json`).

## Copy

Copies libraries and `fileCopies` files to their destinations based on the `mod.json` (generating it with `qpm qmod manifest` as necessary). This script does not actually build the libraries due to the amount of extra arguments that would be necessary to configure the build script.

May potentially be extended to support BSML asset files in the future, for utility with hot reload.

- `-a` / `--app-id`: The app id, used to determine the destination `Modloader` path for library files. Default: `com.beatgames.beatsaber`.

- `-s` / `--skip`: Skips files that are not found, instead of erroring and exiting the script early.

- `-r` / `--regen`: Always generates the `mod.json`, instead of only doing so when either the `mod.template.json` or `qpm.shared.json` have been more recently modified.

- `-R` / `--no-regen`: Never generates the `mod.json`, even if it does not exist (erroring in that case). Does nothing if `--regen` is specified.

## Debug

Finds, pulls, and analyzes the most recent crash stack trace from the device (with `ndk-stack`). Searches both tombstone files and the global `Paperlog.log` file, for `trace_exception`s.

- `-a` / `--app-id`: The app id, used to determine the tombstone and log file locations. Default: `com.beatgames.beatsaber`.

- `-A` / `--no-analyze`: Skips the analysis step with `ndk-stack`, only outputting the raw stack trace.

- `-i` / `--input`: An optional input file to analyze, instead of pulling the most recent from the device.

- `-o` / `--output`: The output file where the stack trace will be written. Default: `crash.log`.

- `-q` / `--quiet`: Disables the printing of status information about all found tombstones and log stack traces.

- `-s` / `--symbols`: The directory containing `.so` files with debug information, for use in analysis with `ndk-stack`. Default: `build/debug`.

## Log

Retrieves messages logged by mods (primarily with [paperlog](https://github.com/Fernthedev/paperlog)) with a lot of options.

Note that if `--live` and `--all` are used together, and the game is not already running before the script is started, the PID filtering will fail and log messages from other processes will also appear in the output.

- `-a` / `--app-id`: The app id, used to determine the log file locations or process ID. Default: `com.beatgames.beatsaber`.

- `-A` / `--all`: Filters for logs from all mods, instead of only a specific tag.

- `-c` / `--clear`: Clears the logcat buffer before starting to log. Does nothing if `--live` is not specified.

- `-l` / `--live`: Uses realtime messages from `adb logcat` instead of the written log files. Errors if `--interactive` is also specified.

- `-i` / `--interactive`: Presents a list of written log files instead of using `--tag` or automatically detecting. Errors if `--live` is also specified.

- `-L` / `--level`: The minimum log level to filter for. Options: `debug`, `info`, `warning`, `error`, or `critical` (or any substring those options begin with). Default: `debug`.

- `-o` / `--out`: The output file for log messages. Default: `log.log`. Does nothing if `--print` is specified.

- `-p` / `--print`: Prints log messages to the console instead of to the output file.

- `-r` / `--raw`: Disables all processing and normalization of log messages. `--tag` and `--level` will still work.

- `-t` / `--tag`: Filter for a custom log tag, instead of detecting it based on `name` in `qpm.json` (the default tag with my template, or if `MOD_ID` is used). Does nothing if `--all` is specified.

- `-T` / `--trim`: Trims header information from log messages. Options (multiple can be specified): `time`, `level`, `tag`, `line`, or `all`. Does nothing if `--raw` is specified.

- `-x` / `--expand-paths`: Adds the current directory to the paths in log messages with function and line information. This can be useful if `PAPER_ROOT_FOLDER_LENGTH` is defined, since VSCode only seems to recognize absolute file paths in `.log` files.

## Profile

Profiles the game's (CPU) performance to a HTML output file, using the NDK Simpleperf tool. This requires the game to be patched with debugging allowed in its manifest, unless `adb root` is available.

- `-a` / `--app-id`: The app id to profile. Default: `com.beatgames.beatsaber`.

- `-d` / `--data`: The file to output the raw performance data to (not the HTML report). Default: `perf.data`.

- `-o` / `--out`: The final output file for the HTML performance report. Default: `report.html`.

- `-P` / `--no-profile`: Skips the on-device profiling step and only creates a report based on a preexisting data file.

- `-R` / `--no-report`: Skips the report creation step and only creates a data file with an on-device profile.

- `-s` / `--symbols`: The directory containing `.so` files with debug symbols, used by Simpleperf to get readable function names. Default: `build/debug`.

- `-u` / `--use-root`: Attempts to use `adb root` for the profiling, bypassing the need for the app to be debuggable. Does nothing if `--no-profile` is specified.

## Restart

Launches the game, closing it if it was already running, so that newly copied or installed mods can be automatically reloaded. Can also modify the proximity sensor state and power on the device.

- `-a` / `--app-id`: The app id to force stop and launch. Default: `com.beatgames.beatsaber`.

- `-d` / `--double`: Waits a second after launching the game then sends the launch command again. This has been inconsistently useful in the past to bypass the "Restore app" prompt.

- `-p` / `--power-on`: Turns on the device before restarting the app.

- `-P` / `--proximity`: Enables the proximity sensor on Quest headsets, which makes the screen go black if an object (typically your head) is detected close to the area directly above the lenses. Does nothing if `--no-proximity` is specified.

- `-N` / `--no-proximity`: Disables the proximity sensor on Quest headsets, allowing it to stay awake even when not worn.
