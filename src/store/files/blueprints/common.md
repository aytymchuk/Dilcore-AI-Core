# Blueprints — Overview

## What is Blueprints?

Blueprints is the part of the platform where you define what your business application looks like. Instead of writing code or waiting for developers, you describe the shape of your business data — what you track, how it connects, and how it behaves — and the platform builds a working application from that description.

Think of it as a digital blueprint for your business: you decide what "Customers," "Orders," or "Tickets" look like, what information they carry, and how they relate to each other. The system takes care of everything else — storing data, enforcing rules, and presenting it to users.

## What problem does it solve?

Building custom software is slow and expensive. Off-the-shelf products rarely match how your business actually works. The result is spreadsheets, manual handoffs, and disconnected tools.

Blueprints solves this by letting you:

- **Define your process in one place** — model your real business objects and workflows, not someone else's template.
- **Move fast** — go from idea to a working application in days, not months.
- **Stay independent** — change and extend your application when your process changes, without waiting on developers.
- **Keep everything connected** — replace scattered spreadsheets and manual steps with a single, structured system.

## Key concepts

### Your workspace is private

Every organization has its own isolated workspace. The business objects you define, the data you store, and the rules you set are completely separate from any other organization. Nothing leaks between workspaces.

### Entity types — the building blocks

An **entity type** is a category of business object you want to track. Examples: "Customer," "Invoice," "Support Ticket," "Employee." You give each entity type a name, a description, and define what information it carries through **fields**.

### Fields — what information you track

Each entity type has fields that describe the data it holds. A "Customer" might have fields like "Full Name," "Email Address," and "Phone Number." Fields can be simple (text, numbers, dates) or structured (a group of related sub-fields like an address with street, city, and zip code).

### Tags — organizing your definitions

You can label your entity types with tags (like "crm," "billing," "hr") to group and find them easily. This is especially helpful when you have many entity types across different business areas.

### Inheritance — sharing common structures

If several entity types share the same base information, you can define a parent type and have others inherit from it. For example, "Person" and "Organization" could both extend a "Base Contact" type that carries shared fields like name and email.

### Naming stability

When you create an entity type or a field, the system generates an internal identifier from the name you give it. You can rename the display name freely at any time — the internal identifier stays the same, so nothing breaks. This means you can refine your naming without worrying about disrupting existing data or integrations.

## What can you configure?

Today, Blueprints supports configuring **Entity Definitions** — the core business object types with their fields, relationships, tags, and inheritance. Additional configuration areas (projections, views, forms, workflows, integrations) will be added over time.

## Practical limits

To keep things manageable and performant, there are sensible limits:

- Entity type names must be between 2 and 128 characters
- Descriptions can be up to 200 characters
- Each entity type can have up to 100 top-level fields
- You can assign up to 20 tags per entity type
- Entity type names must be unique within your workspace
