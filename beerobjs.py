class Brewery(object):
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self._data = None

class Beer(object):
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.brewery = None
        self.brewery_id = None

class BeerListRowProcessor(object):
    """
    This is the row processor for listing all beers (with their brewery IDs)
    """
    def __init__(self):
        self.iterator = None


    def handle_rows(self, rows, connection, include_docs):
        ret = []
        by_docids = {}

        for r in rows:
            b = Beer(r['id'], r['key'])
            ret.append(b)
            by_docids[b.id] = b

        keys_to_fetch = [ x.id for x in ret ]
        docs = connection.get_multi(keys_to_fetch)
        for beer_id, doc in docs.items():
            beer = by_docids[beer_id]
            beer.brewery_id = doc.value['brewery_id']

        self.iterator = iter(ret)

    def __iter__(self):
        if not self.iterator:
            return


        for beer in self.iterator:
            yield beer

        self.iterator = None
