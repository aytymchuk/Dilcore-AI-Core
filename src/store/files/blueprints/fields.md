# Blueprints — Field Types and Structure

## What are fields?

Fields define what information an entity carries. Every piece of data you track — a name, a date, a price, an address — is represented as a field on an entity type.

## Field types

Each field has a type that determines what kind of data it holds. Choosing the right type ensures the data is stored correctly and presented properly to users.

### Simple fields (single values)

| Type | What it holds | Examples |
|---|---|---|
| **Text** | Names, labels, descriptions, emails, addresses, statuses, any written content | Customer Name, Email Address, Notes, Status |
| **Number** | Quantities, amounts, prices, percentages, scores | Total Amount, Quantity, Discount Percentage, Rating |
| **Yes / No** | Binary choices, toggles, flags | Is Active, Is Verified, Has Signed Contract |
| **Date and Time** | Dates, timestamps, deadlines, schedules | Created Date, Due Date, Appointment Time |
| **File** | Attachments, images, documents, uploads | Profile Photo, Contract PDF, Receipt |
| **Reference** | Links to other entity records or external system identifiers | Assigned Customer, Parent Company, External CRM ID |

### Structured fields (groups and lists)

| Type | What it holds | Examples |
|---|---|---|
| **Group** | Several related sub-fields bundled together as one unit | Shipping Address (with Street, City, Zip Code), Contact Info (with Phone, Email, Preferred Method) |
| **List** | A repeating collection of structured items, where each item has the same sub-fields | Line Items (each with Product Name, Quantity, Price), Phone Numbers (each with Label, Number) |

### How structured fields work

Structured fields can contain sub-fields, and those sub-fields can themselves be structured. This lets you model rich business data naturally:

- An "Order" entity might have a **List** field called "Line Items"
- Each line item has sub-fields: "Product Name" (text), "Quantity" (number), "Unit Price" (number)
- An entity might have a **Group** field called "Billing Address"
- The address has sub-fields: "Street" (text), "City" (text), "State" (text), "Zip Code" (text)

You can nest structures up to **5 levels deep**, which covers even complex business data.

## Choosing the right field type

When deciding what type to use for a field, think about **what the data means**, not just what it looks like:

- A phone number looks like a number, but it is really **Text** — you don't do math on it, and it may have dashes or country codes.
- A price is a **Number** — you may need to calculate totals or averages.
- "Is this customer active?" is a **Yes / No** — it has exactly two states.
- "When was this created?" is a **Date and Time** — it represents a point in time.
- "Which customer does this order belong to?" is a **Reference** — it points to another record.
- An address is a **Group** — it bundles several related text fields into one logical unit.
- Order line items are a **List** — the same structure repeats for each item in the order.

## Practical limits

- Each level of nesting can have up to **50 sub-fields**
- Nesting goes up to **5 levels** deep
- Field names must be between 2 and 128 characters
- Field names must be unique within the same level (you can't have two fields called "Name" at the same level, but you can have "Name" inside different groups)
- Every Group or List must have at least one sub-field
- Simple fields cannot have sub-fields

## Naming your fields well

Clear, descriptive field names matter — not just for users reading the application, but for AI agents that will interpret the data. A field called "Amount" is less clear than "Total Order Amount." A field called "Ref" is less clear than "Assigned Customer."

When you create a field, the system generates a stable internal identifier from the name. You can rename the display name later without affecting stored data — the internal identifier stays the same.
