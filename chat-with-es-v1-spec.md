# Chat with Elasticsearch — V1 Specification

**Index:** `rlo-audit-elastic-ingestion-index`
**Query language:** ES|QL (pipe-based)
**Version:** 1.0 — April 2026
**Status:** DRAFT

---

## 1. Executive summary

This document specifies the V1 implementation of a natural language query interface for the RLO Audit Elasticsearch index. Users ask questions in plain English — either by typing freely or by clicking template hints — and receive formatted answers backed by ES|QL queries.

**What the index is:** An audit log of real-time lending offer (RLO) API calls. Each document captures a single request/response with a snapshot of the customer's financial profile at lookup time.

**What the index is NOT:** A multi-step application journey tracker. There are no step names, funnel stages, or completion states.

**Core design principle:** Every query is a base metric + zero or more filters. In ES|QL, filters are `WHERE` clauses that stack by appending lines. The template engine is string concatenation, not JSON construction.

---

## 2. Architecture

### 2.1 Three-world model

| Layer | V1 implementation | V2 evolution |
|-------|-------------------|--------------|
| **Human world** | NL text input + template hints, answer formatter | Conversational follow-ups, chart rendering |
| **Semantic world** | LLM converts NL → ES\|QL using few-shot prompt | Fine-tuned model, multi-turn context |
| **Data world** | Single index executor + result normalizer | Multi-index joins, backend adapters |

### 2.2 V1 request flow

```
User types question (or clicks template hint)
       ↓
[1] LLM receives: system prompt (schema + syntax + 18 few-shot examples) + user question
       ↓
[2] LLM generates ES|QL query
       ↓
[3] Validator checks: syntax valid? fields exist? functions correct?
       ↓
       ├── Valid → [4] Execute against ES
       │              ↓
       │          [5] Result normalizer flattens response
       │              ↓
       │          [6] Answer formatter generates human-readable response
       │
       └── Invalid → [3b] Fallback: match to closest template, re-generate
                         ↓
                      Retry once → if still invalid, show error + suggest template
```

### 2.3 UX pattern: input-first, templates as scaffolding

The text input is the primary interaction. Template hints sit below as clickable suggestions that teach vocabulary, show customizable slots, and narrow as the user types.

```
┌─────────────────────────────────────────────────────┐
│  Ask anything about RLO audit data...          [↑]  │
└─────────────────────────────────────────────────────┘
  Try a template ─────────────────────────────────────
  [All] [Volume] [Performance] [Health] [Segments] [OD]

  V  How many {customers} applied in the last {7 days}
  V  Show lookup volume trend by {day} for the last {7 days}
  P  What is the average response time {today}
  H  What is the success vs failure rate {today}
  S  How many customers with tenure {< 1 year} applied
  O  How many customers have overdrafted in the last {12 months}
```

**Template slots** (shown in `{curly braces}`) are editable parameters. Clicking a template fills the text input with the default values. The user edits slot values before submitting.

**As-you-type filtering:** Templates filter to match what the user is typing, guiding them toward valid phrasing.

**Templates serve triple duty:**
1. UI hints for users
2. Few-shot examples for the LLM system prompt
3. Fallback queries when LLM generation fails

---

## 3. Schema registry

Source: `rlo-audit-elastic-ingestion-index`
Inspected: April 1, 2026 via Kibana Discover

### 3.1 Request / audit trail

| Field | Type | Sample | Description |
|-------|------|--------|-------------|
| `applicationCrossReferenceId` | keyword | `69adf179-abdf-42a6-...` | Unique application identifier (UUID) |
| `applicationType` | keyword | `PERSONAL` | Application type (PERSONAL, BUSINESS, etc.) |
| `consumerName` | keyword | `SOM` | Calling consumer/channel name |
| `dateTimeRequest` | date | `2026-04-01T20:57:58Z` | Timestamp when API request was made |
| `dateTimeResponse` | date | `2026-04-01T20:57:58Z` | Timestamp when API response returned |
| `status` | keyword | `SUCCESS` | Lookup result status |

### 3.2 Customer identity

| Field | Type | Sample | Description |
|-------|------|--------|-------------|
| `mdmKey` | keyword | `200139307391` | MDM party identifier (unique customer) |
| `custEfDt` | date | `2025-01-06` | Customer effective date (onboarding) |
| `tenure` | number | `0` | Customer tenure — **UNIT UNVERIFIED** |

### 3.3 Balance snapshot

| Field | Type | Sample | Description |
|-------|------|--------|-------------|
| `currBalCd` | number | `0` | Current balance — Certificate of Deposit |
| `currBalDda` | number | `0` | Current balance — Demand Deposit Account |
| `currBalIra` | number | `0` | Current balance — IRA |
| `currBalSav` | number | `0` | Current balance — Savings |
| `totalBalDeposit` | number | `0` | Total deposit balance (all products) |
| `totalAvgBalDeposit` | number | `0` | Total average deposit balance |
| `aggOdBalMtd` | number | `0` | Aggregate overdraft balance MTD |

### 3.4 Product presence flags

| Field | Type | Sample | Description |
|-------|------|--------|-------------|
| `cdPresenceFlg` | keyword | `N` | Customer has CD product (Y/N) |
| `depositsPresenceFlg` | keyword | `Y` | Customer has deposit product (Y/N) |
| `iraPresenceFlg` | keyword | `N` | Customer has IRA product (Y/N) |
| `savingsPresenceFlg` | keyword | `N` | Customer has savings product (Y/N) |

### 3.5 Relationship dates

| Field | Type | Sample | Description |
|-------|------|--------|-------------|
| `oldestDepRlshp` | keyword | `2025-11-04` | Oldest deposit relationship date (⚠️ stored as keyword, not date) |
| `newestDepRlshp` | keyword | `2025-11-05` | Newest deposit relationship date (⚠️ stored as keyword, not date) |

### 3.6 Overdraft history

| Field | Type | Sample | Description |
|-------|------|--------|-------------|
| `noItemsOdMtd` | number | `0` | Overdraft item count this month |
| `noTimesOd03` | number | `0` | Overdraft count — last 3 months |
| `noTimesOd12` | number | `0` | Overdraft count — last 12 months |

### 3.7 System / metadata

| Field | Type | Sample | Description |
|-------|------|--------|-------------|
| `timeStamp` | date | `2026-04-01T20:57:58.587Z` | System timestamp (epoch millis) |
| `realtimeUpdateDate` | text+keyword | `2026-04-01 16:36:26.652` | Realtime update date (⚠️ dual mapped) |
| `time_bucket` | number | `38955478000` | Epoch-based time bucket |

### 3.8 Schema issues to resolve before build

1. **`tenure` field unit:** Sample shows `tenure: 0` for a customer with `custEfDt` of Jan 2025. Is the field in years, months, or something else? If unreliable, compute tenure from `custEfDt` via `DATE_DIFF`.
2. **`oldestDepRlshp` / `newestDepRlshp`:** Stored as keyword, not date — cannot do range queries or compute durations.
3. **`realtimeUpdateDate`:** Stored as text — consider re-indexing as proper date type.
4. **`status` field values:** Only `SUCCESS` observed in sample. Need to enumerate all possible values (FAILURE? ERROR? TIMEOUT?) for health queries.
5. **`applicationCrossReferenceId` cardinality:** Verify if this is 1:1 with actual applications, or if one application can generate multiple audit log entries.

---

## 4. V1 question catalog

V1 ships with 18 predefined question templates across 5 categories. Each serves as a UI hint, an LLM few-shot example, and a fallback query.

### 4.1 Volume and traffic

| ID | Template | Slots | ES\|QL pattern |
|----|----------|-------|---------------|
| Q-VOL-01 | How many `{customers}` applied in the last `{7 days}` | entity, time range | `STATS COUNT(*), COUNT_DISTINCT(mdmKey), COUNT_DISTINCT(applicationCrossReferenceId)` |
| Q-VOL-02 | Show lookup volume trend by `{day}` for the last `{7 days}` | granularity, time range | `EVAL day = DATE_FORMAT(...) \| STATS COUNT(*) BY day` |
| Q-VOL-03 | Which consumer has the most lookups `{today}` | time range | `STATS COUNT(*) BY consumerName \| SORT count DESC` |
| Q-VOL-04 | What is the split between application types `{this week}` | time range | `STATS COUNT(*) BY applicationType` |

### 4.2 Performance and SLA

| ID | Template | Slots | ES\|QL pattern |
|----|----------|-------|---------------|
| Q-PERF-01 | What is the average response time `{today}` for consumer `{all}` | time range, consumer | `EVAL resp_ms = DATE_DIFF("milliseconds", dateTimeRequest, dateTimeResponse) \| STATS AVG(resp_ms), PERCENTILE(resp_ms, 95)` |
| Q-PERF-02 | Which consumer has the slowest response times `{this week}` | time range | `EVAL resp_ms = ... \| STATS AVG(resp_ms) BY consumerName \| SORT avg DESC` |
| Q-PERF-03 | Show me lookups slower than `{500ms}` in the last `{1 day}` | threshold, time range | `EVAL resp_ms = ... \| WHERE resp_ms > 500` |

### 4.3 System health

| ID | Template | Slots | ES\|QL pattern |
|----|----------|-------|---------------|
| Q-HLTH-01 | What is the success vs failure rate `{today}` | time range | `STATS COUNT(*) BY status` |
| Q-HLTH-02 | Are there failure spikes in the last `{1 hour}` | time range | `WHERE status != "SUCCESS" \| EVAL bucket = DATE_FORMAT(...) \| STATS COUNT(*) BY bucket` |
| Q-HLTH-03 | Which consumer has the highest failure rate `{this week}` | time range | `STATS total = COUNT(*), failures = SUM(CASE(status != "SUCCESS", 1, 0)) BY consumerName` |

### 4.4 Customer segments

| ID | Template | Slots | ES\|QL pattern |
|----|----------|-------|---------------|
| Q-SEG-01 | What percentage of lookups have `{deposits}` presence | product type | `STATS COUNT(*) BY depositsPresenceFlg` |
| Q-SEG-02 | What is the product presence breakdown `{this week}` | time range | `STATS SUM(CASE(...)) for each *PresenceFlg` |
| Q-SEG-03 | What is the tenure distribution for the last `{7 days}` | time range | `EVAL tenure_band = CASE(...) \| STATS COUNT_DISTINCT(mdmKey) BY tenure_band` |
| Q-SEG-04 | Average deposit balance by `{deposit presence}` for the last `{7 days}` | group field, time range | `STATS AVG(totalBalDeposit) BY depositsPresenceFlg` |

### 4.5 Overdraft analysis

| ID | Template | Slots | ES\|QL pattern |
|----|----------|-------|---------------|
| Q-OD-01 | How many customers have overdrafted in the last `{12 months}` | OD window | `WHERE noTimesOd12 > 0 \| STATS COUNT_DISTINCT(mdmKey), AVG(noTimesOd12)` |
| Q-OD-02 | What is the overdraft balance distribution `{this month}` | time range | `EVAL od_band = CASE(...) \| STATS COUNT(*) BY od_band` |
| Q-OD-03 | Show top `{10}` customers by overdraft count | limit | `WHERE noTimesOd12 > 0 \| SORT noTimesOd12 DESC \| LIMIT 10` |

---

## 5. Composable query system (ES|QL)

### 5.1 Why ES|QL over JSON DSL

| Concern | JSON DSL | ES\|QL |
|---------|----------|--------|
| Template engine complexity | ~100 lines of nested JSON construction | ~15 lines of string concatenation |
| Filter composition | Push objects into `bool.filter[]` array | Append `\| WHERE` lines |
| LLM generation reliability | Nested brackets, easy to malform | Pipe-based, close to SQL, LLMs generate well |
| Human readability | Requires ES expertise | Readable by anyone who knows SQL |
| Lines for a typical query | 15–25 | 4–6 |

### 5.2 Query anatomy

Every ES|QL query follows this structure:

```
FROM rlo-audit-elastic-ingestion-index     ← always the same
| WHERE timeStamp > NOW() - {time_range}   ← always present (time filter)
| WHERE {filter_1}                          ← optional: stacked filters
| WHERE {filter_2}                          ← optional: more filters
| EVAL {computed_field} = {expression}      ← optional: computed columns
| STATS {metrics} BY {group_by}            ← the actual question
| SORT {field} {direction}                  ← optional: ordering
| LIMIT {n}                                 ← optional: top-N
```

### 5.3 Template engine pseudocode

```javascript
const METRICS = {
  count_customers: `STATS total = COUNT(*),
    unique_customers = COUNT_DISTINCT(mdmKey),
    unique_apps = COUNT_DISTINCT(applicationCrossReferenceId)`,

  response_time: `EVAL resp_ms = DATE_DIFF("milliseconds", dateTimeRequest, dateTimeResponse)
| STATS avg_ms = AVG(resp_ms),
    p95_ms = PERCENTILE(resp_ms, 95),
    max_ms = MAX(resp_ms)`,

  volume_trend: `EVAL day = DATE_FORMAT("yyyy-MM-dd", timeStamp)
| STATS count = COUNT(*) BY day
| SORT day`,

  status_breakdown: `STATS count = COUNT(*) BY status`,

  // ... other metric types
};

function buildESSQL(metricType, filters = [], timeRange = "7 days") {
  let query = `FROM rlo-audit-elastic-ingestion-index`;
  query += `\n| WHERE timeStamp > NOW() - ${timeRange}`;

  // Stack user-selected filters
  for (const filter of filters) {
    query += `\n| WHERE ${filter}`;
  }

  // Add metric
  query += `\n| ${METRICS[metricType]}`;

  return query;
}
```

### 5.4 Available filters

| Filter | Slot values | ES\|QL clause |
|--------|-------------|---------------|
| Time range | `1 day`, `7 days`, `30 days`, `1 hour` | `timeStamp > NOW() - {value}` |
| Application type | `PERSONAL`, `BUSINESS` | `applicationType == "{value}"` |
| Consumer | `SOM`, `[dynamic]` | `consumerName == "{value}"` |
| Tenure — new | `< 1 year` | `tenure <= 1` |
| Tenure — mid | `1–5 years` | `tenure >= 1 AND tenure <= 5` |
| Tenure — established | `> 5 years` | `tenure > 5` |
| Has deposits | Y/N | `depositsPresenceFlg == "Y"` |
| Has savings | Y/N | `savingsPresenceFlg == "Y"` |
| Has CD | Y/N | `cdPresenceFlg == "Y"` |
| Has IRA | Y/N | `iraPresenceFlg == "Y"` |
| Status | `SUCCESS`, `FAILURE` | `status == "{value}"` |
| Overdraft history | has OD | `noTimesOd12 > 0` |

### 5.5 Worked example: compound question

**User types:** "How many new customers with no deposits applied last month"

**Decomposition:**

| Word/phrase | Maps to |
|-------------|---------|
| "how many" | metric: `count_customers` |
| "new customers" | filter: `tenure <= 1` |
| "no deposits" | filter: `depositsPresenceFlg == "N"` |
| "last month" | time range: `30 days` |

**Generated ES|QL:**

```sql
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 30 days
| WHERE tenure <= 1
| WHERE depositsPresenceFlg == "N"
| STATS total = COUNT(*),
    unique_customers = COUNT_DISTINCT(mdmKey),
    unique_apps = COUNT_DISTINCT(applicationCrossReferenceId)
```

---

## 6. Answer formatting

### 6.1 Principle: always give context, never a bare number

Every answer follows: **primary number → context → optional breakdown**.

### 6.2 Answer patterns by category

**Volume (count questions):**
> "In the last 7 days, **3,847 unique customers** were looked up across **2,190 unique applications** and **14,320 total lookups**."

Always surface all three: total lookups, unique customers, unique applications. Let the user decide which matters.

**Performance:**
> "Average response time today is **45ms**. The slowest 5% take over **320ms**. Consumer SOM averages 38ms while XYZ averages 92ms."

Always include avg + p95. Break down by consumer when the spread is significant.

**Health:**
> "Success rate today is **99.2%** (14,208 of 14,320 lookups). 112 failures detected, concentrated between 2:00–2:15 PM."

Lead with rate, follow with absolute count, note any clustering.

**Segments:**
> "Of customers looked up this week, **62% have deposit presence**, 28% have savings, 8% have CD, and 4% have IRA."

Use percentages for comparison, absolute numbers in parentheses.

**Overdraft:**
> "**847 unique customers** have overdraft history in the last 12 months, averaging **3.2 overdrafts** per customer with a mean MTD balance of **$245**."

### 6.3 Ambiguity handling rule

When a question can be interpreted multiple ways (e.g., "how many applied" could mean total lookups, unique customers, or unique applications), **always return all three numbers** and let the user decide which matters. Do not force the system to guess.

---

## 7. Terminology dictionary

Maps user language to index fields. Used in the LLM system prompt for few-shot context and in V2 for explicit terminology resolution.

| User says | Maps to | Notes |
|-----------|---------|-------|
| "customers" / "borrowers" / "applicants" | `mdmKey` (cardinality) | Always count unique unless explicitly asked for total |
| "applied" / "applications" | `applicationCrossReferenceId` | Audit log captures lookups, not actual submissions |
| "last week" / "past 7 days" | `timeStamp > NOW() - 7 days` | Default to rolling 7 days, not calendar week |
| "today" | `timeStamp > NOW() - 1 day` | Calendar day |
| "this month" | `timeStamp > NOW() - 30 days` | Rolling 30 days |
| "response time" / "latency" / "SLA" | `DATE_DIFF("milliseconds", dateTimeRequest, dateTimeResponse)` | No dedicated field; computed at query time |
| "failures" / "errors" | `status != "SUCCESS"` | Need to verify all possible status values |
| "new customers" / "tenure < 1 year" | `tenure <= 1` | UNIT UNVERIFIED — may need `DATE_DIFF` from `custEfDt` |
| "has deposits" / "deposit customers" | `depositsPresenceFlg == "Y"` | Keyword field, Y/N values |
| "overdraft" / "OD" | `noTimesOd03`, `noTimesOd12`, `aggOdBalMtd` | Multiple fields depending on context |
| "channel" / "consumer" / "source" | `consumerName` | The calling system, not the end customer |
| "balance" / "deposit balance" | `totalBalDeposit` | Total across all product types |

---

## 8. LLM system prompt

This is the complete system prompt sent to the LLM for NL → ES|QL conversion.

### 8.1 Prompt structure

```
[ROLE]
You are an ES|QL query generator for the rlo-audit-elastic-ingestion-index.
Convert the user's natural language question into a valid ES|QL query.
Return ONLY the ES|QL query, nothing else.

[SCHEMA]
{paste section 3 schema tables here}

[ES|QL SYNTAX RULES]
- Always start with: FROM rlo-audit-elastic-ingestion-index
- Always include a time filter: | WHERE timeStamp > NOW() - {duration}
- Use COUNT_DISTINCT(mdmKey) for unique customers
- Use COUNT_DISTINCT(applicationCrossReferenceId) for unique applications
- Use DATE_DIFF("milliseconds", dateTimeRequest, dateTimeResponse) for response time
- String comparisons use ==, not =
- String values must be in double quotes: consumerName == "SOM"
- Available functions: COUNT, COUNT_DISTINCT, AVG, SUM, MIN, MAX,
  PERCENTILE, DATE_FORMAT, DATE_DIFF, CASE, NOW, ROUND
- Group with BY clause in STATS
- Sort with | SORT field ASC/DESC
- Limit with | LIMIT n

[TERMINOLOGY]
{paste section 7 terminology dictionary here}

[FEW-SHOT EXAMPLES]
{paste all 18 templates as input/output pairs — see section 8.2}

[RULES]
- If the time range is ambiguous, default to 7 days
- For "how many" questions, ALWAYS include all three counts:
  COUNT(*), COUNT_DISTINCT(mdmKey), COUNT_DISTINCT(applicationCrossReferenceId)
- For response time questions, ALWAYS include AVG and PERCENTILE(95)
- Never use fields not in the schema
- Never use functions not in the available list
- If you cannot generate a valid query, respond with: CANNOT_GENERATE
```

### 8.2 Few-shot examples (included in system prompt)

```
User: How many customers applied in the last 7 days
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 7 days
| STATS total = COUNT(*),
    unique_customers = COUNT_DISTINCT(mdmKey),
    unique_apps = COUNT_DISTINCT(applicationCrossReferenceId)

---

User: Show lookup volume trend by day for the last 7 days
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 7 days
| EVAL day = DATE_FORMAT("yyyy-MM-dd", timeStamp)
| STATS count = COUNT(*) BY day
| SORT day

---

User: Which consumer has the most lookups today
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 1 day
| STATS count = COUNT(*) BY consumerName
| SORT count DESC

---

User: What is the average response time today
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 1 day
| EVAL resp_ms = DATE_DIFF("milliseconds", dateTimeRequest, dateTimeResponse)
| STATS avg_ms = AVG(resp_ms),
    p95_ms = PERCENTILE(resp_ms, 95),
    max_ms = MAX(resp_ms)

---

User: Which consumer has the slowest response times this week
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 7 days
| EVAL resp_ms = DATE_DIFF("milliseconds", dateTimeRequest, dateTimeResponse)
| STATS avg_ms = AVG(resp_ms) BY consumerName
| SORT avg_ms DESC

---

User: Show me lookups slower than 500ms in the last 1 day
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 1 day
| EVAL resp_ms = DATE_DIFF("milliseconds", dateTimeRequest, dateTimeResponse)
| WHERE resp_ms > 500

---

User: What is the success vs failure rate today
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 1 day
| STATS count = COUNT(*) BY status

---

User: Are there failure spikes in the last 1 hour
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 1 hour
| WHERE status != "SUCCESS"
| EVAL bucket = DATE_FORMAT("yyyy-MM-dd HH:mm", timeStamp)
| STATS failures = COUNT(*) BY bucket
| SORT bucket

---

User: Which consumer has the highest failure rate this week
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 7 days
| STATS total = COUNT(*),
    failures = SUM(CASE(status != "SUCCESS", 1, 0)) BY consumerName
| EVAL failure_pct = ROUND(failures * 100.0 / total, 1)
| SORT failure_pct DESC

---

User: What percentage of lookups have deposits presence
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 7 days
| STATS count = COUNT(*) BY depositsPresenceFlg

---

User: What is the product presence breakdown this week
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 7 days
| STATS total = COUNT(*),
    has_cd = SUM(CASE(cdPresenceFlg == "Y", 1, 0)),
    has_deposits = SUM(CASE(depositsPresenceFlg == "Y", 1, 0)),
    has_ira = SUM(CASE(iraPresenceFlg == "Y", 1, 0)),
    has_savings = SUM(CASE(savingsPresenceFlg == "Y", 1, 0))

---

User: What is the tenure distribution for the last 7 days
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 7 days
| EVAL tenure_band = CASE(
    tenure <= 1, "New (< 1yr)",
    tenure <= 5, "Mid (1-5yr)",
    tenure > 5, "Established (5yr+)")
| STATS count = COUNT_DISTINCT(mdmKey) BY tenure_band

---

User: Average deposit balance by deposit presence for the last 7 days
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 7 days
| STATS avg_bal = AVG(totalBalDeposit) BY depositsPresenceFlg

---

User: How many customers have overdrafted in the last 12 months
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 7 days
| WHERE noTimesOd12 > 0
| STATS od_customers = COUNT_DISTINCT(mdmKey),
    avg_od_count = AVG(noTimesOd12),
    avg_od_bal = AVG(aggOdBalMtd)

---

User: Show top 10 customers by overdraft count
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE noTimesOd12 > 0
| SORT noTimesOd12 DESC
| LIMIT 10
| KEEP mdmKey, noTimesOd12, aggOdBalMtd, tenure

---

User: How many new customers with no deposits applied last month
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 30 days
| WHERE tenure <= 1
| WHERE depositsPresenceFlg == "N"
| STATS total = COUNT(*),
    unique_customers = COUNT_DISTINCT(mdmKey),
    unique_apps = COUNT_DISTINCT(applicationCrossReferenceId)

---

User: What is the application type split for consumer SOM this week
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 7 days
| WHERE consumerName == "SOM"
| STATS count = COUNT(*) BY applicationType

---

User: How many customers with tenure less than 1 year applied in last 7 days
ES|QL:
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 7 days
| WHERE tenure <= 1
| STATS total = COUNT(*),
    unique_customers = COUNT_DISTINCT(mdmKey),
    unique_apps = COUNT_DISTINCT(applicationCrossReferenceId)
```

---

## 9. Validation and fallback strategy

### 9.1 ES|QL validation checks

Before executing any LLM-generated query, run these checks:

| Check | Rule | Action on failure |
|-------|------|-------------------|
| Starts with FROM | Must be `FROM rlo-audit-elastic-ingestion-index` | Replace with correct FROM clause |
| Valid field names | All field names must exist in schema (section 3) | Remove invalid WHERE clause, warn user |
| Valid functions | Only functions from the allowed list | Strip invalid function, fallback to template |
| Has time filter | Must have at least one `WHERE timeStamp > NOW() - ...` | Inject default: `7 days` |
| No injection | No `DELETE`, `DROP`, or write operations | Reject entirely |
| Syntax parse | All pipes, keywords, quotes balanced | Fallback to closest template |

### 9.2 Fallback strategy

```
LLM generates query
       ↓
  Validation passes? ──yes──→ Execute
       │ no
       ↓
  Match to closest template (cosine similarity on user input vs 18 templates)
       ↓
  Fill template slots with extracted parameters (time range, consumer, etc.)
       ↓
  Execute template query + append note:
  "I wasn't sure exactly what you meant, so I answered the closest
   question I could. Did you mean: {matched template}?"
```

### 9.3 Confidence scoring

For each LLM-generated query, assign a confidence score:

| Confidence | Criteria | Behavior |
|------------|----------|----------|
| **High** (> 0.8) | Query matches a known template pattern exactly | Execute, show answer |
| **Medium** (0.5–0.8) | Query is valid but uses novel filter combinations | Execute, show ES\|QL preview with "is this right?" |
| **Low** (< 0.5) | LLM returned `CANNOT_GENERATE` or validation failed | Show closest template suggestions, ask user to refine |

---

## 10. Open questions and risks

### 10.1 Must resolve before build

1. **`tenure` field unit:** Sample shows `tenure: 0` for a customer with `custEfDt` of Jan 2025 (~15 months). Verify the unit. If unreliable, compute via `DATE_DIFF("years", custEfDt, NOW())`.
2. **`status` field values:** Enumerate all possible values beyond `SUCCESS`. This determines health query filters.
3. **`applicationCrossReferenceId` cardinality:** Is this 1:1 with actual applications? Determines if COUNT_DISTINCT on this field is meaningful.
4. **`consumerName` values:** Need full list for the filter dropdown and for LLM context.
5. **ES|QL version compatibility:** Verify which ES|QL functions (`DATE_DIFF`, `PERCENTILE`, `CASE`) are available in your Elasticsearch version. Some are 8.11+.

### 10.2 V2 considerations (not in scope)

1. **Multi-index joins:** If a separate application journey index exists, V2 could cross-reference `applicationCrossReferenceId` to answer funnel/drop-off questions.
2. **Conversational follow-ups:** "Now break that down by consumer" should reference the previous query's context.
3. **Chart rendering:** Return data as chart-ready JSON, render bar/line/pie charts inline with the answer.
4. **Response time field at ingestion:** Add a computed `responseTimeMs` field during ingestion to eliminate `DATE_DIFF` scripts.
5. **Date type re-mapping:** Re-index `oldestDepRlshp`, `newestDepRlshp`, and `realtimeUpdateDate` as proper date types.

---

## 11. V1 build roadmap

| Week | Deliverable | Details |
|------|-------------|---------|
| **Week 1** | Schema verification + ES\|QL validation | Verify tenure unit, enumerate status values, test all 18 ES\|QL queries against live index, confirm function support |
| **Week 2** | LLM integration + prompt engineering | Set up LLM API call, build system prompt with schema + few-shots, test NL → ES\|QL on 50 sample questions, tune prompt |
| **Week 3** | Template engine + validator | Build composable query builder as fallback, implement validation checks, fallback matching logic |
| **Week 4** | UI — three-panel layout | Sidebar (session mgmt + search), chat area (messages + input + template hints), debug panel (expandable LLM logs). See section 12 for full spec |
| **Week 5** | Answer formatter + integration | Template-based answer generation, inline metric cards, ES\|QL reveal, suggested follow-ups. Wire UI → LLM → validator → ES → formatter |
| **Week 6** | Debug panel + polish | Per-step pipeline logging, confidence badges, session stats. Error handling, loading states, keyboard shortcuts |
| **Week 7** | QA + ship | Edge cases (empty results, timeouts, ambiguous questions), responsive behavior, deploy to staging, user acceptance testing, free-text query logging for V2 |

---

## Appendix A: ES|QL quick reference

```sql
-- Basic count
FROM index | WHERE field > value | STATS count = COUNT(*)

-- Unique count
STATS unique = COUNT_DISTINCT(field)

-- Aggregation with grouping
STATS avg_val = AVG(field) BY group_field

-- Computed columns
EVAL new_field = DATE_DIFF("milliseconds", field1, field2)

-- Conditional aggregation
STATS total = SUM(CASE(condition, 1, 0))

-- Date formatting for time buckets
EVAL bucket = DATE_FORMAT("yyyy-MM-dd HH:mm", dateField)

-- Sorting and limiting
| SORT field DESC | LIMIT 10

-- Select specific columns
| KEEP field1, field2, field3

-- Multiple WHERE clauses (AND logic)
| WHERE condition1 | WHERE condition2
```

## Appendix B: Sample end-to-end trace

**User input:** "How many new customers with no deposits applied last month"

**Step 1 — LLM generates ES|QL:**
```sql
FROM rlo-audit-elastic-ingestion-index
| WHERE timeStamp > NOW() - 30 days
| WHERE tenure <= 1
| WHERE depositsPresenceFlg == "N"
| STATS total = COUNT(*),
    unique_customers = COUNT_DISTINCT(mdmKey),
    unique_apps = COUNT_DISTINCT(applicationCrossReferenceId)
```

**Step 2 — Validation:** All fields exist, all functions valid, time filter present → PASS (confidence: HIGH)

**Step 3 — Execution result:**
```json
{
  "columns": [
    {"name": "total", "type": "long"},
    {"name": "unique_customers", "type": "long"},
    {"name": "unique_apps", "type": "long"}
  ],
  "values": [[4670, 1230, 890]]
}
```

**Step 4 — Formatted answer:**
> "In the last 30 days, **1,230 unique new customers** (tenure ≤ 1 year) without deposit products were looked up, across **890 unique applications** and **4,670 total lookups**."

---

## 12. UI specification

### 12.1 Layout: three-panel design

```
┌──────────┬──────────────────────────────────┬──────────────────┐
│          │                                  │                  │
│ SIDEBAR  │         CHAT AREA               │  DEBUG PANEL     │
│ 260px    │         flex: 1                 │  360px           │
│          │                                  │  (collapsible)   │
│          │                                  │                  │
└──────────┴──────────────────────────────────┴──────────────────┘
```

**Responsive behavior:**
- Desktop (> 1200px): all three panels visible
- Tablet (768–1200px): sidebar collapses to icon rail (48px), debug panel hidden by default with toggle button
- Mobile (< 768px): sidebar as overlay drawer, debug panel as bottom sheet

### 12.2 Panel A — Sidebar (260px)

The sidebar manages chat sessions (conversations) and provides quick access to history.

```
┌─────────────────────────┐
│ ◈ Chat with ES     [+]  │  ← App title + new session button
├─────────────────────────┤
│ 🔍 Search sessions...   │  ← Search input (filters session list)
├─────────────────────────┤
│                         │
│  TODAY                  │  ← Date group header (muted, uppercase, 11px)
│  ┌─────────────────┐   │
│  │ How many custo.. │   │  ← Active session (highlighted bg)
│  │ 3 messages · 2m  │   │     First message preview + count + time
│  └─────────────────┘   │
│  ┌─────────────────┐   │
│  │ Response time ..  │   │  ← Inactive session
│  │ 5 messages · 1h  │   │
│  └─────────────────┘   │
│                         │
│  YESTERDAY              │
│  ┌─────────────────┐   │
│  │ Failure spikes .. │   │
│  │ 8 messages · 1d  │   │
│  └─────────────────┘   │
│                         │
│  LAST 7 DAYS            │
│  ┌─────────────────┐   │
│  │ Overdraft analy.. │   │
│  │ 12 messages · 4d │   │
│  └─────────────────┘   │
│                         │
├─────────────────────────┤
│ ⚙ Settings              │  ← Bottom: settings link
│ 📊 Query history         │  ← All past queries log
└─────────────────────────┘
```

**Session card behavior:**
- Click → loads session in chat area
- Right-click / long-press → context menu: rename, delete, export
- New session `[+]` clears chat area, shows template hints
- Sessions persist in localStorage (V1) or backend DB (V2)
- Search filters by session title and message content

**Session data model:**
```typescript
interface Session {
  id: string;
  title: string;              // Auto-generated from first message
  createdAt: Date;
  updatedAt: Date;
  messages: Message[];
  queries: QueryLog[];        // All ES|QL queries run in this session
}
```

### 12.3 Panel B — Chat area (flex: 1, min-width 480px)

The main interaction area. Contains message history, template hints, and input.

#### 12.3.1 Empty state (new session)

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│                                                      │
│            ◈ Chat with Elasticsearch                 │
│            Ask anything about RLO audit data         │
│                                                      │
│   ┌──────────────────────────────────────────────┐   │
│   │  Ask anything about RLO audit data...   [↑]  │   │  ← Main input
│   └──────────────────────────────────────────────┘   │
│                                                      │
│   Try a template ────────────────────────────────    │
│   [All] [Volume] [Performance] [Health] [Segments]   │  ← Category pills
│                                                      │
│   V  How many {customers} applied in the last        │  ← Template hints
│      {7 days}                                        │
│   V  Show lookup volume trend by {day} for the       │
│      last {7 days}                                   │
│   P  What is the average response time {today}       │
│   H  What is the success vs failure rate {today}     │
│   S  How many customers with tenure {< 1 year}       │
│   O  How many customers have overdrafted in the      │
│      last {12 months}                                │
│                                                      │
└──────────────────────────────────────────────────────┘
```

#### 12.3.2 Active conversation

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│   ┌──────────────────────────────────────┐           │
│   │ How many new customers with no       │  USER     │  ← Right-aligned
│   │ deposits applied last month?         │           │     user bubble
│   └──────────────────────────────────────┘           │
│                                                      │
│   ┌──────────────────────────────────────────────┐   │
│   │ In the last 30 days, 1,230 unique new        │   │  ← Left-aligned
│   │ customers (tenure ≤ 1yr) without deposit     │   │     assistant
│   │ products were looked up, across 890 unique   │   │     bubble
│   │ applications and 4,670 total lookups.        │   │
│   │                                              │   │
│   │ ┌──────────────────────────────────────┐     │   │
│   │ │ 1,230          890         4,670     │     │   │  ← Inline metric
│   │ │ unique         unique      total     │     │   │     cards
│   │ │ customers      apps        lookups   │     │   │
│   │ └──────────────────────────────────────┘     │   │
│   │                                              │   │
│   │ [Show ES|QL ▾] [Copy] [Export CSV]           │   │  ← Action buttons
│   └──────────────────────────────────────────────┘   │
│                                                      │
│   ┌──────────────────────────────────────┐           │
│   │ Now break that down by consumer      │  USER     │
│   └──────────────────────────────────────┘           │
│                                                      │
│   ┌──────────────────────────────────────────────┐   │
│   │ ● ● ● Generating query...                   │   │  ← Loading state
│   └──────────────────────────────────────────────┘   │
│                                                      │
│   ┌──────────────────────────────────────────────┐   │
│   │  Ask a follow-up or new question...     [↑]  │   │  ← Input stays
│   └──────────────────────────────────────────────┘   │     at bottom
│                                                      │
│   Related: [By app type?] [By time of day?]          │  ← Suggested
│            [With tenure breakdown?]                  │     follow-ups
│                                                      │
└──────────────────────────────────────────────────────┘
```

#### 12.3.3 Message types

| Type | Alignment | Style | Content |
|------|-----------|-------|---------|
| **User message** | Right | Light blue bg (`#E6F1FB`), rounded corners, 14px | Plain text question |
| **Assistant answer** | Left | White bg, subtle border, 14px | Formatted answer with inline metric cards |
| **Assistant — error** | Left | Light red bg (`#FCEBEB`), red left border | Error message + suggestion to rephrase |
| **Assistant — clarification** | Left | Light amber bg (`#FAEEDA`) | "Did you mean..." with clickable options |
| **System message** | Center | Muted text, no bubble, 12px | "Session started", "Query failed — retrying" |

#### 12.3.4 Inline metric cards

When the answer contains numeric results, render them as a horizontal card row inside the assistant bubble:

```
┌────────────┬────────────┬────────────┐
│   1,230    │    890     │   4,670    │
│  unique    │  unique    │   total    │
│ customers  │   apps     │  lookups   │
└────────────┴────────────┴────────────┘
```

- Background: `#F8F8F6` (light surface)
- Number: 20px, weight 500, dark text
- Label: 12px, muted text
- Grid: auto-fit, min 120px per card, gap 8px

#### 12.3.5 ES|QL reveal (inside assistant bubble)

Clicking `[Show ES|QL ▾]` expands a code block below the answer:

```
┌──────────────────────────────────────────────┐
│ ES|QL                              [Copy ↗]  │
│ ──────────────────────────────────────────── │
│ FROM rlo-audit-elastic-ingestion-index       │
│ | WHERE timeStamp > NOW() - 30 days         │
│ | WHERE tenure <= 1                          │
│ | WHERE depositsPresenceFlg == "N"           │
│ | STATS total = COUNT(*),                    │
│     unique_customers = COUNT_DISTINCT(mdmKey)│
│                                              │
│ Executed in 42ms · Confidence: HIGH          │
└──────────────────────────────────────────────┘
```

- Background: `#F1F5F9` (code surface)
- Font: monospace, 12px
- Bottom bar: execution time + confidence badge (green/amber/red)

#### 12.3.6 Input area behavior

| State | Behavior |
|-------|----------|
| **Empty + new session** | Placeholder: "Ask anything about RLO audit data..." Template hints visible below |
| **Empty + active session** | Placeholder: "Ask a follow-up or new question..." Suggested follow-ups shown as pills |
| **Typing** | Templates filter to match input. Send button activates. `Enter` to submit, `Shift+Enter` for newline |
| **Loading** | Input disabled, animated dots in chat. Cancel button appears |
| **Error** | Input re-enabled, error shown in chat, last question pre-filled for easy retry |

#### 12.3.7 Suggested follow-ups

After each answer, show 2–3 contextual follow-up suggestions as clickable pills below the input:

```
Related: [By consumer?] [By app type?] [Show trend?]
```

Follow-up logic:
- If answer was a count → suggest "break down by {consumer / app type / tenure}"
- If answer was a trend → suggest "compare with previous period"
- If answer had a filter → suggest "remove the {filter} filter" or "also filter by {related field}"
- Generated by the LLM alongside the answer (add to system prompt: "also suggest 2–3 follow-up questions")

### 12.4 Panel C — Debug panel (360px, collapsible)

A developer-facing panel that shows the full pipeline for each query. Collapsible via toggle button in the chat area header.

#### 12.4.1 Layout

```
┌─────────────────────────────┐
│ Debug                 [×]   │  ← Panel header + close button
├─────────────────────────────┤
│                             │
│ ▼ Request #3 — 2s ago       │  ← Expandable log entry (most recent first)
│ ┌───────────────────────┐   │
│ │ STEP 1: User input    │   │
│ │ "How many new         │   │
│ │  customers with no    │   │
│ │  deposits last month" │   │
│ ├───────────────────────┤   │
│ │ STEP 2: LLM prompt    │   │  ← Expandable: shows full prompt sent
│ │  tokens: 2,140 in     │   │
│ │  tokens: 186 out      │   │
│ │  latency: 1.2s        │   │
│ │  model: claude-sonnet  │   │
│ │  [View full prompt ▾] │   │
│ ├───────────────────────┤   │
│ │ STEP 3: Generated     │   │
│ │  ES|QL                │   │
│ │ ┌─────────────────┐   │   │
│ │ │ FROM rlo-audit.. │   │   │
│ │ │ | WHERE ...      │   │   │
│ │ └─────────────────┘   │   │
│ │  confidence: 0.92     │   │
│ ├───────────────────────┤   │
│ │ STEP 4: Validation    │   │
│ │  ✓ fields valid       │   │
│ │  ✓ functions valid    │   │
│ │  ✓ time filter exists │   │
│ │  ✓ syntax OK          │   │
│ │  result: PASS         │   │
│ ├───────────────────────┤   │
│ │ STEP 5: Execution     │   │
│ │  status: 200 OK       │   │
│ │  took: 42ms           │   │
│ │  hits: 4,670          │   │
│ │  [View raw response ▾]│   │
│ ├───────────────────────┤   │
│ │ STEP 6: Answer        │   │
│ │  format: count_volume │   │
│ │  template: multi_stat │   │
│ │  [View raw answer ▾]  │   │
│ └───────────────────────┘   │
│                             │
│ ▶ Request #2 — 5m ago       │  ← Collapsed entry (click to expand)
│ ▶ Request #1 — 12m ago      │
│                             │
├─────────────────────────────┤
│ Avg latency: 1.8s           │  ← Session stats footer
│ Queries run: 3              │
│ Fallbacks: 0                │
│ ES time: 38ms avg           │
└─────────────────────────────┘
```

#### 12.4.2 Debug log entry data model

```typescript
interface DebugEntry {
  id: string;
  timestamp: Date;

  // Step 1: Input
  userInput: string;

  // Step 2: LLM
  llm: {
    model: string;
    promptTokens: number;
    completionTokens: number;
    latencyMs: number;
    fullPrompt?: string;        // Expandable
    rawResponse?: string;       // Expandable
  };

  // Step 3: Generated query
  generatedESSQL: string;
  confidence: number;           // 0.0 – 1.0
  matchedTemplate?: string;     // Template ID if matched (e.g., "Q-VOL-01")

  // Step 4: Validation
  validation: {
    fieldsValid: boolean;
    functionsValid: boolean;
    timeFilterPresent: boolean;
    syntaxValid: boolean;
    result: "PASS" | "FAIL" | "FIXED";
    fixes?: string[];           // What was auto-corrected
  };

  // Step 5: Execution
  execution: {
    statusCode: number;
    tookMs: number;
    totalHits: number;
    rawResponse?: object;       // Expandable
    error?: string;
  };

  // Step 6: Answer
  answer: {
    formatTemplate: string;     // Which answer pattern was used
    formattedText: string;
    metrics?: Record<string, number>;
    suggestedFollowUps: string[];
  };

  // Meta
  totalLatencyMs: number;
  usedFallback: boolean;
}
```

#### 12.4.3 Debug panel step badges

| Step status | Badge | Color |
|-------------|-------|-------|
| Success | ✓ | Green (`#0F6E56` on `#E1F5EE`) |
| Warning (auto-fixed) | ⚠ | Amber (`#854F0B` on `#FAEEDA`) |
| Failure | ✗ | Red (`#A32D2D` on `#FCEBEB`) |
| Skipped (fallback) | ○ | Gray (`#5F5E5A` on `#F1EFE8`) |

#### 12.4.4 Debug panel toggle

- Toggle button in chat area header bar: `[⟨⟩ Debug]`
- Keyboard shortcut: `Ctrl + D` (or `Cmd + D` on Mac)
- Remembers open/closed state in localStorage
- When closed, show a small floating indicator if the last query had warnings: `⚠ 1 validation fix`

### 12.5 Component hierarchy

```
App
├── Sidebar
│   ├── AppHeader (logo + new session button)
│   ├── SearchInput
│   ├── SessionList
│   │   ├── DateGroupHeader ("Today", "Yesterday", etc.)
│   │   └── SessionCard (title, preview, count, time)
│   └── SidebarFooter (settings, query history)
│
├── ChatArea
│   ├── ChatHeader (session title, debug toggle, export button)
│   ├── MessageList
│   │   ├── UserMessage
│   │   ├── AssistantMessage
│   │   │   ├── AnswerText
│   │   │   ├── MetricCards (inline stat grid)
│   │   │   ├── ESQLReveal (collapsible code block)
│   │   │   └── ActionBar (copy, export CSV, show ES|QL)
│   │   ├── ErrorMessage
│   │   ├── ClarificationMessage (with clickable options)
│   │   └── SystemMessage
│   ├── TemplateHints (empty state + as-you-type filtering)
│   │   ├── CategoryPills
│   │   └── TemplateRow (icon, text with slots, click-to-fill)
│   ├── SuggestedFollowUps (pill row after each answer)
│   └── InputArea
│       ├── TextInput
│       └── SendButton
│
└── DebugPanel
    ├── DebugHeader (title + close button)
    ├── DebugLogList
    │   └── DebugEntry (expandable, per-step breakdown)
    │       ├── StepInput
    │       ├── StepLLM (tokens, latency, expandable prompt)
    │       ├── StepQuery (ES|QL code block, confidence)
    │       ├── StepValidation (checklist with badges)
    │       ├── StepExecution (status, time, expandable response)
    │       └── StepAnswer (template, metrics, follow-ups)
    └── SessionStatsFooter (avg latency, query count, fallbacks)
```

### 12.6 Color system (light theme)

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#FFFFFF` | Card backgrounds, chat bubbles |
| `--bg-secondary` | `#F8F8F6` | Page background, metric cards, sidebar |
| `--bg-tertiary` | `#F1EFE8` | Code blocks, debug panel bg |
| `--bg-user-bubble` | `#E6F1FB` | User message bubble |
| `--text-primary` | `#1A1A1A` | Headings, primary content |
| `--text-secondary` | `#6B6B6B` | Descriptions, labels |
| `--text-tertiary` | `#9B9B9B` | Placeholders, hints, timestamps |
| `--accent` | `#185FA5` | Links, active states, send button |
| `--accent-light` | `#E6F1FB` | Accent backgrounds |
| `--border` | `#E5E5E3` | Card borders, dividers |
| `--border-hover` | `#C8C8C5` | Hover state borders |
| `--success` | `#0F6E56` | Validation pass, confidence high |
| `--success-bg` | `#E1F5EE` | Success backgrounds |
| `--warning` | `#854F0B` | Validation warning, confidence medium |
| `--warning-bg` | `#FAEEDA` | Warning backgrounds |
| `--error` | `#A32D2D` | Validation fail, errors |
| `--error-bg` | `#FCEBEB` | Error backgrounds |
| `--code-bg` | `#F1F5F9` | ES\|QL code blocks |

### 12.7 Typography

| Element | Font | Size | Weight | Color |
|---------|------|------|--------|-------|
| App title | System sans | 16px | 600 | `--text-primary` |
| Session title | System sans | 13px | 500 | `--text-primary` |
| Session preview | System sans | 12px | 400 | `--text-secondary` |
| Chat message | System sans | 14px | 400 | `--text-primary` |
| Metric number | System sans | 20px | 500 | `--text-primary` |
| Metric label | System sans | 12px | 400 | `--text-secondary` |
| Code (ES\|QL) | Monospace | 12px | 400 | `--text-secondary` |
| Template hint | System sans | 13px | 400 | `--text-primary` |
| Template slot | System sans | 13px | 500 | `#854F0B` on `#FAEEDA` |
| Debug step | System sans | 12px | 400 | `--text-secondary` |
| Category pill | System sans | 12px | 500 | varies by state |
| Timestamp | System sans | 11px | 400 | `--text-tertiary` |

### 12.8 Interaction patterns

#### 12.8.1 Template-to-input flow

```
1. User sees template: "How many {customers} applied in the last {7 days}"
2. User clicks template
3. Input fills with: "How many customers applied in the last 7 days"
4. Cursor auto-focuses in input
5. User optionally edits: "How many customers applied in the last 30 days"
6. User presses Enter
7. Template hints collapse, message appears in chat
```

#### 12.8.2 As-you-type template filtering

```
1. User starts typing: "fail"
2. Template list filters in real-time to show only matching templates:
   - "What is the success vs failure rate {today}"
   - "Are there failure spikes in the last {1 hour}"
   - "Which consumer has the highest failure rate {this week}"
3. User can click a filtered template or keep typing freely
4. If input is cleared, full template list restores
```

#### 12.8.3 Conversation follow-up flow

```
1. Assistant answers with metric cards
2. Below the input, follow-up pills appear:
   [By consumer?] [By app type?] [Show trend?]
3. User clicks "By consumer?"
4. System sends: "{previous question} broken down by consumer"
5. LLM has conversation context, generates grouped ES|QL
6. New answer with per-consumer breakdown appears
```

#### 12.8.4 Error → retry flow

```
1. LLM generates invalid ES|QL
2. Validator catches error
3. System falls back to closest template
4. Chat shows:
   ┌─────────────────────────────────────────────┐
   │ ⚠ I wasn't sure how to answer that exactly, │
   │ so I answered the closest question I could:  │
   │                                              │
   │ "How many customers applied in the last      │
   │  7 days?"                                    │
   │                                              │
   │ [That's right] [Let me rephrase]             │
   └─────────────────────────────────────────────┘
5. Debug panel shows validation failure + fallback details
```

### 12.9 State management

```typescript
interface AppState {
  // Sidebar
  sessions: Session[];
  activeSessionId: string | null;
  sidebarSearch: string;
  sidebarCollapsed: boolean;        // For responsive

  // Chat
  messages: Message[];
  inputValue: string;
  isLoading: boolean;
  templateCategory: string;         // "all" | "volume" | "perf" | etc.
  showTemplates: boolean;           // Hidden after first message in session

  // Debug
  debugOpen: boolean;
  debugEntries: DebugEntry[];

  // Settings
  showESQLPreview: boolean;         // Auto-show ES|QL in assistant bubbles
  defaultTimeRange: string;         // User's preferred default
  llmModel: string;                 // Model selection for NL → ES|QL
}
```

### 12.10 Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift + Enter` | New line in input |
| `Ctrl/Cmd + K` | Focus search in sidebar |
| `Ctrl/Cmd + N` | New session |
| `Ctrl/Cmd + D` | Toggle debug panel |
| `Ctrl/Cmd + E` | Toggle ES\|QL preview in current answer |
| `Ctrl/Cmd + Shift + C` | Copy last ES\|QL query |
| `Esc` | Close debug panel / clear input |
| `↑` (in empty input) | Load last sent message for editing |
