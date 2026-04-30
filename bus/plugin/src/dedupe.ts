// Bounded LRU dedupe set for msg_id seen-tracking. Pure data structure, no I/O.
// Cap defaults to 1000 — at 200 msg/min that's ~5min protection window;
// designed to absorb spool-truncation re-emission (S3 §7 Q&A) and any
// accidental cross-spool duplicate (broadcast vs targeted same msg_id).

export class SeenSet {
  private readonly cap: number;
  private readonly m: Map<string, true> = new Map();

  constructor(cap = 1000) {
    if (cap < 1) throw new RangeError("cap must be >= 1");
    this.cap = cap;
  }

  has(msgId: string): boolean {
    return this.m.has(msgId);
  }

  add(msgId: string): void {
    // Touch-to-front semantics: re-adding moves to most-recent.
    if (this.m.has(msgId)) {
      this.m.delete(msgId);
    }
    this.m.set(msgId, true);
    while (this.m.size > this.cap) {
      // Map insertion order: first key = oldest.
      const oldest = this.m.keys().next().value;
      if (oldest === undefined) break;
      this.m.delete(oldest);
    }
  }

  get size(): number {
    return this.m.size;
  }
}
