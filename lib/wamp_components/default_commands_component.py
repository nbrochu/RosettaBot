import asyncio

from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from lib.config import config

from redis import StrictRedis

import re
import random
import json


class DefaultCommandsComponent:
    def run(self):
        print("Starting Default Commands Component...")

        url = "ws://%s:%s/ws" % (config["crossbar"]["host"], config["crossbar"]["port"])

        runner = ApplicationRunner(url=url, realm=config["crossbar"]["realm"])
        runner.run(DefaultCommandsWAMPComponent)


class DefaultCommandsWAMPComponent(ApplicationSession):

    def __init__(self, c=None):
        super().__init__(c)

        self.redis_client = StrictRedis(
            host=config["redis"]["host"],
            port=config["redis"]["port"],
            db=config["redis"]["databases"]["main"]
        )

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
                "text": "Hello @%s!" % kwargs.get("user_info").get("name"),
                "parse": "full"
            }

            return response

        def echo(**kwargs):
            response = {
                "channel": kwargs.get("event").get("channel"),
                "text": re.sub(r'^echo\s', "", kwargs.get("message")),
                "parse": "full"
            }

            return response

        def slap(**kwargs):
            emoji_list = eval(self.redis_client.lrange("slack:emojis", 0, 9999)[0].decode("utf-8"))
            emoji = random.choice(emoji_list)

            slap_phrases = config["slap"]
            slap_phrase = random.choice(slap_phrases)

            response = {
                "channel": kwargs.get("event").get("channel"),
                "text": slap_phrase
                    .replace("$SOURCEUSER$", "@%s" % kwargs.get("user_info").get("name"))
                    .replace("$TARGETUSER$", kwargs.get("message").split(" ")[1])
                    .replace("$EMOJI$", emoji),
                "parse": "none",
                "link_names": 1
            }

            return response

        yield from self.register(hello, "%s.hello" % config["crossbar"]["realm"])
        yield from self.register(echo, "%s.echo" % config["crossbar"]["realm"])
        yield from self.register(slap, "%s.slap" % config["crossbar"]["realm"])
