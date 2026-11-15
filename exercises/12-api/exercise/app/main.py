from datetime import date, datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.db import get_session
from app.models import Customer, Film, Inventory, Rental

app = FastAPI(title="Exercício 12: alugueres")

MAX_ATTEMPTS = 3


class NewRental(BaseModel):
    customer_id: int
    film_id: int
    store_id: int
    staff_id: int


def is_open_copy_conflict(error: IntegrityError) -> bool:
    """True se o INSERT falhou por causa do índice rental_one_open_per_copy."""
    return getattr(error.orig.diag, "constraint_name", None) == "rental_one_open_per_copy"


@app.post("/rentals", status_code=201)
def create_rental(body: NewRental, session: Session = Depends(get_session)):
    for _ in range(MAX_ATTEMPTS):
        try:
            with session.begin():
                if session.get(Customer, body.customer_id) is None:
                    raise HTTPException(404, "Customer not found")
                if session.get(Film, body.film_id) is None:
                    raise HTTPException(404, "Film not found")

                # Uma cópia do filme nesta loja sem aluguer aberto.
                # skip_locked: as cópias que outro pedido já bloqueou são saltadas em vez de esperar.
                has_open_rental = exists().where(
                    Rental.inventory_id == Inventory.inventory_id, Rental.return_date.is_(None)
                )
                copy = session.scalars(
                    select(Inventory)
                    .where(Inventory.film_id == body.film_id, Inventory.store_id == body.store_id, ~has_open_rental)
                    .order_by(Inventory.inventory_id)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                ).first()
                if copy is None:
                    raise HTTPException(409, "No copy available")

                rental = Rental(
                    rental_date=datetime.now(timezone.utc),
                    inventory_id=copy.inventory_id,
                    customer_id=body.customer_id,
                    staff_id=body.staff_id,
                )
                session.add(rental)
                session.flush()  # o INSERT corre aqui; se violar o índice, dá IntegrityError
            return {"rental_id": rental.rental_id, "inventory_id": rental.inventory_id}
        except IntegrityError as error:
            # Outro pedido alugou a mesma cópia entre a nossa leitura e o nosso INSERT:
            # a transação já foi desfeita pelo session.begin(); tenta outra vez.
            if not is_open_copy_conflict(error):
                raise
    raise HTTPException(409, "No copy available")


@app.post("/rentals/{rental_id}/return")
def return_rental(rental_id: int, session: Session = Depends(get_session)):
    with session.begin():
        rental = session.scalars(
            select(Rental).where(Rental.rental_id == rental_id).with_for_update()
        ).one_or_none()
        if rental is None:
            raise HTTPException(404, "Rental not found")
        if rental.return_date is not None:
            raise HTTPException(409, "Rental already returned")
        rental.return_date = datetime.now(timezone.utc)
    return {"rental_id": rental.rental_id, "return_date": rental.return_date}


@app.get("/rentals/overdue")
def overdue_rentals(as_of: date = Query(...), session: Session = Depends(get_session)):
    # due_date = rental_date + rental_duration dias
    due_date = Rental.rental_date + func.make_interval(0, 0, 0, Film.rental_duration)
    stmt = (
        select(Rental, due_date.label("due_date"))
        .join(Rental.inventory)
        .join(Inventory.film)
        # joinedload: cliente, cópia e filme vêm na MESMA query (sem N+1)
        .options(joinedload(Rental.customer), joinedload(Rental.inventory).joinedload(Inventory.film))
        .where(Rental.return_date.is_(None), due_date < as_of)
        .order_by(Rental.rental_date, Rental.rental_id)
    )
    return [
        {
            "rental_id": r.rental_id,
            "rental_date": r.rental_date,
            "due_date": due,
            "customer": {
                "customer_id": r.customer.customer_id,
                "first_name": r.customer.first_name,
                "last_name": r.customer.last_name,
            },
            "film": {"film_id": r.inventory.film.film_id, "title": r.inventory.film.title},
        }
        for r, due in session.execute(stmt)
    ]
