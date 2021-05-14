import dataflows as DF
from .utilities import get_session, rate_limiter


def load_from_airtable(base, table, view=None, apikey='env://DATAFLOWS_AIRTABLE_APIKEY'):
    session = get_session(apikey)

    def load():
        url = f'https://api.airtable.com/v0/{base}/{table}'
        params = dict(
            maxRecords=999999,
            view=view,
            pageSize=100
        )
        while True:
            resp = rate_limiter.execute(lambda: session.get(url, params=params).json())
            yield from map(
                lambda r: dict(__airtable_id=r['id'], **r['fields']),
                resp.get('records', [])
            )
            if not resp.get('offset'):
                break
            params['offset'] = resp.get('offset')

    return DF.Flow(
        load(),
        DF.update_resource(-1, name=table)
    )
