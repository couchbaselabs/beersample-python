from collections import namedtuple
import json

from flask import Flask, request, redirect, abort, render_template

from couchbase.bucket import Bucket
from couchbase.exceptions import KeyExistsError, NotFoundError
from couchbase.views.iterator import RowProcessor
from couchbase.views.params import UNSPEC, Query


BreweryRow = namedtuple('BreweryRow', ['name', 'value', 'id', 'doc'])

class Beer(object):
    def __init__(self, id, name, doc=None):
        self.id = id
        self.name = name
        self.brewery = None
        self.doc = doc

    def __getattr__(self, name):
        if not self.doc:
            return ""
        return self.doc.get(name, "")


class BeerListRowProcessor(object):
    """
    This is the row processor for listing all beers (with their brewery IDs).
    """
    def handle_rows(self, rows, connection, include_docs):
        ret = []
        by_docids = {}

        for r in rows:
            b = Beer(r['id'], r['key'])
            ret.append(b)
            by_docids[b.id] = b

        keys_to_fetch = [x.id for x in ret]
        docs = connection.get_multi(keys_to_fetch, quiet=True)

        for beer_id, doc in docs.items():
            if not doc.success:
                ret.remove(beer)
                continue

            beer = by_docids[beer_id]
            beer.brewery_id = doc.value['brewery_id']

        return ret


CONNSTR = 'couchbase://localhost/beer-sample'
ENTRIES_PER_PAGE = 30


app = Flask(__name__, static_url_path='')
app.config.from_object(__name__)


def connect_db():
    return Bucket(CONNSTR)


db = connect_db()

@app.route('/')
@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/beers')
def beers():
    rp = BeerListRowProcessor()
    rows = db.query("beer", "by_name",
                    limit=ENTRIES_PER_PAGE,
                    row_processor=rp)

    return render_template('beer/index.html', results=rows)

@app.route('/breweries')
def breweries():
    rp = RowProcessor(rowclass=BreweryRow)
    rows = db.query("brewery", "by_name",
                    row_processor=rp,
                    limit=ENTRIES_PER_PAGE)

    return render_template('brewery/index.html', results=rows)


@app.route('/<otype>/delete/<id>')
def delete_object(otype, id):
    try:
        db.delete(id)
        return redirect('/welcome')

    except NotFoundError:
        return "No such {0} '{1}'".format(otype, id), 404

@app.route('/beers/show/<beer_id>')
def show_beer(beer_id):
    doc = db.get(beer_id, quiet=True)
    if not doc.success:
        return "No such beer {0}".format(beer_id), 404


    return render_template(
        'beer/show.html',
        beer=Beer(beer_id, doc.value['name'], doc.value))

@app.route('/breweries/show/<brewery>')
def show_brewery(brewery):
    doc = db.get(brewery, quiet=True)
    if not doc.success:
        return "No such brewery {0}".format(brewery), 404

    obj = BreweryRow(name=doc.value['name'], value=None, id=brewery, doc=doc.value)

    return render_template('/brewery/show.html', brewery=obj)

@app.route('/beers/edit/<beer>')
def edit_beer_display(beer):
    bdoc = db.get(beer, quiet=True)
    if not bdoc.success:
        return "No Such Beer", 404

    return render_template('beer/edit.html',
                           beer=Beer(beer, bdoc.value['name'], bdoc.value),
                           is_create=False)

@app.route('/beers/create')
def create_beer_display():
    return render_template('beer/edit.html', beer=Beer('', ''), is_create=True)


def normalize_beer_fields(form):
    doc = {}
    for k, v in form.items():
        name_base, fieldname = k.split('_', 1)
        if name_base != 'beer':
            continue

        doc[fieldname] = v

    if not 'name' in doc or not doc['name']:
        return (None, ("Must have name", 400))

    if not 'brewery_id' in doc or not doc['brewery_id']:
        return (None, ("Must have brewery ID", 400))

    if not db.get(doc['brewery_id'], quiet=True).success:
        return (None,
                ("Brewery ID {0} not found".format(doc['brewery_id']), 400))

    return doc, None


@app.route('/beers/create', methods=['POST'])
def create_beer_submit():
    doc, err = normalize_beer_fields(request.form)
    if not doc:
        return err

    id = '{0}-{1}'.format(doc['brewery_id'],
                          doc['name'].replace(' ', '_').lower())
    try:
        db.add(id, doc)
        return redirect('/beers/show/' + id)

    except KeyExistsError:
        return "Beer already exists!", 400

@app.route('/beers/edit/<beer>', methods=['POST'])
def edit_beer_submit(beer):
    doc, err = normalize_beer_fields(request.form)

    if not doc:
        return err

    db.set(beer, doc)
    return redirect('/beers/show/' + beer)


def return_search_json(ret):
    response = app.make_response(json.dumps(ret))
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/beers/search')
def beer_search():
    value = request.args.get('value')
    q = Query()
    q.mapkey_range = [value, value + Query.STRING_RANGE_END]
    q.limit = ENTRIES_PER_PAGE

    ret = []

    rp = BeerListRowProcessor()
    res = db.query("beer", "by_name",
                   row_processor=rp,
                   query=q,
                   include_docs=True)

    for beer in res:
        ret.append({'id' : beer.id,
                    'name' : beer.name,
                    'brewery' : beer.brewery_id})

    return return_search_json(ret)

@app.route('/breweries/search')
def brewery_search():
    value = request.args.get('value')
    q = Query()
    q.mapkey_range = [value, value + Query.STRING_RANGE_END]
    q.limit = ENTRIES_PER_PAGE

    ret = []

    rp = RowProcessor(rowclass=BreweryRow)
    res = db.query("brewery", "by_name",
                   row_processor=rp,
                   query=q,
                   include_docs=True)
    for brewery in res:
        ret.append({'id' : brewery.id,
                    'name' : brewery.name})

    return return_search_json(ret)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
