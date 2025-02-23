*************
API Reference
*************

Loading
=======
.. autosummary::
   :toctree: api

   byoc.load
   byoc.load_collection
   byoc.recursive_load
   byoc.recursive_load_from_list
   byoc.recursive_load_from_dict_values
   byoc.Loader
   byoc.Attribute

Parameters
==========
.. autosummary::
   :toctree: api

   byoc.param
   byoc.Getter
   byoc.Key
   byoc.Method
   byoc.Func
   byoc.Value
   byoc.PythonMeta
   byoc.getitem

Configs
=======
.. autosummary::
   :toctree: api

   byoc.Config
   byoc.ConfigAttr
   byoc.ConfigAttrMeta
   byoc.Finder
   byoc.DictFinder
   byoc.configs
   byoc.config_attr
   byoc.dict_like

Command line
------------
.. autosummary::
   :toctree: api

   byoc.CliConfig
   byoc.CliMeta
   byoc.ArgparseConfig
   byoc.DocoptConfig
   byoc.mako_usage

Files
-----
.. autosummary::
   :toctree: api

   byoc.FileConfig
   byoc.FileMeta
   byoc.JsonConfig
   byoc.NtConfig
   byoc.TomlConfig
   byoc.YamlConfig

Environment variables
---------------------
.. autosummary::
   :toctree: api

   byoc.EnvVarConfig
   byoc.EnvVarMeta

Apply functions
===============
.. autosummary::
   :toctree: api

   byoc.relpath
   byoc.int_eval
   byoc.float_eval
   byoc.arithmetic_eval

Pick functions
==============
.. autosummary::
   :toctree: api

   byoc.first
   byoc.list
   byoc.merge_dicts
   byoc.ValuesIter

Metadata
========
.. autosummary::
   :toctree: api

   byoc.meta
   byoc.meta_from_collection

Errors
======
.. autosummary::
   :toctree: api

   byoc.UsageError
   byoc.NoValueFound
