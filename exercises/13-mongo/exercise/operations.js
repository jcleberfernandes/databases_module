// Exercício 13, tarefa 2: 8 operações (mongosh, base pagila_docs)
// Correr logo depois do load.py (as operações 6, 7 e 8 alteram os dados).

print("1. PG-13 com mais de 120 minutos");
print(db.films.countDocuments({ rating: "PG-13", length: { $gt: 120 } }));

print("2. filmes do ator 1");
print(db.films.countDocuments({ "actors.actor_id": 1 }));

print("3. Horror com rental_rate 0.99");
print(db.films.countDocuments({ categories: "Horror", rental_rate: NumberDecimal("0.99") }));

print("4. clientes com um aluguer por devolver em recent_rentals ($elemMatch)");
print(db.customers.countDocuments({ recent_rentals: { $elemMatch: { return_date: null } } }));

print("5. cliente 1: nome e títulos de recent_rentals (projeção)");
printjson(db.customers.findOne(
  { _id: 1 },
  { _id: 0, first_name: 1, last_name: 1, "recent_rentals.title": 1 }
));

print("6. +0.50 no rental_rate dos NC-17 com menos de 60 minutos");
printjson(db.films.updateMany(
  { rating: "NC-17", length: { $lt: 60 } },
  { $inc: { rental_rate: NumberDecimal("0.50") } }
));

print("7. novo aluguer à frente de recent_rentals do cliente 1, ficando só 10");
printjson(db.customers.updateOne(
  { _id: 1 },
  { $push: { recent_rentals: {
      $each: [{ rental_id: 999999, film_id: 1, title: "ACADEMY DINOSAUR",
                rental_date: new Date("2026-07-31T10:00:00Z"), return_date: null }],
      $position: 0,
      $slice: 10
  } } }
));
const c1 = db.customers.findOne({ _id: 1 });
print("recent_rentals:", c1.recent_rentals.length, "| primeiro:", c1.recent_rentals[0].rental_id, c1.recent_rentals[0].title);

print("8. upsert com $setOnInsert, 2 vezes");
for (let run = 1; run <= 2; run++) {
  const r = db.films.updateOne(
    { _id: 1001 },
    { $setOnInsert: { title: "TEST FILM" } },
    { upsert: true }
  );
  print(`execução ${run}: matched=${r.matchedCount} modified=${r.modifiedCount} upserted=${r.upsertedCount}`);
}
