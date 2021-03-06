import os
import re
import sys

from yaku.environment \
    import \
        Environment

COMPILE_TEMPLATE_SHELL = '''
def f(task):
    env = task.env
    wd = getattr(task, 'cwd', None)
    p = env.get_flat
    cmd = \'\'\' %s \'\'\' % s
    return task.exec_command(cmd, cwd=wd)
'''

COMPILE_TEMPLATE_NOSHELL = '''
def f(task):
	env = task.env
	wd = getattr(task, 'cwd', None)
	def to_list(xx):
		if isinstance(xx, str): return [xx]
		return xx
	lst = []
	%s
	lst = [x for x in lst if x]
	return task.exec_command(lst, cwd=wd)
'''


def funex(c):
    dc = {}
    exec(c, dc)
    return dc['f']

reg_act = re.compile(r"(?P<backslash>\\)|(?P<dollar>\$\$)|(?P<subst>\$\{(?P<var>\w+)(?P<code>.*?)\})", re.M)
def compile_fun_shell(name, line):
    """Compiles a string (once) into a function, eg:
    simple_task_type('c++', '${CXX} -o ${TGT[0]} ${SRC} -I ${SRC[0].parent.bldpath()}')

    The env variables (CXX, ..) on the task must not hold dicts (order)
    The reserved keywords TGT and SRC represent the task input and output nodes

    quick test:
    bld(source='wscript', rule='echo "foo\\${SRC[0].name}\\bar"')
    """

    extr = []
    def repl(match):
        g = match.group
        if g('dollar'): return "$"
        elif g('backslash'): return '\\\\'
        elif g('subst'): extr.append((g('var'), g('code'))); return "%s"
        return None

    line = reg_act.sub(repl, line)

    parm = []
    dvars = []
    app = parm.append
    for (var, meth) in extr:
        if var == 'SRC':
            if meth:
                app('task.inputs%s' % meth)
            else:
                app('" ".join(task.inputs)')
        elif var == 'TGT':
            if meth:
                app('task.outputs%s' % meth)
            else:
                app('" ".join(task.outputs)')
        else:
            if not var in dvars:
                dvars.append(var)
            app("p('%s')" % var)
    if parm:
        parm = "%% (%s) " % (',\n\t\t'.join(parm))
    else:
        parm = ''

    c = COMPILE_TEMPLATE_SHELL % (line, parm)

    #debug('action: %s', c)
    return (funex(c), dvars)

def compile_fun_noshell(name, line):

    extr = []
    def repl(match):
        g = match.group
        if g('dollar'): return "$"
        elif g('subst'): extr.append((g('var'), g('code'))); return "<<|@|>>"
        return None

    line2 = reg_act.sub(repl, line)
    params = line2.split('<<|@|>>')

    buf = []
    dvars = []
    app = buf.append
    for x in xrange(len(extr)):
        params[x] = params[x].strip()
        if params[x]:
            app("lst.extend(%r)" % params[x].split())
        (var, meth) = extr[x]
        if var == 'SRC':
            if meth: app('lst.append(task.inputs%s)' % meth)
            else: app("lst.extend(task.inputs)")
        elif var == 'TGT':
            if meth: app('lst.append(task.outputs%s)' % meth)
            else: app("lst.extend(task.outputs)")
        else:
            app('lst.extend(to_list(env[%r]))' % var)
            if not var in dvars: dvars.append(var)

    if params[-1]:
        app("lst.extend(%r)" % shlex.split(params[-1]))

    fun = COMPILE_TEMPLATE_NOSHELL % "\n\t".join(buf)
    #debug('action: %s', fun)
    return (funex(fun), dvars)

def compile_fun(name, line, shell=None):
    "commands can be launched by the shell or not"
    if line.find('<') > 0 or line.find('>') > 0 or line.find('&&') > 0:
        shell = True

    if shell is None:
        if sys.platform == 'win32':
            shell = False
        else:
            shell = True

    if shell:
        return compile_fun_shell(name, line)
    else:
        return compile_fun_noshell(name, line)

if __name__ == "__main__":
    f, e = compile_fun("yo", "${CC} -o ${TGT[0]} -c ${SRC}", False)
    class Foo(object):
        def __init__(self):
            self.inputs = ["foo.c"]
            self.outputs = ["foo.o"]
        def exec_command(self, cmd, cwd):
            print "execute %r in %s" % (cmd, cwd)

    foo = Foo()
    foo.env = Environment([("CC", "gcc")])
    foo.cwd = os.getcwd() + "/build"

    f(foo)
