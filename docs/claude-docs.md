# The Claude Docs copy (optional)

If you use Claude Docs, Perkins can keep a copy of your master resume and each tailored resume there too. That gives you a nicer editor, a resume tab you can share and get comments on (from a referrer or a coach, say), and export to Word or Google Docs when an employer's form wants a `.docx`.

Markdown stays the record. The Docs copy follows it.

## Turn it on

1. Create a Claude Docs doc for your resumes (any title), and copy its id from its link.
2. In `perkins.toml`, set:

   ```toml
   docs_mirror = true
   docs_id = "<the doc's id>"
   ```

3. Have the Claude Docs connector enabled in your Claude Code session.

## How the two copies stay equal

- **One write path.** Every change goes to the Markdown file first, then the same text goes to its Docs tab in the same run. Nothing edits one copy alone. The master resume's tab is named "Master resume"; each tailored resume's tab is "<Company> · <Role>".
- **Check before reading, check after writing.** Before tailoring, Perkins exports the master's tab as Markdown and compares it with `master.md`. After writing a tab, it compares that tab with its file. The comparison ignores line endings and trailing spaces, nothing else.
- **A difference stops the run.** Perkins shows the lines that differ and asks you which copy is right. It never picks one itself.

If you edit only through Perkins, the two never drift and the check is just a backstop. If you edit a tab by hand, the next run will catch it.

## Under the hood

The connector's export arrives inside the Claude Code session, so `run.py sync-check` reads it from the session's transcript rather than having anyone retype it. That transcript format belongs to Claude Code and may change. If it does, the check reports the export as missing and stops. It never reports a false match.

```
python run.py sync-check --pair "Master resume=master.md"
python run.py sync-check --compare a.md b.md
```
