#!/usr/bin/env python
#-*- coding:utf-8 -*-
##
## decide.py
##
##  Created on: Feb 19, 2026
##      Author: Alexey Ignatiev
##      E-mail: alexey.ignatiev@monash.edu
##

#
#==============================================================================
import getopt
import itertools
from pysat.formula import CNF, IDPool
from pysat.solvers import Solver
import os
import re
import sys


#
#==============================================================================
def read_input(filename):
    """
        Reads the input file and returns a list of clauses and a variable
        mapping (if one exists).
    """

    clauses, vmap = [], {}

    if filename == '-':
        lines = sys.stdin.read().splitlines()
    else:
        with open(filename, 'r') as fp:
            lines = fp.read().splitlines()

    # expected format:
    #   line 1: CNF expression
    #   blank line
    #   mapping lines: <alias> <full_name>
    expr, blank = None, False

    for line in lines:
        if not line.strip():
            if expr is not None:
                blank = True
            continue

        if expr is None:
            expr = line.strip()
            continue

        if blank:
            parts = line.split()
            if len(parts) != 2:
                raise ValueError('Malformed mapping line: {0}'.format(line.strip()))
            vmap[parts[0]] = parts[1]
        else:
            raise ValueError('Multiple non-empty lines found in input expression')

    if expr:
        clauses = [[l.strip() for l in cl.strip(' ()').split('|')] for cl in expr.split('&')]

    return clauses, vmap


#
#==============================================================================
def make_cnf(filename):
    """
        Converts a textual input CNF formula to DIMACS CNF format.
    """

    # we are going to save the result here
    res = CNF()

    # first, reading the input file
    clauses, vmap = read_input(filename)

    if clauses:
        # if there are any clauses
        # mapping from textual literals to DIMACS ids
        res.pool = IDPool()

        # collecting all variables in the formula
        variables = set()
        for cl in clauses:
            for lit in cl:
                var = lit.strip('~').strip()
                variables.add(vmap.get(var, var))

        # mapping them deterministically to DIMACS ids
        for var in sorted(variables):
            res.comments.append(f'c {var} {res.pool.id(var)}')

        # converting the clauses to DIMACS format
        for cl in clauses:
            # translating the clause
            newcl = []
            for lit in cl:
                var, neg = lit.strip('~').strip(), lit.count('~') % 2 == 1
                var = vmap.get(var, var)
                newcl.append(res.pool.id(var) * (-1 if neg else +1))

            # adding the new clause to the CNF formula
            res.append(newcl)

        # pattern for matching variable names
        pat = re.compile(r'^a([1-9][0-9]*)t([0-9]+)r([1-9][0-9]*)c([1-9][0-9]*)$')

        # parsing the maximal time step and grid size from the variable names
        res.maxa, res.maxt, res.maxr, res.maxc = problem_dimensions(res.pool)

    return res


#
#==============================================================================
def problem_dimensions(pool):
    """
        Returns the maximal time step and grid size inferred from the variable names.
    """

    # pattern for matching variable names
    pat = re.compile(r'^a([1-9][0-9]*)t([0-9]+)r([1-9][0-9]*)c([1-9][0-9]*)$')

    # problem dimensions
    max_a, max_r, max_c, max_t = 0, 0, 0, 0

    for obj in pool.obj2id:
        m = pat.match(obj)
        if not m:
            continue

        a, t, r, c = [int(x) for x in m.groups()]
        max_a = max(max_a, a)
        max_t = max(max_t, t)
        max_r = max(max_r, r)
        max_c = max(max_c, c)

    return max_a, max_t, max_r, max_c


#
#==============================================================================
def agent_name(i):
    """
        Returns a readable agent label from a numeric id.
    """

    assert 0 <= i <= 25, 'Agent id out of range: {0}'.format(i)
    return chr(ord('A') + i)


#
#==============================================================================
def print_plan(model, mode, cnf):
    """
        Pretty-prints the model as a sequence of grid states over time.
    """

    if mode == 'vals':
        for t in range(cnf.maxt + 1):
            for a in range(cnf.maxa):
                for r, c in itertools.product(range(1, cnf.maxr + 1), range(1, cnf.maxc + 1)):
                    var = cnf.pool.id(f'a{a + 1}t{t}r{r}c{c}')
                    if model[var - 1] == var:
                        print(f'  agent {agent_name(a)}, at time t = {t}, is at cell ({r}, {c})')
                        break

    elif mode == 'grid':
        for t in range(cnf.maxt + 1):
            print('  t = {0}'.format(t))

            # constructing the grid state at time t, row by row
            for r in range(1, cnf.maxr + 1):
                row = []

                for c in range(1, cnf.maxc + 1):
                    row.append('.')
                    for a in range(cnf.maxa):
                        var = cnf.pool.id(f'a{a + 1}t{t}r{r}c{c}')
                        if model[var - 1] == var:
                            if row[-1] == '.':
                                row[-1] = agent_name(a)
                            else:
                                row[-1] = '*'
                                break

                print('    ' + ' '.join(row))


#
#==============================================================================
def parse_options():
    """
        Parse command-line options.
    """

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   'e:h:p:s:',
                                   ['enum=', 'help', 'print=', 'solver='])
    except getopt.GetoptError as err:
        sys.stderr.write(str(err).capitalize() + '\n')
        usage()
        sys.exit(1)

    enum = 1
    print_mode = 'vals'
    solver = 'g3'

    for opt, arg in opts:
        if opt in ('-e', '--enum'):
            enum = str(arg)
            enum = int(enum) if enum != 'all' else -1
        elif opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif opt in ('-p', '--print'):
            print_mode = str(arg)
        elif opt in ('-s', '--solver'):
            solver = str(arg)
        else:
            assert False, 'Unhandled option: {0} {1}'.format(opt, arg)

    assert len(args) <= 1, 'At most one input file can be provided'
    assert print_mode in ('vals', 'grid'), 'Invalid print mode: {0}'.format(print_mode)
    assert enum == -1 or enum > 0, 'Invalid number of models to enumerate: {0}'.format(enum)

    # determining what input to read (from a file or from stdin)
    fname = args[0] if args and args[0] else '-'

    return enum, print_mode, solver, fname


#
#==============================================================================
def usage():
    """
        Print usage message.
    """

    print('Usage:', os.path.basename(sys.argv[0]), '[options] [input-file.txt|-]')
    print('Options:')
    print('        -h, --help               Show this message')
    print('        -e, --enum=<int>         Number of models to compute')
    print('                                 Available values: [1 .. INT_MAX], all (default = 1)')
    print('        -p, --print=<string>     How to print solutions')
    print('                                 Available values: vals, grid (default = vals)')
    print('        -s, --solver=<string>    SAT solver to use (default: g3)')
    print('                                 Available values: cd15, cd19, g3, g4, lgl, mcb, mcm, mpl, m22, mc, mgh (default = g3)')


# main block
#==============================================================================
if __name__ == '__main__':
    # parsing command-line options
    nof_models, print_mode, solver, fname = parse_options()

    # converting to DIMACS
    cnf = make_cnf(fname)

    # getting a model if the formula is satisfiable
    if cnf:
        with Solver(name=solver, bootstrap_with=cnf) as sat:
            found = False
            for i, model in enumerate(sat.enum_models(), 1):
                found = True
                if i == 1:
                    print('SATISFIABLE')

                print_plan(model, print_mode, cnf)

                if i == nof_models:
                    break

            if not found:
                print('UNSAT')
    else:
        print('SAT but empty formula')
        sys.exit(1)
