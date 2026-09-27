# seedgraph comparisons

The claims that the [seedgraph](https://github.com/jrachid/seedgraph) README makes about other libraries, each measured by a script you can run. Every library lives in its own folder with its own pinned environment, since they need different SQLAlchemy versions.

## Run a measurement

Requires [uv](https://docs.astral.sh/uv/). The `sowdb` one also needs Docker, to start a disposable PostgreSQL.

```bash
cd polyfactory && uv run measure.py
```

Each script prints what it measured and asserts the claim: if a new release changes the behaviour, the script fails and the seedgraph README needs a correction.

## Results — 27 September 2026, Python 3.12, SQLAlchemy 2.1.1 unless stated

| Library | Measured | Script |
| --- | --- | --- |
| polyfactory 3.3.0 | In memory, `post.author_id` disagrees with `post.author.id`; once written, SQLAlchemy syncs them and every link is right. Primary keys are drawn at random, so writing 50 posts fails with `IntegrityError` in 27 to 36 runs out of 100, 100 posts in 78 to 81, 200 posts in every run. With `id = Ignore()` on a factory per model: 0 failures, and 6 posts get 6 distinct authors. seedgraph, 50 users × 4 posts: 0 failures in 100 runs. | [`polyfactory/measure.py`](polyfactory/measure.py) |
| faker-sqlalchemy 0.10.2208140 (SQLAlchemy 1.4.54) | With `generate_related=True`: `RecursionError` on a `backref` relationship and on a self-referential FK, none on a one-way relationship. A foreign key passed alone in overrides is kept; combined with `generate_related`, it is replaced by a generated parent. | [`faker-sqlalchemy/measure.py`](faker-sqlalchemy/measure.py) |
| sqlalchemyseed 2.6.1 | Loaders for CSV, JSON and YAML; no import of faker, random or mimesis: it writes the data you give it. | [`sqlalchemyseed/measure.py`](sqlalchemyseed/measure.py) |
| sqlseed 0.2.4 | One count per table; with the `coverage` strategy, 6 posts over 3 users give exactly 2 each and 30 comments over 6 posts exactly 5 each. | [`sqlseed/measure.py`](sqlseed/measure.py) |
| sowdb 0.3.0 (PostgreSQL 16) | One count per table; foreign keys draw a random parent. Over seeds 1 to 10, 6 posts over 3 users came out as 2, 2, 2 once, and one run left a user with none. | [`sowdb/measure.py`](sowdb/measure.py) |
