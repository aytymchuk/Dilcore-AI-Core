# Field Definitions — API Reference

Technical reference for field definitions within entity types. Used by the Generate agent to produce valid field payloads.

## Field Structure

```json
{
  "schemaName": "shippingAddress",
  "displayName": "Shipping Address",
  "type": "Object",
  "fields": [
    {
      "schemaName": "street",
      "displayName": "Street",
      "type": "String",
      "fields": null
    },
    {
      "schemaName": "city",
      "displayName": "City",
      "type": "String",
      "fields": null
    }
  ]
}
```

## Property Reference

| Property | Type | Required on Create | Required on Update | Description |
|---|---|---|---|---|
| `schemaName` | string | No | No (recommended for existing fields) | Immutable storage identifier. Auto-generated from `displayName` if omitted. Include on updates to preserve field identity. |
| `displayName` | string | Yes | Yes | Human-readable name. 2–128 characters, at least one alphanumeric character. |
| `type` | string | Yes | Yes | Data type. See Field Types below. |
| `fields` | array or null | Only for Object/Array | Only for Object/Array | Nested field definitions. Required (min 1) for complex types. Must be null or absent for primitives. |

## Field Types

| API Type | Category | Nested Fields | Business meaning |
|---|---|---|---|
| `String` | Primitive | No | Text: names, labels, descriptions, emails, URLs, addresses, statuses |
| `Number` | Primitive | No | Numeric: quantities, amounts, prices, percentages, scores |
| `Boolean` | Primitive | No | Binary: yes/no flags, toggles |
| `DateTime` | Primitive | No | Temporal: dates, timestamps, deadlines |
| `File` | Primitive | No | Attachments: images, documents, uploads |
| `Identifier` | Primitive | No | References: links to other entity instances or external IDs |
| `Object` | Complex | Yes (min 1) | Group: bundles related sub-fields into one unit |
| `Array` | Complex | Yes (min 1) | List: repeating structured items |

## Business-to-API Type Mapping

When users describe fields in business terms, map to API types:

| User says | API type |
|---|---|
| Text, Name, Label, Email, Address, Status | `String` |
| Amount, Price, Quantity, Score, Percentage | `Number` |
| Yes/No, Active, Verified, Flag | `Boolean` |
| Date, Time, Deadline, Schedule | `DateTime` |
| Attachment, Upload, Document, Image | `File` |
| Reference, Link to, Belongs to | `Identifier` |
| Address (with parts), Contact Info, grouped fields | `Object` |
| Line Items, Phone Numbers, repeating entries | `Array` |

## Validation Constraints

| Constraint | Value |
|---|---|
| Display name length | 2–128 characters |
| Nested fields per level | Max 50 |
| Maximum nesting depth | 5 levels |
| Schema name duplicates | Not allowed within the same nesting level |
| Schema name reserved words | Rejected at any depth |
| Object/Array fields | Must have at least 1 nested field |
| Primitive fields | Must not have nested fields |

## Schema Name Rules

- Auto-generated from `displayName` using camelCase conversion
- Non-alphanumeric characters treated as word separators
- Immutable once assigned
- On updates, include existing `schemaName` to preserve identity
- Omitting `schemaName` on update generates a new one (effectively a new field)

### Reserved Schema Names

Cannot be used at any nesting depth:

`id`, `eTag`, `createdAt`, `updatedAt`, `isDeleted`, `tenantId`, `schemaName`, `type`
