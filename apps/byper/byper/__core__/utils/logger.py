from colorama import Fore, init

init(autoreset=True)


class Logger:
    @staticmethod
    def log(message, level="info", indent=0, newline=False):
        prefix = {
            "info": Fore.CYAN,
            "warn": Fore.YELLOW,
            "error": Fore.RED,
            "success": Fore.GREEN,
            "download": Fore.BLUE,
            "install": Fore.MAGENTA,
            "debug": Fore.WHITE,
            "step": Fore.CYAN,
            "replace": Fore.YELLOW,
            "skip": Fore.GREEN,
            "remove": Fore.RED,
            "command": Fore.BLACK,
        }.get(level, "")
        indent_space = "  " * indent
        print(f"{indent_space}{prefix}{message}", end="\n" if not newline else "\n\n")
