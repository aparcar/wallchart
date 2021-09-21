def test_create_tables(app):
    runner = app.test_cli_runner()

    result = runner.invoke(args=["db", "create-tables"])
    assert "Done" in result.output
