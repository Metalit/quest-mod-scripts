from lib.args import parse

from debug import DebugArgs, main

if __name__ == "__main__":
    with parse(DebugArgs) as args:
        main(args)
