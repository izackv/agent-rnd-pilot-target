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

// Role travels in the X-Role header, never in the URL: a navigation or `<a href download>` sends no
// custom header, so an anchor control would download the viewer file for an admin too. A role in the
// query string would be a second permission door and a shareable widening link (contract §1).
async function exportCsv() {
  const role = document.getElementById("role").value;
  const status = document.getElementById("status");
  let res;
  try {
    res = await fetch("/api/reports.csv", { headers: { "X-Role": role } });
  } catch {
    status.textContent = EXPORT_FAILED;
    return;
  }
  if (!res.ok) { status.textContent = EXPORT_FAILED; return; }
  const text = await res.text();
  // The BOM is client-side only; the API bytes carry none. The downloaded file and the response
  // differ by exactly the leading EF BB BF, and that is intended (contract §4, [D-3]).
  const blob = new Blob(["\ufeff" + text], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filenameFrom(res.headers.get("Content-Disposition")) ?? "reports.csv";
  a.click();
  URL.revokeObjectURL(url);
}

document.getElementById("role").addEventListener("change", load);
document.getElementById("export").addEventListener("click", exportCsv);
load();
