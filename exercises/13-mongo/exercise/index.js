// Exercício 13, tarefa 4: explain antes e depois do índice em actors.actor_id
function summary(label) {
  const e = db.films.find({ "actors.actor_id": 1 }).explain("executionStats");
  let stage = e.queryPlanner.winningPlan;
  const stages = [];
  while (stage) { stages.push(stage.stage); stage = stage.inputStage; }
  const s = e.executionStats;
  print(`${label}: stage=${stages.join(" <- ")} totalDocsExamined=${s.totalDocsExamined} ` +
        `totalKeysExamined=${s.totalKeysExamined} nReturned=${s.nReturned} ms=${s.executionTimeMillis}`);
}

// para poder correr outra vez: apaga o índice se já existir
if (db.films.getIndexes().some(i => i.name === "actors.actor_id_1")) db.films.dropIndex("actors.actor_id_1");
summary("ANTES ");
db.films.createIndex({ "actors.actor_id": 1 });
summary("DEPOIS");
