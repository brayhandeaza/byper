from byper.States.__module__.manager import Manager as Manager

manager = Manager.get_instance()


class __State__:
    @staticmethod
    def set(key, value):
        manager.set(key, value)

    @staticmethod
    def watch(key):
        return manager.watch(key)

    @staticmethod
    def get(key):
        return manager.get(key)
