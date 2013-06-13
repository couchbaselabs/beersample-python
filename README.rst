=================================
Couchbase Beer Python Application
=================================

This is a sample web application written with the Python Couchbase Library.
Currently it relies on the latest patches from gerrit (Specifically,
http://review.couchbase.org/#/c/26856/ and
http://review.couchbase.org/#/c/26934/).

To test this application, install `Flask` (``pip install flask``).

The actual Python routing code is found in the ``beer.py`` file.


You will need to have the ``beer-sample`` bucket installed.
Additionally, you will need two additional views:

``beer/by_name``::

    function(doc, meta) {
        if (doc.type && doc.type == "beer") {
            emit(doc.name, null);
        }
    }


Here you will need to create a new design document, called
``brewery``.

``brewery/by_name``::

    function(doc, meta) {
        if (doc.type && doc.type == "brewery") {
            emit(doc.name, null);
        }
    }



To run the webapp, simply do::

    python beer.py

And connect to ``localhost:5000``
