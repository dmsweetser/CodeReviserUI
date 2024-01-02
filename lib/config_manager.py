import json
import shutil

def load_config():
    try:
        with open('userconfig.json', 'r') as file:
            config_data = json.load(file)
    except FileNotFoundError:
        with open('config.json', 'r') as file:
            config_data = json.load(file)

    return config_data

def copy_to_user_config():
    base_config = load_config()
    with open('userconfig.json', 'w') as file:
        json.dump(base_config, file, indent=2)

def get_config(key, default=None):
    config = load_config()

    if key not in config:
        config[key] = default
        update_config(key, default)

    return config.get(key, default)

def update_config(key, value):
    config = load_config()
    config[key] = value

    with open('userconfig.json', 'w') as file:
        json.dump(config, file, indent=2)

    # After updating the user config, copy it to userconfig.json
    copy_to_user_config()
