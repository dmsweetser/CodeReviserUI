import json
import shutil

def load_config():
    with open('config.json', 'r') as file:
        config_data = json.load(file)

    return config_data

def is_numeric(value):
    return isinstance(value, (int, float)) and (isinstance(value, float) or str(value).replace('.', '', 1).isdigit())

def get_config(key, default=None):
    config = load_config()

    if key not in config:
        config[key] = default
        update_config(key, default)

    # Check if the value is numeric and cast it to the appropriate type
    if is_numeric(config[key]):
        config[key] = int(config[key]) if float(config[key]).is_integer() else float(config[key])

    return config.get(key, default)

def update_config(key, value):
    config = load_config()

    # Cast the value to the appropriate type if it is numeric
    if is_numeric(value):
        value = int(value) if float(value).is_integer() else float(value)

    config[key] = value

    with open('config.json', 'w') as file:
        json.dump(config, file, indent=2)
