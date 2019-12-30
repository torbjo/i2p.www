from math import ceil
from werkzeug import import_string, cached_property

########################
# General helper methods

def get_for_page(items, page, per_page):
    from_item = (page-1)*per_page
    to_item = page*per_page
    return items[from_item:to_item]

def get_metadata_from_meta(meta, supported_metatags, list_metatags):
    metaLines = meta.split('\n')
    ret = {}
    for metaTag in supported_metatags:
        metaLine = [s for s in metaLines if 'name="%s"' % metaTag in s]
        ret[metaTag] = metaLine[0].split('content="')[1].split('"')[0] if len(metaLine) > 0 else supported_metatags[metaTag]
        if metaTag in list_metatags and ret[metaTag]:
            ret[metaTag] = [s.strip() for s in ret[metaTag].split(',')]
    return ret


########################
# General helper classes

class LazyView(object):
    def __init__(self, import_name):
        self.__module__, self.__name__ = import_name.rsplit('.', 1)
        self.import_name = import_name

    @cached_property
    def view(self):
        return import_string(self.import_name)

    def __call__(self, *args, **kwargs):
        return self.view(*args, **kwargs)

class Pagination(object):
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and \
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num
