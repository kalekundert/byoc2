from __future__ import annotations

from .params.param import param
from .utils import do_nothing
from .errors import UsageError
from itertools import chain
from functools import partial
from collections.abc import MutableSequence, MutableMapping, Iterable
from more_itertools import one, value_chain
from operator import setitem

from typing import Any, Optional, Callable, Sequence, Mapping
from .configs import Config

class Loader:
    """
    Manage the process of loading configuration values.

    Arguments:

        attrs:
            A list of `Attribute` objects.  Each of these objects represents 
            (i) the information necessary to calculate a value for a parameter 
            and (ii) the location where that value should be stored.  In the 
            context of `load`, these attributes represent the actual attributes 
            of the application object.  In the context of `load_collection`, 
            they represent entries in the nested lists/dicts that make up the 
            application data structure.  When you're using the `Loader` class 
            directly, they can represent anything.  Refer to `Attribute` for 
            more information on exactly what these objects know and how they 
            can be created.

            It is not necessary to provide any attributes when instantiating a 
            Loader.  More attributes can be registered at any time (that is, 
            before of after calling `load`) using the `add_attributes` method.

        configs:
            A list of `Config` objects.  Each of these objects represents a 
            source of configuration data (e.g. the command-line, a file, 
            environment variables), and will be made available to the 
            parameters as they're calculating values for themselves.

    .. autoclasstoc::

    This class is primarily meant for internal use, specifically to implement 
    the `load` and `load_collection` functions.  However, it can also be used 
    externally to handle cases where parameters are mapped to one or more 
    application objects in complicated/non-standard ways.  For example, if you 
    wanted to use a dictionary of `param` instances to fill in an unrelated 
    object (perhaps because you don't have control over the object's class), 
    you could use a loader to do this.

    To use this class, follow these steps:

    - Create a list of `Attribute` objects.  See the `Attribute` class for a 
      detailed description of all of the information you need to provide, but 
      broadly speaking you need enough information to calculate a value and to 
      know where to store it.

    - Call `Loader.load`.  This method carries out the entire loading process.  
      That is, it calculates and stores a value for each attribute that the 
      loader has been given.  During this process, you can:

      - Call `param.get_value()` or `load_attribute_value()` to manually 
        calculate a value for a parameter, e.g. when you need to know the value 
        of one parameter to calculate another.  The former method is usually 
        preferred, because it doesn't require a reference to the loader object 
        itself (the parameter already has this), but both do the same thing.

      - Call `add_attributes()` to add more attributes to process.  You would 
        typically do this when one parameter produces a value that itself has 
        parameters that need to be loaded.

    During loading, each parameter will keep a reference to the loader.  
    Parameters cannot reference two loaders at once, so you cannot have 
    multiple loaders acting on the same parameters at the same time.  It should 
    never be necessary to have more than one loader, though, since one loader 
    can act on any number of application objects at the same time.

    Example:

        Load a hard-coded value into a pre-existing object:

            .. tab:: app.py

                .. code-block:: python

                    import byoc
                    from types import SimpleNamespace

                    app = SimpleNamespace()

                    attrs = [
                        byoc.Attribute(
                            app=app,
                            meta=app,
                            param=byoc.param(byoc.Value(1)),
                            set_attr=lambda value: setattr(app, 'x', value),
                            del_attr=lambda: delattr(app, 'x'),
                            set_meta=lambda value: setattr(app, 'y', value),
                            del_meta=lambda: delattr(app, 'y'),
                        )
                    ]

                    loader = byoc.Loader(attrs, [])
                    loader.load()

                    print(f'{app.x=}')
                    print(f'{app.y=}')

            .. tab:: bash

                .. code-block:: console

                    $ python app.py
                    app.x=1
                    app.y=PythonMeta(file='/path/to/app.py', line=12)
    """

    def __init__(self, attrs: Sequence[Attribute], configs: Sequence[configs]):
        self._attributes = {}
        self._locked_keys = []
        self._loaded_keys = set()
        self._pending_keys = []
        self._mid_load_keys = set()
        self._configs = configs
        self._loaded_configs = []
        self._is_loading = False

        self.add_attributes(attrs)

    def load(self):
        """
        Load values for each attribute.

        The steps carried out by this method are as follows:

        - Give each parameter a reference to this `Loader` object.  The 
          parameters will use this reference to notify the loader when they are 
          accessed during the loading process.

        - Call `Config.load` for each config provided to the loader, in order.  
          Configs are allowed to access parameters at any time during this 
          process.  Any parameters accessed in this way will be calculated 
          using only the configs that have been previously loaded.  After each 
          config finishes loading, any intermediate parameter values that may 
          have been calculated are discarded.

        - Calculate and store a value for each attribute.  Attributes are 
          generally processed in order.  However, if one attribute depends on 
          the value of another, the second attribute will be loaded right as 
          it's needed.  If a circular dependency is detected, an error will be 
          raised.

        - Remove the reference to this loader from each parameter.  This allows 
          the parameters to be used by a subsequent loader, if necessary.

        It is possible for new attributes to be added to the loader, via 
        `add_attributes`, during the second and third steps listed above.  When 
        this happens, the first step is immediately carried out for the new 
        attributes, then the rest of the process continues from where it was.
        """
        self._is_loading = True

        try:
            for attr in self._attributes.values():
                attr.param.begin_load(self)

            # Allow each config to load itself in a context without any 
            # upstream configs.  One important use-case for this feature is to 
            # allow command-line argument parsers to display usage text with 
            # config-aware default values.

            self._loaded_configs = []

            for config in self._configs:
                self._reset_attributes()
                config.load()
                self._loaded_configs.append(config)

            self._reset_attributes()

            while self._pending_keys:
                k = self._pending_keys[0]
                attr = self._attributes[k]
                self.load_attribute_value(attr.app, attr.param)

        finally:
            for attr in self._attributes.values():
                attr.param.end_load()

    def add_attributes(self, attrs: Sequence[Attribute]):
        """
        Register an additional set of attributes to be loaded.

        Arguments:
            attrs:
                A list of `Attribute` objects to add to the loader.  As in the 
                constructor, each attribute must have its own unique 
                application/parameter combination.

        This method can be called at any time before or during the loading 
        process.  The main reason to add attributes during the loading process 
        is to handle the case where a parameter produces a value that has 
        parameters of its own.

        It is usually not necessary to call this method directly.  The 
        `recursive_load` function and its siblings are meant to be more 
        convenient wrappers around this method, for objects that could be 
        passed to :func:`byoc.load()` if they were on their own.  This method should 
        only be used directly when these wrappers are somehow inadequate.
        """
        for attr in attrs:
            k = _key_from_attr(attr)
            if k in self._attributes:
                err = UsageError("cannot load the same attribute twice")
                err.info += f"app: {attr.app!r}"
                err.info += f"param: {attr.param!r}"
                raise err

            self._attributes[k] = attr
            self._pending_keys.append(k)

        if self._is_loading:
            for attr in attrs:
                attr.param.begin_load(self)

            self._mid_load_keys |= {_key_from_attr(attr) for attr in attrs}

    def load_attribute_value(self, app: Any, param: param):
        """
        Calculate and store a value for the given parameter in the given app.

        Arguments:
            app:
                The application associated with the desired attribute.
            param:
                The parameter associated with the desired attribute.

        This method should only be called if the attribute in question does not 
        already have a value.  If it does, that value should simply be looked 
        up and returned.  Often this does not require any special logic, since 
        values are typically stored in the exact places where they would be 
        looked for in the first place (i.e. in an object's 
        :attr:`~object.__dict__`).

        It is unusual to need to call this method directly:

        - When working with application objects that have parameters as class 
          attributes, i.e. inputs that would be compatible with 
          :func:`byoc.load`, simply accessing these attributes will cause this 
          method to be called, if necessary.  The reason this works is that 
          `param` objects are `descriptors <descriptors>`, so they are capable 
          of reacting to attribute access.

        - When working with lists/dicts of parameters, i.e. inputs that would 
          be compatible with `load_collection`, the :func:`byoc.getitem` 
          function provides a more convenient way to (i) check if a certain 
          parameter already has a value and (ii) call this method only if it 
          doesn't.

        - When neither of the above options are suitable, it's often more 
          convenient to call `param.get_value` than it is to call this method 
          directly.  Both of these methods do the same thing, but the former 
          doesn't require the caller to have a reference to the loader object, 
          because the parameter itself already has one.
        """
        k = _key_from_app_param(app, param)

        if k not in self._attributes:
            err = UsageError("cannot load unknown attribute")
            err.info += f"app: {app!r}"
            err.info += f"param: {param!r}"
            raise err

        attr = self._attributes[k]
        app, param = attr.app, attr.param

        if k in self._loaded_keys:
            err = UsageError("attribute already loaded")
            err.info += f"app: {app!r}"
            err.info += f"param: {param!r}"
            raise err

        assert k in self._pending_keys

        if k in self._locked_keys:
            err = UsageError("encountered circular dependency while loading the following parameters:")
            err.info += [
                    repr(attr)
                    for attr in value_chain(
                        (self._attributes[k] for k in self._locked_keys),
                        attr,
                    )
            ]
            raise err

        self._locked_keys.append(k)
        try:
            value, meta = param.load_value(app, self._loaded_configs)
        finally:
            self._locked_keys.pop()

        attr.set_attr(value)
        attr.set_meta(meta)

        self._loaded_keys.add(k)
        self._pending_keys.remove(k)

        return value

    def _reset_attributes(self):
        assert not self._locked_keys

        for k in self._loaded_keys:
            attr = self._attributes[k]
            attr.del_attr()
            attr.del_meta()

        for k in self._mid_load_keys:
            attr = self._attributes.pop(k)
            attr.param.end_load()

        self._mid_load_keys = set()
        self._loaded_keys = set()
        self._pending_keys = list(self._attributes)

class Attribute:
    """
    All of the information needed to calculate and store a value for a parameter.

    .. attribute:: app
        :type: Any

        The object that this attribute will belong to.  This object is made 
        available to various callback functions, but does not affect where the 
        value is actually stored.  That is purely determined by `set_attr`.

    .. attribute:: meta
        :type: Any

        The object that this attribute's metadata will belong to.  This 
        object is made available to various callback functions, but does not 
        affect where metadata is actually stored.  That is purely determined by 
        `set_meta`.

    .. attribute:: param
        :type: byoc.param

        The parameter associated with this attribute.  Note that it is possible 
        for the same parameter to be associated with multiple attributes.  This 
        might come up if you're loading a list of objects, all of which share 
        the same parameter instances (e.g. the parameters are class attributes, 
        and the objects are all from the same class).

    .. attribute:: set_attr
        :type: Callable[[Any], None]

        The function that will be called to store a value for this attribute, 
        once that value has been calculated.  This function should accept one 
        argument—the value to store—and should not return anything.

    .. attribute:: del_attr
        :type: Callable[[], None]

        The function that will be called to delete the value for this 
        attribute.  This only happens when an attribute value is needed before 
        all the configs have been loaded.  When this happens, the value in 
        question is calculated using only the configs that have been loaded so 
        far.  However, this value needs to subsequently be discarded, so that 
        a final value can be recalculated once all of the configs are available.

        If you know for sure that you won't use any configs that access 
        attribute values while they're being loaded, then you don't really need 
        to implement this function.  Instead, you can just provide a function 
        that raises an exception or something.

    .. attribute:: set_meta
        :type: Callable[[Any], None]

        The function that will be called to store metadata about the value.  
        The metadata is an arbitrary object that typically contains some 
        information about where the value in question was loaded from, e.g. a 
        file path and line number.  This function should accept one 
        argument—the metadata to store—and should not return anything.

    .. attribute:: del_meta
        :type: Callable[[], None]

        The function that will be called to delete the metadata for this value.  
        See `del_attr` for the details on when exactly this happens.

    Each `Attribute` object must be uniquely identifiable by the combination of 
    its `app` and its `param`.  Specifically, by the tuple ``id(app), id(param)``.
    """

    def __init__(
            self, *,
            app: Any,
            meta: Any,
            param: param,
            set_attr: Callable[[Any], None],
            del_attr: Callable[[], None],
            set_meta: Callable[[Any], None],
            del_meta: Callable[[], None],
    ):
        self.app = app
        self.meta = meta
        self.param = param
        self.set_attr, self.del_attr = set_attr, del_attr
        self.set_meta, self.del_meta = set_meta, del_meta

    def __repr__(self):
        return f'<Attribute app={self.app} param={self.param}>'

def load(
        app: Any,
        *,
        configs: Optional[Iterable[Config]] = None,
        meta: Optional[Any] = None,
):
    """
    Load configuration values into a custom object designed to hold them.

    Arguments:
        app:
            The object to load.  This object can be of any class (i.e. it 
            doesn't have to inherit from anything), but it should have class 
            attributes that are instances of `param`, as shown in the examples 
            below.  A value will be loaded for each of these parameters, then 
            stored in an instance attribute with the same name as the class 
            attribute (thereby shadowing the latter).  The result will be a 
            completely normal object with no remaining ties to BYOC.

            If the app has any parent classes, they will also be searched for 
            parameters.  The usual rules of inheritance are followed: if a 
            parameter of the same name is defined in multiple classes, only the 
            first in the method resolution order (MRO) will be used.  Likewise, 
            if a parameter in one class is shadowed by a normal attribute 
            (class or instance) in another, the normal attribute will be used 
            and that parameter will not be loaded.

        configs:
            The `Config` objects to use when loading the app.  If not provided, 
            the app will be searched for a method marked with the `configs` 
            decorator, and that method will be called to produce the configs.

        meta:
            The object where metadata about each loaded configuration value 
            (e.g. file and line number) should be stored.  The only requirement 
            for this object is that it must be possible to set attributes with 
            the same names as the parameters.  :class:`~types.SimpleNamespace` 
            works for this, but in some cases it might make sense to use a 
            custom class.

            If not provided, the app will be searched for a method marked with 
            the `meta` decorator, and that method will be called to produce the 
            meta object.  If no such method is found, or if it returns `None`, 
            the metadata information collected during the load process will not 
            be stored.  It will still be made available to various callbacks (e.g. 
            :paramref:`param.apply`), though.

    The loading process has two main steps:

    - The first step is to load all of the given `Config` objects.  
      Specifically, this means calling the :meth:`~Config.load` method for 
      each one.  This gives the configs a chance do any loading/parsing that 
      they need to.  The documentation for the `Config` class has more 
      information on exactly how this works.

      One important point to note is that configs are allowed to access the 
      app's parameters while they are being loaded.  This comes up if you want 
      to have the source for one config depend on values read from another, 
      e.g. a file path specified on the command-line.  When this happens, the 
      parameter's value is calculated using only the configs that have been 
      loaded so far.  This means that the order in which the configs are given 
      (which is the same as the order that they're loaded in) matters.  After 
      each config finishes loading, any intermediate parameter values that may 
      have been calculated are discarded.  It is possible for one parameter to 
      be calculated several times during the loading process, for this reason.

    - The second step is to load a value for each of the app's parameters.  
      Parameters can depend on other parameters, so long as no circular 
      dependencies are formed.  As each value is loaded, it is assigned to the 
      app using `setattr`.

    In the vast majority of cases, this function is the recommended way to use 
    BYOC.  The syntax for making custom app classes is succinct, clear, and 
    powerful.  However, there are alternatives:

    - If you'd rather not define a custom class, you can use 
      `load_collection` to read configuration values directly into an 
      arbitrarily nested list/dict data structure.

    - If the paradigm of setting attributes on an application object is too 
      limiting, you can use the `Loader` class to have complete control over 
      how parameters are stored after being loaded.  You can also use 
      `recursive_load` to add more application objects during the loading 
      process.  For example, you could use this to have a parameter produce 
      an object that has parameters of its own.

    Examples:

        Load a hard-coded value:

        .. code-block:: python-console

            >>> import byoc
            >>> from byoc import Value
            >>> class App:
            ...     a = byoc.param(Value(1))
            ...
            >>> app = App()
            >>> byoc.load(app)
            >>> app.a
            1

        Load a value from a file:

        .. tab:: python

            .. code-block:: python-console

                >>> import byoc
                >>> from byoc import Key, TomlConfig
                >>> class App:
                ...
                ...     @byoc.configs
                ...     def iter_configs(self):
                ...         yield TomlConfig('config.toml')

                ...     a = byoc.param(Key(TomlConfig, 'a'))
                ...
                >>> app = App()
                >>> byoc.load(app)
                >>> app.a
                1

        .. tab:: config.toml

            .. code-block:: toml

                a = 1

        Load a value from a file specified on the command-line:

        .. tab:: app.py

            .. code-block:: python

                import byoc
                from byoc import Key, Value, ArgparseConfig, TomlConfig

                class App:

                    # If no path is provided, use `config_1.toml` by 
                    # default.
                    path = byoc.param(
                        Key(ArgparseConfig, 'path'),
                        Value('config_1.toml'),
                    )
                    value = byoc.param(Key(TomlConfig, 'value'))

                    @byoc.configs
                    def iter_configs(self):
                        # The configs will be loaded in the order they are 
                        # given here.  We need the `TomlConfig` to be 
                        # loaded after the `ArgparseConfig`, because 
                        # `self.path` won't have a value until then.
                        yield ArgparseConfig(self.get_argument_parser)
                        yield TomlConfig(lambda: self.path)

                    def get_argument_parser(self):
                        import argparse
                        parser = argparse.ArgumentParser()
                        parser.add_argument('path')
                        return parser

                app = App()
                byoc.load(app)
                print(app.value)

        .. tab:: config_1.toml

            .. code-block:: toml

                value = 1

        .. tab:: config_2.toml

            .. code-block:: toml

                value = 2

        .. tab:: bash

            .. code-block:: console

                $ python app.py
                1
                $ python app.py config_2.toml
                2
    """
    configs = _find_configs_in_obj(app) if configs is None else configs
    meta = _find_meta_in_obj(app) if meta is None else meta
    attrs = _find_attrs_in_obj(app, meta)

    loader = Loader(attrs, configs)
    loader.load()

def load_collection(
        app: MutableSequence | MutableMapping,
        configs: Iterable[Config],
        *,
        meta: Optional[Any] = None,
):
    """
    Load configuration values into a nested list/dict data structure.

    Arguments:
        app:
            The data structure to fill with configuration values.  This data 
            structure can be composed of arbitrarily nested lists and dicts (or 
            any other collection implementing the :class:`~collections.abc.MutableSequence` 
            or :class:`~collections.abc.MutableMapping` interfaces).  This 
            function will search the given data structure for `param` 
            instances, then replace each one with its corresponding value.  The 
            result will be a completely normal data structure with no remaining 
            ties to BYOC.

        configs:
            The `Config` objects to make available to the parameters.

        meta:
            The data structure where metadata about each loaded configuration 
            value (e.g. file and line number) should be stored.  This should be 
            a data structure with the same structure as 
            :paramref:`~load_collection.app`.  When a value is set for a 
            particular key/index in the app, the corresponding metadata will be 
            set for the same key/index in the meta data structure.  You can use 
            `meta_from_collection` to automatically construct an appropriate 
            data structure.

            If not provided, the metadata information collected during the load 
            process will not be stored.  It will still be made available to 
            various callbacks (e.g. :paramref:`param.apply`), though.

    See `load` for more details on how the loading process works.  Although 
    note that instead of using `setattr` to set parameter values, this version 
    of the function uses `operator.setitem`.

    This function is meant to be used for very simple applications, where 
    defining a custom class to hold parameters would feel too "heavy".  The 
    main downside of this approach is that it's harder to make parameters that 
    depend on other parameters (e.g. have one parameter serve as the default 
    value for another, or loading from a file specified on the command line).  
    With `load`, this just works.  With `load_collection`, you need to be 
    careful to use :func:`byoc.getitem` when accessing other parameters.  This 
    function checks whether or not the dependent parameter has already been 
    assigned a value, and loads it on-the-fly if not.

    Examples:

        Load some hard-coded values:

        .. code-block:: python-console

            >>> import byoc
            >>> from byoc import Value
            >>> app = {
            ...     'a': byoc.param(Value(1)),
            ...     'b': [byoc.param(Value(2)), 3],
            ...     'c': 4,
            ... }
            >>> byoc.load_collection(app, [])
            >>> app
            {'a': 1, 'b': [2, 3], 'c': 4}

        Load some values from a file:

        .. tab:: python

            .. code-block:: python

                >>> import byoc
                >>> from byoc import Key, TomlConfig
                >>> app = {
                ...     'a': byoc.param(Key(TomlConfig, 'a'))
                ... }
                >>> configs = [TomlConfig('config.toml')]
                >>> byoc.load_collection(app, configs)
                >>> app
                {'a': 1}

        .. tab:: config.toml

            .. code-block:: toml

                a = 1
    """
    attrs = _find_attrs_in_collection(app, meta)

    loader = Loader(attrs, configs)
    loader.load()

def recursive_load(loader: Loader, app: Any):
    """
    Load parameters for an object created and/or discovered while loading 
    another.

    Arguments:
        loader:
            The currently active loader.
        app:
            The new object to begin loading.  See :paramref:`load.app` for 
            more information.

    This function is meant to be passed to :paramref:`param.on_load`, where it 
    will be called once a value has been loaded for the parameter in question.  
    Any new parameters contained in that value will then subsequently be 
    loaded.

    Note that this function cannot change which `Config` objects the loader is 
    using.  Configs are set when the loading process begins, and cannot later 
    be added or removed.  Therefore, if there are any configs that will be 
    needed by recursively-loaded applications, but not by the main application, 
    they still must be provided from the beginning.

    The app given to this function must adhere to the API expected by `load`, 
    as mentioned above.  Currently, there is no convenient way to recursively 
    load apps that adhere to the API expected by `load_collection`.  This was 
    an intentional choice.  The `load_collection` function is meant for very 
    simple use cases, and recursive loading is not a simple use case.  If you 
    want something like this, you can implement it using 
    `Loader.add_attributes`.

    Examples:

        Load a hard-coded value in a child object:

        .. code-block:: python-console

            >>> import byoc
            >>> from byoc import Func, Value
            >>> class ChildApp:
            ...     x = byoc.param(Value(1))
            ...
            >>> class App:
            ...     child = byoc.param(
            ...         Func(ChildApp),
            ...         on_load=byoc.recursive_load,
            ...     )
            ...
            >>> app = App()
            >>> byoc.load(app)
            >>> app.child.x
            1

        Load a value from a file in a child object.  Note how the child has 
        access to the configs defined by the parent:

        .. tab:: python

            .. code-block:: python-console

                >>> import byoc
                >>> from byoc import Key, Func, TomlConfig
                >>> class ChildApp:
                ...     x = byoc.param(Key(TomlConfig, 'x'))
                ...
                >>> class App:
                ...     @byoc.configs
                ...     def iter_configs(self):
                ...         yield TomlConfig('config.toml')
                ...
                ...     child = byoc.param(
                ...         Func(ChildApp),
                ...         on_load=byoc.recursive_load,
                ...     )
                ...
                >>> app = App()
                >>> byoc.load(app)
                >>> app.child.x
                1

        .. tab:: config.toml

            .. code-block:: toml

                x = 1
    """
    meta = _find_meta_in_obj(app)
    attrs = _find_attrs_in_obj(app, meta)
    loader.add_attributes(attrs)

def recursive_load_from_list(loader: Loader, apps: Sequence):
    """
    Recursively load a list of objects.

    Arguments:
        loader:
            See `recursive_load`.
        apps:
            The list of objects to recursively load.  See `recursive_load` for 
            more details on the individual objects.

    This function is basically the same as `recursive_load`, except that it 
    expects a list of application objects rather than a single one.

    Example:

        .. code-block:: python-console

            >>> import byoc
            >>> from byoc import Method, Value
            >>> class ChildX:
            ...     x = byoc.param(Value(1))
            ...
            >>> class ChildY:
            ...     y = byoc.param(Value(2))
            ...
            >>> class App:
            ...     def make_children(self):
            ...         return [ChildX(), ChildY()]
            ...
            ...     children = byoc.param(
            ...         Method(make_children),
            ...         on_load=byoc.recursive_load_from_list,
            ...     )
            ...
            >>> app = App()
            >>> byoc.load(app)
            >>> app.children[0].x
            1
            >>> app.children[1].y
            2
    """

    for app in apps:
        recursive_load(loader, app)

def recursive_load_from_dict_values(loader: Loader, apps: Mapping):
    """
    Recursively load a dictionary of objects.

    Arguments:
        loader:
            See `recursive_load`.
        apps:
            The dictionary containing, as values, the objects to recursively 
            load.  See `recursive_load` for more details on the individual 
            objects.

    This function is basically the same as `recursive_load`, except that it 
    expects to be given a dictionary of application objects instead of a single 
    one.

    Example:

        .. code-block:: python-console

            >>> import byoc
            >>> from byoc import Method, Value
            >>> class ChildX:
            ...     x = byoc.param(Value(1))
            ...
            >>> class ChildY:
            ...     y = byoc.param(Value(2))
            ...
            >>> class App:
            ...     def make_children(self):
            ...         return {'x': ChildX(), 'y': ChildY()}
            ...
            ...     children = byoc.param(
            ...         Method(make_children),
            ...         on_load=byoc.recursive_load_from_dict_values,
            ...     )
            ...
            >>> app = App()
            >>> byoc.load(app)
            >>> app.children['x'].x
            1
            >>> app.children['y'].y
            2
    """
    for app in apps.values():
        recursive_load(loader, app)

def configs(method):
    """
    A decorator used to mark the method that :func:`~byoc.load()` should call to get 
    the list of configs to use.

    Arguments:
        method:
            The method that will be called to produce the configs.  This method 
            should accept no arguments (other than ``self``) and should return 
            an iterable of `Config` objects.  It's conventional to name the 
            decorated method ``iter_configs`` and to have it yield the relevant 
            configs, just because this is usually the most succinct way to 
            write the code.

    Example:

        .. tab:: python

            .. code-block:: python

                >>> import byoc
                >>> from byoc import Key, TomlConfig
                >>> class App:
                ...
                ...     @byoc.configs
                ...     def iter_configs(self):
                ...         yield TomlConfig('config.toml')
                ...
                ...     x = byoc.param(Key(TomlConfig, 'x'))
                ...
                >>> app = App()
                >>> byoc.load(app)
                >>> app.x
                1

        .. tab:: config.toml

            .. code-block:: toml

                x = 1
    """
    method._byoc_is_config_factory = True
    return method

def meta(method):
    """
    A decorator used to mark the method that :func:`~byoc.load()` should call 
    to get the object where metadata will be stored.

    Arguments:
        method:
            The method that will be called to produce the meta object.  This 
            method should accept no arguments (other than ``self``) and should 
            return an object that can have attributes set on it, e.g. an 
            instance of :class:`~types.SimpleNamespace`.  This object will be 
            used to store metadata about each loaded configuration value, e.g. 
            file and line number.  If the method returns `None`, then no 
            metadata will be stored.

    Example:

        .. tab:: python

            .. code-block:: python

                >>> import byoc
                >>> from byoc import Key, TomlConfig
                >>> from types import SimpleNamespace
                >>> class App:
                ...
                ...     def __init__(self):
                ...         self.meta = SimpleNamespace()

                ...     @byoc.meta
                ...     def get_meta(self):
                ...         return self.meta
                ...
                ...     @byoc.configs
                ...     def iter_configs(self):
                ...         yield TomlConfig('config.toml')
                ...
                ...     x = byoc.param(Key(TomlConfig, 'x'))
                ...
                >>> app = App()
                >>> byoc.load(app)
                >>> app.x
                1
                >>> app.meta.x
                FileMeta(path='config.toml')

        .. tab:: config.toml

            .. code-block:: toml

                x = 1
    """
    method._byoc_is_meta_factory = True
    return method


def _find_attrs_in_obj(app, meta):
    params = _find_cls_attrs(
            app,
            lambda k, v: isinstance(v, param)
    )
    return [
            Attribute(
                app=app,
                meta=meta,
                param=v,
                set_attr=partial(setattr, app, k),
                del_attr=partial(delattr, app, k),
                set_meta=partial(setattr, meta, k) \
                        if meta is not None else do_nothing,
                del_meta=partial(delattr, meta, k) \
                        if meta is not None else do_nothing,
            )
            for k, v in params.items()
    ]

def _find_attrs_in_collection(app, meta):
    if not isinstance(app, (MutableSequence, MutableMapping)):
        raise UsageError(f"expected list or dict, not {app!r}")

    # Note that we wrap the app in a list to get the recursive algorithm 
    # started.  If the app were a parameter, this would produce unexpected 
    # results: the setters would modify this temporary list instead of anything 
    # visible to the user.  However, because we check that the app is actually 
    # a collection above, this cannot happen.

    return list(_iter_attrs_in_collection(app, meta, [app], [meta], 0))

def _iter_attrs_in_collection(app, meta, app_collection, meta_collection, key):
    app_item = app_collection[key]
    meta_item = meta_collection[key] if meta_collection is not None else None

    if isinstance(app_item, param):
        yield Attribute(
                app=app,
                meta=meta,
                param=app_item,
                set_attr=partial(setitem, app_collection, key),
                del_attr=partial(setitem, app_collection, key, app_item),
                set_meta=partial(setitem, meta_collection, key) \
                        if meta_collection is not None else do_nothing,
                del_meta=partial(setitem, meta_collection, key, None) \
                        if meta_collection is not None else do_nothing,
        )

    elif isinstance(app_item, MutableSequence):
        for i, _ in enumerate(app_item):
            yield from _iter_attrs_in_collection(
                    app, meta, app_item, meta_item, i)

    elif isinstance(app_item, MutableMapping):
        for k in app_item:
            yield from _iter_attrs_in_collection(
                    app, meta, app_item, meta_item, k)

    else:
        pass

def _find_configs_in_obj(app):
    config_factories = _find_cls_attrs(
            app,
            lambda k, v: getattr(v, '_byoc_is_config_factory', False)
    )
    configs = chain.from_iterable(
            f(app) for f in config_factories.values()
    )
    return list(configs)

def _find_meta_in_obj(app):
    meta_factories = _find_cls_attrs(
            app,
            lambda k, v: getattr(v, '_byoc_is_meta_factory', False)
    )

    if not meta_factories:
        return None

    if len(meta_factories) > 1:
        err = UsageError("cannot mark more than one method with `@byoc.meta`")
        err.info += "found the following marked methods:\n" + '\n'.join(meta_factories)
        raise err

    meta_factory = one(
            meta_factories.values(),
            too_short=AssertionError,
            too_long=AssertionError,
    )
    return meta_factory(app)

def _key_from_attr(attr):
    return _key_from_app_param(attr.app, attr.param)

def _key_from_app_param(app, param):
    return id(app), id(param)

def _find_cls_attrs(obj, predicate=lambda k, v: True):
    cls_attrs = {}
    defined_keys = set(obj.__dict__)

    for cls in obj.__class__.__mro__:
        for k, v in cls.__dict__.items():
            if k in defined_keys:
                continue
            defined_keys.add(k)

            if predicate(k, v):
                cls_attrs[k] = v

    return cls_attrs
