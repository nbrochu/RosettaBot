import asyncio
import json
import time

import redis
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

from lib.config import config


class CommandRunnerComponent:
    def run(self):
        print("Starting Command Runner WAMP Component...")

        url = "ws://%s:%s/ws" % (config["crossbar"]["host"], config["crossbar"]["port"])

        runner = ApplicationRunner(url=url, realm=config["crossbar"]["realm"])
        runner.run(CommandRunnerWAMPComponent)


class CommandRunnerWAMPComponent(ApplicationSession):
    def __init__(self, c=None):
        super().__init__(c)

        self.redis_client = redis.StrictRedis(
            host=config["redis"]["host"],
            port=config["redis"]["port"],
            db=config["redis"]["databases"]["main"]
        )

        self._stopped = False

    def onConnect(self):
        self.join(config["crossbar"]["realm"])

    def onDisconnect(self):
        print("Disconnected from Crossbar!")
        self._stopped = True

    @asyncio.coroutine
    def onJoin(self, details):
        while not self._stopped:
            command = self.redis_client.rpop("rosetta:commands:queue")

            if command is None:
                time.sleep(0.1)
                continue

            try:
                command_object = json.loads(command.decode("utf-8"))
                print(command_object)

                response = yield from self.call(command_object.get("endpoint"), **command_object)
                self.redis_client.lpush("rosetta:responses:queue", json.dumps(response))
            except Exception as e:
                print(e)
                pass