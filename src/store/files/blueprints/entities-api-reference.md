# Entity Definitions — API Reference

Technical reference for the Entity Definitions API. Used by the Generate agent to produce valid payloads.

## Base Path

`/blueprints/entity-definitions`

All endpoints require authentication and the `x-tenant` header.

## Operations

| Operation | Method | Path | Description |
|---|---|---|---|
| List | `GET` | `/blueprints/entity-definitions` | Paginated listing with search and filters |
| Get by ID | `GET` | `/blueprints/entity-definitions/{id}` | Retrieve single entity definition |
| Create | `POST` | `/blueprints/entity-definitions` | Define a new entity type |
| Update | `PUT` | `/blueprints/entity-definitions/{id}` | Modify an existing entity type (requires eTag) |
| Delete | `DELETE` | `/blueprints/entity-definitions/{id}` | Permanently remove an entity type |

---

## Entity Definition Structure (Response)

```json
{
  "id": "b7e3f1a2-4c8d-4f2a-9b1e-6d5a3c8f2e1b",
  "eTag": 1,
  "schemaName": "customerOrder",
  "displayName": "Customer Order",
  "description": "Represents a customer purchase order with line items and totals",
  "isAbstract": false,
  "extendsEntityId": null,
  "fields": [
    {
      "schemaName": "orderNumber",
      "displayName": "Order Number",
      "type": "String",
      "fields": null
    },
    {
      "schemaName": "totalAmount",
      "displayName": "Total Amount",
      "type": "Number",
      "fields": null
    },
    {
      "schemaName": "lineItems",
      "displayName": "Line Items",
      "type": "Array",
      "fields": [
        {
          "schemaName": "productName",
          "displayName": "Product Name",
          "type": "String",
          "fields": null
        },
        {
          "schemaName": "quantity",
          "displayName": "Quantity",
          "type": "Number",
          "fields": null
        }
      ]
    }
  ],
  "tags": ["orders", "crm"],
  "createdAt": "2026-03-01T12:00:00Z",
  "updatedAt": "2026-03-01T12:00:00Z"
}
```

### Property Reference

| Property | Type | Description |
|---|---|---|
| `id` | GUID | Unique identifier assigned at creation. |
| `eTag` | long | Version counter for optimistic concurrency. Every mutation increments this value. Clients must send the current eTag on updates. |
| `schemaName` | string | Immutable, camelCase storage identifier. Auto-generated from `displayName` at creation. Never changes. |
| `displayName` | string | Human-readable name. 2–128 characters. |
| `description` | string or null | Purpose of this entity type. Max 200 characters. |
| `isAbstract` | boolean | When `true`, entity is a base type meant to be extended, not used directly. |
| `extendsEntityId` | GUID or null | Parent entity definition ID within the same tenant. Child inherits parent's field structure. |
| `fields` | array | Ordered list of field definitions. See fields-api-reference.md. |
| `tags` | array of strings | Free-form labels for categorization. |
| `createdAt` | datetime | UTC timestamp of creation. |
| `updatedAt` | datetime | UTC timestamp of last modification. |

---

## Schema Name Generation

- Non-alphanumeric characters are treated as word separators
- First word is fully lowercased, subsequent words are capitalized (camelCase)

| Display Name | Generated Schema Name |
|---|---|
| Customer Order | `customerOrder` |
| First Name | `firstName` |
| My CRM Entity | `myCrmEntity` |

### Immutability Rules

- Schema names are assigned at creation and **never change**
- On update, fields with a matching `schemaName` preserve their identity
- Only newly added fields (without a `schemaName`) get auto-generated names
- Renaming a `displayName` does not change the `schemaName`

### Reserved Schema Names

Cannot be used as field schema names at any nesting depth:

`id`, `eTag`, `createdAt`, `updatedAt`, `isDeleted`, `tenantId`, `schemaName`, `type`

---

## Validation Constraints

### Entity-Level

| Constraint | Value |
|---|---|
| Display name length | 2–128 characters |
| Display name content | Must contain at least one alphanumeric character |
| Description length | Max 200 characters |
| Top-level fields per entity | Max 100 |
| Tags per entity | Max 20 |
| Tag length | Max 64 characters |
| Tag format | `^[a-zA-Z0-9_-]+$` |
| Schema name uniqueness | Must be unique within the tenant |

### Field-Level

| Constraint | Value |
|---|---|
| Display name length | 2–128 characters |
| Nested fields per level | Max 50 |
| Maximum nesting depth | 5 levels |
| Schema name duplicates | Not allowed within the same nesting level |
| Schema name reserved words | Rejected at any depth |
| Object/Array fields | Must have at least 1 nested field |
| Primitive fields | Must not have nested fields |

---

## Create Entity Definition

**Method:** `POST /blueprints/entity-definitions`

### Request Body

```json
{
  "displayName": "Customer Order",
  "description": "Represents a customer purchase order with line items and totals",
  "isAbstract": false,
  "extendsEntityId": null,
  "fields": [
    {
      "displayName": "Order Number",
      "type": "String"
    },
    {
      "displayName": "Total Amount",
      "type": "Number"
    },
    {
      "displayName": "Line Items",
      "type": "Array",
      "fields": [
        {
          "displayName": "Product Name",
          "type": "String"
        },
        {
          "displayName": "Quantity",
          "type": "Number"
        }
      ]
    }
  ],
  "tags": ["orders", "crm"]
}
```

### Request Properties

| Property | Type | Required | Description |
|---|---|---|---|
| `displayName` | string | Yes | 2–128 chars, at least one alphanumeric character |
| `description` | string | No | Max 200 chars. |
| `isAbstract` | boolean | No | Defaults to `false`. |
| `extendsEntityId` | GUID | No | Parent entity ID. Must exist in the same tenant. |
| `schemaName` | string | No | Custom override for auto-generated schema name. |
| `fields` | array | No | Defaults to empty array. |
| `tags` | array | No | Defaults to empty array. |

### Responses

- **201 Created**: Returns full Entity Definition with `Location` header
- **400 Validation Failed**: See Error Formats
- **409 Conflict**: Schema name already exists in the tenant

### Business Rules

1. Schema name must not already exist in the tenant (409 if duplicate).
2. If `extendsEntityId` is provided, the referenced entity must exist in the same tenant.

---

## Update Entity Definition

**Method:** `PUT /blueprints/entity-definitions/{id}`

### Request Body

```json
{
  "eTag": 1,
  "displayName": "Customer Order v2",
  "description": "Updated description with new priority field",
  "isAbstract": false,
  "fields": [
    {
      "schemaName": "orderNumber",
      "displayName": "Order Number",
      "type": "String"
    },
    {
      "displayName": "Priority",
      "type": "String"
    }
  ],
  "tags": ["orders", "crm", "v2"]
}
```

### Request Properties

| Property | Type | Required | Description |
|---|---|---|---|
| `eTag` | long | Yes | Must match entity's current version. |
| `displayName` | string | No | New display name. Does not change schema name. |
| `description` | string | No | Pass `null` to clear. |
| `isAbstract` | boolean | No | |
| `fields` | array | No | Full replacement of field tree. |
| `tags` | array | No | Full replacement of tags. |

### Field Update Behavior

Full replacement with schema name preservation:
- Fields with a `schemaName` matching an existing field keep that schema name
- Fields without a `schemaName` are new additions with auto-generated names
- Fields absent from the new tree are removed

### Responses

- **200 OK**: Returns updated Entity Definition
- **404 Not Found**: Entity does not exist
- **409 Conflict (eTag mismatch)**: Version conflict

---

## List Entity Definitions

**Method:** `GET /blueprints/entity-definitions`

### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `skip` | int | 0 | Pagination offset |
| `take` | int | 20 | Page size, max 100 |
| `search` | string | — | Full-text search on display name |
| `isAbstract` | boolean | — | Filter abstract/concrete |
| `tags` | string | — | Comma-separated tag filter |

### Response

```json
{
  "items": [ /* array of Entity Definitions */ ],
  "totalCount": 42
}
```

---

## Get Entity Definition

**Method:** `GET /blueprints/entity-definitions/{id}`

- **200 OK**: Returns single Entity Definition
- **404 Not Found**: Does not exist in this tenant

---

## Delete Entity Definition

**Method:** `DELETE /blueprints/entity-definitions/{id}`

- **200 OK**: Permanently removed
- **404 Not Found**: Does not exist

---

## Error Formats

### Validation Error (400)

```json
{
  "type": "https://api.dilcore.com/errors/data-validation-failed",
  "title": "Validation Failed",
  "status": 400,
  "detail": "One or more validation errors occurred.",
  "errorCode": "DATA_VALIDATION_FAILED",
  "errors": {
    "displayName": ["DisplayName is required."],
    "fields[0].type": ["Field type 'Invalid' is not valid. Allowed: String, Number, Boolean, DateTime, Object, Array, File, Identifier."]
  }
}
```

### Not Found (404)

```json
{
  "type": "https://api.dilcore.com/errors/not-found",
  "title": "Resource Not Found",
  "status": 404,
  "detail": "Entity definition '{id}' does not exist.",
  "errorCode": "NOT_FOUND"
}
```

### Conflict — Schema Name (409)

Schema name already exists in the tenant.

### Conflict — ETag Mismatch (409)

```json
{
  "type": "https://api.dilcore.com/errors/etag-mismatch",
  "title": "Conflict",
  "status": 409,
  "detail": "ETag mismatch for entity definition '{id}'. Expected {current}, got {provided}.",
  "errorCode": "ETAG_MISMATCH"
}
```
