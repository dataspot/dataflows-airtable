import time
import dataflows as DF
from .utilities import get_session, rate_limiter
from .consts import AIRTABLE_ID_FIELD, HTTP_TIMEOUT

SCHEMA_CACHE = {}


def load_from_airtable(base, table, view=None, apikey='env://DATAFLOWS_AIRTABLE_TOKEN'):
    session = get_session(apikey)

    MESSAGE_COUNT = 1000
    TYPE_CONVERSION = dict(
        aiText='object',
        autoNumber='integer',
        barcode='object',
        button='object',
        checkbox='boolean',
        count='number',
        createdBy='object',
        createdTime='datetime',
        currency='number',
        date='date',
        dateTime='datetime',
        duration='number',
        email='string',
        externalSyncSource='string',     
        formula='any',
        lastModifiedBy='object',
        lastModifiedTime='datetime',
        lookup='array',
        multilineText='string',
        multipleAttachments='array',
        multipleCollaborators='array',
        multipleLookupValues='array',
        multipleRecordLinks='array',
        multipleSelects='array',
        number='number',
        percent='number',
        phoneNumber='string',
        rating='number',
        richText='string',
        rollup='any',
        singleCollaborator='object',
        singleLineText='string',
        singleSelect='string',
        url='string',
    )
    EXTRA_FIELDS = dict(
        createdTime=dict(format='%Y-%m-%dT%H:%M:%S.%fZ'),
        dateTime=dict(format='%Y-%m-%dT%H:%M:%S.%fZ'),
        lastModifiedTime=dict(format='%Y-%m-%dT%H:%M:%S.%fZ'),
    )


    def describe_table():
        try:
            if base in SCHEMA_CACHE:
                resp = SCHEMA_CACHE[base]
            else:
                url = f'https://api.airtable.com/v0/meta/bases/{base}/tables?include=visibleFieldIds'
                resp = rate_limiter.execute(lambda: session.get(url, timeout=HTTP_TIMEOUT).json())
                SCHEMA_CACHE[base] = resp
            tables = resp.get('tables', [])
            table_rec = next(filter(lambda t: t['name'] == table, tables), None)
            views = table_rec.get('views', [])
            view_rec = next(filter(lambda v: v['name'] == view, views), None)
            visibleFields = view_rec.get('visibleFieldIds') if view_rec else None
            select_field_names = None
            if table_rec:
                steps = [
                    [],
                    DF.update_resource(-1, name=table),
                    DF.add_field(AIRTABLE_ID_FIELD, 'string', resources=table),
                ]
                field_names = [AIRTABLE_ID_FIELD]
                for field in table_rec['fields']:
                    if visibleFields and field['id'] not in visibleFields:
                        continue
                    field_names.append(field['name'])
                    steps.append(
                        DF.add_field(field['name'], TYPE_CONVERSION[field['type']], resources=table, **EXTRA_FIELDS.get(field['type'], {})),
                    )
                if visibleFields:
                    select_field_names = DF.Flow(DF.select_fields(field_names, regex=False, resources=table))
                return DF.Flow(*steps), select_field_names
        except Exception as e:
            print('Error fetching schema:', e)
        print(f'Failed to find table {table} in base schema')

    def records():
        url = f'https://api.airtable.com/v0/{base}/{table}'
        params = dict(
            maxRecords=999999,
            view=view,
            pageSize=100
        )
        count = 0
        message_count = -MESSAGE_COUNT

        print(f'Loading records for {base}/{table}...')
        while True:
            retries = 3
            while True:
                try:
                    resp = rate_limiter.execute(lambda: session.get(url, params=params, timeout=HTTP_TIMEOUT).json())
                    break
                except Exception as e:
                    retries -= 1
                    if retries == 0:
                        raise(e)
                    time.sleep(5)
                    continue
            yield from map(
                lambda r: dict(**{AIRTABLE_ID_FIELD: r['id']}, **r['fields']),
                resp.get('records', [])
            )
            count += len(resp.get('records', []))

            if count >= message_count + MESSAGE_COUNT:
                message_count += MESSAGE_COUNT
                print(f'Loaded {message_count} records for {base}/{table}')
            if not resp.get('offset'):
                break
            params['offset'] = resp.get('offset')
        print(f'Loaded {count} records for {base}/{table}')

    def load():
        def func(rows):
            if rows.res.name == table:
                yield from records()
            else:
                yield from rows
        return func

    describe, select = describe_table()
    if describe:
        return DF.Flow(
            describe,
            load(),
            select,
        )
    else:
        return DF.Flow(
            records(),
            DF.update_resource(-1, name=table)
        )
