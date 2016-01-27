# -*- coding: utf-8 -*-
import atexit
import os
import time
import signal
import logging

from hupwatch.service import Service
from hupwatch.args_parser import parse_args


logger = logging.getLogger(__name__)

delayed_exit = False


def setup_logging(verbosity):
    ilogger = logging.getLogger(__name__)

    if verbosity:
        handler = logging.StreamHandler()
        if verbosity == 1:
            handler.setLevel(logging.ERROR)
        if verbosity == 2:
            handler.setLevel(logging.WARNING)
        if verbosity >= 3:
            handler.setLevel(logging.DEBUG)
    else:
        handler = logging.NullHandler()

    formatter = logging.Formatter(
        '=> HUP watch [%(levelname)-8s]: %(message)s'
    )

    handler.setFormatter(formatter)
    ilogger.setLevel(logging.DEBUG)
    ilogger.addHandler(handler)


def main():
    args, command = parse_args()
    setup_logging(args.verbose)

    logger.info("Starting HUP watch (%s)" % os.getpid())

    # use list becasue Python 2 does not provide nonlocal statement
    services = [Service(command)]
    services[0].start()
    logger.info("Child process {pid} started".format(
        pid=services[0].process.pid
    ))

    def hup_handler(*_):
        logger.debug("HUP: >>>")
        try:
            old_service = services.pop()
        except IndexError:
            logger.error("HUP: Received HUP while service list is empty")
            return

        new_service = Service(command)
        new_service.start()

        logger.debug("HUP: Waiting for process ({pid}) to warm up".format(
            pid=new_service.process.pid,
        ))
        time.sleep(args.warmup_time)

        if new_service.is_up():
            logger.debug("HUP: Sending SIGTERM to old process ({pid})".format(
                pid=old_service.process.pid,
            ))
            old_service.process.send_signal(signal.SIGTERM)

            logger.debug("HUP: Waiting for process ({pid}) to quit...".format(
                pid=old_service.process.pid
            ))
            logger.info(
                "HUP: Old process quit with code: {code}".format(
                    code=old_service.process.wait()
                )
            )
            services.append(new_service)
        else:
            # note: It may look like there is a small race condition between
            #       SIGHUP and SIGCHLD but sigchld_handler will check if
            #       current service is running so hupwatch won't quit eagerly
            # note: We may think about getting rid of SIGCHLD handler anyway
            #       and simply poll service[0] process later in the main loop.
            #       This may simplify things a bit
            logger.error("HUP: new process failed to start. Abort reload")
            services.append(old_service)

        logger.debug("HUP: <<<")

    def sigchld_handler(*_):
        logger.debug("CHLD: >>>")

        try:
            service = services.pop()
        except IndexError:
            logger.info("CHLD: Child process quit")
        else:
            if service.is_up():
                logger.warning(
                    "CHLD: Primary child process quit, quitting"
                )
                exit(1)
            else:
                logger.info(
                    "CHLD: Primary process is up, continuing..."
                )
                services.append(service)

        logger.debug("CHLD: <<<")

    def term_handler(*_):
        logger.debug("TERM: >>>")

        try:
            service = services.pop()
        except IndexError:
            # note: apparently we have interrupted other signal handler
            #       so raise alarm that will try to run this handler again
            logger.info(
                "TERM: TERM/ALARM received during other signal handling. Defer."
            )
            signal.alarm(1)
        else:
            if service.is_up():
                if args.kill_at_exit:
                    logger.warning(
                        "TERM: Quiting with --kill-at-exit and running "
                        "child process. Killing it!"
                    )
                    service.kill()
                else:
                    logger.warning(
                        "TERM: Quiting with running child process. "
                        "Doing nothing, child will be detached to new parent."
                    )
            else:
                logger.debug("Child process not up. Quiting.")

            services.append(service)

            logger.debug("TERM: <<<")
            exit()

    signal.signal(signal.SIGHUP, hup_handler)
    signal.signal(signal.SIGCHLD, sigchld_handler)

    signal.signal(signal.SIGTERM, term_handler)
    signal.signal(signal.SIGALRM, term_handler)

    atexit.register(term_handler)

    while services[0].is_up():
        logger.info("Pausing for signal")
        signal.pause()

        if delayed_exit:
            logger.info("delayed exit")
            exit()

