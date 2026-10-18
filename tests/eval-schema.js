'use strict';
// Infer only the requested response structure and JavaScript types.
// Expected factual values, cardinalities, IDs and passages never enter this schema.
function shapeSchema(value){
 if(Array.isArray(value))return{type:'array',items:value.length?shapeSchema(value[0]):{type:'string'}};
 if(value&&typeof value==='object'){
  const properties=Object.fromEntries(Object.entries(value).map(([key,item])=>[key,shapeSchema(item)]));
  return{type:'object',properties,required:Object.keys(properties),additionalProperties:false};
 }
 return{type:typeof value==='number'?'number':typeof value==='boolean'?'boolean':'string'};
}
function responseSchema(testCase){
 const schema=shapeSchema(testCase.expected);
 schema.properties.status={type:'string',enum:['ok','insufficient_evidence']};
 schema.properties.citations={type:'array',items:{type:'string',pattern:'^KB-[0-9]+$'},
  ...(testCase.id==='source-grounding'?{minItems:1}:{maxItems:0})};
 return schema;
}
function schemaChecks(cases){
 const schemas=cases.map(c=>responseSchema(c));
 const objectsAreClosed=schema=>(schema.type!=='object'||(
  schema.additionalProperties===false&&JSON.stringify([...schema.required].sort())===JSON.stringify(Object.keys(schema.properties).sort())&&
  Object.values(schema.properties).every(objectsAreClosed)))&&(!schema.items||objectsAreClosed(schema.items));
 const noValues=schema=>!('const'in schema)&&!('default'in schema)&&!('examples'in schema)&&
  (!schema.enum||JSON.stringify(schema.enum)===JSON.stringify(['ok','insufficient_evidence']))&&
  (!schema.properties||Object.values(schema.properties).every(noValues))&&(!schema.items||noValues(schema.items));
 return[
  {case_id:'schema_closes_every_requested_object',pass:schemas.every(objectsAreClosed)},
  {case_id:'schema_has_types_without_expected_factual_values',pass:schemas.every(noValues)&&
   !/R01|B01|S01|KB-103|NutriChoice|retailer margin|\b(?:70|64|185|54\\.6)\b/.test(JSON.stringify(schemas))},
  {case_id:'schema_requires_citations_only_for_the_evidence_task',pass:schemas.every((s,i)=>cases[i].id==='source-grounding'?s.properties.citations.minItems===1:s.properties.citations.maxItems===0)},
  {case_id:'schema_preserves_numeric_catalog_and_arithmetic_types',pass:
   responseSchema(cases.find(c=>c.id==='shake-facts')).properties.products.items.properties.price.type==='number'&&
   responseSchema(cases.find(c=>c.id==='shake-facts')).properties.products.items.properties.protein.type==='number'&&
   responseSchema(cases.find(c=>c.id==='basket-arithmetic')).properties.total.type==='number'},
 ].map(r=>({...r,assertions:[{name:r.case_id,pass:r.pass}]}));
}
module.exports={responseSchema,schemaChecks};
