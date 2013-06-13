from flask import Flask, request, session, g, redirect, url_for, \
        abort, render_template, flash

from couchbase import Couchbase

from beerobjs import BeerListRowProcessor


DATABASE = 'beer-sample'
HOST = 'localhost'
ENTRIES_PER_PAGE = 30

app = Flask(__name__, static_url_path='')
app.config.from_object(__name__)

def connect_db():
    return Couchbase.connect(
            bucket=app.config['DATABASE'],
            host=app.config['HOST'])


db = connect_db()

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/beers')
def beers():
    rp = BeerListRowProcessor()
    rows = db.query("beer", "by_name",
                    limit=ENTRIES_PER_PAGE,
                    row_processor=rp)

    return render_template('beerlist.html',
                           results=rows)

if __name__ == "__main__":
    app.run(debug=True)
