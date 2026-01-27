"""Re-score all domains with the new euphony-aware scoring system."""
import sqlite3
from src.scoring.scorer import DomainScorer

# Connect to database
db = sqlite3.connect('data/results/domains.db')
cursor = db.cursor()

# Initialize scorer
scorer = DomainScorer()

# Fetch all domains
cursor.execute('SELECT domain FROM domains')
domains = [row[0] for row in cursor.fetchall()]

print(f"Re-scoring {len(domains)} domains...")

# Collect all updates into a list for batch processing
update_data = []
for i, domain in enumerate(domains):
    score = scorer.score(domain)
    update_data.append((
        score.total_score,
        score.pronounceability,
        score.spellability,
        score.length_score,
        score.memorability,
        score.brandability,
        score.dictionary_score,
        score.euphony,
        score.tld_multiplier,
        domain
    ))

    # Show progress every 100 domains
    if (i + 1) % 100 == 0:
        print(f"  Progress: {i + 1}/{len(domains)} domains scored...")

# Batch update all domains at once
cursor.executemany('''
    UPDATE domains SET
        total_score = ?,
        pronounceability = ?,
        spellability = ?,
        length_score = ?,
        memorability = ?,
        brandability = ?,
        dictionary_score = ?,
        euphony = ?,
        tld_multiplier = ?
    WHERE domain = ?
''', update_data)

db.commit()
print(f"✓ Re-scored {len(domains)} domains")

# Show top 30 available .com domains
print("\n=== TOP 30 AVAILABLE .COM DOMAINS ===")
cursor.execute('''
    SELECT domain, total_score, euphony, dictionary_score as meaning, brandability, memorability
    FROM domains
    WHERE available = 1 AND tld = 'com'
    ORDER BY total_score DESC
    LIMIT 30;
''')
results = cursor.fetchall()
for i, row in enumerate(results, 1):
    domain, total, euphony, meaning, brand, mem = row
    print(f"{i:2d}. {domain:30s} | Total: {total:5.1f} | Euphony: {euphony:3d} | Meaning: {meaning:3d} | Brand: {brand:3d} | Mem: {mem:3d}")

# Show examples of high euphony domains (not necessarily real words)
print("\n=== HIGH EUPHONY DOMAINS (not real words) ===")
cursor.execute('''
    SELECT domain, euphony, total_score, dictionary_score
    FROM domains
    WHERE euphony >= 70 AND dictionary_score < 85
    ORDER BY euphony DESC, total_score DESC
    LIMIT 15;
''')
results = cursor.fetchall()
for i, row in enumerate(results, 1):
    domain, euphony, total, meaning = row
    print(f"{i:2d}. {domain:30s} | Euphony: {euphony:3d} | Total: {total:5.1f} | Meaning: {meaning:3d}")

db.close()
print("\n✓ Database update complete!")
