``byoc`` — Build Your Own Config
================================

[![Last release](https://img.shields.io/pypi/v/byoc.svg)](https://pypi.python.org/pypi/byoc)
[![Python version](https://img.shields.io/pypi/pyversions/byoc.svg)](https://pypi.python.org/pypi/byoc)
[![Documentation](https://img.shields.io/readthedocs/byoc.svg)](https://byoc.readthedocs.io/en/latest/)
[![Test status](https://img.shields.io/github/actions/workflow/status/kalekundert/byoc/test.yml?branch=master)](https://github.com/kalekundert/byoc/actions)
[![Test coverage](https://img.shields.io/codecov/c/github/kalekundert/byoc)](https://app.codecov.io/github/kalekundert/byoc)
[![Last commit](https://img.shields.io/github/last-commit/kalekundert/byoc?logo=github)](https://github.com/kalekundert/byoc)

BYOC is a python library for integrating configuration values from any 
number/kind of sources, e.g. files, command-line arguments, environment 
variables, databases, remote JSON APIs, etc.  The primary goal of BYOC is to 
give your application complete control over its own configuration.  This means:

- Complete control over how files, options, etc. are named and organized.

- Complete control over how values from different config sources are parsed and 
  merged.

- Support for any kind of file format, argument parsing library, etc.

- No opinions about anything enforced by BYOC.

Below is an example showing how BYOC works.  The first step is to define a 
class with "parameters" that each specify how to look up one configuration 
value.  Usually this means checking in multiple places (e.g. the command line 
then a file) for a value, and using whichever is found first.  The second step 
is to call `byoc.load()`.  This will replace each parameter with its 
corresponding value.  The result is a normal object (i.e. no ties to BYOC) 
containing all of the configuration values:

```python
import byoc
from byoc import DocoptConfig, YamlConfig, Key, Value

class Greet:
    """
    Say a greeting.

    Usage:
        greet <name> [-g <greeting>]

    Options:
        -g <greeting>   The greeting to use.
    """

    # Define the config sources that will be available to the following
    # parameters.
    @byoc.configs
    def iter_configs(self):
        yield DocoptConfig(self.__doc__)
        yield YamlConfig('conf.yml')

    # The name has to come from the command-line.
    name = byoc.param(
            Key(DocoptConfig, '<name>'),
    )

    # The greeting can come from either the command-line or the YAML file.
    # If it's not specified in either place, the default value is "Hello".
    greeting = byoc.param(
            Key(DocoptConfig, '-g'),
            Key(YamlConfig, 'greeting'),
            Value('Hello'),
    )

if __name__ == '__main__':
    app = Greet()
    byoc.load(app)
    print(f"{app.greeting}, {app.name}!")
```

We can configure this script from the command line:

```console
$ ./greet 'Sir Bedevere'
Hello, Sir Bedevere!
$ ./greet 'Sir Lancelot' -g Goodbye
Goodbye, Sir Lancelot!
```

...or from its configuration file:

```console
$ echo "greeting: Run away" > conf.yml
$ greet 'Sir Robin'
Run away, Sir Robin!
```

