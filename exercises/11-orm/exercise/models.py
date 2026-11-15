"""As 6 tabelas do Pagila do exercício: film, language, actor, film_actor, category, film_category.
Só as colunas que usamos; o SQLAlchemy ignora as outras."""

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from sqlalchemy import Column, ForeignKey, Table, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

load_dotenv()
_root = dotenv_values(Path(__file__).resolve().parents[3] / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or (
    f"postgresql+psycopg://{_root['POSTGRES_USER']}:{_root['POSTGRES_PASSWORD']}@localhost:5432/ex11"
)


def make_engine(echo: bool = True):
    # echo=True escreve no terminal cada SQL que o ORM envia
    return create_engine(DATABASE_URL, echo=echo)


class Base(DeclarativeBase):
    pass


# Tabelas de ligação N:N: só têm as duas chaves
film_actor = Table(
    "film_actor",
    Base.metadata,
    Column("actor_id", ForeignKey("actor.actor_id"), primary_key=True),
    Column("film_id", ForeignKey("film.film_id"), primary_key=True),
)

film_category = Table(
    "film_category",
    Base.metadata,
    Column("film_id", ForeignKey("film.film_id"), primary_key=True),
    Column("category_id", ForeignKey("category.category_id"), primary_key=True),
)


class Language(Base):
    __tablename__ = "language"

    language_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    films: Mapped[list["Film"]] = relationship(back_populates="language")   # 1:N


class Film(Base):
    __tablename__ = "film"

    film_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    length: Mapped[int | None]
    language_id: Mapped[int] = mapped_column(ForeignKey("language.language_id"))
    language: Mapped[Language] = relationship(back_populates="films")                          # N:1
    actors: Mapped[list["Actor"]] = relationship(secondary=film_actor, back_populates="films")  # N:N
    categories: Mapped[list["Category"]] = relationship(secondary=film_category, back_populates="films")


class Actor(Base):
    __tablename__ = "actor"

    actor_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    films: Mapped[list[Film]] = relationship(secondary=film_actor, back_populates="actors")


class Category(Base):
    __tablename__ = "category"

    category_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    films: Mapped[list[Film]] = relationship(secondary=film_category, back_populates="categories")
