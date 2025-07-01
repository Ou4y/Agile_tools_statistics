import pandas as pd
import csv
import sys

# Allow large text fields
csv.field_size_limit(sys.maxsize)

# Helper function to load a CSV file in chunks
def load_csv_in_chunks(filepath, usecols):
    chunks = pd.read_csv(
        filepath,
        usecols=usecols,
        chunksize=10000,
        engine='python',
        dtype=str  # Treat all columns as strings to avoid parsing errors
    )
    return pd.concat(chunks)

# === 1. Load issues.csv ===
print("Loading issues.csv...")
issues = load_csv_in_chunks('issues.csv', usecols=['key', 'created', 'reporter'])
issues = issues.rename(columns={'key': 'issue_id', 'created': 'account_created', 'reporter': 'user'})

# === 2. Load changelog.csv ===
print("Loading changelog.csv...")
changelog = load_csv_in_chunks('changelog.csv', usecols=['key', 'author', 'created', 'field'])
moves = changelog[changelog['field'] == 'status'].copy()
moves['action'] = 'move'
moves['comment'] = ''
moves = moves.rename(columns={'key': 'issue_id', 'author': 'user', 'created': 'date'})

# Add account_created to moves
moves = moves.merge(issues[['issue_id', 'user', 'account_created']], on=['issue_id', 'user'], how='left')

# === 3. Load comments.csv ===
print("Loading comments.csv...")
comments = load_csv_in_chunks('comments.csv', usecols=['key', 'comment.author', 'comment.created', 'comment.body'])
comments = comments.rename(columns={
    'key': 'issue_id',
    'comment.author': 'user',
    'comment.created': 'date',
    'comment.body': 'comment'
})
comments['action'] = ''

# Add account_created to comments
comments = comments.merge(issues[['issue_id', 'user', 'account_created']], on=['issue_id', 'user'], how='left')

# === 4. Combine moves + comments ===
print("Combining and cleaning...")
activity = pd.concat([moves[['user','date','action','comment','account_created']],
                      comments[['user','date','action','comment','account_created']]])
activity = activity.dropna(subset=['user','date'])

# === 5. Save the final CSV ===
output_file = 'activity_log.csv'
activity.to_csv(output_file, index=False)
print(f"\n✅ Saved: {output_file}")