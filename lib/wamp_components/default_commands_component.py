import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from lib.config import config

import re


class DefaultCommandsComponent:
    def run(self):
        print("Starting Default Commands Component...")

        url = "ws://%s:%s/ws" % (config["crossbar"]["host"], config["crossbar"]["port"])

        runner = ApplicationRunner(url=url, realm=config["crossbar"]["realm"])
        runner.run(DefaultCommandsWAMPComponent)


class DefaultCommandsWAMPComponent(ApplicationSession):
    def onConnect(self):
        self.join(config["crossbar"]["realm"])

    def onDisconnect(self):
        print("Disconnected from Crossbar!")

    @asyncio.coroutine
    def onJoin(self, details):

        # RPC Endpoints
        def hello(**kwargs):
            response = {
                "channel": kwargs.get("event").get("channel"),
                "text": "Hello @%s!" % kwargs.get("user_info").get("name")
            }

            return response

        def echo(**kwargs):
            response = {
                "channel": kwargs.get("event").get("channel"),
                "text": re.sub(r'^echo\s', "", kwargs.get("message"))
            }

            return response

        yield from self.register(hello, "%s.hello" % config["crossbar"]["realm"])
        yield from self.register(echo, "%s.echo" % config["crossbar"]["realm"])
