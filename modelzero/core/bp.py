
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

def indent(level): return "  " * level

def eprint(expr):
    """ Pretty prints an expression. """
    val = expr.variant_value 
    eprint_helper(val.printables())

def eprint_helper(printables, depth = 0):
    for level, printable in printables:
        if type(printable) is str:
            print(indent(depth + level) + printable)
        else:
            eprint_helper(printable, depth + level)

