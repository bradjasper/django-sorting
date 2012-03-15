from django import template
from django.http import Http404
from django.conf import settings
from django.core.exceptions import FieldError

register = template.Library()

DEFAULT_SORT_UP = getattr(settings, 'DEFAULT_SORT_UP' , '&uarr;')
DEFAULT_SORT_DOWN = getattr(settings, 'DEFAULT_SORT_DOWN' , '&darr;')
INVALID_FIELD_RAISES_404 = getattr(settings, 
        'SORTING_INVALID_FIELD_RAISES_404' , False)

sort_directions = {
    'asc': {'icon':DEFAULT_SORT_UP, 'inverse': 'desc'}, 
    'desc': {'icon':DEFAULT_SORT_DOWN, 'inverse': 'asc'}, 
    '': {'icon':DEFAULT_SORT_DOWN, 'inverse': 'asc'}, 
}

def anchor(parser, token):
    """
    Parses a tag that's supposed to be in this format: {% anchor field title sortdir %}
    """
    bits = [b.strip('"\'') for b in token.split_contents()]

    if len(bits) < 2:
        raise TemplateSyntaxError, "anchor tag takes at least 1 argument"

    field = bits[1].strip()
    title = field.capitalize()
    sortdir = ''

    if len(bits) >= 3:
        title = bits[2]

    if len(bits) == 4:
        sortdir = bits[3]

    return SortAnchorNode(field, title, sortdir)

class SortAnchorNode(template.Node):
    """
    Renders an <a> HTML tag with a link which href attribute 
    includes the field on which we sort and the direction.
    and adds an up or down arrow if the field is the one 
    currently being sorted on.

    Eg.
        {% anchor name Name asc %} generates
        <a href="/the/current/path/?sort=name&dir=asc" title="Name">Name</a>

    """
    def __init__(self, field, title, sortdir):
        self.field = field
        self.title = title
        self.sortdir = sortdir

    def render(self, context):
        request = context['request']
        getvars = request.GET.copy()
        if 'sort' in getvars:
            sortby = getvars['sort']
            del getvars['sort']
        else:
            sortby = ''

        if 'dir' in getvars:
            sortdir = getvars['dir']
            del getvars['dir']
        else:
            sortdir = self.sortdir

        if sortby == self.field:
            getvars['dir'] = sort_directions[sortdir]['inverse']
            icon = sort_directions[sortdir]['icon']
        else:
            # If we're not on the current field, use the default sortdir
            # rather than the order
            if self.sortdir:
                getvars['dir'] = self.sortdir
            icon = ''

        if len(getvars.keys()) > 0:
            urlappend = "&%s" % getvars.urlencode()
        else:
            urlappend = ''

        if icon:
            title = "%s %s" % (self.title, icon)
        else:
            title = self.title

        url = '%s?sort=%s%s' % (request.path, self.field, urlappend)
        return '<a href="%s" title="%s">%s</a>' % (url, self.title, title)


def autosort(parser, token):
    bits = [b.strip('"\'') for b in token.split_contents()]
    if len(bits) != 2:
        raise TemplateSyntaxError, "autosort tag takes exactly one argument"
    return SortedDataNode(bits[1])

class SortedDataNode(template.Node):
    """
    Automatically sort a queryset with {% autosort queryset %}
    """
    def __init__(self, queryset_var, context_var=None):
        self.queryset_var = template.Variable(queryset_var)
        self.context_var = context_var

    def render(self, context):
        key = self.queryset_var.var
        value = self.queryset_var.resolve(context)
        order_by = context['request'].field
        if len(order_by) > 1:
            try:
                try:
                    val = list(value.order_by(order_by))
                    context[key] = val
                except:
                    ## Support for sorting on properties

                    # Split off reverse sort
                    reverse = False
                    if order_by.startswith("-"):
                        order_by = order_by[1:]
                        reverse = True

                    context[key] = sorted(value, key=lambda v: getattr(v, order_by), reverse=reverse)

            except template.TemplateSyntaxError:
                if INVALID_FIELD_RAISES_404:
                    raise Http404('Invalid field sorting. If DEBUG were set to ' +
                    'False, an HTTP 404 page would have been shown instead.')
                context[key] = value
        else:
            context[key] = value

        return ''

anchor = register.tag(anchor)
autosort = register.tag(autosort)

