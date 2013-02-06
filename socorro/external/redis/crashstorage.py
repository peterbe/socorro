# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import redis

from configman import Namespace

from socorro.external.fs.crashstorage import (
    FSRadixTreeStorage
)


class ConfigurationError(Exception):
    pass


class RedisCrashStorage(FSRadixTreeStorage):

    required_config = Namespace()
    required_config.add_option(
        'publish_crashes',
        doc='whether we should publish the message',
        default=False
    )
    required_config.add_option(
        'channel_name',
        doc='Name used for the pub/sub channel',
        default='crashes'
    )
    required_config.add_option(
        'key_name',
        doc='Internally named list that crash IDs are stored',
        default='crash_ids'
    )
    required_config.namespace('redis')
    required_config.redis.add_option(
        'host',
        doc='Hostname to your Redis server or your Redis connection pool',
        default='localhost'
    )
    required_config.redis.add_option(
        'port',
        doc='Port number to your Redis server or your Redis connection pool',
        default=6379
    )
    required_config.redis.add_option(
        'db',
        doc='Redis DB number to use',
        default=0
    )
    required_config.redis.add_option(
        'unix_socket_path',
        doc='Set if you want to use a UnixDomainSocketConnection connection '
            'to Redis.',
        default=None
    )

    def connect(self):
        ns = self.config.redis
        if ns.host and ns.host:
            return redis.Redis(host=ns.host, port=ns.port, db=ns.db)
        elif ns.unix_socket_path:
            return redis.Redis(unix_socket_path=ns.unix_socket_path)
        raise ConfigurationError("No redis host:port or unix_socket_path")

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        connection = self.connect()
        super(RedisCrashStorage, self).save_raw_crash(
            raw_crash, dumps, crash_id
        )

        connection.rpush(
            self.config.key_name,
            crash_id
        )

        # tell the listeners there's something to do
        if self.config.publish_crashes:
            connection.publish(
                self.config.channel_name,
                crash_id
            )

    def new_crashes(self):
        connection = self.connect()
        crashes = connection.lrange(self.config.redis.key_name, 0, -1)
        for crash_id in crashes:
            yield crash_id
