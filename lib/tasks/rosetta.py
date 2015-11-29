from lib.config import config
from lib.commands import commands

import invoke
from invoke import task

from slackclient import SlackClient
from redis import StrictRedis

import json
import time
import sys
import re


redis_client = StrictRedis(
    host=config["redis"]["host"],
    port=config["redis"]["port"],
    db=config["redis"]["databases"]["main"]
)

channels = dict()


@task
def bot():
    try:
        slack_client = SlackClient(token=config["slack"]["token"])
        slack_client.rtm_connect()

        bot_info = json.loads(slack_client.api_call("auth.test").decode("utf-8"))
        last_ping = 0

        while True:
            last_ping = autoping(slack_client, last_ping)

            process_queued_responses(slack_client)

            for event in slack_client.rtm_read():
                print(event)
                event_type = event.get("type")

                if event_type == "message":
                    process_message_event(slack_client, bot_info, event)

                time.sleep(0.1)
    except KeyboardInterrupt:
        sys.exit(0)


# Autoping
def autoping(slack_client, last_ping):
    now = int(time.time())

    if now > last_ping + 10:
        slack_client.server.ping()
        return now
    else:
        return last_ping


def process_message_event(slack_client, bot_info, event):
    if event.get("channel") in channels:
        channel = channels[event.get("channel")]
    else:
        channel = slack_client.server.channels.find(event.get("channel"))
        channels[event.get("channel")] = channel

    is_private_message = True if len(channel.members) == 0 else False
    message = event.get("text")

    if is_private_message is False:
        if message.startswith("<@%s> " % bot_info.get("user_id")) or message.startswith("%s " % bot_info.get("user")):
            message = re.sub(r'^\<\@%s\> ' % bot_info.get("user_id"), "", message)
            message = re.sub(r'^%s ' % bot_info.get("user"), "", message)
        else:
            return None

    if message == "help":
        slack_client.api_call(
            "chat.postMessage",
            channel=event.get("channel"),
            text=generate_help_content(bot_info),
            as_user=True
        )
    else:
        command = fetch_command(message)

        if command is None:
            return None

        user_info = None

        if command.get("forward_user"):
            user_info = json.loads(slack_client.api_call("users.info", user=event.get("user")).decode("utf-8")).get("user")

        queue_command(
            command.get("endpoint"),
            message=message,
            event=event,
            user_info=user_info
        )

# Add more event type processing...


def generate_help_content(bot_info):
    supported_commands = []

    for command, params in commands.items():
        supported_commands.append("*%s*: %s" % (params.get("usage").replace("$BOTNAME$", bot_info.get("user")), params.get("description")))

    sorted_supported_commands = sorted(supported_commands)

    return "\n".join(sorted_supported_commands)


def fetch_command(message):
    for command, params in commands.items():
        if message.startswith("%s" % command):
            return params

    return None


def queue_command(endpoint, message=None, event=None, user_info=None):
    command = {
        "endpoint": endpoint,
        "message": message,
        "event": event,
        "user_info": user_info
    }

    redis_client.lpush("rosetta:commands:queue", json.dumps(command))

def process_queued_responses(slack_client):
    responses_to_process = redis_client.llen("rosetta:responses:queue")

    current_response = 1
    while current_response <= responses_to_process:
        try:
            response = json.loads(redis_client.rpop("rosetta:responses:queue").decode("utf-8"))

            slack_client.api_call(
                "chat.postMessage",
                as_user=True,
                parse="full",
                **response
            )

            current_response += 1
        except Exception:
            current_response += 1
            continue


namespace = invoke.Collection("rosetta")
namespace.add_task(bot, name="bot")
