---
description: "Model variables/fields/concepts that always appear together as a cohesive whole, not scattered fragments"
---

When designing or understanding any system, if a group of variables, fields, or concepts always appear together and express the same semantic unit, they should be modeled as a single whole rather than scattered fragments:

- **Go** — define a struct
- **Java/Python** — define a class
- **TypeScript** — define an interface/type
- **Config** — group into a nested config block
- **Module partitioning** — split into an independent module

The essence is the same principle: **highly cohesive things should be a single thing at the moment of modeling.**

## Trigger Scenarios

1. Within a function/method parameter list, a few parameters are always passed together → extract into a parameter object
2. Multiple variables are always assigned, passed, and returned together → merge into a struct/class
3. A group of keys in a config file always appears in pairs/clusters → group into a nested config block
4. You find yourself repeatedly declaring the same set of fields across different files → extract a shared type/interface
5. Modifying one value requires synchronously modifying another → they belong to the same invariant and should be encapsulated together

## Anti-Patterns (Avoid)

- **Primitive Obsession**: using scattered string/number in place of meaningful types
- **Data Clumps**: the same group of data repeatedly appearing in parameter lists, return values, and variable declarations
- **Shotgun Surgery**: adding one field requires changing function signatures across N files

## How to Apply

- When you spot a trigger scenario, extract the cohesive group into a named unit in one pass — do not leave it for "later refactoring."
- Prefer immutability for the extracted unit to preserve the invariant across the codebase.
- Name the unit after the domain concept it represents, not the data it happens to contain (e.g., `Money`, not `AmountAndCurrency`).
- Apply the rule at the lowest level first (parameter object, struct), then propagate upward to interfaces and modules if the cohesion holds.

## Related Principles

- **Single Responsibility Principle** — a cohesive unit should have one reason to change.
- **Invariant Encapsulation** — bundle data that must satisfy a shared constraint so the constraint can be enforced in one place.
- **Tell, Don't Ask** — once grouped, expose behavior on the whole rather than dissecting it at call sites.
