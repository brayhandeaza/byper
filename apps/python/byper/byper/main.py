import sys

from byper.__core__.commands import Commands
from byper.__core__.constants import VERSION
from byper.__core__.helpers import generate_env_stub, generate_tasks_stub
from byper.__core__.tasks import Tasks
from byper.__core__.utils.logger import Logger


def cli():
    if len(sys.argv) > 1 and sys.argv[1].endswith(".py"):
        Commands.run_python_file(sys.argv[1])
        return

    parser = Commands.register_command()
    args = parser.parse_args()

    if args.command == "init":
        Commands.init(args.name, args.y)

    elif args.command == "task":
        Tasks.run_task(args.name)

    elif args.command == "cache":
        Commands.cache(args.action)

    elif args.command == "wheel":
        for pkg in args.packages:
            Commands.wheel(pkg)

    elif args.command == "list":
        flags = [
            "--outdated" if args.outdated else "",
            "freeze" if args.freeze else "",
            "cache" if args.cache else "",
        ]
        Commands.list(flags)

    elif args.command == "install":
        if args.packages:
            download = "--download" in (args.flags or [])
            flags = " ".join(args.flags or [])
            for pkg in args.packages:
                Commands.install_package(pkg, download, args.no_cache, args.offline, args.upgrade, flags)
        else:
            Commands.install(args.offline)

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
        flags = " ".join(args.flags or [])
        for pkg in args.packages:
            Commands.remove_package(pkg, flags)

    elif args.command == "login":
        Commands.login()

    elif args.command == "logout":
        Commands.logout()

    elif args.command == "publish":
        Commands.publish()

    elif args.command == "refresh":
        generate_tasks_stub()
        generate_env_stub()

    elif args.command == "doctor":
        if args.fix:
            Commands.doctor_fix(args.yes)
        else:
            Commands.doctor()

    elif args.command == "build":
        Commands.build()

    elif args.command == "path":
        Commands.path()

    elif args.command == "use":
        Commands.use(args.target)

    elif args.command == "python":
        if hasattr(args, "python_command") and args.python_command == "install":
            Commands.python_install(args.python_version)
        elif hasattr(args, "python_command") and args.python_command == "use":
            Commands.python_use(args.python_version)
        elif hasattr(args, "python_command") and args.python_command == "list":
            Commands.python_list()
        else:
            Commands.python_info()

    elif args.command == "reset":
        Commands.reset(args.yes)

    else:
        if len(sys.argv) > 1:
            Commands.print_help(exit_code=1)
        else:
            Commands.install(args.offline)
