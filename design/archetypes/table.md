# table — data table

Sortable columns, filters, pagination, row actions.

## When to use

- Lists of records (users, orders, transactions, signals).
- Admin CRUD interfaces.
- Anywhere data is multi-dimensional and scannable.

## Structural skeleton

```
┌──────────────────────────────────────────────┐
│ Title         [search] [filter ▾] [+ New]    │
├──────────────────────────────────────────────┤
│ ☐  Col 1 ▼   Col 2    Col 3   Col 4   ⋮      │  sticky header
├──────────────────────────────────────────────┤
│ ☐  cell      cell     cell    cell    ⋮      │
│ ☐  cell      cell     cell    cell    ⋮      │
│ ☐  cell      cell     cell    cell    ⋮      │
├──────────────────────────────────────────────┤
│  Showing 1-25 of 1,243   ‹ 1 2 3 4 ... ›     │
└──────────────────────────────────────────────┘
```

## Required components

- **Toolbar**: search input, filter pills/menu, action buttons (`+ New`, bulk action).
- **Header row**: sortable cols (arrow indicator), checkbox for select-all.
- **Body rows**: select checkbox, data cells, row action menu (⋮).
- **Footer**: pagination + total count + page-size selector.

## Common mistakes

- No sticky header — context lost on scroll.
- Right-aligned numbers missing tabular-nums.
- Row actions hidden inside ⋮ for primary actions (open/edit should be one click).
- Pagination without total count.
- Filtering doesn't persist in URL (lost on refresh).

## Density rules

- Row height: 36-44px standard, 28-32px compact, 56px relaxed.
- Cell padding: 12-16px horizontal, 8-12px vertical.
- Header text 12-13px, weight 500-600, often uppercased.
- Body text 14-16px.
- Numbers right-aligned, `font-variant-numeric: tabular-nums`.

## Accessibility notes

- `<table>` semantics. `<th scope="col">` and `scope="row"`.
- Sortable: `aria-sort="ascending" | "descending" | "none"`.
- Row selection: checkbox with accessible label ("Select row {N}").
- Keyboard: arrow keys cycle cells, `space` selects, `enter` opens row.
- Long cell content: truncate with title attribute or expandable.

## Sample DTCG

```json
{
  "table": {
    "row-h":         { "$type":"dimension", "$value":{"value":40,"unit":"px"} },
    "cell-padding":  { "$type":"dimension", "$value":{"value":12,"unit":"px"} },
    "header-bg":     { "$type":"color",     "$value":"{color.surface-2}" },
    "row-hover":     { "$type":"color",     "$value":"{color.surface}" }
  }
}
```
