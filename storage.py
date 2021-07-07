from simpy.core import Environment


class File:
    def __init__(self, path: str, tier: "Tier", size: int, ctime: float, last_mod: float, last_access: float):
        """
        :param path: full qualified path
        :param tier: host tier
        :param size: octets
        :param ctime: seconds
        :param last_mod: seconds
        :param last_access: seconds
        """
        self.path = path
        self.tier = tier
        self.size = size
        self.creation_time = ctime
        self.last_modification = last_mod
        self.last_access = last_access


class Tier:
    def __init__(self, storage: "StorageManager", name: str, size: int, latency: float, throughput: float):
        """
        :param size: octets
        :param latency: seconds
        :param throughput: Go/seconds
        """
        self.name = name
        self.size = size
        self.latency = latency
        self.throughput = throughput
        self.content = dict()  # key: path, value: File
        self.manager = storage
        storage.tiers += [self]

    def has_file(self, path):
        return path in self.content.keys()

    def rename_file(self):
        """
        :return: time in seconds until operation completion
        """
        return 0

    def create_file(self, timestamp, path):
        """
        :return: time in seconds until operation completion
        """
        file = File(path, self.manager.get_default_tier(), size=0, ctime=timestamp, last_mod=timestamp, last_access=timestamp)
        self.content[path]=file
        self.manager.fire_event(self.manager.on_file_created_event, (file, self)) # file, tier
        return 0

    def open_file(self):
        """
        :return: time in seconds until operation completion
        """
        return 0

    def read_file(self, timestamp, path):
        """
        :return: time in seconds until operation completion
        """
        self.manager.fire_event(self.manager.on_file_access_event, (self.content[path], self, False)) # file, tier, is_write
        return 0

    def write_file(self, timestamp, path):
        """
        :return: time in seconds until operation completion
        """
        self.manager.fire_event(self.manager.on_file_access_event, (self.content[path], self, True)) # file, tier, is_write
        self.manager.fire_event(self.manager.on_disk_occupation_increase_event, (self,)) # tier TODO: reduce call freq
        return 0

    def close_file(self):
        """
        :return: time in seconds until operation completion
        """
        return 0

    def delete_file(self):
        """
        :return: time in seconds until operation completion
        """
        return 0


class StorageManager:
    def __init__(self, env: Environment, default_tier_index: int = 0):
        self._env = env
        self.tiers = []
        self.default_tier_index = default_tier_index
        self.on_file_created_event = [env.event()]
        self.on_file_access_event = [env.event()]
        self.on_disk_occupation_increase_event = [env.event()]

    def fire_event(self, event, value):
        e = event[0]
        event[0] = self._env.event()
        e.succeed(value)

    def get_default_tier(self):
        return self.tiers[self.default_tier_index]

    def get_file(self, path):
        """
        :param path: Fully qualified path
        :return: The first file with the corresponding path found
        """
        for tier in self.tiers:
            if tier.has_file(path):
                return tier.content[path]
        return None

    @staticmethod
    def migrate(file: File, target_tier: Tier):
        """
        :return: The time needed until completion of the migration
        """

        if file.tier is target_tier:
            return # Migration has already been done. Nothing to do?

        # TODO: find migration delay from a paper
        delay = 0.
        delay += target_tier.create_file()
        delay += max(file.tier.read_file(), target_tier.write_file())
        delay += file.tier.delete_file()

        return delay