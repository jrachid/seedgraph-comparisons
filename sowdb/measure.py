"""Ask sowdb for 6 posts over 3 users on a disposable PostgreSQL and count the posts each user gets."""

import subprocess
import time

CONTAINER = "sowdb-compare"
DSN = "postgresql+psycopg://postgres:pw@localhost:55432/postgres"
SCHEMA = """
CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE posts (id SERIAL PRIMARY KEY, title TEXT NOT NULL, author_id INT NOT NULL REFERENCES users(id));
"""


def psql(sql: str) -> str:
    return subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", "postgres", "-At", "-c", sql], check=True, capture_output=True, text=True
    ).stdout.strip()


def posts_per_user(seed: int) -> list[int]:
    subprocess.run(
        ["sowdb", "generate", "--dsn", DSN, "--rows-for", "users=3", "--rows-for", "posts=6", "--seed", str(seed), "--truncate"],
        check=True, capture_output=True,
    )
    counts = psql("SELECT COUNT(p.id) FROM users u LEFT JOIN posts p ON p.author_id = u.id GROUP BY u.id ORDER BY u.id")
    return sorted((int(count) for count in counts.splitlines()), reverse=True)


def main() -> None:
    subprocess.run(
        ["docker", "run", "-d", "--rm", "--name", CONTAINER, "-e", "POSTGRES_PASSWORD=pw", "-p", "55432:5432", "postgres:16-alpine"],
        check=True, capture_output=True,
    )
    try:
        while subprocess.run(["docker", "exec", CONTAINER, "pg_isready", "-U", "postgres"], capture_output=True).returncode:
            time.sleep(1)
        time.sleep(2)
        psql(SCHEMA)
        shapes = {seed: posts_per_user(seed) for seed in range(1, 11)}
        for seed, shape in shapes.items():
            print(f"seed {seed}: posts per user {shape}")
        even = sum(shape == [2, 2, 2] for shape in shapes.values())
        print(f"runs where each user got exactly 2 posts: {even}/10")
        assert even < 10
    finally:
        subprocess.run(["docker", "stop", CONTAINER], capture_output=True)


if __name__ == "__main__":
    main()
