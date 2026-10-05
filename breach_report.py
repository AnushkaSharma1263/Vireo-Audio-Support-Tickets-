#!/usr/bin/env python3
"""Vireo weekly first-response SLA breach report (by agent and shift).

usage: python breach_report.py --tickets tickets.csv --agents agents.csv --out out/
Deterministic pandas only; no LLM / network needed.

Decisions (see README):
 - timestamps in export are UTC -> converted to IST (+5:30) for shift & week
 - duplicate ticket_ids (migration re-import): keep legacy_fd row, drop helpdesk copy
 - breach = first_response - created > channel target (strictly greater)
 - shift = IST hour of ticket CREATION (06-14 Morning, 14-22 Day, 22-06 Night)
 - roster joined as-of the creation date (agents who moved have 2 rows)
 - 'uncovered' breach = ticket created in a shift where no agent of the channel's
   frontline team was rostered that day -> not attributable to any agent
"""
import argparse, os
import numpy as np, pandas as pd

TARGET_MIN = {"chat": 15, "voice": 120, "social": 240, "email": 480}
CH_TEAM = {"chat": "Chat Frontline", "social": "Chat Frontline",
           "email": "Email Frontline", "voice": "Voice Frontline"}
CREDIT = 350
IST = pd.Timedelta(hours=5, minutes=30)

def shift_of_hour(h):
    return np.where((h >= 22) | (h < 6), "Night", np.where(h < 14, "Morning", "Day"))

def load(tickets, agents):
    t = pd.read_csv(tickets, parse_dates=["created_at", "first_response_at"])
    a = pd.read_csv(agents, parse_dates=["from_date", "to_date"])
    n0 = len(t)
    t = t.sort_values("source_system").drop_duplicates("ticket_id", keep="first")  # legacy_fd < helpdesk
    t.attrs["dupes_dropped"] = n0 - len(t)
    return t.copy(), a

def build(t, a):
    t["created_ist"] = t.created_at + IST
    t["wait_min"] = (t.first_response_at - t.created_at).dt.total_seconds() / 60
    t["target_min"] = t.channel.map(TARGET_MIN)
    t["breach"] = t.wait_min > t.target_min
    t["shift"] = shift_of_hour(t.created_ist.dt.hour)
    t["day"] = t.created_ist.dt.normalize()
    t["week"] = (t.day - pd.to_timedelta(t.day.dt.weekday, unit="D")).dt.date  # Monday start
    # roster as-of creation date, for the resolving agent
    r = a.copy(); r["to_date"] = r.to_date.fillna(pd.Timestamp("2099-01-01"))
    m = t[["ticket_id", "agent_id", "day"]].merge(r, on="agent_id")
    m = m[(m.from_date <= m.day) & (m.day <= m.to_date)]
    t = t.merge(m[["ticket_id", "name", "team", "shift", "site"]]
                .rename(columns={"name": "agent", "team": "agent_team", "shift": "agent_shift", "site": "agent_site"}),
                on="ticket_id", how="left")
    # coverage: is any agent of the channel's team on the ticket's shift that day?
    cov = r.assign(k=1)
    days = t[["day"]].drop_duplicates()
    cs = days.assign(k=1).merge(cov, on="k")
    cs = cs[(cs.from_date <= cs.day) & (cs.day <= cs.to_date)]
    covered = set(zip(cs.day, cs.team, cs["shift"]))
    t["covered"] = [(d, CH_TEAM[c], s) in covered for d, c, s in zip(t.day, t.channel, t["shift"])]
    t["breach_type"] = np.where(~t.breach, "", np.where(t.covered, "staffed", "uncovered"))
    return t

def tables(t):
    def agg(g):
        return pd.Series({"tickets": len(g), "breaches": int(g.breach.sum()),
                          "breach_pct": round(100 * g.breach.mean(), 1),
                          "uncovered_breaches": int((g.breach_type == "uncovered").sum()),
                          "staffed_breaches": int((g.breach_type == "staffed").sum()),
                          "staffed_breach_pct": round(100 * (g.breach_type == "staffed").sum() / max(1, g.covered.sum()), 1),
                          "credit_inr": int(g.breach.sum()) * CREDIT})
    by_shift = t.groupby(["week", "shift"]).apply(agg, include_groups=False).reset_index()
    by_agent = t.groupby(["week", "agent_id", "agent", "agent_team", "agent_shift"]).apply(agg, include_groups=False).reset_index()
    by_ch = t.groupby(["week", "shift", "channel"]).apply(agg, include_groups=False).reset_index()
    return by_shift, by_agent, by_ch

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tickets", required=True); p.add_argument("--agents", required=True)
    p.add_argument("--out", default="out")
    x = p.parse_args(); os.makedirs(x.out, exist_ok=True)
    t, a = load(x.tickets, x.agents); dropped = t.attrs["dupes_dropped"]
    t = build(t, a)
    s, ag, ch = tables(t)
    s.to_csv(f"{x.out}/weekly_by_shift.csv", index=False)
    ag.to_csv(f"{x.out}/weekly_by_agent.csv", index=False)
    ch.to_csv(f"{x.out}/weekly_by_shift_channel.csv", index=False)
    t[["ticket_id", "created_ist", "channel", "wait_min", "target_min", "breach", "breach_type", "shift", "covered",
       "agent_id", "agent", "agent_shift"]].to_csv(f"{x.out}/ticket_level.csv", index=False)
    tot = t.groupby("shift").apply(lambda g: pd.Series({"tickets": len(g), "breaches": int(g.breach.sum()),
          "uncovered": int((g.breach_type == "uncovered").sum())}), include_groups=False)
    print(f"tickets={len(t)} dupes_dropped={dropped} breaches={int(t.breach.sum())} "
          f"({100*t.breach.mean():.1f}%) uncovered={int((t.breach_type=='uncovered').sum())}")
    print(tot); print(f"files written to {x.out}/")

if __name__ == "__main__":
    main()
