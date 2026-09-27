"""Build 3 users x 2 posts x 5 comments with sqlseed, through per-table counts and the coverage strategy."""

import sqlite3
import tempfile
from pathlib import Path

import sqlseed

SCHEMA = """
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT NOT NULL, author_id INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE comments (id INTEGER PRIMARY KEY, body TEXT NOT NULL, post_id INTEGER NOT NULL REFERENCES posts(id));
"""


def covering(table: str) -> dict:
    return {"generator": "foreign_key", "params": {"ref_table": table, "ref_column": "id", "strategy": "coverage"}}


def children_per_parent(database: Path, sql: str) -> list[int]:
    with sqlite3.connect(database) as connection:
        return [count for (count,) in connection.execute(sql)]


def main() -> None:
    database = Path(tempfile.mkdtemp()) / "shape.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA)
    sqlseed.fill(str(database), table="users", count=3, provider="base", seed=1)
    sqlseed.fill(str(database), table="posts", count=6, columns={"author_id": covering("users")}, provider="base", seed=1)
    sqlseed.fill(str(database), table="comments", count=30, columns={"post_id": covering("posts")}, provider="base", seed=1)

    posts = children_per_parent(database, "SELECT COUNT(*) FROM posts GROUP BY author_id ORDER BY author_id")
    comments = children_per_parent(database, "SELECT COUNT(*) FROM comments GROUP BY post_id ORDER BY post_id")
    print("posts per user:", posts)
    print("comments per post:", comments)
    assert posts == [2, 2, 2]
    assert comments == [5] * 6


if __name__ == "__main__":
    main()
