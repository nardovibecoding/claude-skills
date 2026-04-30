// Shared envelope schema. Reader (S3 spool tail) MUST import from this file.
// snake_case keys for jq compatibility on the wire.

export type BusMode = "notify" | "ask" | "consensus" | "reply";

export const BUS_MODES: ReadonlySet<BusMode> = new Set([
  "notify",
  "ask",
  "consensus",
  "reply",
]);

// Consensus sub-type: question (initiator → all), vote (peer → initiator), verdict (initiator → all).
export type ConsensusKind = "question" | "vote" | "verdict";
export const CONSENSUS_KINDS: ReadonlySet<ConsensusKind> = new Set([
  "question",
  "vote",
  "verdict",
]);

export interface BusEnvelope {
  msg_id: string;            // ulid or `${sessionId}-${counter}`; caller-generated
  from: string;              // sender bus name (e.g. "A") or session_id
  from_session_id: string;   // sender claude PID; routing key for replies
  to: string;                // "all" | recipient bus name | recipient session_id
  mode: BusMode;
  ts: string;                // ISO8601 with TZ
  payload: string;           // raw text body
  in_reply_to?: string;      // msg_id of original (replies)
  reply_from?: string;       // sender of reply (mode=reply)
  // Consensus fields — required when mode=consensus; forbidden otherwise.
  round?: number;            // 1, 2, or 3 — which consensus round this belongs to
  kind?: ConsensusKind;      // sub-type: "question" | "vote" | "verdict"
  consensus_id?: string;     // groups all envelopes for one run; format: "<sid>-c-<epoch>"
}

export const REQUIRED_KEYS: ReadonlyArray<keyof BusEnvelope> = [
  "msg_id",
  "from",
  "from_session_id",
  "to",
  "mode",
  "ts",
  "payload",
];

// Fields required on every mode=consensus envelope.
export const CONSENSUS_REQUIRED_KEYS: ReadonlyArray<"round" | "kind" | "consensus_id"> = [
  "round",
  "kind",
  "consensus_id",
];
