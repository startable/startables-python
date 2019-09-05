from pyscheme import parse_expression, make_root_environment


def test_main_use_case():
    root = make_root_environment()
    root.define('zFoo', parse_expression('(+ aPar 7)'))

    root.define('aPar', 3)
    assert root.evaluate(parse_expression('(- zFoo 1)')) == 9

    root.define('aPar', 4)
    assert root.evaluate(parse_expression('zFoo')) == 11
    assert root.evaluate(parse_expression('zFoo - 1')) == 10

# TODO: Test notifications
