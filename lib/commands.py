import yaml

with open("config/commands.yaml", "r") as f:
    commands_default = yaml.load(f)

with open("config/commands.custom.yaml", "r") as f:
    commands_custom = yaml.load(f) or dict()

commands = commands_default.copy()
commands.update(commands_custom)