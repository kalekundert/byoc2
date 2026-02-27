``byoc`` — Build Your Own Config
================================

[![Last release](https://img.shields.io/pypi/v/byoc.svg)](https://pypi.python.org/pypi/byoc)
[![Python version](https://img.shields.io/pypi/pyversions/byoc.svg)](https://pypi.python.org/pypi/byoc)
[![Documentation](https://img.shields.io/readthedocs/byoc.svg)](https://byoc.readthedocs.io/en/latest/)
[![Test status](https://img.shields.io/github/actions/workflow/status/kalekundert/byoc/test.yml?branch=master)](https://github.com/kalekundert/byoc/actions)
[![Test coverage](https://img.shields.io/codecov/c/github/kalekundert/byoc)](https://app.codecov.io/github/kalekundert/byoc)
[![Last commit](https://img.shields.io/github/last-commit/kalekundert/byoc?logo=github)](https://github.com/kalekundert/byoc)

BYOC is a python library for loading and combining configuration values from 
any number/kind of sources, e.g. files, command-line arguments, environment 
variables, databases, remote JSON APIs, etc.  It is meant to solve the 
following kinds of problems:

- You generally want basic configuration behavior: command-line options that 
  override environment variables that override configuration files.  But with 
  exceptions: maybe it doesn't make sense for a required command-line argument 
  to be specified in a file, or maybe it doesn't make sense for a complex, 
  nested value that doesn't change often to be specified on the command line.

- You want multiple command line options that can assign different values to 
  the same configuration value, e.g. `--color` and `--no-color`.

- For a few specific values, instead of having the command line override the 
  configuration file like usual, you want access to both values.

- You want users to be able to define "preset" combinations of configuration 
  values in a file, and then refer to those presets by name from the command 
  line.

- You want to read default configuration values from non-standard sources, like 
  SQL databases or remote API endpoints, but still want to allow users to 
  override those values from the command line or from local configuration 
  files.

- You want your application to have an interface that is complete and powerful, 
  but doesn't feel auto-generated.

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
            Value("Hello"),
    )

if __name__ == '__main__':
    app = Greet()
    byoc.load(app)
    print(f"{app.greeting}, {app.name}!")
```

We can configure this script from the command line:

```console
$ ./greet "Sir Bedevere"
Hello, Sir Bedevere!
$ ./greet "Sir Lancelot" -g Goodbye
Goodbye, Sir Lancelot!
```

...or from its configuration file:

```console
$ echo "greeting: Run away" > conf.yml
$ greet "Sir Robin"
Run away, Sir Robin!
```

