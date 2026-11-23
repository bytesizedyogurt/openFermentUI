-- H5: a concept graph as a build would leave it, written by hand into a bh_h5_ test database (no model).
-- The shared chunk is the passage of 'A secret paper' (B pastes the same text, so B holds it too); the A-only
-- chunk is the passage of 'A graph note', which A alone holds.
SELECT c.id AS shared, c.document_id AS shareddoc FROM sci_rag.chunks c JOIN sci_rag.documents d ON d.id = c.document_id
 WHERE d.title = 'A secret paper' \gset
SELECT c.id AS aonly, c.document_id AS aonlydoc FROM sci_rag.chunks c JOIN sci_rag.documents d ON d.id = c.document_id
 WHERE d.title = 'A graph note' \gset
UPDATE sci_rag.chunks SET graph_extracted_at = now() WHERE id IN (:'shared', :'aonly');
INSERT INTO sci_rag.kg_entities (id, name, entity_type, description, aliases, document_ids, chunk_ids) VALUES
 ('h5e1', 'RACEMARKZQ', 'organism', 'A-only entity, described from A''s private note', '{}', ARRAY[:'aonlydoc'], ARRAY[:'aonly']),
 ('h5e2', 'xylose', 'chemical', 'xylose described from A''s private note and the shared paper', '{}', ARRAY[:'shareddoc', :'aonlydoc'], ARRAY[:'shared', :'aonly']),
 ('h5e3', 'Zymomonas xylofermentans', 'organism', 'described from the shared paper alone', '{}', ARRAY[:'shareddoc'], ARRAY[:'shared']),
 ('h5e4', 'ethanol', 'chemical', 'ethanol described from the shared paper', '{}', ARRAY[:'shareddoc'], ARRAY[:'shared']),
 ('h5e5', 'private race note', 'process', 'A-only name', '{}', ARRAY[:'aonlydoc'], ARRAY[:'aonly'])
ON CONFLICT DO NOTHING;
INSERT INTO sci_rag.kg_relationships (id, source_entity_id, target_entity_id, relation_type, evidence, confidence, document_id, chunk_id) VALUES
 ('h5r1', 'h5e3', 'h5e4', 'produces', 'produced ethanol at a titre of 41 g/L', 0.9, :'shareddoc', :'shared'),
 ('h5r2', 'h5e3', 'h5e1', 'related_to', 'RACEMARKZQ appears in A''s private race note', 0.9, :'aonlydoc', :'aonly'),
 ('h5r3', 'h5e2', 'h5e5', 'related_to', 'xylose in a private race note', 0.9, :'shareddoc', :'shared'),
 ('h5r4', 'h5e3', 'h5e2', 'consumes', 'an A-only quote naming SECRET-QUOTE-A', 0.8, :'shareddoc', :'shared')
ON CONFLICT DO NOTHING;
