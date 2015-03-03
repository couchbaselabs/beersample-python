import json

from flask import Flask, request, redirect, render_template

from couchbase.bucket import Bucket
from couchbase.exceptions import KeyExistsError, NotFoundError
from couchbase.views.params import Query
from couchbase.views.iterator import RowProcessor


class BreweryRow(object):
    def __init__(self, name, value, id, doc):
        self.name = name
        self.id = id
        self.doc = doc.value if doc and doc.success else None


class Beer(object):
    def __init__(self, name, _=None, id='', doc=None):
        self.id = id
        self.name = name
        self.brewery = None

        if doc and doc.success:
            doc = doc.value
        else:
            doc = None

        self.doc = doc
        if doc and 'brewery_id' in doc:
            self.brewery_id = doc['brewery_id']

    def __getattr__(self, name):
        if not self.doc:
            return ""
        return self.doc.get(name, "")


class BeerRowProcessor(RowProcessor):
    def __init__(self):
        super(BeerRowProcessor, self).__init__(rowclass=Beer)


class BreweryRowProcessor(RowProcessor):
    def __init__(self):
        super(BreweryRowProcessor, self).__init__(rowclass=BreweryRow)


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
    rows = db.query("beer", "by_name", limit=ENTRIES_PER_PAGE,
                    row_processor=BeerRowProcessor(), include_docs=True)
    return render_template('beer/index.html', results=rows)

@app.route('/breweries')
def breweries():
    rows = db.query("brewery", "by_name", limit=ENTRIES_PER_PAGE,
                    row_processor=BreweryRowProcessor(), include_docs=True)
    return render_template('brewery/index.html', results=rows)

@app.route('/<otype>/delete/<id>')
def delete_object(otype, id):
    try:
        db.remove(id)
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
        beer=Beer(id=beer_id, name=doc.value['name'], doc=doc))

@app.route('/breweries/show/<brewery>')
def show_brewery(brewery):
    doc = db.get(brewery, quiet=True)
    if not doc.success:
        return "No such brewery {0}".format(brewery), 404

    obj = BreweryRow(name=doc.value['name'], value=None, id=brewery, doc=doc)

    return render_template('/brewery/show.html', brewery=obj)

@app.route('/beers/edit/<beer>')
def edit_beer_display(beer):
    bdoc = db.get(beer, quiet=True)
    if not bdoc.success:
        return "No Such Beer", 404

    return render_template(
        'beer/edit.html',
        beer=Beer(id=beer, name=bdoc.value['name'], doc=bdoc),
        is_create=False)

@app.route('/beers/create')
def create_beer_display():
    return render_template('beer/edit.html', beer=Beer(name=''), is_create=True)


def normalize_beer_fields(form):
    doc = {}
    for k, v in form.items():
        name_base, fieldname = k.split('_', 1)
        if name_base != 'beer':
            continue

        doc[fieldname] = v

    if not 'name' in doc or not doc['name']:
        return None, ("Must have name", 400)

    if not 'brewery_id' in doc or not doc['brewery_id']:
        return None, ("Must have brewery ID", 400)

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

    res = db.query("beer", "by_name", row_processor=BeerRowProcessor(),
                   query=q, include_docs=True)

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

    rp = BreweryRowProcessor()
    res = db.query("brewery", "by_name",
                   row_processor=rp, query=q, include_docs=True)
    for brewery in res:
        ret.append({'id' : brewery.id,
                    'name' : brewery.name})

    return return_search_json(ret)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
