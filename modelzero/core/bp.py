
conditions = {
}

def set(checkvar):
    conditions[checkvar] = True

def clear(checkvar):
    conditions[checkvar] = False

def getcond(checkvar):
    return conditions.get(checkvar, None)

def debug(checkvar = None):
    from ipdb import set_trace
    if not checkvar:
        # BP unconditionally
        set_trace()
    elif conditions.get(checkvar, False):
        print("BP Condition hit: %s" % checkvar)
        set_trace()

def funcprint(func, writer = None):
    from modelzero.core.printers import Writer, PrettyPrinter
    pp = PrettyPrinter()
    writer = writer or Writer()
    pp.eprintFuncDecl(func, writer)
    return writer

def eprint(expr, writer = None):
    """ Pretty prints an expression. """
    from modelzero.core.printers import Writer, PrettyPrinter
    pp = PrettyPrinter()
    writer = writer or Writer()
    pp(expr, writer)
    return writer
