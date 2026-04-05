from lib.args import arg, parse
from lib.constants import DEFAULT_APP
from lib.run import run
from lib.util import get_pid, kill_app, start_unity_app

from time import sleep


class RestartArgs:
    """
    restart
    Closes and relaunches the Beat Saber application.
    """

    app_id = arg("a", "app-id", DEFAULT_APP, help="the application id")
    double = arg("d", "double", False, help="launches the game twice with a delay")
    power_on = arg("p", "power-on", False, help="turns on the headset after launching")
    proximity = arg("P", "proximity", False, help="enables the proximity sensor")
    no_proximity = arg("N", "no-proximity", False, help="disables the proximity sensor")


def enable_power():
    power = run(
        'adb shell "dumpsys power | grep mHoldingDisplaySuspendBlocker"',
        capture=True,
    )
    if "false" in power:
        run("adb shell input keyevent KEYCODE_POWER")


def set_proximity(args: RestartArgs):
    sensor_broadcast = None
    if args.no_proximity:
        sensor_broadcast = "com.oculus.vrpowermanager.prox_close"
    elif args.proximity:
        sensor_broadcast = "com.oculus.vrpowermanager.automation_disable"
    if sensor_broadcast:
        run("adb shell am broadcast -a", sensor_broadcast, silent=True)


def main(args: RestartArgs):
    if args.power_on:
        enable_power()
    if get_pid(args.app_id) is not None:
        kill_app(args.app_id)
    start_unity_app(args.app_id)
    set_proximity(args)
    if args.double:
        sleep(1)
        start_unity_app(args.app_id)


if __name__ == "__main__":
    with parse(RestartArgs) as args:
        main(args)
