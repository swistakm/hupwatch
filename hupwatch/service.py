# -*- coding: utf-8 -*-
import subprocess
import logging

import os

logger = logging.getLogger(__name__)


class Service(object):
    def __init__(self, command):
        self.command = command
        self.process = None

    def start(self):
        """ Start service process.
        :return:
        """
        logger.debug("starting service: %s" % " ".join(self.command))
        self.process = subprocess.Popen(self.command, preexec_fn=os.setpgrp)

    def is_up(self):
        """
        Poll service process to check if service is up.
        :return:
        """
        logger.debug("polling service")
        return bool(self.process) and self.process.poll() is None

    def kill(self):
        """
        Kill service process """
        logger.debug("killing service")
        if self.process is None:
            raise RuntimeError("Process does not exist")

        self.process.kill()
