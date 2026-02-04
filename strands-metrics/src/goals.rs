use anyhow::Result;
use rusqlite::{params, Connection};
use serde::Deserialize;
use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Debug, Deserialize)]
#[serde(untagged)]
enum GoalEntry {
    Simple(f64),
    WithLabel { value: f64, label: String },
}

#[derive(Debug, Deserialize)]
struct GoalsConfig {
    goals: HashMap<String, GoalEntry>,
}

pub fn init_goals_table(conn: &Connection) -> Result<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS goals (
            metric TEXT PRIMARY KEY,
            value REAL NOT NULL,
            label TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )",
        [],
    )?;
    // Add label column if it doesn't exist (migration for existing DBs)
    let _ = conn.execute("ALTER TABLE goals ADD COLUMN label TEXT", []);
    Ok(())
}

pub fn load_goals<P: AsRef<Path>>(conn: &Connection, yaml_path: P) -> Result<usize> {
    let content = fs::read_to_string(yaml_path)?;
    let config: GoalsConfig = serde_yaml::from_str(&content)?;

    let mut count = 0;
    for (metric, entry) in config.goals {
        let (value, label) = match entry {
            GoalEntry::Simple(v) => (v, None),
            GoalEntry::WithLabel { value, label } => (value, Some(label)),
        };
        conn.execute(
            "INSERT INTO goals (metric, value, label, updated_at)
             VALUES (?1, ?2, ?3, datetime('now'))
             ON CONFLICT(metric) DO UPDATE SET
                value = excluded.value,
                label = excluded.label,
                updated_at = datetime('now')",
            params![metric, value, label],
        )?;
        count += 1;
    }

    Ok(count)
}

pub fn get_goal(conn: &Connection, metric: &str) -> Result<Option<f64>> {
    let result = conn.query_row(
        "SELECT value FROM goals WHERE metric = ?1",
        params![metric],
        |row| row.get(0),
    );

    match result {
        Ok(value) => Ok(Some(value)),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
        Err(e) => Err(e.into()),
    }
}

pub fn list_goals(conn: &Connection) -> Result<Vec<(String, f64, Option<String>)>> {
    let mut stmt = conn.prepare("SELECT metric, value, label FROM goals ORDER BY metric")?;
    let rows = stmt.query_map([], |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)))?;

    let mut goals = Vec::new();
    for row in rows {
        goals.push(row?);
    }
    Ok(goals)
}

pub fn get_goals_map(conn: &Connection) -> Result<HashMap<String, (f64, String)>> {
    let mut stmt = conn.prepare("SELECT metric, value, label FROM goals")?;
    let rows = stmt.query_map([], |row| {
        let metric: String = row.get(0)?;
        let value: f64 = row.get(1)?;
        let label: Option<String> = row.get(2)?;
        Ok((metric, value, label.unwrap_or_else(|| "Goal".to_string())))
    })?;

    let mut map = HashMap::new();
    for row in rows {
        let (metric, value, label) = row?;
        map.insert(metric, (value, label));
    }
    Ok(map)
}
