import os

from cPickle \
    import \
        load

RULES_REGISTRY = {}

CACHE_FILE = ".cache.lock"

def extension(ext):
    def _f(f):
        RULES_REGISTRY[ext] = f
        return f
    return _f

def set_extension_hook(ext, hook):
    old = RULES_REGISTRY[ext]
    RULES_REGISTRY[ext] = hook
    return old

def get_extension_hook(ext):
    try:
        return RULES_REGISTRY[ext]
    except KeyError:
        raise ValueError("No hook registered for extension %r" % ext)

class BuildContext(object):
    def __init__(self):
        self.object_tasks = []
        self.cache = {}
        self.env = {}

def create_tasks(ctx, sources):
    tasks = []

    for s in sources:
        base, ext = os.path.splitext(s)
        if not RULES_REGISTRY.has_key(ext):
            raise RuntimeError("No rule defined for extension %r" % ext)
        else:
            task_gen = RULES_REGISTRY[ext]
            tasks.extend(task_gen(ctx, s))
    return tasks

def run_tasks(ctx, tasks):
    def run(t):
        t.run()
        ctx.cache[tuid] = t.signature()

    for t in tasks:
        tuid = t.get_uid()
        for o in t.outputs:
            if not os.path.exists(o):
                run(t)
                break
        if not tuid in ctx.cache:
            run(t)
        else:
            sig = t.signature()
            if sig != ctx.cache[tuid]:
                run(t)

def build_dag(tasks):
    # Build dependency graph (DAG)
    # task_deps[target] = list_of_dependencies
    # At this point, task_deps is not guaranteed to be a DAG (may have
    # cycle) - will be detected during topological sort
    task_deps = {}
    output_to_tuid = {}
    for t in tasks:
        for o in t.outputs:
            try:
                task_deps[o].extend(t.inputs + t.deps)
            except KeyError:
                task_deps[o] = t.inputs[:] + t.deps[:]
            output_to_tuid[o] = t.get_uid()
    return task_deps, output_to_tuid

def topo_sort(task_deps):
    # Topological sort (depth-first search)
    # XXX: cycle detection is missing
    tmp = []
    nodes = []
    for dep in task_deps.values():
        nodes.extend(dep)
    nodes.extend(task_deps.keys())
    nodes = set(nodes)

    visited = set()
    def visit(node):
        if not node in visited:
           visited.add(node)
           deps = task_deps.get(node, None)
           if deps:
               for c in deps:
                   visit(c)
           tmp.append(node)

    for node in nodes:
        visit(node)

    return tmp

def get_bld():
    bld = BuildContext()

    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as fid:
            bld.cache = load(fid)
    else:
        bld.cache = {}

    return bld

class TaskGen(object):
    def __init__(self, name, sources, target):
        self.name = name
        self.sources = sources
        self.target = target

        self.env = {}

class CompiledTaskGen(TaskGen):
    def __init__(self, name, sources, target):
        TaskGen.__init__(self, name, sources, target)
        self.object_tasks = []
