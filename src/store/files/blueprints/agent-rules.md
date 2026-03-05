# Blueprints — Agent Behavior Rules

These rules govern how AI agents interact with the Blueprints domain. They ensure generated output is valid, safe, and consistent.

## Rules

1. **Schema integrity** — Never produce output that would break schema name stability. Existing schema names are immutable. New fields get auto-generated schema names from display names.

2. **Validation compliance** — All generated payloads must satisfy the validation rules defined for each domain part. Verify constraints before producing output.

3. **Tenant isolation** — Always assume operations are scoped to a single tenant. Never reference entities across tenant boundaries.

4. **Concurrency safety** — Updates require the current eTag. Acknowledge and handle version conflicts.

5. **Domain accuracy** — Use the correct field types based on semantic meaning. Follow the type mapping:
   - Text → `String`
   - Number → `Number`
   - Yes/No → `Boolean`
   - Date and Time → `DateTime`
   - File → `File`
   - Reference → `Identifier`
   - Group → `Object`
   - List → `Array`

6. **Completeness** — Always generate a description for entities. Always add meaningful tags for categorization.

7. **Constraint awareness** — Know and respect all limits (field counts, nesting depth, name lengths, reserved words). If a user request would violate a constraint, explain the issue and suggest an alternative.

8. **Semantic quality** — Entity names, field names, and descriptions should be clear enough for downstream AI agents to interpret correctly. Prefer descriptive names over abbreviations.
