# -*- coding: utf-8 -*-
import argparse
import sys
import logging

logger = logging.getLogger(__name__)


class CustomFormatter(argparse.HelpFormatter):
    def __init__(self, prog):
        # default max_help_position increased for readability
        super(CustomFormatter, self).__init__(prog, max_help_position=50)

    def add_usage(self, usage, actions, groups, prefix=None):
        """
        Hack add_usage to add fake "-- command [arguments]" to usage
        """
        actions.append(argparse._StoreAction(
            option_strings=[],
            dest="-- command [arguments]"
        ))
        return super(CustomFormatter, self).add_usage(
            usage, actions, groups, prefix
        )


def get_parser():
    """ Create ianotor argument parser with a set of reasonable defaults
    :return: argument parser
    """
    parser = argparse.ArgumentParser(
        "hupswitch",
        description="Greceful reloader for services",
        formatter_class=CustomFormatter,
    )

    parser.add_argument(
        "-v", "--verbose",
        action="count",
        help="enable logging to stdout (use multiple times to increase verbosity)",  # noqa
    )

    parser.add_argument(
        '-w', '--warmup-time',
        metavar='SEC',
        type=float,
        default=0,
        help="Time for warmup of new service before attempting to shutdown the old one",  # noqa
    )

    parser.add_argument(
        '-k', '--kill-at-exit',
        action="store_true",
        help="Kill the child process when HUP watch exits"
    )
    return parser


def parse_args():
    """
    Parse program arguments.
    This function ensures that argv arguments after '--' won't be parsed by
    `argparse` and will be returned as separate list.
    :return: (args, command) two-tuple
    """

    parser = get_parser()

    try:
        split_point = sys.argv.index('--')

    except ValueError:
        if "--help" in sys.argv or "-h" in sys.argv or len(sys.argv) == 1:
            parser.print_help()
            exit(0)
        else:
            parser.print_usage()
            print(parser.prog, ": error: command missing")
            exit(1)

    else:
        argv = sys.argv[1:split_point]
        invocation = sys.argv[split_point + 1:]

        args = parser.parse_args(argv)

        return args, invocation
