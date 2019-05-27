import click.testing

from cfgrib import __main__


def test_cfgrib_cli_selfcheck():
    runner = click.testing.CliRunner()

    res = runner.invoke(__main__.cfgrib_cli, ['selfcheck'])

    assert res.exit_code == 0
    assert 'Your system is ready.' in res.output

    res = runner.invoke(__main__.cfgrib_cli, ['non-existent-command'])
    assert res.exit_code == 2
