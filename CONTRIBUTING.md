# Contributing

## Co-ordinator

Oskar Jarczyk (`oskar.jarczyk@gmail.com`)

## Adding features or fixing bugs

* Fork the repo
* Check out a feature or bug branch
* Add your changes
* Update README when needed
* Add an entry under `## [Unreleased]` in `CHANGELOG.md`
* Submit a pull request to upstream repo
* Add description of your changes
* Ensure tests are passing
* Ensure branch is mergeable

## Development setup

```
pip install -e '.[dev]'
```

## Testing

* Please make sure `pytest` passes fully
* The fast, offline tests run with a plain `pytest`
* Tests that need Redis and a DBpedia download are marked `integration` and only
  run with `pytest --run-integration`. Easiest way to get a Redis for them:
  `docker compose up -d redis`

## What is wanted at the moment

* Check "Issues" section for some job for you
* I'm looking for people who would check the SKOS dataset of their native language and write an appropriate unit test
