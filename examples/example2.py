import os
import sys

from yaku.context \
    import \
        get_bld, get_cfg

# Use cases:
#   - just load the tool, its configuration should be automatic, and
#   building is one function call away
#   - customizing tool configuration
def configure(ctx):
    tools = ctx.use_tools(["pyext", "ctasks"], ["tools"])

def build(ctx):
    python_builder = ctx.builders["pyext"]
    python_builder.extension("_bar", ["src/hellomodule.c"])

if __name__ == "__main__":
    ctx = get_cfg()
    configure(ctx)
    ctx.store()

    ctx = get_bld()
    build(ctx)
    ctx.store()
