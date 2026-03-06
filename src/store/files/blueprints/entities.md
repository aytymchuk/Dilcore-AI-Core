# Blueprints — Entity Definitions

## What is an Entity Definition?

An Entity Definition describes a type of business object in your workspace. It answers the question: **"What kinds of things does my business track?"**

When you create an Entity Definition called "Customer Order" with fields like "Order Number" and "Line Items," you are telling the system what a Customer Order looks like. The platform then knows how to store, validate, and display instances of that object.

### Real-world examples

| Business area | Entity types you might define |
|---|---|
| CRM | Lead, Deal, Company, Contact |
| HR | Employee, Department, Leave Request, Performance Review |
| Operations | Work Order, Inventory Item, Supplier, Shipment |
| Finance | Invoice, Payment, Expense Report, Budget |

## What makes up an Entity Definition?

Every Entity Definition has these parts:

### Name and description

- **Display name** — the human-readable name shown everywhere in the application (e.g., "Customer Order"). You can rename it at any time without breaking anything.
- **Description** — a short explanation of what this entity type represents in your business (e.g., "Represents a customer purchase order with line items and totals"). Helps both people and AI agents understand the purpose.

### Fields

Fields define what information the entity carries. A "Customer" entity might have:
- Full Name (text)
- Email Address (text)
- Date of Birth (date)
- Is Active (yes/no)
- Shipping Address (a group with Street, City, Zip Code)
- Phone Numbers (a repeating list, each with Label and Number)

Fields can be simple values or structured groups. See the Fields reference for all available field types.

### Tags

Free-form labels you assign to organize and categorize your entity types. Examples: "crm," "billing," "hr," "priority." Tags help you find and filter entity types when you have many of them.

### Inheritance

An entity type can extend another entity type, inheriting its fields. This is useful when several entity types share common information:

- Define a "Base Contact" with fields like Name, Email, Phone
- Create "Person" extending Base Contact — it gets all those fields plus any you add
- Create "Organization" extending Base Contact — same shared fields, different additions

A **base type** (marked as abstract) exists only to be extended — you don't create records of it directly. It's a template for other entity types.

## What can you do with Entity Definitions?

| Action | What it does |
|---|---|
| **Create** | Define a new type of business object with a name, description, fields, and tags |
| **Update** | Change the name, description, fields, or tags of an existing entity type |
| **Browse** | See a list of all entity types in your workspace, with search and filtering |
| **View details** | Look at a single entity type and its full structure |
| **Remove** | Permanently delete an entity type you no longer need |

## Important rules

### Naming

- Names must be between 2 and 128 characters and contain at least one letter or number.
- Each entity type name must be unique within your workspace.
- When you rename an entity type, the internal identifier stays the same — existing data and integrations are not affected.

### Fields on update

When you update an entity type's fields, you are replacing the entire field structure:
- Existing fields you include are preserved (their identity stays the same).
- New fields you add get created automatically.
- Fields you leave out are removed.

This means you should always include all the fields you want to keep when making changes.

### Version safety

The system tracks a version for each entity type. When you update, you must reference the current version. If someone else modified the entity type since you last looked at it, the system will tell you there is a conflict — preventing accidental overwrites.

### Descriptions matter

Always provide a meaningful description for entity types. Descriptions help users understand what each entity type is for, and they help AI agents interpret and work with your business data more effectively.
