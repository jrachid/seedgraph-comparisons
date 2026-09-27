"""Measure what polyfactory gives on a User <- Post <- Comment schema, next to seedgraph."""

from polyfactory import Ignore
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from sqlalchemy import ForeignKey, create_engine, event
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


def register_the_workaround() -> type[SQLAlchemyFactory[Post]]:
    """Declare one factory per model with its keys ignored; the User and Comment ones become the defaults."""

    class UserWithoutIdFactory(SQLAlchemyFactory[User]):
        __set_as_default_factory_for_type__ = True
        id = Ignore()

    class CommentWithoutIdFactory(SQLAlchemyFactory[Comment]):
        __set_as_default_factory_for_type__ = True
        id = Ignore()
        post_id = Ignore()

    class PostWithoutIdFactory(SQLAlchemyFactory[Post]):
        __set_relationships__ = True
        id = Ignore()
        author_id = Ignore()

    return PostWithoutIdFactory


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

    PostWithoutIdFactory = register_the_workaround()
    workaround = failed_runs(lambda session: session.add_all(PostWithoutIdFactory.batch(200)))
    print(f"polyfactory with id = Ignore() on every factory, 200 posts: {workaround}/{RUNS} runs fail")
    assert workaround == 0
    with new_session() as session:
        posts = PostWithoutIdFactory.batch(6)
        session.add_all(posts)
        session.commit()
        authors = len({post.author_id for post in posts})
    print(f"polyfactory, 6 posts: {authors} distinct authors")
    assert authors == 6

    seeded = failed_runs(lambda session: seed(session, User, user=50, post=4, post__comment=1))
    print(f"seedgraph, 50 users x 4 posts: {seeded}/{RUNS} runs fail")
    assert seeded == 0


if __name__ == "__main__":
    main()
