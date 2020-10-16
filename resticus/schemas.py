import re

from django.conf import settings
from django.contrib.admindocs.views import simplify_regex
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.urls import URLPattern, URLResolver

from . import mixins
from .serializers import Serializer


class SchemaGenerator(object):
    def __init__(
        self, title=None, description=None, prefix=None, urlconf=None, version=None
    ):

        if not urlconf:
            self.urlconf = __import__(settings.ROOT_URLCONF, {}, {}, [""])
        else:
            self.urlconf = urlconf

        self.prefix = prefix
        self.title = title
        self.description = description
        self.version = version
        self.fields_dict = {
            # ArrayField items should technically be oneOf multiple types but Swagger UI does not support oneOf
            "ArrayField": {"type": "array", "items": {"type": "string"}},
            "AutoField": {"type": "integer"},
            "BigAutoField": {"type": "integer"},
            "BigIntegerField": {"type": "integer"},
            "BigIntegerRangeField": {"type": "array", "items": {"type": "integer"}},
            "BinaryField": {"type": "bytes"},
            "BooleanField": {"type": "boolean"},
            "CharField": {"type": "string"},
            "CICharField": {"type": "string"},
            "CIEmailField": {"type": "string"},
            "CITextField": {"type": "string"},
            "DateField": {"type": "string"},
            "DateRangeField": {"type": "array", "items": {"type": "string"}},
            "DateTimeField": {"type": "string"},
            "DateTimeRangeField": {"type": "array", "items": {"type": "string"}},
            "DecimalField": {"type": "number"},
            "DecimalRangeField": {"type": "array", "items": {"type": "number"}},
            "DurationField": {"type": "integer"},
            "EmailField": {"type": "string"},
            "FileField": {"type": "string"},
            "FilePathField": {"type": "string"},
            "FloatField": {"type": "number"},
            "FloatRangeField": {"type": "array", "items": {"type": "number"}},
            # ForeignKey should be a string if it's forward and an array if reverse, how to tell which?
            "ForeignKey": {"type": "string"},
            "ImageField": {"type": "string"},
            "IntegerField": {"type": "integer"},
            "IntegerRangeField": {"type": "array", "items": {"type": "integer"}},
            "GenericIPAddressField": {"type": "string"},
            "GeometryCollectionField": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "number"}},
            },
            "HStoreField": {"type": "object", "properties": {"type": "string"}},
            "JSONField": {"type": "object", "properties": {"type": "string"}},
            "LineStringField": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "number"}},
            },
            "LinearRingField": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "number"}},
            },
            "ManyToManyField": {"type": "array", "items": {"type": "string"}},
            "MultiLineStringField": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "number"}},
                },
            },
            "MultiPointField": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "coordinates": {"type": "array", "items": {"type": "number"}},
                    },
                },
            },
            "MultiPolygonField": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "number"}},
                },
            },
            "NullBooleanField": {"type": "boolean"},
            "OneToOneField": {"type": "string"},
            "PointField": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "coordinates": {"type": "array", "items": {"type": "number"}},
                },
            },
            "PolygonField": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "number"}},
            },
            "PositiveIntegerField": {"type": "integer"},
            "PositiveSmallIntegerField": {"type": "integer"},
            "RasterField": {"type": "string"},
            # RasterField should technically be oneOf: string/object but Swagger UI does not support oneOf
            "SlugField": {"type": "string"},
            "SmallIntegerField": {"type": "integer"},
            "TextField": {"type": "string"},
            "TimeField": {"type": "string"},
            "TreeForeignKey": {"type": "string"},
            "URLField": {"type": "string"},
            "UUIDField": {"type": "string"},
        }

    def get_model_props(self, view_class):
        model = {}

        if isinstance(view_class.fields, tuple):
            for field in view_class.fields:
                if isinstance(field, str):
                    try:
                        name = view_class.model._meta.get_field(field).name
                        field_type = view_class.model._meta.get_field(
                            field
                        ).get_internal_type()
                        if field_type in self.fields_dict:
                            model.update({name: self.fields_dict[field_type]})
                    except FieldDoesNotExist:
                        continue
                elif isinstance(field, tuple):
                    result = {}
                    if isinstance(field[0], str):
                        try:
                            name = view_class.model._meta.get_field(field[0]).name
                            try:
                                related_obj = view_class.model._meta.get_field(
                                    name
                                ).related_model
                                if isinstance(field[1], dict):
                                    fields = field[1].get("fields")
                                elif issubclass(field[1], Serializer):
                                    fields = field[1].fields
                                else:
                                    fields = None
                                if fields:
                                    properties = {}

                                    for f in fields:
                                        if isinstance(f, tuple) and isinstance(
                                            f[1], dict
                                        ):
                                            field_list = f[1].get("fields", [])
                                        else:
                                            field_list = [f]

                                        for _f in field_list:
                                            try:
                                                related_name = related_obj._meta.get_field(
                                                    _f
                                                ).name
                                                related_type = related_obj._meta.get_field(
                                                    _f
                                                ).get_internal_type()
                                                if related_type in self.fields_dict:
                                                    properties.update(
                                                        {
                                                            related_name: self.fields_dict[
                                                                related_type
                                                            ]
                                                        }
                                                    )
                                            except FieldDoesNotExist:
                                                continue
                                result = {
                                    name: {"type": "object", "properties": properties}
                                }
                                model.update(result)
                            except ObjectDoesNotExist:
                                continue
                        except FieldDoesNotExist:
                            continue
        return model

    def get_form_params(self, callback, parameters):
        params_with_form = list(parameters)

        if callback.view_class.form_class:
            description = ""
            if callback.view_class.model:
                description = callback.view_class.model.__name__ + " object."
            form_param = {
                "name": "body",
                "in": "body",
                "description": description,
                "required": True,
                "schema": {"type": "object", "properties": {}},
            }

            if hasattr(callback.view_class.form_class, "_meta"):
                for field in callback.view_class.form_class._meta.fields:
                    field_type = callback.view_class.form_class._meta.model._meta.get_field(
                        field
                    ).get_internal_type()
                    if field_type in self.fields_dict:
                        form_param["schema"]["properties"].update(
                            {field: self.fields_dict[field_type]}
                        )

            params_with_form.append(form_param)
        return params_with_form

    def list_routes(self, callback, parameters):
        """
        Add http methods and responses to routes
        """
        functions = ["get", "post", "patch", "delete"]
        routes = {}
        summary = ""

        if hasattr(callback, "view_class"):
            for f in functions:
                if hasattr(callback.view_class, f):
                    routes.update(
                        {
                            f: {
                                "summary": "",
                                "parameters": parameters,
                                "responses": {"200": {"description": "success"}},
                            }
                        }
                    )

                    if hasattr(callback.view_class, "model"):
                        attr = getattr(callback.view_class, f)
                        try:
                            tag = name = callback.view_class.model.__name__
                            summary = attr.__doc__.replace("object", name)
                        except AttributeError:
                            name = ""
                            tag = "default"
                            summary = attr.__doc__

                        if f == "delete":
                            routes.update(
                                {
                                    f: {
                                        "tags": [tag],
                                        "summary": summary,
                                        "responses": {
                                            "204": {"description": "Deleted"}
                                        },
                                        "parameters": parameters,
                                    }
                                }
                            )
                        if (
                            f == "post"
                            and mixins.ListModelMixin in callback.view_class.__mro__
                        ):
                            routes.update(
                                {
                                    f: {
                                        "tags": [tag],
                                        "summary": summary,
                                        "parameters": parameters,
                                        "responses": {
                                            "201": {
                                                "description": "Created "
                                                + name
                                                + " object",
                                                "content": {
                                                    "application/json": {
                                                        "schema": {
                                                            "type": "object",
                                                            "properties": {
                                                                "data": {
                                                                    "type": "object",
                                                                    "properties": self.get_model_props(
                                                                        callback.view_class
                                                                    ),
                                                                }
                                                            },
                                                        }
                                                    }
                                                },
                                            }
                                        },
                                    }
                                }
                            )

                        if (
                            f == "patch"
                            and mixins.DetailModelMixin in callback.view_class.__mro__
                        ):
                            routes.update(
                                {
                                    f: {
                                        "tags": [tag],
                                        "summary": summary,
                                        "parameters": self.get_form_params(
                                            callback, parameters
                                        ),
                                        "responses": {
                                            "200": {
                                                "description": "Updated "
                                                + name
                                                + " object",
                                                "content": {
                                                    "application/json": {
                                                        "schema": {
                                                            "type": "object",
                                                            "properties": {
                                                                "data": {
                                                                    "type": "object",
                                                                    "properties": self.get_model_props(
                                                                        callback.view_class
                                                                    ),
                                                                }
                                                            },
                                                        }
                                                    }
                                                },
                                            }
                                        },
                                    }
                                }
                            )

                        if (
                            f == "get"
                            and mixins.DetailModelMixin in callback.view_class.__mro__
                        ):
                            routes.update(
                                {
                                    f: {
                                        "tags": [tag],
                                        "summary": summary,
                                        "parameters": parameters,
                                        "responses": {
                                            "200": {
                                                "description": "A single "
                                                + name
                                                + " object",
                                                "content": {
                                                    "application/json": {
                                                        "schema": {
                                                            "type": "object",
                                                            "properties": {
                                                                "data": {
                                                                    "type": "object",
                                                                    "properties": self.get_model_props(
                                                                        callback.view_class
                                                                    ),
                                                                }
                                                            },
                                                        }
                                                    }
                                                },
                                            }
                                        },
                                    }
                                }
                            )

                        if (
                            f == "get"
                            and mixins.ListModelMixin in callback.view_class.__mro__
                        ):
                            routes.update(
                                {
                                    f: {
                                        "tags": [tag],
                                        "summary": summary,
                                        "parameters": parameters,
                                        "responses": {
                                            "200": {
                                                "description": "A list of "
                                                + name
                                                + " objects",
                                                "content": {
                                                    "application/json": {
                                                        "schema": {
                                                            "type": "object",
                                                            "properties": {
                                                                "data": {
                                                                    "type": "object",
                                                                    "properties": self.get_model_props(
                                                                        callback.view_class
                                                                    ),
                                                                },
                                                                "page": {
                                                                    "type": "integer",
                                                                },
                                                                "count": {
                                                                    "type": "integer",
                                                                },
                                                                "pages": {
                                                                    "type": "integer",
                                                                },
                                                                "has_next_page": {
                                                                    "type": "boolean",
                                                                },
                                                                "has_previous_page": {
                                                                    "type": "boolean",
                                                                },
                                                            },
                                                        }
                                                    }
                                                },
                                            }
                                        },
                                    }
                                }
                            )
        return routes

    def parse_patterns(self, patterns, paths, prefix):
        """
        Parse through url resolvers until all url patterns have been added
        """
        for p in patterns:
            if isinstance(p, URLPattern):
                urlstring = prefix + simplify_regex(str(p.pattern))
                urlstring = re.sub(r"//", r"/", urlstring)
                parameters = []
                params_list = re.findall("<(.*?)>", urlstring, re.DOTALL)
                for param in params_list:
                    parameters.append(
                        {
                            "name": param,
                            "in": "path",
                            "description": param,
                            "required": True,
                            "type": "string",
                            "format": "string",
                        }
                    )

                path_info = self.list_routes(p.callback, parameters)
                path_info.update({"description": "test"})

                a_list = ("description", "get", "post", "patch", "put", "delete")

                pi_sorted = dict(
                    [(key, path_info[key]) for key in a_list if key in path_info]
                )

                path = {urlstring: pi_sorted}
                paths.update(path)

            elif isinstance(p, URLResolver):
                self.list_urls(p, paths=paths, prefix=prefix)

            elif isinstance(p, list):
                self.parse_patterns(p, paths=paths, prefix=prefix)

    def list_urls(self, urls, paths=None, prefix=None, count=0):
        """
        Get a list of all urls from the given urlconf and all children
        """
        if paths is None:
            paths = {}

        if prefix is not None and hasattr(urls, "pattern"):
            prefix = prefix + simplify_regex(str(urls.pattern))
        elif not prefix:
            prefix = ""

        if hasattr(urls, "urlpatterns"):
            patterns = urls.urlpatterns
            self.parse_patterns(patterns, paths, prefix)

        elif hasattr(urls, "url_patterns"):
            patterns = urls.url_patterns
            self.parse_patterns(patterns, paths, prefix)

        return paths

    def get_paths(self):
        paths = self.list_urls(self.urlconf, prefix=self.prefix)
        return paths

    def get_info(self):
        # Title and version are required by openapi specification 3.x
        info = {"title": self.title or "", "version": self.version or ""}

        if self.description is not None:
            info["description"] = self.description

        return info

    def get_schema(self, request=None, public=False):
        """
        Generate a OpenAPI schema.
        """
        paths = self.get_paths()
        if not paths:
            return None

        schema = {
            "openapi": "3.0.2",
            "info": self.get_info(),
            "paths": paths,
        }

        return schema
