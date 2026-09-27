"""Measure faker-sqlalchemy on two-way, self-referential and overridden relationships."""

from faker import Faker
from faker_sqlalchemy import SqlAlchemyProvider
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship

fake = Faker()
fake.add_provider(SqlAlchemyProvider)

TwoWay = declarative_base()


class User(TwoWay):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class Post(TwoWay):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author = relationship(User, backref="posts")


OneWay = declarative_base()


class Writer(OneWay):
    __tablename__ = "writers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class Article(OneWay):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    writer_id = Column(Integer, ForeignKey("writers.id"), nullable=False)
    writer = relationship(Writer)


SelfRef = declarative_base()


class Category(SelfRef):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"))
    parent = relationship("Category", remote_side=[id])


def raises_recursion(model) -> bool:
    try:
        fake.sqlalchemy_model(model, generate_related=True)
    except RecursionError:
        return True
    return False


def written_writer_id(**options) -> tuple[int, int]:
    engine = create_engine("sqlite://")
    OneWay.metadata.create_all(engine)
    with Session(engine) as session:
        alice = Writer(name="alice")
        session.add(alice)
        session.flush()
        article = fake.sqlalchemy_model(Article, writer_id=alice.id, **options)
        session.add(article)
        session.commit()
        return alice.id, article.writer_id


def main() -> None:
    backref = raises_recursion(Post)
    print(f"generate_related on a backref relationship raises RecursionError: {backref}")
    assert backref

    one_way = raises_recursion(Article)
    print(f"generate_related on a one-way relationship raises RecursionError: {one_way}")
    assert not one_way

    self_ref = raises_recursion(Category)
    print(f"generate_related on a self-referential FK raises RecursionError: {self_ref}")
    assert self_ref

    passed, written = written_writer_id()
    print(f"overrides writer_id={passed} alone: written as {written}")
    assert written == passed

    passed, written = written_writer_id(generate_related=True)
    print(f"overrides writer_id={passed} with generate_related: written as {written}")
    assert written != passed


if __name__ == "__main__":
    main()
