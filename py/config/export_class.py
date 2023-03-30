from io import TextIOWrapper
import json
from pathlib import Path

PATH = "./config/"
CONFIG_JSON_PATH = PATH + "config.json"
CONFIG_PY_PATH = PATH + "config.py"
CONFIG_FILE = Path(CONFIG_JSON_PATH).resolve()


class ConfigManager:
    def __init__(self, config_file: Path) -> None:
        with config_file.open("r", encoding="utf-8") as f:
            self.config: dict = json.load(f)

        self.upper_keys = []
        for key, values in self.config.items():
            if isinstance(values, dict):
                u_key = key.upper()
                self.upper_keys.append(u_key)
                class_def = [f"class {u_key}:"]
                class_def.append("\tdef __init__(self, config):")
                class_def.append('\t\t"""')
                class_def.append(f" config: {CONFIG_FILE.stem}['{key}']")
                class_def.append("\t\t\"\"\"")
                for k1, v1 in values.items():
                    class_def.append(f"\t\tself.{k1.upper()} = config['{k1}']")
                class_def.append("\n")
                exec("\n".join(class_def))

        self.classes = {}
        for u_key in self.upper_keys:
            self.classes[u_key] = eval(
                f"{u_key}(self.config['{u_key.lower()}'])")

    def get_config(self, key: str) -> dict:
        return self.config.get(key, {})

    def export(self) -> None:
        with open(CONFIG_PY_PATH, "w", encoding="utf-8") as file:
            file.writelines([
                "import json\n",
                "from pathlib import Path\n",
                f'CONFIG_FILE = "{CONFIG_JSON_PATH}"\n',
                "\n\n"
            ])
            for u_key in self.upper_keys:
                file.writelines([
                    f'class {u_key}: \n',
                    '\tdef __init__(self, config):\n',
                    '\t\t"""',
                    f'\t\tconfig: {CONFIG_FILE.stem}.json[\'{u_key.lower()}\']\n',
                    '\t\t\"\"\"\n'
                ])
                for k1, v1 in self.classes[u_key].__dict__.items():
                    if not k1.startswith("_"):
                        file.write(
                            f"\t\tself.{k1}: {type(v1).__name__} = config['{k1.lower()}']\n")
                if u_key == "OPENAI":
                    self.generate_key(file)
                file.write("\n\n")

            file.writelines([
                f'class ConfigManager:\n',
                '\tdef __init__(self, config_file):\n',
                f'\t\tconfig_file = Path(config_file).resolve()\n',
                f'\t\twith open(config_file, "r", encoding="utf-8") as f:\n',
                '\t\t\tself.config_manager = json.load(f)\n'
            ])

            for u_key in self.upper_keys:
                file.write(
                    f"\t\tself.{u_key} = {u_key}(self.config_manager['{u_key.lower()}'])\n")
            file.write("\n")
            file.write("\tdef get_config(self, key):\n")
            file.write("\t\treturn self.config_manager.get(key)\n")
            file.write("\n")
            file.write("config = ConfigManager(CONFIG_FILE)\n")

    def generate_key(self, file:TextIOWrapper):
        varName = "CURRENT_KEY_INDEX"
        file.write(f"\t\tself.{varName}:int = 0\n\n")
        # get_current_key
        file.writelines([
            "\tdef get_curren_key(self, index:int = None):\n",
            f"\t\tindex = index or self.{varName}\n",
            "\t\treturn self.API_KEY[index]\n",
            "\n"
            ])
        # add_key_index
        file.write(f"\tdef add_key_index(self):\n\t\tself.{varName} += 1\n")
        file.write("\n")
        # reset_key_index
        file.write(f"\tdef reset_key_index(self):\n\t\tself.{varName} = 0\n")
        file.write("\n")


ConfigManager(config_file=CONFIG_FILE).export()
