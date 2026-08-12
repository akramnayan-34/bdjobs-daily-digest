"""
Builds the Telegram Markdown message from validated, structured job results.
The LLM never writes this text directly -- this keeps formatting,
links, and deadlines under the code's control instead of the model's.
"""

from datetime import date

MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
MAX_SHORTLIST = 10
MIN_SHORTLIST = 5
MAX_EXCLUDED_SHOWN = 3
CHUNK_LIMIT = 4000


def build_digest_text(scored_results: list) -> str:
    eligible = [r for r in scored_results
                if r["eligibility_status"] == "ELIGIBLE"
                and r.get("total_score") is not None]
    eligible = _dedupe_by_group(eligible)
    eligible.sort(key=lambda r: r["total_score"], reverse=True)
    eligible = [r for r in eligible if r["total_score"] >= 70][:MAX_SHORTLIST]

    excluded = [r for r in scored_results
                if r["eligibility_status"] == "INELIGIBLE"][:MAX_EXCLUDED_SHOWN]
    unverified_count = sum(1 for r in scored_results
                            if r["eligibility_status"] == "UNVERIFIED")

    if not eligible:
        body = "No jobs cleared the eligibility + quality bar today."
        if unverified_count:
            body += (f"\n\n{unverified_count} job(s) could not be fully "
                     f"verified (incomplete description data) and were "
                     f"excluded from the shortlist pending manual review.")
        return f"🔥 DAILY PERSONALIZED JOB SHORTLIST\n{date.today():%d %b %Y}\n\n{body}"

    lines = [f"🔥 DAILY PERSONALIZED JOB SHORTLIST",
             f"{date.today():%d %b %Y}", ""]

    if len(eligible) < MIN_SHORTLIST:
        lines.append(f"(Only {len(eligible)} job(s) met the 70+ quality "
                      f"bar today -- showing all of them.)\n")

    for idx, r in enumerate(eligible):
        meta = r["_job_meta"]
        medal = MEDALS[idx] if idx < len(MEDALS) else f"{idx + 1}."
        lines.append(f"{medal} {meta.get('company', 'Unknown Org')} — "
                      f"{meta.get('title', 'Unknown Title')}")
        lines.append(f"📍 {meta.get('location', 'N/A')}")
        lines.append(f"⏰ Deadline: {meta.get('deadline') or 'Not stated'}")
        lines.append(f"🎯 Fit: {r['total_score']}%")
        lines.append(f"📈 Shortlist: {r.get('shortlist_probability') or 'N/A'}")
        lines.append(f"🚀 Career value: {r.get('career_value') or 'N/A'}")
        lines.append("")
        lines.append("WHY:")
        for reason in r.get("eligibility_reasons", [])[:3]:
            lines.append(f"- {reason}")
        if r.get("gaps"):
            lines.append("")
            lines.append("GAP:")
            for gap in r["gaps"][:3]:
                lines.append(f"- {gap}")
        lines.append("")
        lines.append(f"VERDICT: {_verdict_emoji(r['verdict'])} {r['verdict']}")
        lines.append("")
        lines.append(f"🔗 Application: {meta.get('url', 'N/A')}")
        lines.append("")

    if excluded:
        lines.append("❌ IMPORTANTLY EXCLUDED")
        lines.append("")
        for r in excluded:
            meta = r["_job_meta"]
            reason = r.get("eligibility_reasons", ["Not eligible"])[0]
            lines.append(f"❌ {meta.get('company', 'Unknown Org')} — "
                          f"{meta.get('title', 'Unknown Title')}")
            lines.append(f"Reason: {reason}")
            lines.append("")

    if unverified_count:
        lines.append(f"ℹ️ {unverified_count} additional job(s) could not be "
                      f"fully verified (incomplete data) and were withheld "
                      f"from the shortlist pending manual review.")

    return "\n".join(lines)


def _dedupe_by_group(eligible: list) -> list:
    """When several eligible jobs share a duplicate_group (same org +
    project + location), keep only the highest-scoring one."""
    best_by_group = {}
    ungrouped = []
    for r in eligible:
        group = r.get("duplicate_group")
        if not group:
            ungrouped.append(r)
            continue
        current_best = best_by_group.get(group)
        if not current_best or r["total_score"] > current_best["total_score"]:
            best_by_group[group] = r
    return ungrouped + list(best_by_group.values())


def _verdict_emoji(verdict: str) -> str:
    return {"APPLY FIRST": "🔥", "CONSIDER": "👍"}.get(verdict, "")


def chunk_message(text: str, limit: int = CHUNK_LIMIT) -> list:
    """Split on job-entry boundaries (blank lines) rather than raw
    character count, so Markdown formatting never breaks mid-token."""
    if len(text) <= limit:
        return [text]

    blocks = text.split("\n\n")
    chunks, current = [], ""
    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) > limit and current:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks

