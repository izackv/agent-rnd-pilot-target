async function load() {
  const role = document.getElementById("role").value;
  const status = document.getElementById("status");
  status.textContent = "Loading…";
  const res = await fetch("/api/reports", { headers: { "X-Role": role } });
  const tbody = document.querySelector("#reports tbody");
  tbody.innerHTML = "";
  if (!res.ok) { status.textContent = `Error ${res.status}`; return; }
  const rows = await res.json();
  for (const r of rows) {
    const tr = document.createElement("tr");
    tr.dataset.id = r.id;
    tr.innerHTML = `<td>${r.id}</td><td>${r.title}</td><td>${r.owner}</td><td>${r.rows}</td>`;
    tbody.appendChild(tr);
  }
  status.textContent = rows.length ? `${rows.length} reports` : "No reports";
}
// D-13 failure copy. Written to #status on click only: tests/e2e/test_journey.py asserts #status
// reads exactly "3 reports" on load, so nothing export-related may touch it before a click.
const EXPORT_FAILED = "Export failed. Please try again.";

// The server emits `attachment; filename="reports-YYYY-MM-DD.csv"` and, the name being ASCII, no
// RFC 5987 `filename*`. The unquoted branch and the null return are fallbacks for a missing or
// unparseable header; the response's name is authoritative whenever it is present (contract §1.3).
function filenameFrom(disposition) {
  if (!disposition) return null;
  const match = /filename="([^"]*)"|filename=([^;]*)/i.exec(disposition);
  if (!match) return null;
  return (match[1] ?? match[2]).trim() || null;
}

// Firefox and WebKit have historically required the download anchor to be in the document when
// clicked and the object URL to be revoked on a later task; Chromium needs neither precaution.
// Taking both is free, and it keeps a one-engine verification from reading as a portability claim
// (contract §1, [E-3]).
function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

// Role travels in the X-Role header, never in the URL: a navigation or `<a href download>` sends no
// custom header, so an anchor control would download the viewer file for an admin too. A role in the
// query string would be a second permission door and a shareable widening link (contract §1).
async function exportCsv() {
  const role = document.getElementById("role").value;
  const status = document.getElementById("status");
  // One guarded region. The body read can reject after the response headers have arrived, so it and
  // the file build sit inside the try rather than after it (contract §1 [E-2], §7 UI rows).
  try {
    const res = await fetch("/api/reports.csv", { headers: { "X-Role": role } });
    if (!res.ok) {
      // The HTTP arm shows the same copy as the throw path below, and it is the likeliest real
      // failure (a 403 from the role guard, a 500 from the serializer), so it needs the same
      // diagnosability. Status line only: the response body, the Content-Disposition value and the
      // selected role must not reach the console.
      console.error("CSV export failed: HTTP", res.status, res.statusText);
      status.textContent = EXPORT_FAILED;
      return;
    }
    const text = await res.text();
    // The BOM is client-side only; the API bytes carry none. The downloaded file and the response
    // differ by exactly the leading EF BB BF, and that is intended (contract §4, [D-3]).
    const blob = new Blob(["\ufeff" + text], { type: "text/csv;charset=utf-8" });
    triggerDownload(blob, filenameFrom(res.headers.get("Content-Disposition")) ?? "reports.csv");
    // F-1: a succeeding export used to leave an earlier click's EXPORT_FAILED copy standing in
    // #status forever. Restore the steady state `load()` would have left instead of clearing or
    // announcing: the write is *idempotent*, so on a first-click success #status is byte-identical
    // and AC-1's negative half still holds (tests/e2e/test_export.py
    // ::test_page_state_is_unchanged_after_export asserts text equality, not absence of a write).
    // The string must stay in lockstep with the one line 16 produces, or that guard fails.
    // Deliberately not an announcement: whether a success should reach assistive tech is F-2, open
    // as AGE-42, and differing text here would break AC-1.
    const rows = document.querySelectorAll("#reports tbody tr");
    status.textContent = rows.length ? `${rows.length} reports` : "No reports";
  } catch (err) {
    // Every failure mode in this region reaches the same user-facing copy (contract §1 point 6), so
    // the cause — a dropped connection, a decode error, a Content-Length mismatch — is only
    // recoverable from the console. Log it so a field report of "the export says it failed" is
    // diagnosable; the #status copy below is unchanged (contract §7).
    console.error("CSV export failed", err);
    status.textContent = EXPORT_FAILED;
  }
}

document.getElementById("role").addEventListener("change", load);
document.getElementById("export").addEventListener("click", exportCsv);
load();
