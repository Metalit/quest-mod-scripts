from lib.util import log

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)


T = TypeVar("T")

_order = 0


@dataclass
class Argument:
    short: str
    long: str
    default: Any
    metavar: Optional[str]
    help: Optional[str]
    typ: type
    order: int


@overload
def arg(
    short: str,
    long: str,
    def_or_type: Type[T],
    mv: Optional[str] = None,
    help: Optional[str] = None,
) -> Optional[T]: ...


@overload
def arg(
    short: str,
    long: str,
    def_or_type: List[Any],
    mv: Optional[str] = None,
    help: Optional[str] = None,
) -> List[str]: ...


@overload
def arg(
    short: str,
    long: str,
    def_or_type: T,
    mv: Optional[str] = None,
    help: Optional[str] = None,
) -> T: ...


def arg(
    short: str,
    long: str,
    def_or_type: Union[T, Type[T]],
    mv: Optional[str] = None,
    help: Optional[str] = None,
) -> Optional[T]:
    global _order
    _order += 1
    if isinstance(def_or_type, type):
        a = Argument(short, long, None, mv, help, def_or_type, _order)
    else:
        a = Argument(short, long, def_or_type, mv, help, type(def_or_type), _order)
    # Basically, lie about the type, then fix it in parse() so it's correct when used
    return a  # type: ignore


def _parse(args_class: Type[T]) -> Tuple[T, Optional[str]]:
    inst = args_class()
    attributes: Dict[str, Argument] = {}

    for name in dir(inst):
        attribute = getattr(inst, name)
        if isinstance(attribute, Argument):
            attributes[name] = attribute

    split = (inst.__doc__ or "").strip().splitlines() or [""]
    title = split[0].strip() or None
    desc = "\n".join(split[1:]).strip() or None

    parser = ArgumentParser(
        prog=title, description=desc, formatter_class=ArgumentDefaultsHelpFormatter
    )
    for name, arg in sorted(attributes.items(), key=lambda tup: tup[1].order):
        if arg.typ == bool:
            action = "store_false" if arg.default else "store_true"
            parser.add_argument(
                "-" + arg.short,
                "--" + arg.long,
                action=action,
                dest=name,
                help=arg.help,
            )
        else:
            nargs = None
            action = "store"
            if arg.typ == list:
                action = "extend"
                if len(arg.default) > 0:
                    nargs = "+"
                    arg.typ = type(arg.default[0])
                else:
                    nargs = "*"
                    arg.typ = str
            parser.add_argument(
                "-" + arg.short,
                "--" + arg.long,
                nargs=nargs,
                action=action,
                dest=name,
                default=arg.default,
                type=arg.typ,
                metavar=arg.metavar,
                help=arg.help,
            )

    output = parser.parse_args()
    for name in attributes:
        setattr(inst, name, getattr(output, name))

    return (inst, title)


# Context manager to handle exceptions in fewer lines
class parse(Generic[T]):
    def __init__(self, args_class: Type[T]) -> None:
        self.inst, self.title = _parse(args_class)

    def __enter__(self) -> T:
        return self.inst

    def __exit__(self, type: Type[Any], value: Optional[Exception], _) -> bool:
        if value is None:
            return True
        if type is KeyboardInterrupt:
            exit(1)
        if issubclass(type, Exception):
            if self.title:
                log("Error running script:", self.title)
            log(type.__name__ + ":", *value.args)
            return True
        return False


__all__ = ["arg", "parse"]
