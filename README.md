# runescape-plugin

NOTE: this plugin was never updated and is not currently in use, so it's being archived for now.

Plugin for Seabird to get Old-School Runescape player information.

## Commands
Level information:
```
<prefix>rlvl <server> <skill>[, <skill>...]
```

Skill rank information:
```
<prefix>rrank <server> <skill>[, <skill>...]
```

Experience information:
```
<prefix>rexp <server> <skill>[, <skill>...]
```

## Configuration

Configuration is passed via environment variables. You can also set values with a `.env` file.

Expected values:
`HOST_PORT`: host and port to connect to
`TOKEN`: your core authentication token

## Usage

```
$ pipenv shell
$ pipenv install

# Set configuration options
$ $EDITOR .env
$ cd runescape-plugin
$ python3 .
```

## License

[MIT](LICENSE)
