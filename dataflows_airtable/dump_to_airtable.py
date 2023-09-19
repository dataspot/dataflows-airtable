import logging

from requests.sessions import Session
from decimal import Decimal

from .utilities import get_session, rate_limiter
from .consts import AIRTABLE_ID_FIELD, HTTP_TIMEOUT


class AirtableUploader():
    def __init__(self, session: Session, base, table, typecast=False):
        self.session = session
        self.base = base
        self.table = table
        self.inserts = []
        self.updates = []
        self.typecast = typecast

    def insert(self, row):
        self.inserts.append(row)
        if len(self.inserts) == 10:
            self.batch_insert()

    def update(self, rid, row):
        self.updates.append((rid, row))
        if len(self.updates) == 10:
            self.batch_update()

    def finalize(self):
        if len(self.inserts) > 0:
            self.batch_insert()
        if len(self.updates) > 0:
            self.batch_update()

    def batch_insert(self):
        payload = dict(records=list(dict(fields=r) for r in self.inserts), typecast=self.typecast)
        self.inserts = []
        url = f'https://api.airtable.com/v0/{self.base}/{self.table}'
        rate_limiter.execute(lambda: self.do_request('post', url, payload))

    def batch_update(self):
        payload = dict(records=list(dict(id=rid, fields=fields) for rid, fields in self.updates), typecast=self.typecast)
        self.updates = []
        url = f'https://api.airtable.com/v0/{self.base}/{self.table}'
        rate_limiter.execute(lambda: self.do_request('patch', url, payload))

    def do_request(self, method, url, payload):
        resp = self.session.__getattribute__(method)(url, json=payload, timeout=HTTP_TIMEOUT)
        try:
            resp = resp.json()
            error = resp.get('error')
            if error is not None:
                logging.warning(f'{error} on {method} {payload}')
        except Exception as e:
            logging.warning(f'{e} on {method} {payload}')

def dump_to_airtable(tables, apikey='env://DATAFLOWS_AIRTABLE_TOKEN'):
    session = get_session(apikey)

    def upload(rows, uploaders):
        for row in rows:
            row = dict((k, float(v) if isinstance(v, Decimal) else v) for k, v in row.items())
            for uploader in uploaders:
                rid = row.pop(AIRTABLE_ID_FIELD, None)
                if rid is not None:
                    fields = dict((k, v) for k, v in row.items() if k != AIRTABLE_ID_FIELD)
                    uploader.update(rid, fields)
                else:
                    uploader.insert(row)
            yield row
        for uploader in uploaders:
            uploader.finalize()

    def func(package):
        yield package.pkg
        for res in package:
            uploaders = []
            for (base, table), options in tables.items():
                if options.get('resource-name') == res.res.name:
                    uploaders.append(AirtableUploader(session, base, table, typecast=bool(options.get('typecast'))))
            if len(uploaders) == 0:
                yield res
            else:
                yield upload(res, uploaders)
    return func
