// Exercício 14: 4 pipelines de agregação (mongosh, base pagila_docs)
// films e rentals carregados de uma cópia nova do Pagila (load.py do exercício 13, com as coleções apagadas antes).

function show(label, docs, n = 3) {
  print(`\n===== ${label}: ${docs.length} documentos`);
  docs.slice(0, n).forEach(d => printjson(d));
}

// 1. Receita por categoria por mês em 2025 (por rental_date), a partir de rentals
const revenue = db.rentals.aggregate([
  { $match: { rental_date: { $gte: ISODate("2025-01-01"), $lt: ISODate("2026-01-01") } } },
  { $unwind: "$categories" },               // um filme com 3 categorias conta nas 3
  { $group: {
      _id: { category: "$categories", month: { $dateTrunc: { date: "$rental_date", unit: "month" } } },
      revenue: { $sum: "$amount" }
  } },
  { $project: { _id: 0, category: "$_id.category",
                month: { $dateToString: { date: "$_id.month", format: "%Y-%m" } },
                revenue: 1 } },
  { $sort: { category: 1, month: 1 } }
]).toArray();
show("1. receita por categoria por mês (2025)", revenue);
printjson(revenue.find(d => d.category === "Action" && d.month === "2025-01"));

// 2. O(s) ator(es) com mais filmes em cada categoria, com empates
const topActors = db.films.aggregate([
  { $unwind: "$categories" },
  { $unwind: "$actors" },
  { $group: { _id: { category: "$categories", actor_id: "$actors.actor_id" },
              name: { $first: "$actors.name" }, films: { $sum: 1 } } },
  { $group: { _id: "$_id.category", max: { $max: "$films" },
              actors: { $push: { actor_id: "$_id.actor_id", name: "$name", films: "$films" } } } },
  { $project: {
      _id: 0, category: "$_id", films: "$max",
      // só os que têm o máximo: assim os empates entram todos
      actors: { $map: {
        input: { $sortArray: { input: { $filter: { input: "$actors", cond: { $eq: ["$$this.films", "$max"] } } },
                               sortBy: { actor_id: 1 } } },
        in: { actor_id: "$$this.actor_id", name: "$$this.name" } } }
  } },
  { $sort: { category: 1 } }
]).toArray();
show("2. ator com mais filmes por categoria", topActors);
print("total de atores:", topActors.reduce((n, d) => n + d.actors.length, 0));

// 3. Distribuição das durações com $bucket
const lengths = db.films.aggregate([
  { $bucket: { groupBy: "$length", boundaries: [0, 60, 90, 120, 150, 186], default: "outros",
               output: { films: { $sum: 1 } } } }
]).toArray();
show("3. filmes por duração ($bucket)", lengths, 10);

// 4. $facet: totais, filmes por rating e os 5 mais longos
const summary = db.films.aggregate([
  { $facet: {
      totals: [ { $group: { _id: null, films: { $sum: 1 }, avg_rental_rate: { $avg: "$rental_rate" } } },
                { $project: { _id: 0, films: 1, avg_rental_rate: { $round: ["$avg_rental_rate", 2] } } } ],
      by_rating: [ { $group: { _id: "$rating", films: { $sum: 1 } } },
                   { $project: { _id: 0, rating: "$_id", films: 1 } },
                   { $sort: { rating: 1 } } ],
      longest: [ { $sort: { length: -1, title: 1 } }, { $limit: 5 },
                 { $project: { _id: 0, title: 1, length: 1 } } ]
  } }
]).toArray();
show("4. $facet", summary);
