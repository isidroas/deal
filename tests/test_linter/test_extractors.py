import ast
import astroid
from textwrap import dedent

import pytest

from deal.linter._extractors import get_returns, get_exceptions, get_prints, get_imports, get_contracts


@pytest.mark.parametrize('text, expected', [
    ('return 1', (1, )),
    ('return -1', (-1, )),
    ('return 3.14', (3.14, )),
    ('return -3.14', (-3.14, )),
    ('return "lol"', ('lol', )),
    ('return b"lol"', (b'lol', )),
    ('return True', (True, )),
    ('return None', (None, )),

    ('if True: return 13', (13, )),
    ('if True:\n  return 13\nelse:\n  return 16', (13, 16)),
    ('for i in lst: return 13', (13, )),
    ('try:\n lol()\nexcept:\n 1\nelse:\n return 3', (3, )),
    ('try:\n lol()\nexcept:\n 1\nfinally:\n return 3', (3, )),
    ('with lol():\n return 3', (3, )),
])
def test_get_returns_simple(text, expected):
    tree = astroid.parse(text)
    print(tree.repr_tree())
    returns = tuple(r.value for r in get_returns(body=tree.body))
    assert returns == expected

    tree = ast.parse(text)
    print(ast.dump(tree))
    returns = tuple(r.value for r in get_returns(body=tree.body))
    assert returns == expected


@pytest.mark.parametrize('text, expected', [
    ('return 1 + 2', (3, )),
    ('return a', ()),
])
def test_get_returns_inference(text, expected):
    tree = astroid.parse(text)
    print(tree.repr_tree())
    returns = tuple(r.value for r in get_returns(body=tree.body))
    assert returns == expected


@pytest.mark.parametrize('text, expected', [
    ('raise BaseException', (BaseException, )),
    ('raise ValueError', (ValueError, )),
    ('raise UnknownError', ('UnknownError', )),
    ('raise ValueError("lol")', (ValueError, )),
    ('raise unknown()', ()),
    ('assert False', (AssertionError, )),
    ('12 / 0', (ZeroDivisionError, )),
    ('exit(13)', (SystemExit, )),
    ('sys.exit(13)', (SystemExit, )),

    ('if True: raise KeyError', (KeyError, )),
    ('for i in lst: raise KeyError', (KeyError, )),
])
def test_get_exceptions_simple(text, expected):
    tree = astroid.parse(text)
    print(tree.repr_tree())
    returns = tuple(r.value for r in get_exceptions(body=tree.body))
    assert returns == expected

    tree = ast.parse(text)
    print(ast.dump(tree))
    returns = tuple(r.value for r in get_exceptions(body=tree.body))
    assert returns == expected


@pytest.mark.parametrize('text, expected', [
    ('print(1)', ('print', )),
    ('sys.stdout.write(1)', ('sys.stdout', )),
    ('open("fpath", "w")', ('open', )),
    ('open("fpath", mode="w")', ('open', )),
    ('with open("fpath", "w") as f: ...', ('open', )),
    ('with something: ...', ()),
    ('open("fpath", "r")', ()),
    ('open("fpath")', ()),
    ('open("fpath", encoding="utf8")', ()),
])
def test_get_prints_simple(text, expected):
    tree = astroid.parse(text)
    print(tree.repr_tree())
    returns = tuple(r.value for r in get_prints(body=tree.body))
    assert returns == expected

    tree = ast.parse(text)
    print(ast.dump(tree))
    returns = tuple(r.value for r in get_prints(body=tree.body))
    assert returns == expected


@pytest.mark.parametrize('text, expected', [
    ('from pathlib import Path\np = Path()\np.write_text("lol")', ('Path.open', )),
    ('from pathlib import Path\np = Path()\np.open("w")', ('Path.open', )),
    ('from pathlib import Path\np = Path()\nwith p.open("w"): ...', ('Path.open', )),
    ('from pathlib import Path\np = Path()\np.read_text()', ()),
    ('from pathlib import Path\np = Path()\np.open()', ()),
    ('with something.open("w"): ...', ()),
    ('something = file\nwith something.open("w"): ...', ()),
])
def test_get_prints_infer(text, expected):
    tree = astroid.parse(text)
    print(tree.repr_tree())
    returns = tuple(r.value for r in get_prints(body=tree.body))
    assert returns == expected


@pytest.mark.parametrize('text, expected', [
    ('from deal import pre', ('deal', )),
])
def test_get_imports_simple(text, expected):
    tree = astroid.parse(text)
    print(tree.repr_tree())
    returns = tuple(r.value for r in get_imports(body=tree.body))
    assert returns == expected

    tree = ast.parse(text)
    print(ast.dump(tree))
    returns = tuple(r.value for r in get_imports(body=tree.body))
    assert returns == expected


@pytest.mark.parametrize('text, expected', [
    ('@deal.post(lambda x: x>0)', ('post', )),
    ('@deal.silent', ('silent', )),
    ('@deal.silent()', ('silent', )),
    ('@deal.chain(deal.silent)', ('silent', )),
    ('@deal.chain(deal.silent, deal.post(lambda x: x>0))', ('silent', 'post')),
])
def test_get_contracts_decorators(text, expected):
    text += '\ndef f(x): pass'

    tree = astroid.parse(text)
    print(tree.repr_tree())
    decos = tree.body[-1].decorators.nodes
    returns = tuple(cat for cat, _ in get_contracts(decos))
    assert returns == expected

    tree = ast.parse(text)
    print(ast.dump(tree))
    decos = tree.body[-1].decorator_list
    returns = tuple(cat for cat, _ in get_contracts(decos))
    assert returns == expected


def test_get_contracts_infer():
    text = """
        from io import StringIO
        import deal

        contracts = deal.chain(deal.silent, deal.post(lambda x: x>0))

        @contracts
        def f(x):
            return x

        with StringIO() as contracts2:
            @contracts2
            def f(x):
                return x
    """

    tree = astroid.parse(dedent(text))
    print(tree.repr_tree())
    decos = tree.body[-2].decorators.nodes
    returns = tuple(cat for cat, _ in get_contracts(decos))
    assert returns == ('silent', 'post')
