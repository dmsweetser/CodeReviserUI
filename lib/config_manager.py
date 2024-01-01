import json

def load_config():
    try:
        with open('config.json', 'r') as file:
            config_data = json.load(file)
    except FileNotFoundError:
        config_data = {}
    
    return config_data

def get_config(key, default=None):
    config = load_config()

    if key not in config:
        config[key] = default
        update_config(key, default)

    return config.get(key, default)

def update_config(key, value):
    config = load_config()
    config[key] = value

    with open('config.json', 'w') as file:
        json.dump(config, file, indent=2)
