"""Measure what polyfactory gives on a User <- Post <- Comment schema, next to seedgraph."""

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from sqlalchemy import ForeignKey, create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from seedgraph import seed

RUNS = 100


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    posts: Mapped[list["Post"]] = relationship(back_populates="author")


class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    subtitle: Mapped[str | None]
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped[User] = relationship(back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship(back_populates="post")


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str]
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"))
    post: Mapped[Post] = relationship(back_populates="comments")


class PostFactory(SQLAlchemyFactory[Post]):
    __set_relationships__ = True


class PostWithoutKeysFactory(SQLAlchemyFactory[Post]):
    __set_primary_key__ = False


class UserWithoutKeysFactory(SQLAlchemyFactory[User]):
    __set_primary_key__ = False


class CommentWithoutKeysFactory(SQLAlchemyFactory[Comment]):
    __set_primary_key__ = False


def new_session() -> Session:
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enforce_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return Session(engine)


def failed_runs(write) -> int:
    failures = 0
    for _ in range(RUNS):
        with new_session() as session:
            try:
                write(session)
                session.commit()
            except IntegrityError:
                failures += 1
    return failures


def links_hold_once_written() -> bool:
    while True:
        with new_session() as session:
            posts = PostFactory.batch(5)
            session.add_all(posts)
            try:
                session.commit()
            except IntegrityError:
                continue
            return all(post.author_id == post.author.id for post in posts)


def main() -> None:
    built = PostFactory.build()
    print(f"in memory, before any write: author_id={built.author_id}, author.id={built.author.id}")
    assert built.author_id != built.author.id

    print(f"once written, default factory: every post.author_id equals post.author.id: {links_hold_once_written()}")
    assert links_hold_once_written()

    for count in (50, 100, 200):
        failures = failed_runs(lambda session: session.add_all(PostFactory.batch(count)))
        print(f"polyfactory, {count} posts: {failures}/{RUNS} runs fail with IntegrityError")
    assert failed_runs(lambda session: session.add_all(PostFactory.batch(200))) > RUNS * 0.9

    one_line_fix = failed_runs(lambda session: session.add_all(PostWithoutKeysFactory.batch(200)))
    print(f"polyfactory with __set_primary_key__ = False, 200 posts: {one_line_fix}/{RUNS} runs fail")
    assert one_line_fix == 0

    with new_session() as session:
        users = [
            UserWithoutKeysFactory.build(
                posts=[PostWithoutKeysFactory.build(comments=CommentWithoutKeysFactory.batch(5)) for _ in range(2)]
            )
            for _ in range(3)
        ]
        session.add_all(users)
        session.commit()
        rows = [session.scalar(select(func.count()).select_from(model)) for model in (User, Post, Comment)]
        per_user = [len(user.posts) for user in users]
        per_post = [len(post.comments) for user in users for post in user.posts]
        linked = all(post.author_id == user.id for user in users for post in user.posts)
    print(f"polyfactory built top-down, 3 x 2 x 5: rows {rows}, posts per user {per_user}, comments per post {per_post}, links right: {linked}")
    assert rows == [3, 6, 30] and per_user == [2, 2, 2] and per_post == [5] * 6 and linked

    seeded = failed_runs(lambda session: seed(session, User, user=50, post=4, post__comment=1))
    print(f"seedgraph, 50 users x 4 posts: {seeded}/{RUNS} runs fail")
    assert seeded == 0


if __name__ == "__main__":
    main()
