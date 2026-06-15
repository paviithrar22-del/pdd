import sqlite3
conn = sqlite3.connect('cybershield.db')
c = conn.cursor()

# Remove bad violations (numeric IDs, 'Active', dots)
bad_identifiers = ['Active', '......', '17846298465389613', '17849292590709077']
for bad in bad_identifiers:
    deleted = c.execute("DELETE FROM violations WHERE user_identifier = ?", (bad,)).rowcount
    print(f"Deleted {deleted} violations for '{bad}'")

# Also clear moderation_results that are linked to old bad data
# (we wipe all - comments will be freshly scraped)
c.execute("DELETE FROM moderation_results")
print(f"Cleared all moderation_results for fresh analysis")

# Clear all comments too (they were never scraped correctly)
c.execute("DELETE FROM comments")
print("Cleared all comments for fresh scrape")

conn.commit()
print("\nRemaining violations by user:")
for r in c.execute("SELECT user_identifier, COUNT(*) FROM violations GROUP BY user_identifier").fetchall():
    print(f"  {r[0]}: {r[1]} violations")
conn.close()
print("Done.")
