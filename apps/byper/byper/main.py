import importlib
import sys
from byper.__core__.constants import VERSION
from byper.__core__.commands import Commands
from byper.__core__.environment import Environment
from byper.__core__.helpers import generate_aliases_pyi, generate_env_stub, generate_tasks_stub


Logger = getattr(importlib.import_module("byper.__core__.utils.logger"), "Logger")


def cli():
    if len(sys.argv) > 1 and sys.argv[1].endswith(".py"):
        Environment.find_nested_venv()
        Commands.run_python_file(sys.argv[1])
        return

    parser = Commands.register_command()
    args = parser.parse_args()

    if args.command != "doctor":
        Environment.find_nested_venv()

    if args.command == "init":
        Commands.init(args.name)

    elif args.command == "task":
        Commands.run_task(args.name)

    elif args.command == "add":
        for pkg in args.packages:
            Commands.add_package(pkg, args.no_cache, args.upgrade)

    elif args.command == "tree":
        Commands.print_directory_tree()

    elif args.command == "run":
        Commands.run_script(args.script)

    elif args.version or args.command == "version":
        Logger.log(VERSION, level="info")

    elif args.help or args.command == "help":
        Commands.print_help()

    elif args.u_all or args.command == "update-all":
        Commands.upgrade_all()

    elif args.command == "remove":
        for pkg in args.packages:
            Commands.remove_package(pkg)

    elif args.command == "login":
        Commands.login()

    elif args.command == "logout":
        Commands.logout()

    elif args.command == "publish":
        Commands.publish()

    elif args.command == "refresh":
        generate_tasks_stub()
        generate_aliases_pyi()
        generate_env_stub()

    elif args.command == "doctor":
        Commands.doctor()

    elif args.command == "build":
        Commands.build()

    else:
        if len(sys.argv) > 1:
            Commands.print_help()

        else:
            Commands.install()

