// Shared envelope schema. Reader (S3 spool tail) MUST import from this file.
// snake_case keys for jq compatibility on the wire.

export type BusMode = "notify" | "ask" | "consensus" | "reply";

export const BUS_MODES: ReadonlySet<BusMode> = new Set([
  "notify",
  "ask",
  "consensus",
  "reply",
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
