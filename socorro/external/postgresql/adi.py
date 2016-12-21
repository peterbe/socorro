# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging

from socorro.lib import MissingArgumentError, external_common
from socorro.external.postgresql.base import PostgreSQLBase


logger = logging.getLogger("webapi")


class ADI(PostgreSQLBase):

    def get(self, **kwargs):
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(1)
        tomorrow = yesterday + datetime.timedelta(2)
        yesterday = yesterday.date()
        tomorrow = tomorrow.date()
        filters = [
            ('start_date', yesterday, 'date'),
            ('end_date', tomorrow, 'date'),
            ('product', '', 'str'),
            ('versions', [], 'list'),
            ('platforms', [], 'list'),
            # In (old) postgres it's called "build_type" but the (new)
            # name we want to "promote" is "channel"
            ('channels', [], 'list'),
            ('by_build', False, bool),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        required = (
            'start_date',
            'end_date',
            'product',
            # 'versions',
            # 'platforms',
        )
        missing = []
        for each in required:
            if not params.get(each):
                missing.append(each)
        if missing:
            raise MissingArgumentError(', '.join(missing))

        if params['versions']:
            versions = []
            for i, version in enumerate(params['versions'], start=1):
                key = 'version{}'.format(i)
                # We make a very special exception for versions that end with
                # the letter 'b'. It means it's a beta version and when some
                # queries on that version they actually mean all
                # the "sub-versions". For example version="19.0b" actually
                # means "all versions starting with '19.0b'".
                # This is succinct with what we do in SuperSearch.
                if version.endswith('b'):
                    # exception!
                    versions.append('pv.version_string LIKE %({})s'.format(
                        key
                    ))
                    version += '%'
                else:
                    # the norm
                    versions.append('pv.version_string = %({})s'.format(key))
                params[key] = version
            sql_versions = 'AND ({})'.format(
                ' OR '.join(versions)
            )
        else:
            sql_versions = ''

        if params['platforms']:
            sql_platforms = 'AND os_name IN %(platforms)s'
            params['platforms'] = tuple(params['platforms'])
        else:
            sql_platforms = ''

        if params['channels']:
            build_types = []
            sql_build_types = ' AND pv.build_type IN %(build_types)s'
            params['build_types'] = tuple(params['channels'])
        else:
            sql_build_types = ''

        if params['by_build']:
            sql_table = 'build_adu'
            sql_selects = [
                'SUM(adu_count)::BIGINT AS adi_count',
                'build_adu.build_date',
                'pv.build_type',
                'pv.version_string AS version',
            ]
            sql_group_by = [
                'build_adu.build_date',
                'build_type',
                'version_string',
            ]
            sql_date_range = (
                'AND build_adu.build_date BETWEEN %(start_date)s AND %(end_date)s'
            )
        else:
            sql_table = 'product_adu'
            sql_selects = [
                'SUM(adu_count)::BIGINT AS adi_count',
                'adu_date AS date',
                'pv.build_type',
                'pv.version_string AS version',
            ]
            sql_group_by = [
                'adu_date',
                'build_type',
                'version_string',
            ]
            sql_date_range = (
                'AND adu_date BETWEEN %(start_date)s AND %(end_date)s'
            )

        sql = """
            SELECT
                {selects}
            FROM
                {table}
            LEFT OUTER JOIN product_versions pv USING (product_version_id)
            WHERE
                pv.product_name = %(product)s
                {versions}
                {platforms}
                {build_types}
                {date_range}
            GROUP BY
                {group_by}

        """.format(
            selects=',\n'.join(sql_selects),
            table=sql_table,
            versions=sql_versions,
            platforms=sql_platforms,
            build_types=sql_build_types,
            date_range=sql_date_range,
            group_by=',\n'.join(sql_group_by),
        )

        # print "\nSQL"
        # print sql
        # print "\nPARAMS"
        # from pprint import pprint
        # pprint(params)
        #print "\n", '-'*100


        assert isinstance(params, dict)
        results = self.query(sql, params)

        rows = results.zipped()
        return {'hits': rows, 'total': len(rows)}
