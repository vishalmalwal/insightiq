# InsightIQ — 60–90s demo script

A tight walkthrough that finds **two planted insights** on the sample data: the
**Tier-2 Q3 revenue dip** (e-commerce) and the **92-day churn cliff** (SaaS).
Record at 1280×800, dark mode, reduced-motion off. Times are cumulative.

---

### 0:00–0:08 — Hook (hero)

**On screen:** Live demo loads on the e-commerce project; the aurora hero and Ask
bar are centered; sample-question chips visible.

**Say:** "This is InsightIQ. You ask a question in plain English, and it plans the
queries, writes safe SQL, and builds a whole dashboard. Watch."

---

### 0:08–0:22 — The resolving-dashboard moment

**Do:** Click the chip **"compare monthly revenue by region this year vs last year
and show top products."**

**On screen:** The Ask bar collapses to the top; cards animate into a grid —
a monthly revenue-by-region comparison and a top-categories bar.

**Say:** "One question became a multi-chart dashboard. Every query was generated
through a semantic layer, so it joined orders to customers correctly and never
touched a column that doesn't exist."

---

### 0:22–0:45 — Insight #1: the Tier-2 Q3 dip

**Do:** In the Ask bar type **"revenue by city tier over time"** and hit Ask.

**On screen:** A trend with a line per city tier. Point the cursor at Q3.

**Say:** "Here's something a single chart would hide. Tier-1 cities hold steady
all year — but Tier-2 revenue *collapses in Q3*, to about a third of its own
baseline, then recovers. That's a real seasonal-demand story planted in the data,
and the dashboard surfaces it in one question."

**Do:** Open the **View SQL** drawer on that card for a beat.

**Say:** "And you can always see the exact SQL behind any card."

---

### 0:45–1:08 — Insight #2: the 92-day churn cliff

**Do:** Switch to the **sample-saas** project (top nav). Ask **"number of accounts
by plan"**, then **"mrr by plan."**

**On screen:** Two clean breakdowns across Basic / Pro / Enterprise.

**Say:** "Switching to the SaaS dataset. Basic, Pro, Enterprise — nothing alarming
yet. But the interesting story is churn timing."

**Do:** (Optional, if a churn view is configured) mention the seeded fact directly.

**Say:** "Accounts don't churn randomly — they churn in a sharp band around a
**92-day** median, and churn is heavily concentrated in the Basic plan at about
**45%**, versus **10%** for Enterprise. That 'churn cliff' is exactly the kind of
retention signal a founder needs, and it's one question away."

---

### 1:08–1:22 — Proof: the eval tab

**Do:** Click the **Evals** tab. Click **Run suite**.

**On screen:** Metric cards fill in — execution accuracy, valid-SQL rate — and a
per-case pass/fail table.

**Say:** "And because 'looks right' isn't good enough, there's an eval suite. It
runs the whole pipeline against hand-written gold queries. The deterministic
planner clears every clear case — the CI regression gate — and *deliberately*
fails the hard ones, so the number actually means something."

---

### 1:22–1:30 — Close

**On screen:** Back to a dashboard; hover a card.

**Say:** "Semantic layer, multi-query planning, a real safety boundary, and an
eval you can trust — InsightIQ. Link in the description."

---

## Shot list / b-roll

- Hero with the aurora Ask bar (0:00)
- Grid animating into place (0:15)
- Cursor tracing the Q3 dip on the city-tier trend (0:35)
- View-SQL drawer sliding in (0:42)
- Plan breakdown bars, SaaS (0:50)
- Evals metric cards + pass/fail table (1:12)

## Notes

- The Tier-2 Q3 dip and the 92-day churn cliff are deterministic (seed-fixed), so
  they look identical on every capture.
- If recording the hosted demo, warm the Render API with one request first to
  avoid the cold-start delay on camera.
