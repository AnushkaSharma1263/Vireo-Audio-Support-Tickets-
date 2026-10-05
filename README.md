# Vireo SLA breach report

Clean-machine run (Python 3.10+, pandas only):

    pip install pandas
    python breach_report.py --tickets tickets.csv --agents agents.csv --out out/
    python tests/validate.py tickets.csv agents.csv out     # independent SQLite check + unit tests

Outputs in `out/`: `weekly_by_shift.csv`, `weekly_by_agent.csv`, `weekly_by_shift_channel.csv`, `ticket_level.csv`.
Every breach is labelled `staffed` (agent-addressable) or `uncovered` (created in a shift where no agent of that
channel's team was rostered that day). Reports show both, so an agent is never judged on uncovered breaches.

## Decisions I made (no one to ask)
1. Export timestamps = UTC (Sameer's email); converted +5:30 to IST. Evidence: after conversion, breach rate is flat ~8-9%
   from 06:00-21:59 IST and jumps to ~80% at 22:00 sharp. Nothing else produces a cliff on the policy's shift boundary.
2. Duplicates (616 ticket_ids, legacy_fd + helpdesk re-import): keep the legacy row, drop the helpdesk copy. Rows were identical except csat.
3. Breach = wait strictly greater than target (15m chat / 2h voice / 4h social / 8h email). Calendar time, not business hours (policy sec. 3 says measured from creation).
4. Shift = shift in which the ticket was CREATED (when it started waiting), not the resolver's shift.
5. Agent = resolving agent (the only agent id in the export; policy says helpdesk reports use it). No first-responder id exists, so
   per-agent numbers are a proxy. Tier 2 shown but not comparable on volume (policy sec. 6).
6. Voice treated as covered by Voice Frontline, since voice callbacks only run 08:00-22:00 IST.
7. Left out: CSAT, refunds/replacements, IVR free-text, handle time, legacy money units. None is needed for the breach question.
