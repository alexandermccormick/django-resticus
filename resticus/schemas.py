from django.conf import settings
from django.contrib.admindocs.views import simplify_regex, extract_views_from_urlpatterns
from django.urls import URLPattern, URLResolver

urlconf = __import__(settings.ROOT_URLCONF, {}, {}, [''])


class SchemaGenerator(object):
    def __init__(self, title=None, url=None, description=None, patterns=None, urlconf=None, version=None):
        if url and not url.endswith('/'):
            url += '/'

        self.patterns = patterns
        self.urlconf = urlconf
        self.title = title
        self.description = description
        self.version = version
        self.url = url

    def list_urls(self, urls, paths=None):
        if not paths:
            paths = []

        for p in urls:
            if not hasattr(p, 'url_patterns') and hasattr(p, 'pattern'):
                paths.append(simplify_regex(str(p.pattern)))

            elif hasattr(p, 'url_patterns'):
                self.list_urls(p.url_patterns, paths=paths)

        # for p in urls:
        #     if hasattr(p, 'url_patterns'):
        #         print('hasattr', *p.url_patterns, sep="\n")
        #         # if 'x' is a pattern list, check for patterns and do 'y' wih them until there are none
        #     else:
        #         paths.append(simplify_regex(str(p.pattern)))

        return paths
        # if acc is None:
        #     acc = []
        # if not lis:
        #     return
        # l = lis[0]
        # if isinstance(l, URLPattern) and acc and acc[0] == '^v4/':
        #     # print(l.callback.__name__, l.callback.__dict__)
        #     # print()
        #     # print('simplify', simplify_regex(str(l.pattern)),
        #     #       type(simplify_regex(str(l.pattern))))
        #     yield acc + [str(l.pattern)]
        # if isinstance(l, URLResolver):
        #     print('list_urls', self.list_urls)
        #     yield from self.list_urls(l.url_patterns, acc + [str(l.pattern)])
        # yield from self.list_urls(lis[1:], acc)

    def get_paths(self):
        paths = self.list_urls(urlconf.urlpatterns)
        # for p in self.list_urls(urlconf.urlpatterns):
        #     paths.append(p)
        print(*paths, sep="\n")
        return paths

    def get_info(self):
        # Title and version are required by openapi specification 3.x
        info = {
            'title': self.title or '',
            'version': self.version or ''
        }

        if self.description is not None:
            info['description'] = self.description

        return info

    def get_schema(self, request=None, public=False):
        """
        Generate a OpenAPI schema.
        """
        paths = self.get_paths()
        if not paths:
            return None

        schema = {
            'openapi': '3.0.2',
            'info': self.get_info(),
            'paths': paths,
        }

        return schema
