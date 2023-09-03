import time
import dataflows as DF
from .utilities import get_session, rate_limiter
from .consts import AIRTABLE_ID_FIELD

SCHEMA_CACHE = {}


def load_from_airtable(base, table, view=None, apikey='env://DATAFLOWS_AIRTABLE_TOKEN'):
    session = get_session(apikey)

    TYPE_CONVERSION = dict(
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
                resp = rate_limiter.execute(lambda: session.get(url, timeout=10).json())
                SCHEMA_CACHE[base] = resp
            tables = resp.get('tables', [])
            table_rec = next(filter(lambda t: t['name'] == table, tables), None)
            views = table_rec.get('views', [])
            view_rec = next(filter(lambda v: v['name'] == view, views), None)
            visibleFields = view_rec.get('visibleFieldIds') if view_rec else None
            if table_rec:
                steps = [
                    [],
                    DF.update_resource(-1, name=table),
                    DF.add_field(AIRTABLE_ID_FIELD, 'string', resources=table),
                ]
                for field in table_rec['fields']:
                    if visibleFields and field['id'] not in visibleFields:
                        continue
                    steps.append(
                        DF.add_field(field['name'], TYPE_CONVERSION[field['type']], resources=table, **EXTRA_FIELDS.get(field['type'], {})),
                    )
                return DF.Flow(*steps)
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
        print(f'Loading records for {base}/{table}...')
        while True:
            retries = 3
            while True:
                try:
                    resp = rate_limiter.execute(lambda: session.get(url, params=params, timeout=10).json())
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
            print(f'Loaded {count} records for {base}/{table}')
            if not resp.get('offset'):
                break
            params['offset'] = resp.get('offset')

    def load():
        def func(rows):
            if rows.res.name == table:
                yield from records()
            else:
                yield from rows
        return func

    describe = describe_table()
    if describe:
        return DF.Flow(
            describe,
            load(),
        )
    else:
        return DF.Flow(
            records(),
            DF.update_resource(-1, name=table)
        )
