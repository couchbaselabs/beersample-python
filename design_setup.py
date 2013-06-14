#!/usr/bin/env python

from couchbase import Couchbase
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


cb = Couchbase.connect(bucket='beer-sample')

# Get the beer view
beer_design = cb.design_get("beer", use_devmode=False)
if not 'by_name' in beer_design.value['views']:
    beer_design.value['views']['by_name'] = beer_by_name
    cb.design_create("beer",
                     beer_design.value, syncwait=5, use_devmode=False)

try:
    b_design = cb.design_get("brewery", use_devmode=False)
    if not 'by_name' in b_design.value['views']:
        b_design.value['views']['by_name'] = breweries_by_name
        cb.design_create("brewery",
                         beer_design.value, syncwait=5, use_devmode=False)

except HTTPError:
    cb.design_create("brewery",
                     breweries_design, use_devmode=False, syncwait=5)
