"""As 5 tabelas do Pagila que a API usa. Só as colunas necessárias."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    # Os mesmos tipos que o Pagila usa, para o autogenerate não ver diferenças falsas
    type_annotation_map = {str: Text(), datetime: DateTime(timezone=True)}


def fk(column: str) -> ForeignKey:
    # As FKs do Pagila têm ON UPDATE CASCADE ON DELETE RESTRICT
    return ForeignKey(column, onupdate="CASCADE", ondelete="RESTRICT")


class Customer(Base):
    __tablename__ = "customer"

    customer_id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int]
    first_name: Mapped[str]
    last_name: Mapped[str]
    email: Mapped[str | None]
    # Coluna nova (migração 0002)
    loyalty_points: Mapped[int] = mapped_column(server_default=text("0"))


class Film(Base):
    __tablename__ = "film"

    film_id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    rental_duration: Mapped[int] = mapped_column(SmallInteger)


class Staff(Base):
    __tablename__ = "staff"

    staff_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    store_id: Mapped[int]


class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id: Mapped[int] = mapped_column(primary_key=True)
    film_id: Mapped[int] = mapped_column(fk("film.film_id"))
    store_id: Mapped[int]
    film: Mapped[Film] = relationship()


class Rental(Base):
    __tablename__ = "rental"
    # Índice da migração 0003: no máximo um aluguer aberto por cópia
    __table_args__ = (
        Index("rental_one_open_per_copy", "inventory_id", unique=True,
              postgresql_where=text("return_date IS NULL")),
    )

    rental_id: Mapped[int] = mapped_column(primary_key=True)
    rental_date: Mapped[datetime]
    inventory_id: Mapped[int] = mapped_column(fk("inventory.inventory_id"))
    customer_id: Mapped[int] = mapped_column(fk("customer.customer_id"))
    return_date: Mapped[datetime | None]
    staff_id: Mapped[int] = mapped_column(fk("staff.staff_id"))
    customer: Mapped[Customer] = relationship()
    inventory: Mapped[Inventory] = relationship()
