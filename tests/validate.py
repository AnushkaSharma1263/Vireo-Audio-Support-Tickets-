"""Independent check: recompute breaches in SQLite (different code path, no pandas shift/roster logic)
and compare to the tool's ticket_level.csv. Plus edge-case unit tests. Run: python tests/validate.py TICKETS AGENTS OUT"""
import sys, sqlite3, csv, pandas as pd, io
sys.path.insert(0, ".")
import breach_report as b

def sqlite_check(tickets, out):
    con = sqlite3.connect(":memory:")
    pd.read_csv(tickets).to_sql("t", con, index=False)
    q = """
    WITH d AS (SELECT * FROM t WHERE rowid IN (SELECT MIN(rowid) FROM t GROUP BY ticket_id
               HAVING 1) OR 0)
    SELECT ticket_id, channel, created_at, first_response_at, source_system FROM t"""
    df = pd.read_sql(q, con)
    # keep legacy_fd row if duplicated
    df["pri"] = (df.source_system != "legacy_fd").astype(int)
    df.to_sql("u", con, index=False, if_exists="replace")
    r = con.execute("""
      SELECT ticket_id,
        CASE channel WHEN 'chat' THEN 15 WHEN 'voice' THEN 120 WHEN 'social' THEN 240 ELSE 480 END AS tgt,
        (julianday(first_response_at)-julianday(created_at))*1440 AS wait,
        CAST(strftime('%H', datetime(created_at,'+330 minutes')) AS INT) AS h
      FROM u WHERE rowid IN (SELECT rowid FROM u x WHERE pri=(SELECT MIN(pri) FROM u y WHERE y.ticket_id=x.ticket_id)
                              AND rowid=(SELECT MIN(rowid) FROM u z WHERE z.ticket_id=x.ticket_id AND z.pri=x.pri))""").fetchall()
    sq = pd.DataFrame(r, columns=["ticket_id", "tgt", "wait", "h"])
    sq["breach_sql"] = sq.wait.round(3) > sq.tgt
    sq["shift_sql"] = sq.h.map(lambda h: "Night" if h >= 22 or h < 6 else ("Morning" if h < 14 else "Day"))
    tool = pd.read_csv(out + "/ticket_level.csv")
    m = tool.merge(sq, on="ticket_id")
    print("rows tool/sql/joined:", len(tool), len(sq), len(m))
    print("breach mismatches:", int((m.breach != m.breach_sql).sum()))
    print("shift mismatches:", int((m["shift"] != m.shift_sql).sum()))

def unit():
    # boundary: exactly at target is NOT a breach; 1 min over IS
    t = pd.DataFrame({"ticket_id": ["a", "b", "c"], "channel": ["chat"] * 3, "source_system": ["helpdesk"] * 3,
        "created_at": pd.to_datetime(["2025-08-01 16:30"] * 3),   # 22:00 IST -> Night
        "first_response_at": pd.to_datetime(["2025-08-01 16:45", "2025-08-01 16:46", "2025-08-01 16:44"]),
        "agent_id": ["A3004"] * 3})
    a = pd.read_csv(sys.argv[2], parse_dates=["from_date", "to_date"])
    r = b.build(t.copy(), a)
    assert list(r.breach) == [False, True, False], r.breach.tolist()
    assert (r["shift"] == "Night").all()          # 16:30 UTC == 22:00 IST
    t2 = t.copy(); t2["created_at"] = pd.to_datetime(["2025-08-01 16:29"] * 3)
    assert (b.build(t2, a)["shift"] == "Day").all()   # 21:59 IST
    # roster as-of: A3002 Night until 29 Jun 2025, Day from 30 Jun
    for day, exp in [("2025-06-29 10:00", "Night"), ("2025-06-30 10:00", "Day")]:
        x = t.iloc[:1].copy(); x["agent_id"] = "A3002"; x["created_at"] = pd.to_datetime([day]); x["first_response_at"] = x.created_at
        assert b.build(x, a).agent_shift.iloc[0] == exp
    print("unit tests passed")

if __name__ == "__main__":
    unit(); sqlite_check(sys.argv[1], sys.argv[3])
