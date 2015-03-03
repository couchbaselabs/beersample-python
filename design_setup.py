#!/usr/bin/env python

from couchbase.bucket import Bucket
from couchbase.exceptions import HTTPError

beer_by_name = {
    'map' : '''
    function(doc, meta) {
        if (doc.type && doc.type == "beer") {
            emit(doc.name, null);
        }
    }
    '''
}

breweries_by_name = {
    'map' : '''
    function(doc, meta) {
        if (doc.type && doc.type == "brewery") {
            emit(doc.name, null);
        }
    }
    '''
}

breweries_design = {
    'views' : {
        'by_name' : breweries_by_name
    }
}

cb = Bucket('couchbase://localhost/beer-sample')
mgr = cb.bucket_manager()

# Get the beer view
beer_design = mgr.design_get("beer", use_devmode=False)
if 'by_name' not in beer_design.value['views']:
    beer_design.value['views']['by_name'] = beer_by_name
    mgr.design_create("beer",
                      beer_design.value, syncwait=5, use_devmode=False)

try:
    b_design = mgr.design_get("brewery", use_devmode=False)
    if 'by_name' not in b_design.value['views']:
        b_design.value['views']['by_name'] = breweries_by_name
        mgr.design_create("brewery",
                          beer_design.value, syncwait=5, use_devmode=False)

except HTTPError:
    mgr.design_create("brewery",
                      breweries_design, use_devmode=False, syncwait=5)
