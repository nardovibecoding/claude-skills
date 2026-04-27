# Phase 1.5: Merge near-duplicates (if semantic_dedup warnings found)

After Phase 1, check for `semantic_dedup` warnings in the output. For each flagged pair:

1. Read both files
2. Show the user a one-line summary of each: title, type, key facts
3. Ask: **"[A] Keep A, [B] Keep B, [M] Merge both, [S] Skip"**
4. Before any deletion: move the file to be deleted into `~/NardoWorld/archive/` (safety backup — not a git commit, just a move)
5. Act on answer:
   - **A**: archive fileB, update all wikilinks in all files pointing to fileB's title → fileA's title; remove fileB's entry from `~/NardoWorld/index.md` and `MEMORY.md` if present
   - **B**: archive fileA, update all wikilinks pointing to fileA's title → fileB's title; remove fileA's entry from indexes
   - **M**: combine both files — merge content (keep best of each section, deduplicate facts, union tags/labels, use earlier `created`, today's `updated`), write merged result to fileA, archive fileB, update wikilinks + indexes
   - **S**: leave both, continue
6. After resolving all pairs, re-run `--no-semantic` to confirm no new issues.

Skip Phase 1.5 for `/lint --quick`.

## Unattended variant (if `--unattended`)

DO NOT delete or archive any file. Instead:
1. Collect every `semantic_dedup` warning pair from Phase 1 output.
2. For each pair: read both files, extract title + 1-line summary.
3. Write a single memo file: `$MEMO_DIR/lint-dedup-pairs-$TODAY.md`
   Format per pair:
   ```
   ## Pair N
   **File A**: <title> — <1-line summary>
   **File B**: <title> — <1-line summary>
   **Recommended**: [A|B|M|S] — <reason>
   Pick: [A] [B] [M] [S]
   ```
4. Skip if no dedup warnings found.
