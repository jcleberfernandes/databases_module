// Exercício 13, tarefa 3: validação $jsonSchema na coleção films
db.runCommand({
  collMod: "films",
  validationLevel: "strict",
  validationAction: "error",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      // Só o título é obrigatório: o TEST FILM da operação 8 só tem título.
      // Os outros campos, quando existem, têm de ter o tipo certo.
      required: ["title"],
      properties: {
        title: { bsonType: "string" },
        rating: { enum: ["G", "PG", "PG-13", "R", "NC-17"] },
        length: { bsonType: "int", minimum: 1, maximum: 999 },
        rental_rate: { bsonType: "decimal" },
        categories: { bsonType: "array", items: { bsonType: "string" } },
        actors: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["actor_id", "name"],
            properties: {
              actor_id: { bsonType: "int" },
              name: { bsonType: "string" }
            }
          }
        }
      }
    }
  }
});
print("validador aplicado a films");

function tryInsert(label, doc) {
  try {
    db.films.insertOne(doc);
    print(`${label}: ACEITE (não devia)`);
  } catch (e) {
    const rule = e.errInfo.details.schemaRulesNotSatisfied[0];
    const prop = rule.propertiesNotSatisfied[0];
    print(`${label}: REJEITADO -> "${e.message}" (code ${e.code}) | campo "${prop.propertyName}": ` +
          JSON.stringify(prop.details));
  }
}

tryInsert('rating: "XXX"', { _id: 9001, title: "BAD RATING", rating: "XXX", length: 90 });
tryInsert('length: "long"', { _id: 9002, title: "BAD LENGTH", rating: "PG", length: "long" });
